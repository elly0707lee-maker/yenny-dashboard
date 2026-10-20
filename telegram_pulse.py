"""
텔레 이슈 크로스체크 (Telegram Pulse)
- 여러 텔레 채널을 t.me/s/{channel} 스크래핑
- Claude로 공통 이슈 추출 (2개 채널 이상 언급된 것)
- 관련 링크 자동 첨부
"""
import os
import asyncio
import aiohttp
import re
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from anthropic import Anthropic

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# 예니가 참고하는 채널들 (기본값)
BASE_CHANNELS = [
    "GoUpstock", "FastStockNews", "YeouidoStory2", "tazastock",
    "valjuman", "JCxTB", "HANAchina", "jeilstock", "bornlupin",
    "Yeouido_Lab", "psychotherapy101", "newszzang",
    "aetherjapanresearch", "fundeasy_choi", "HI_GS",
    "stock_messenger", "EMchina", "selfstudyview",
]


def _env_channels(key: str) -> list:
    """환경변수로 채널 추가/제외 — 콤마나 줄바꿈 구분, @ 붙여도 됨."""
    raw = os.environ.get(key, "") or ""
    out = []
    for tok in re.split(r"[,\s]+", raw):
        tok = tok.strip().lstrip("@").strip()
        if tok.startswith("http"):
            tok = tok.rstrip("/").split("/")[-1]
        if tok:
            out.append(tok)
    return out


def _resolve_channels() -> list:
    """TG_CHANNELS가 있으면 그걸로 완전 교체, 없으면 기본 + TG_CHANNELS_ADD - TG_CHANNELS_SKIP."""
    override = _env_channels("TG_CHANNELS")
    base = override if override else list(BASE_CHANNELS) + _env_channels("TG_CHANNELS_ADD")
    skip = {c.lower() for c in _env_channels("TG_CHANNELS_SKIP")}
    seen, out = set(), []
    for c in base:
        k = c.lower()
        if k in seen or k in skip:
            continue
        seen.add(k)
        out.append(c)
    return out


CHANNELS = _resolve_channels()

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# ── 채널 스크래핑 ─────────────────────────────
async def fetch_channel(channel: str, hours: int = 12) -> dict:
    """한 채널의 최근 hours 시간 메시지 스크래핑."""
    url = f"https://t.me/s/{channel}"
    headers = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"}

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    messages = []

    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    print(f"[tgpulse] @{channel} HTTP {r.status}")
                    return {"channel": channel, "messages": [], "error": f"HTTP {r.status}"}
                html = await r.text()
                soup = BeautifulSoup(html, "html.parser")

                for msg_el in soup.select(".tgme_widget_message"):
                    # 시간
                    time_el = msg_el.select_one("time")
                    if not time_el or not time_el.get("datetime"):
                        continue
                    try:
                        dt = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
                    except Exception:
                        continue
                    if dt < cutoff:
                        continue

                    # 본문
                    text_el = msg_el.select_one(".tgme_widget_message_text")
                    if not text_el:
                        continue
                    text = text_el.get_text("\n", strip=True)
                    if not text or len(text) < 5:
                        continue

                    # 링크 추출 (본문 안 링크)
                    links = []
                    for a in text_el.select("a[href]"):
                        href = a.get("href", "")
                        if not href or href.startswith("tg://") or href.startswith("?"):
                            continue
                        if href.startswith("/"):
                            href = "https://t.me" + href
                        if href not in links:
                            links.append(href)

                    # 원본 메시지 링크
                    msg_link_el = msg_el.select_one("a.tgme_widget_message_date")
                    msg_link = msg_link_el.get("href", "") if msg_link_el else ""

                    messages.append({
                        "text": text[:500],
                        "time": dt.isoformat(),
                        "links": links[:3],
                        "msg_url": msg_link,
                    })

        print(f"[tgpulse] @{channel}: {len(messages)}개")
        return {"channel": channel, "messages": messages}
    except Exception as e:
        print(f"[tgpulse] @{channel} 에러: {e}")
        return {"channel": channel, "messages": [], "error": str(e)[:100]}


async def fetch_all_channels(hours: int = 12) -> list:
    """모든 채널 병렬 fetch"""
    tasks = [fetch_channel(c, hours) for c in CHANNELS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            out.append({"channel": CHANNELS[i], "messages": [], "error": str(r)[:80]})
        else:
            out.append(r)
    return out


# ── Claude 분석 ─────────────────────────────
# 공시·중대 신호 키워드
DISCLOSURE_WORDS = [
    "유상증자", "무상증자", "자사주", "소각", "분할", "합병", "인수",
    "상장폐지", "거래정지", "감자", "전환사채", "신주인수권", "공시",
    "공급계약", "수주", "계약 체결", "지분", "최대주주", "임상", "승인",
    "허가", "특허", "횡령", "배임", "불성실공시", "관리종목",
]


def _detect_kind(text: str) -> str:
    """메시지 성격 — 공시 / 시황 / 뉴스"""
    t = text or ""
    if any(w in t for w in DISCLOSURE_WORDS):
        return "disclosure"
    if any(w in t for w in ("코스피", "코스닥", "지수", "환율", "선물", "개장", "마감")):
        return "market"
    return "news"


def _salvage_issues(raw: str) -> list:
    """잘린 JSON에서도 완성된 이슈 객체만 건져낸다."""
    import json as _json
    out, stack, instr, esc = [], [], False, False
    for i, ch in enumerate(raw):
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
            continue
        if ch == '"':
            instr = True
        elif ch == "{":
            stack.append(i)
        elif ch == "}" and stack:
            st = stack.pop()
            try:
                o = _json.loads(raw[st:i + 1])
            except Exception:
                continue
            if isinstance(o, dict) and str(o.get("title") or "").strip():
                out.append(o)
    return out


def _norm_title(t: str) -> str:
    return re.sub(r"[\s\W_]+", "", (t or "").lower())[:20]


def _shard(channel_data: list, n: int) -> list:
    """메시지 수가 고르게 퍼지도록 채널을 n조각으로."""
    live = [c for c in channel_data if not c.get("error") and c.get("messages")]
    live.sort(key=lambda c: -len(c["messages"]))
    groups = [[] for _ in range(n)]
    for i, c in enumerate(live):
        groups[i % n].append(c)
    return [g for g in groups if g]


_PROMPT = """아래는 증권가 텔레그램 채널들의 최근 메시지입니다.
방송 앵커가 오늘 뭐가 움직이는지 파악하게 이슈를 정리해줘.

규칙:
1. 종목·이슈 단위로 묶고, 언급한 채널을 전부 적을 것
2. 1개 채널만 언급한 것도 버리지 말 것
3. summary는 음슴체 한 줄(최대 60자). 마크다운 기호 금지
4. "관심 집중", "주목됨" 같은 공허한 표현 금지. 구체적 사실만
5. kind: disclosure(공시·계약·증자·자사주), market(지수·환율·수급), news(그 외)
6. 최대 15개까지만

JSON만 출력(설명 금지):
{{"issues":[{{"title":"종목명/이슈명","summary":"한 줄 음슴체","channels":["채널명"],"kind":"news","stocks":["종목명"],"links":["https://..."]}}]}}

메시지:
{body}"""


async def _analyze_shard(group: list) -> list:
    parts = []
    for cd in group:
        parts.append(f"\n=== @{cd['channel']} ===")
        seen = set()
        for m in cd["messages"][:12]:
            t = (m.get("text") or "")[:220]
            k = t[:40]
            if not t or k in seen:
                continue
            seen.add(k)
            parts.append(f"- {t}")
            for l in (m.get("links") or [])[:1]:
                parts.append(f"  LINK {l}")

    body = "\n".join(parts)[:14000]
    if not body.strip():
        return []

    def _call():
        return _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            messages=[{"role": "user", "content": _PROMPT.format(body=body)}],
        )

    try:
        resp = await asyncio.to_thread(_call)
        return _salvage_issues(resp.content[0].text)
    except Exception as e:
        print(f"[tgpulse] shard 실패: {e}")
        return []


async def analyze_issues(channel_data: list) -> dict:
    """채널을 여러 조각으로 나눠 동시 분석 → 제목 기준 병합."""
    if not _client:
        return {"issues": [], "error": "ANTHROPIC_API_KEY 미설정"}

    groups = _shard(channel_data, 3)
    if not groups:
        return {"issues": [], "error": "수집된 메시지 없음"}

    results = await asyncio.gather(*[_analyze_shard(g) for g in groups],
                                   return_exceptions=True)

    merged = {}
    for r in results:
        if isinstance(r, Exception) or not r:
            continue
        for it in r:
            title = str(it.get("title") or "").strip()
            if not title:
                continue
            key = _norm_title(title)
            summary = str(it.get("summary") or "").strip()
            kind = str(it.get("kind") or "").strip()
            if kind not in ("disclosure", "market", "news"):
                kind = _detect_kind(title + " " + summary)

            cur = merged.get(key)
            if not cur:
                cur = merged[key] = {
                    "title": title, "summary": summary, "kind": kind,
                    "channels": [], "stocks": [], "links": [],
                }
            else:
                if len(summary) > len(cur["summary"]):
                    cur["summary"] = summary
                if kind == "disclosure":
                    cur["kind"] = "disclosure"

            for c in (it.get("channels") or []):
                c = str(c).strip().lstrip("@")
                if c and c not in cur["channels"]:
                    cur["channels"].append(c)
            for s in (it.get("stocks") or []):
                s = str(s).strip()
                if s and s not in cur["stocks"]:
                    cur["stocks"].append(s)
            for l in (it.get("links") or []):
                l = str(l).strip()
                if l.startswith("http") and l not in cur["links"]:
                    cur["links"].append(l)

    issues = []
    for v in merged.values():
        v["links"] = v["links"][:3]
        v["count"] = max(1, len(v["channels"]))
        issues.append(v)

    issues.sort(key=lambda x: (-x["count"], 0 if x["kind"] == "disclosure" else 1))

    if not issues:
        return {"issues": [], "error": "분석 결과 없음 — 다시 생성해주세요"}
    return {"issues": issues}


async def generate_pulse(hours: int = 12) -> dict:
    import time as _t
    _t0 = _t.time()
    channel_data = await fetch_all_channels(hours)
    _t1 = _t.time()
    result = await analyze_issues(channel_data)
    _t2 = _t.time()

    total_msgs = sum(len(c.get("messages", [])) for c in channel_data)
    ok_channels = sum(1 for c in channel_data
                      if not c.get("error") and c.get("messages"))
    error_channels = [c["channel"] for c in channel_data if c.get("error")]

    issues = result.get("issues", [])
    return {
        "issues": issues,
        "error": result.get("error", ""),
        "channel_count": len(CHANNELS),
        "ok_channel_count": ok_channels,
        "total_messages": total_msgs,
        "error_channels": error_channels,
        "hours": hours,
        "elapsed": round(_t2 - _t0, 1),
        "elapsed_fetch": round(_t1 - _t0, 1),
        "elapsed_ai": round(_t2 - _t1, 1),
        "stats": {
            "hot": sum(1 for i in issues if i["count"] >= 5),
            "warm": sum(1 for i in issues if 3 <= i["count"] < 5),
            "pin": sum(1 for i in issues if i["count"] == 2),
            "solo": sum(1 for i in issues if i["count"] <= 1),
            "disclosure": sum(1 for i in issues if i["kind"] == "disclosure"),
        },
    }


def generate_pulse_sync(hours: int = 12) -> dict:
    """Flask 동기 wrapper"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(generate_pulse(hours))
    finally:
        try: loop.close()
        except Exception: pass

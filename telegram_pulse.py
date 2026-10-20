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


async def analyze_issues(channel_data: list) -> dict:
    """
    채널 메시지를 Claude에 던져 이슈를 구조화해 받는다.
    1곳만 언급된 것도 버리지 않고 따로 담는다.
    """
    if not _client:
        return {"issues": [], "error": "ANTHROPIC_API_KEY 미설정"}

    parts = []
    for cd in channel_data:
        if cd.get("error") or not cd.get("messages"):
            continue
        parts.append(f"\n=== @{cd['channel']} ===")
        for m in cd["messages"][:15]:
            parts.append(f"- {m['text'][:300]}")
            for l in (m.get("links") or [])[:2]:
                parts.append(f"  LINK {l}")

    if not parts:
        return {"issues": [], "error": "수집된 메시지 없음"}

    all_text = "\n".join(parts)[:28000]

    prompt = f"""아래는 증권가 텔레그램 채널들의 최근 메시지입니다.
방송 앵커가 오늘 뭐가 움직이는지 파악하게 이슈를 정리해줘.

규칙:
1. 종목·이슈 단위로 묶을 것. 겹치는 채널 수를 정확히 세기
2. **1개 채널만 언급한 것도 버리지 말 것** — 의미 있으면 포함
3. 요약은 음슴체 한두 줄 ('~함', '~됨', '~임'). 마크다운 기호 쓰지 말 것
4. "관심 집중", "주목됨" 같은 공허한 표현 금지. 구체적 사실만
5. kind 분류:
   - disclosure: 공시·계약·증자·자사주 등 기업 액션
   - market: 지수·환율·수급 등 시황
   - news: 그 외 종목 뉴스
6. 개수 제한 없음

반드시 아래 JSON만 출력(설명 금지):
{{"issues":[
  {{"title":"종목명 또는 이슈명",
    "summary":"한두 줄 음슴체 요약",
    "channels":["채널명","채널명"],
    "count":2,
    "kind":"news",
    "stocks":["종목명"],
    "links":["https://..."]}}
]}}

메시지:
{all_text}"""

    try:
        resp = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=5000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
    except Exception as e:
        return {"issues": [], "error": f"분석 실패: {e}"}

    import json as _json
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return {"issues": [], "error": "JSON 파싱 실패", "raw": raw[:300]}
    try:
        data = _json.loads(m.group(0))
    except Exception as e:
        return {"issues": [], "error": f"JSON 오류: {e}", "raw": raw[:300]}

    issues = []
    for it in (data.get("issues") or []):
        if not isinstance(it, dict):
            continue
        title = str(it.get("title") or "").strip()
        if not title:
            continue
        chans = [str(c).strip() for c in (it.get("channels") or []) if str(c).strip()]
        cnt = int(it.get("count") or len(chans) or 1)
        summary = str(it.get("summary") or "").strip()
        kind = str(it.get("kind") or "").strip()
        if kind not in ("disclosure", "market", "news"):
            kind = _detect_kind(title + " " + summary)
        issues.append({
            "title": title,
            "summary": summary,
            "channels": chans,
            "count": cnt,
            "kind": kind,
            "stocks": [str(s).strip() for s in (it.get("stocks") or []) if str(s).strip()],
            "links": [str(l).strip() for l in (it.get("links") or [])
                      if str(l).strip().startswith("http")][:3],
        })

    issues.sort(key=lambda x: (-x["count"],
                               0 if x["kind"] == "disclosure" else 1))
    return {"issues": issues}


# ── 오케스트레이션 ────────────────────────
async def generate_pulse(hours: int = 12) -> dict:
    channel_data = await fetch_all_channels(hours)
    result = await analyze_issues(channel_data)

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

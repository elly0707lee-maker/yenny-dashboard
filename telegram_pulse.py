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

# 예니가 참고하는 채널들
CHANNELS = [
    "GoUpstock",
    "FastStockNews",
    "YeouidoStory2",
    "tazastock",
    "valjuman",
    "JCxTB",
    "HANAchina",
    "jeilstock",
    "bornlupin",
    "Yeouido_Lab",
    "psychotherapy101",
    "newszzang",
    "aetherjapanresearch",
    "fundeasy_choi",
    "HI_GS",
    "stock_messenger",
    "EMchina",
    "selfstudyview",
]

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
async def analyze_common_issues(channel_data: list) -> str:
    """여러 채널 메시지를 Claude에 던져 공통 이슈 추출."""
    if not _client:
        return "(ANTHROPIC_API_KEY 미설정)"

    parts = []
    for cd in channel_data:
        if cd.get("error") or not cd.get("messages"):
            continue
        parts.append(f"\n=== @{cd['channel']} ===")
        for m in cd["messages"][:15]:
            parts.append(f"- {m['text'][:300]}")
            if m.get("links"):
                for l in m["links"][:2]:
                    parts.append(f"  🔗 {l}")

    if not parts:
        return "(수집된 메시지 없음 — 채널 접근 실패 가능성)"

    all_text = "\n".join(parts)[:25000]

    prompt = f"""아래는 여러 텔레그램 채널에서 최근 12시간 동안 올라온 메시지들입니다.
방송 앵커가 오늘 뭐가 핫한지 파악할 수 있게 **공통 이슈**를 추출해줘.

⭐ 핵심 규칙:
1. **2개 이상 채널에서 언급된 종목·이슈만** 다룰 것 (1개 채널만 언급은 제외)
2. 개수 제한 없음 — 겹치는 이슈가 많으면 많이, 적으면 적게. TOP N 제한 X
3. 각 이슈에 원문 메시지의 관련 링크(🔗)가 있으면 **반드시 포함**
4. 채널 겹침 수로 강조 표시:
   - 5개 이상 채널 → 🔥
   - 3~4개 채널 → ⚡
   - 2개 채널 → 📌
5. 음슴체로 요약 ('~함', '~됨', '~임')
6. 마크다운 볼드(**) 이탤릭(*) 절대 사용 금지. 그냥 텍스트로.
7. AI 요약 티 나는 문구 지양 — "다수 언급됨"은 OK, "관심 집중 포착됨" 같은 뻣뻣한 표현 X

출력 형식 (반드시 이대로):

🔥 [종목명 or 이슈] (5개 채널)
  한두 줄 요약 (음슴체)
  🔗 https://...
  🔗 https://...

⚡ [이슈] (3개 채널)
  요약
  🔗 https://...

📌 [작은 이슈] (2개 채널)
  요약

(빈 줄로 이슈 구분)

---

만약 정말 겹치는 이슈가 하나도 없으면:
"오늘은 채널마다 관심사가 다양. 뚜렷한 공통 이슈 없음."
이렇게 한 줄로.

메시지 데이터:
{all_text}"""

    try:
        resp = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3500,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return f"(분석 실패: {e})"


# ── 오케스트레이션 ────────────────────────
async def generate_pulse(hours: int = 12) -> dict:
    channel_data = await fetch_all_channels(hours)
    summary = await analyze_common_issues(channel_data)

    total_msgs = sum(len(c.get("messages", [])) for c in channel_data)
    ok_channels = sum(1 for c in channel_data if not c.get("error") and c.get("messages"))
    error_channels = [c["channel"] for c in channel_data if c.get("error")]

    return {
        "summary": summary,
        "channel_count": len(CHANNELS),
        "ok_channel_count": ok_channels,
        "total_messages": total_msgs,
        "error_channels": error_channels,
        "hours": hours,
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

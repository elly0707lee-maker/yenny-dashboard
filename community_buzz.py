"""
커뮤니티 버즈 — 레딧(미국) + 네이버 종토방(한국) 인기 게시글 → Claude 요약
"""
import os
import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from anthropic import Anthropic

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

REDDIT_SUBS = ["wallstreetbets", "stocks", "investing", "StockMarket", "options"]
REDDIT_UA = "Mozilla/5.0 (compatible; YennyBot/1.0; +https://claude.ai)"
BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# ── 레딧 ─────────────────────────────────────────────
async def fetch_reddit_hot(subs: list = None, limit: int = 25) -> list:
    """서브레딧들에서 hot 게시글 (인증 없이 JSON endpoint)"""
    if subs is None:
        subs = REDDIT_SUBS
    headers = {"User-Agent": REDDIT_UA}
    posts = []

    async def fetch_sub(sub: str):
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status != 200:
                        return []
                    j = await r.json()
                    items = []
                    for c in j.get("data", {}).get("children", []):
                        d = c.get("data", {})
                        if d.get("stickied"):
                            continue
                        items.append({
                            "sub": sub,
                            "title": d.get("title", ""),
                            "text": (d.get("selftext", "") or "")[:400],
                            "score": d.get("score", 0),
                            "comments": d.get("num_comments", 0),
                            "url": "https://reddit.com" + d.get("permalink", ""),
                        })
                    return items
        except Exception as e:
            return []

    results = await asyncio.gather(*[fetch_sub(s) for s in subs], return_exceptions=True)
    for r in results:
        if isinstance(r, list):
            posts.extend(r)
    # score 상위로 정렬
    posts.sort(key=lambda x: x.get("score", 0), reverse=True)
    return posts


async def summarize_reddit(posts: list) -> str:
    """레딧 게시글 리스트를 Claude로 요약"""
    if not posts:
        return "(데이터 없음)"
    if not _client:
        return "(ANTHROPIC_API_KEY 미설정)"

    # 게시글 텍스트 조립 (상위 60개까지)
    posts_text = "\n".join([
        f"[{p['sub']}] ▲{p['score']} 💬{p['comments']} | {p['title'][:150]}"
        + (f" · {p['text'][:200]}" if p.get('text') else "")
        for p in posts[:60]
    ])

    prompt = f"""아래는 미국 투자 커뮤니티(레딧 r/wallstreetbets, r/stocks 등)의 hot 게시글 목록입니다.
방송 전 앵커가 훑어볼 수 있게 정리해주세요.

출력 형식 (반드시 이대로):

🔥 뜨는 종목 TOP 5
1. TICKER (종목명) — 뜨는 이유 한 줄
2. TICKER (종목명) — 이유
3. ...

📢 주요 이슈
- 이슈 한 줄
- 이슈 한 줄
- 이슈 한 줄

💭 시장 심리
한 문장으로 (예: 반도체 강세 기대감 팽배함 / FOMC 앞두고 방어적 심리 확산됨)

규칙:
- 모두 음슴체 ('~함', '~됨', '~임')
- 여러 게시글에서 다수 언급된 종목·이슈만 다룰 것
- 단순 밈·개인 자랑 글은 무시
- 종목은 실제 티커만 (SPY, TSLA, NVDA 등)
- TOP 5가 안 나오면 나오는 만큼만
- 정보 부족한 섹션은 "(정보 부족)" 표기

게시글:
{posts_text[:14000]}"""

    try:
        resp = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return f"(요약 실패: {e})"


# ── 네이버 종토방 ─────────────────────────────────────
async def fetch_naver_hot_stocks(top_n: int = 10) -> list:
    """네이버 금융 인기 검색 종목 TOP N"""
    url = "https://finance.naver.com/sise/lastsearch2.naver"
    headers = {"User-Agent": BROWSER_UA}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    return []
                # 네이버 금융은 EUC-KR
                raw = await r.read()
                html = raw.decode("euc-kr", errors="ignore")
                soup = BeautifulSoup(html, "html.parser")
                stocks = []
                seen = set()
                for a in soup.select("a.tltle, a[href*='code=']"):
                    href = a.get("href", "")
                    m = re.search(r"code=(\d{6})", href)
                    if not m:
                        continue
                    code = m.group(1)
                    if code in seen:
                        continue
                    seen.add(code)
                    name = a.get_text(strip=True)
                    if not name:
                        continue
                    stocks.append({"name": name, "code": code})
                    if len(stocks) >= top_n:
                        break
                return stocks
    except Exception:
        return []


async def fetch_naver_board(code: str, name: str, limit: int = 10) -> list:
    """특정 종목의 종토방 상위 게시글"""
    url = f"https://finance.naver.com/item/board.naver?code={code}"
    headers = {"User-Agent": BROWSER_UA}
    posts = []
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status != 200:
                    return []
                raw = await r.read()
                html = raw.decode("euc-kr", errors="ignore")
                soup = BeautifulSoup(html, "html.parser")
                # 게시글 테이블
                for tr in soup.select("table.type2 tr"):
                    tds = tr.select("td")
                    if len(tds) < 6:
                        continue
                    title_el = tds[1].select_one("a")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    if not title:
                        continue
                    # 조회수, 추천, 반대
                    try:
                        views = int(tds[3].get_text(strip=True).replace(",", "") or 0)
                    except:
                        views = 0
                    try:
                        up = int(tds[4].get_text(strip=True).replace(",", "") or 0)
                    except:
                        up = 0
                    try:
                        down = int(tds[5].get_text(strip=True).replace(",", "") or 0)
                    except:
                        down = 0
                    posts.append({
                        "stock": name,
                        "code": code,
                        "title": title,
                        "views": views,
                        "up": up,
                        "down": down,
                    })
                    if len(posts) >= limit:
                        break
    except Exception:
        pass
    return posts


async def fetch_naver_all_forums(top_n_stocks: int = 10, posts_per: int = 8) -> list:
    """인기 종목 TOP N의 종토방 게시글 모두 fetch"""
    stocks = await fetch_naver_hot_stocks(top_n=top_n_stocks)
    if not stocks:
        return []
    tasks = [fetch_naver_board(s["code"], s["name"], limit=posts_per) for s in stocks]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_posts = []
    for r in results:
        if isinstance(r, list):
            all_posts.extend(r)
    # 조회수 상위로 정렬
    all_posts.sort(key=lambda x: x.get("views", 0), reverse=True)
    return all_posts


async def summarize_naver(posts: list) -> str:
    """네이버 종토방 게시글을 Claude로 요약"""
    if not posts:
        return "(데이터 없음 — 네이버 접근 실패 또는 인기 종목 없음)"
    if not _client:
        return "(ANTHROPIC_API_KEY 미설정)"

    posts_text = "\n".join([
        f"[{p['stock']}] 👁 {p['views']} 👍 {p['up']} 👎 {p['down']} | {p['title'][:120]}"
        for p in posts[:80]
    ])

    prompt = f"""아래는 네이버 금융 종토방에서 인기 종목들의 게시글 목록입니다.
방송 전 앵커가 훑어볼 수 있게 정리해주세요.

출력 형식 (반드시 이대로):

🔥 뜨는 종목 TOP 5
1. 종목명 — 뜨는 이유 한 줄
2. 종목명 — 이유
3. ...

📢 주요 이슈
- 이슈 한 줄
- 이슈 한 줄
- 이슈 한 줄

💭 시장 심리
한 문장으로 (예: XX 실적 기대감 팽배함 / YY 개미들 공포심 확산됨)

규칙:
- 모두 음슴체 ('~함', '~됨', '~임')
- 여러 게시글에서 다수 언급된 종목·이슈만
- 개인 자랑·낚시 제목·욕설 무시
- 종목명은 그대로 (한글 종목명)
- TOP 5 안 나오면 나오는 만큼만
- 정보 부족한 섹션은 "(정보 부족)" 표기

게시글:
{posts_text[:14000]}"""

    try:
        resp = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return f"(요약 실패: {e})"


# ── 오케스트레이션 ────────────────────────────────────
async def generate_buzz(source: str = "both") -> dict:
    """레딧 + 네이버 병렬 실행 → 요약 반환.
    source: 'both' | 'reddit' | 'naver'
    """
    tasks = []
    names = []
    if source in ("both", "reddit"):
        async def run_reddit():
            posts = await fetch_reddit_hot()
            summary = await summarize_reddit(posts)
            return {"post_count": len(posts), "summary": summary}
        tasks.append(run_reddit())
        names.append("reddit")
    if source in ("both", "naver"):
        async def run_naver():
            posts = await fetch_naver_all_forums()
            summary = await summarize_naver(posts)
            return {"post_count": len(posts), "summary": summary}
        tasks.append(run_naver())
        names.append("naver")

    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = {}
    for name, res in zip(names, results):
        if isinstance(res, Exception):
            out[name] = {"error": str(res)}
        else:
            out[name] = res
    return out


def generate_buzz_sync(source: str = "both") -> dict:
    """Flask에서 호출용 동기 wrapper"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(generate_buzz(source))
    finally:
        try:
            loop.close()
        except Exception:
            pass

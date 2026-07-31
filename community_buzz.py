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
REDDIT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# ── 레딧 ─────────────────────────────────────────────
async def fetch_reddit_hot(subs: list = None, limit: int = 25) -> list:
    """서브레딧들에서 hot 게시글.
    ★ Railway 데이터센터 IP는 reddit.com이 봇으로 인식해서 종종 차단함.
    → RSS endpoint 사용 (봇 차단 훨씬 덜함, 인증 X)
    """
    import xml.etree.ElementTree as ET
    if subs is None:
        subs = REDDIT_SUBS
    headers = {
        "User-Agent": REDDIT_UA,
        "Accept": "application/atom+xml, application/rss+xml, application/xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    posts = []
    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    async def fetch_sub(sub: str):
        # ★ RSS/Atom 방식 — reddit.com/{sub}/hot/.rss
        url = f"https://www.reddit.com/r/{sub}/hot/.rss?limit={limit}"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status != 200:
                        print(f"[reddit RSS] r/{sub} HTTP {r.status}")
                        return []
                    text = await r.text()
                    try:
                        root = ET.fromstring(text)
                    except ET.ParseError as pe:
                        print(f"[reddit RSS] r/{sub} XML 파싱 실패: {pe}")
                        return []
                    items = []
                    for entry in root.findall('atom:entry', ns):
                        title_el = entry.find('atom:title', ns)
                        content_el = entry.find('atom:content', ns)
                        link_el = entry.find('atom:link', ns)
                        title = (title_el.text or "").strip() if title_el is not None else ""
                        if not title:
                            continue
                        raw_html = (content_el.text or "") if content_el is not None else ""
                        # HTML → text (bs로 안전하게)
                        try:
                            text_content = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)
                        except Exception:
                            text_content = re.sub(r"<[^>]+>", " ", raw_html)
                        text_content = re.sub(r"\s+", " ", text_content).strip()[:400]
                        link = link_el.get("href") if link_el is not None else ""
                        items.append({
                            "sub": sub,
                            "title": title,
                            "text": text_content,
                            "url": link,
                        })
                    print(f"[reddit RSS] r/{sub}: {len(items)}개")
                    return items
        except Exception as e:
            print(f"[reddit RSS] r/{sub} 에러: {e}")
            return []

    results = await asyncio.gather(*[fetch_sub(s) for s in subs], return_exceptions=True)
    for r in results:
        if isinstance(r, list):
            posts.extend(r)
    print(f"[reddit RSS] 총 {len(posts)}개 수집됨")
    return posts


async def summarize_reddit(posts: list) -> str:
    """레딧 게시글 리스트를 Claude로 상세히 요약"""
    if not posts:
        return "(데이터 없음 — 레딧 접근 실패. Railway IP 차단 가능성. 잠시 후 다시 시도해주세요.)"
    if not _client:
        return "(ANTHROPIC_API_KEY 미설정)"

    # 게시글 텍스트 조립 (상위 80개까지)
    posts_text = "\n".join([
        f"[r/{p['sub']}] {p['title']}"
        + (f"\n   본문: {p['text'][:250]}" if p.get('text') else "")
        for p in posts[:80]
    ])

    prompt = f"""아래는 미국 투자 커뮤니티(레딧 r/wallstreetbets, r/stocks 등)의 hot 게시글 목록입니다.
후배 앵커가 방송 전에 선배한테 잠깐 브리핑하는 톤으로 정리해줘.
신문 사설처럼 딱딱하게 X. 옆에 앉아서 짧게 말하듯이.

⭐ 절대 규칙 — 이거 어기면 실패:
1. 마크다운 문법 절대 금지: **볼드**, *이탤릭*, `코드`, ###제목 등 모두 X
2. 실제 게시글에 나온 표현·문구는 큰따옴표("...")로 감싸서 인용
3. "~됨/~함/~임" 음슴체
4. 방송에서 실제 쓸 만한 자연스러운 문장으로

출력 형식:

🔥 뜨는 종목 TOP 5
1. TICKER (종목명) — 자연스러운 한 줄 + 실제 게시글 표현 인용
   예: NVDA (엔비디아) — 실적 앞두고 "this time it's different" 얘기 자주 나옴. 옵션 매수 인증글도 많음
2. ...

📢 주요 이슈 (5~7개)
- 이슈 + 커뮤니티에서 실제로 어떻게 얘기하는지
  예: FOMC 앞두고 방어적 분위기. "cash is king" 얘기 나오고 SPY 풋 사는 사람들 늘어남
- ...

💭 시장 심리
한두 문장으로. 대표적 표현 2~3개 큰따옴표로 인용.
예: 반도체 낙관론 우세. "AI bubble이 아니라 진짜" "NVDA to the moon" 이런 분위기가 지배적이지만 "너무 오른 거 아닌가" 우려도 조금씩 나옴

기사 데이터 부족한 섹션은 "(정보 부족)" 표기.

게시글:
{posts_text[:15000]}"""

    try:
        resp = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return f"(요약 실패: {e})"


# ── 네이버 종토방 ─────────────────────────────────────
def _smart_decode(raw: bytes, resp_headers: dict = None) -> str:
    """네이버 응답 인코딩 자동 감지 — UTF-8 → EUC-KR → CP949 순으로 시도.
    한글 깨짐 방지 (네이버가 페이지마다 다른 인코딩 사용)"""
    # 1) Content-Type header의 charset 확인
    if resp_headers:
        ct = resp_headers.get("Content-Type", "") if hasattr(resp_headers, "get") else ""
        m = re.search(r"charset=([\w-]+)", ct, re.IGNORECASE)
        if m:
            enc = m.group(1).lower()
            try:
                return raw.decode(enc, errors="strict")
            except Exception:
                pass
    # 2) UTF-8 시도
    try:
        text = raw.decode("utf-8", errors="strict")
        # 한글이 정상적으로 있으면 OK
        if any("\uAC00" <= c <= "\uD7A3" for c in text[:5000]):
            return text
    except UnicodeDecodeError:
        pass
    # 3) EUC-KR / CP949 시도
    for enc in ("euc-kr", "cp949"):
        try:
            return raw.decode(enc, errors="strict")
        except UnicodeDecodeError:
            continue
    # 4) 마지막 fallback — UTF-8 with replace
    return raw.decode("utf-8", errors="replace")


async def _naver_fetch_html(url: str, timeout: int = 15) -> tuple:
    """네이버 URL fetch — 상세 진단 로그 반환.
    반환: (html_text, status_code, error_msg)
    """
    # 다양한 UA 시도 (Railway IP 차단 우회)
    uas = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    ]
    for ua in uas:
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Referer": "https://finance.naver.com/",
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
                    raw = await r.read()
                    html = _smart_decode(raw, r.headers)
                    if r.status == 200 and len(html) > 500:
                        return (html, 200, None)
                    print(f"[naver-fetch] {url[:60]} → HTTP {r.status}, len={len(html)}, UA={ua[:30]}...")
        except Exception as e:
            print(f"[naver-fetch] {url[:60]} 에러: {e}, UA={ua[:30]}...")
            continue
    return ("", 0, "모든 UA 시도 실패")


async def fetch_naver_hot_stocks(top_n: int = 10) -> list:
    """네이버 금융 인기 검색 종목 TOP N"""
    url = "https://finance.naver.com/sise/lastsearch2.naver"
    html, status, err = await _naver_fetch_html(url)
    if not html:
        print(f"[naver] 인기종목 접근 실패: status={status}, err={err}")
        return []
    print(f"[naver] 인기종목 페이지 fetch 성공, HTML {len(html)}자")
    try:
        soup = BeautifulSoup(html, "html.parser")
        stocks = []
        seen = set()
        # 여러 셀렉터 시도
        candidates = soup.select("a.tltle") + soup.select("a[href*='code=']")
        print(f"[naver] 후보 링크 {len(candidates)}개 발견")
        for a in candidates:
            href = a.get("href", "")
            m = re.search(r"code=(\d{6})", href)
            if not m:
                continue
            code = m.group(1)
            if code in seen:
                continue
            seen.add(code)
            name = a.get_text(strip=True)
            if not name or len(name) > 30:
                continue
            stocks.append({"name": name, "code": code})
            if len(stocks) >= top_n:
                break
        print(f"[naver] 인기종목 {len(stocks)}개 추출")
        return stocks
    except Exception as e:
        print(f"[naver] 파싱 에러: {e}")
        return []


async def fetch_naver_board(code: str, name: str, limit: int = 10) -> list:
    """특정 종목의 종토방 상위 게시글"""
    url = f"https://finance.naver.com/item/board.naver?code={code}"
    html, status, err = await _naver_fetch_html(url, timeout=12)
    if not html:
        return []
    posts = []
    try:
        soup = BeautifulSoup(html, "html.parser")
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
            try: views = int(tds[3].get_text(strip=True).replace(",", "") or 0)
            except: views = 0
            try: up = int(tds[4].get_text(strip=True).replace(",", "") or 0)
            except: up = 0
            try: down = int(tds[5].get_text(strip=True).replace(",", "") or 0)
            except: down = 0
            posts.append({"stock": name, "code": code, "title": title,
                          "views": views, "up": up, "down": down})
            if len(posts) >= limit:
                break
    except Exception as e:
        print(f"[naver] {name} 파싱 에러: {e}")
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
    """네이버 종토방 게시글을 Claude로 상세히 요약"""
    if not posts:
        return "(데이터 없음 — 네이버 접근 실패 또는 인기 종목 없음)"
    if not _client:
        return "(ANTHROPIC_API_KEY 미설정)"

    posts_text = "\n".join([
        f"[{p['stock']}] 👁 {p['views']} 👍 {p['up']} 👎 {p['down']} | {p['title'][:120]}"
        for p in posts[:100]
    ])

    prompt = f"""아래는 네이버 금융 종토방의 인기 종목 게시글 목록입니다.
후배 앵커가 방송 전에 선배한테 잠깐 브리핑하는 톤으로 정리해줘.
신문 사설처럼 딱딱하게 X. 옆에 앉아서 짧게 말하듯이.

⭐ 절대 규칙 — 이거 어기면 실패:
1. 마크다운 문법 절대 금지: **볼드**, *이탤릭*, `코드`, ###제목 등 모두 X
2. 실제 게시글에 나온 표현·문구는 큰따옴표("...")로 감싸서 인용
3. "~됨/~함/~임" 음슴체
4. 방송에서 실제 쓸 만한 자연스러운 문장으로

출력 형식:

🔥 뜨는 종목 TOP 5
1. 종목명 — 자연스러운 한 줄 + 실제 게시글 표현 인용
   예: SK하이닉스 — "10만원 뚫자" 얘기 계속 나옴. "상한가 3연상 간다" 같은 흥분한 글도 자주 보임
2. ...

📢 주요 이슈 (5~7개)
- 이슈 + 커뮤니티에서 실제 어떻게 얘기하는지
  예: 반도체 랠리 재개. "이번엔 진짜다" "안 사면 후회한다" 이런 FOMO 조장 글 많음
- ...

💭 시장 심리
한두 문장으로. 대표적 표현 2~3개 큰따옴표로 인용.
예: 반도체 상한가에 축제 분위기. "역사적 급등" "지금이라도 사자" 낙관론 우세하지만 "고점 물리는 거 아닌가" 우려도 병존함

기사 데이터 부족한 섹션은 "(정보 부족)" 표기.

게시글:
{posts_text[:15000]}"""

    try:
        resp = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2500,
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

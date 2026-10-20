"""
뉴스 허브 — 1단계 수집

세 갈래로 모아서 같은 형태로 정규화한다.
  1) 네이버 종목뉴스 API  — 종목코드가 이미 매핑돼 있고 매체 수(total)까지 줌
  2) 언론사 섹션 RSS      — 종목이 안 붙은 산업·정책 기사까지 훑음
  3) 텔레그램 채널        — 속보·공시 (채널 목록이 들어오면 활성화)

출력 형태(공통):
  {
    "src": "naver" | "rss" | "tele",
    "title": str, "body": str, "link": str,
    "office": str,          # 매체명
    "ts": datetime,         # 발행 시각
    "cluster": int,         # 같은 이슈를 보도한 매체 수 (모르면 1)
    "codes": [str],         # 확정된 종목코드 (네이버 경로만)
  }
"""
import re
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


# ── 1) 네이버 종목뉴스 ──────────────────────────────
async def fetch_stock_news(session, code: str, name: str = "", limit: int = 10) -> list:
    """
    종목코드로 뉴스를 받는다. 네이버가 종목 매핑과 이슈 묶음을 이미 해둠.
    응답: [{total: N, items: [...]}, ...]  — 바깥 배열이 이슈 묶음
    """
    url = f"https://m.stock.naver.com/api/news/stock/{code}"
    out = []
    try:
        async with session.get(
            url, params={"pageSize": limit, "page": 1},
            headers={"User-Agent": UA,
                     "Referer": f"https://m.stock.naver.com/domestic/stock/{code}/news",
                     "Accept": "application/json, text/plain, */*"},
            timeout=aiohttp.ClientTimeout(total=8),
        ) as r:
            if r.status != 200:
                return []
            data = await r.json(content_type=None)
    except Exception:
        return []

    groups = data if isinstance(data, list) else [data]
    for g in groups:
        if not isinstance(g, dict):
            continue
        total = g.get("total") or 1
        for it in (g.get("items") or []):
            title = _clean(it.get("title"))
            if not title:
                continue
            office_id = (it.get("officeId") or "").strip()
            article_id = (it.get("articleId") or "").strip()
            link = (f"https://n.news.naver.com/mnews/article/{office_id}/{article_id}"
                    if office_id and article_id else "")
            out.append({
                "src": "naver",
                "title": title,
                "body": _clean(it.get("body"))[:200],
                "link": link,
                "office": (it.get("officeName") or "").strip(),
                "ts": _parse_dt(it.get("datetime")),
                "cluster": int(total),
                "codes": [code],
                "stock_name": name or code,
            })
            break          # 묶음당 대표 기사 1건만 (나머지는 cluster 수로 표현)
    return out


async def fetch_stock_news_many(codes: list, name_map: dict = None,
                                limit: int = 10, workers: int = 12) -> list:
    """여러 종목의 뉴스를 한 번에. 종목 수가 많으면 나눠서 돌린다."""
    name_map = name_map or {}
    out = []
    conn = aiohttp.TCPConnector(limit=workers)
    async with aiohttp.ClientSession(connector=conn) as s:
        for i in range(0, len(codes), workers * 2):
            chunk = codes[i:i + workers * 2]
            tasks = [fetch_stock_news(s, c, name_map.get(c, ""), limit) for c in chunk]
            for r in await asyncio.gather(*tasks, return_exceptions=True):
                if isinstance(r, list):
                    out.extend(r)
    return out


# ── 2) 언론사 섹션 RSS ──────────────────────────────
RSS_FEEDS = [
    # /api/rss-test 로 확인된 살아있는 피드만
    ("연합뉴스",   "경제", "https://www.yna.co.kr/rss/economy.xml"),      # 120
    ("아시아경제", "증권", "https://www.asiae.co.kr/rss/stock.htm"),      # 100
    ("머니투데이", "증권", "https://rss.mt.co.kr/mt_news_stock.xml"),     # 100
    ("뉴시스",     "경제", "https://newsis.com/RSS/economy.xml"),         # 100
    ("매일경제",   "증권", "https://www.mk.co.kr/rss/50200011/"),         # 50
    ("매일경제",   "경제", "https://www.mk.co.kr/rss/30100041/"),         # 50
    ("매일경제",   "기업", "https://www.mk.co.kr/rss/50100032/"),         # 50
]


def parse_rss(raw: bytes) -> list:
    """RSS 바이트 → [{title, link, pub}]. EUC-KR·깨진 XML까지 받아낸다."""
    import xml.etree.ElementTree as ET

    def from_xml(data):
        root = ET.fromstring(data)
        res = []
        for it in root.findall(".//item"):
            t = (it.findtext("title") or "").strip()
            if t:
                res.append({"title": t,
                            "link": (it.findtext("link") or "").strip(),
                            "pub": (it.findtext("pubDate") or "").strip(),
                            "desc": (it.findtext("description") or "").strip()})
        return res

    try:
        return from_xml(raw)
    except Exception:
        pass

    for enc in ("euc-kr", "cp949", "utf-8"):
        try:
            text = raw.decode(enc, errors="replace")
            text = re.sub(r'encoding=["\'][^"\']+["\']', 'encoding="utf-8"',
                          text, count=1)
            return from_xml(text.encode("utf-8"))
        except Exception:
            continue

    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            text = raw.decode(enc, errors="replace")
        except Exception:
            continue
        blocks = re.findall(r"<item[^>]*>(.*?)</item>", text, re.S | re.I)
        if not blocks:
            continue
        res = []
        for b in blocks:
            def pick(tag):
                m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", b, re.S | re.I)
                if not m:
                    return ""
                v = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", m.group(1), flags=re.S)
                return re.sub(r"<[^>]+>", "", v).strip()
            t = pick("title")
            if t:
                res.append({"title": t, "link": pick("link"),
                            "pub": pick("pubDate"), "desc": pick("description")})
        if res:
            return res
    return []


async def fetch_rss_one(session, office: str, section: str, url: str,
                        hours: int = 12) -> list:
    cutoff = datetime.now(KST) - timedelta(hours=hours)
    try:
        async with session.get(url, headers={"User-Agent": UA},
                               timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                return []
            raw = await r.read()
    except Exception:
        return []

    out = []
    for it in parse_rss(raw):
        ts = _parse_pubdate(it.get("pub"))
        if ts and ts < cutoff:
            continue
        out.append({
            "src": "rss",
            "title": _clean(it["title"]),
            "body": _clean(it.get("desc"))[:200],
            "link": it.get("link", ""),
            "office": office,
            "section": section,
            "ts": ts or datetime.now(KST),
            "cluster": 1,
            "codes": [],
        })
    return out


async def fetch_all_rss(hours: int = 12) -> list:
    conn = aiohttp.TCPConnector(limit=12)
    async with aiohttp.ClientSession(connector=conn) as s:
        tasks = [fetch_rss_one(s, o, sec, u, hours) for o, sec, u in RSS_FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    out = []
    for r in results:
        if isinstance(r, list):
            out.extend(r)
    return out


# ── 3) 텔레그램 (채널 목록이 들어오면 채움) ──────────
NEWS_CHANNELS: list = []     # 뉴스 채널
DART_CHANNELS: list = []     # 공시 채널


async def fetch_telegram(channels: list, hours: int = 12) -> list:
    """t.me/s/{channel} 공개 미리보기에서 최근 메시지를 긁는다."""
    if not channels:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = []

    async def one(session, ch):
        try:
            async with session.get(f"https://t.me/s/{ch}",
                                   headers={"User-Agent": UA},
                                   timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return []
                html = await r.text()
        except Exception:
            return []

        res = []
        # 메시지 본문과 시각을 쌍으로 추출
        for m in re.finditer(
            r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>.*?'
            r'<time datetime="([^"]+)"', html, re.S
        ):
            body = re.sub(r"<br\s*/?>", "\n", m.group(1))
            body = re.sub(r"<[^>]+>", "", body)
            body = _clean(body)
            if not body:
                continue
            try:
                ts = datetime.fromisoformat(m.group(2).replace("Z", "+00:00"))
            except Exception:
                continue
            if ts < cutoff:
                continue
            first = body.split("\n")[0][:120]
            res.append({
                "src": "tele",
                "title": first,
                "body": body[:300],
                "link": f"https://t.me/{ch}",
                "office": ch,
                "ts": ts.astimezone(KST),
                "cluster": 1,
                "codes": [],
            })
        return res

    conn = aiohttp.TCPConnector(limit=8)
    async with aiohttp.ClientSession(connector=conn) as s:
        for r in await asyncio.gather(*[one(s, c) for c in channels],
                                      return_exceptions=True):
            if isinstance(r, list):
                out.extend(r)
    return out


# ── 공통 유틸 ────────────────────────────────────────
def _clean(s) -> str:
    if not isinstance(s, str):
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = (s.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<")
         .replace("&gt;", ">").replace("&apos;", "'").replace("&nbsp;", " ")
         .replace("&#039;", "'"))
    return re.sub(r"\s+", " ", s).strip()


def _parse_dt(v) -> datetime:
    """네이버 datetime: '202610200925'"""
    try:
        s = str(v).strip()
        if len(s) >= 12:
            return datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]),
                            int(s[8:10]), int(s[10:12]), tzinfo=KST)
    except Exception:
        pass
    return datetime.now(KST)


def _parse_pubdate(v) -> datetime:
    if not v:
        return None
    from email.utils import parsedate_to_datetime
    try:
        d = parsedate_to_datetime(v)
        if d.tzinfo is None:
            d = d.replace(tzinfo=KST)
        return d.astimezone(KST)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(str(v).strip()[:19], fmt).replace(tzinfo=KST)
        except Exception:
            continue
    return None


# ── 동기 래퍼 ────────────────────────────────────────
def _run(coro):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.close()
        except Exception:
            pass


def collect_sync(codes: list = None, name_map: dict = None,
                 hours: int = 12, with_rss: bool = True) -> dict:
    """1단계 수집 — 세 갈래를 모아 한 덩어리로 돌려준다."""
    async def go():
        tasks = []
        if codes:
            tasks.append(fetch_stock_news_many(codes, name_map))
        else:
            tasks.append(asyncio.sleep(0, result=[]))
        tasks.append(fetch_all_rss(hours) if with_rss
                     else asyncio.sleep(0, result=[]))
        tasks.append(fetch_telegram(NEWS_CHANNELS + DART_CHANNELS, hours))
        return await asyncio.gather(*tasks, return_exceptions=True)

    res = _run(go())
    naver, rss, tele = [r if isinstance(r, list) else [] for r in res]
    return {"naver": naver, "rss": rss, "tele": tele,
            "total": len(naver) + len(rss) + len(tele)}

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
            body = _clean(it.get("body"))[:200]
            # ⚠️ 네이버 종목뉴스에는 일반 시황 기사도 섞여 온다.
            #    제목·본문에 종목명이 실제로 있을 때만 그 종목 뉴스로 인정.
            hit = bool(name) and (name in title or name in body)
            out.append({
                "src": "naver",
                "title": title,
                "body": body,
                "link": link,
                "office": (it.get("officeName") or "").strip(),
                "ts": _parse_dt(it.get("datetime")),
                "cluster": int(total),
                "codes": [code] if hit else [],
                "stock_name": name if hit else "",
            })
            break          # 묶음당 대표 1건 (나머지는 cluster 수로 표현)
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


# ── 2단계: 워치리스트 역색인 분류 ────────────────────
# 일반 단어와 겹쳐 오탐을 부르는 종목명은 제외
STOP_NAMES = {
    "대성", "세방", "동양", "한국", "대한", "신원", "유니온",
    "삼성", "현대", "한화", "미래", "우리", "국보", "성지",
    "다우", "경동", "서울", "부산", "대구", "광주", "제주",
    "중앙", "태경", "동국", "영원", "한솔", "금호", "일신", "삼영",
    "이수", "대림", "신일", "코리아", "글로벌", "스마트", "에이스",
    "에스엠", "케이씨", "디아이", "아이티", "피에스", "에이티",
}


def build_index(watchlist: dict) -> dict:
    """
    워치리스트 → 역색인
      {종목명: [{"code","sector","group"}...]}  + 코드 색인
    """
    by_name, by_code = {}, {}
    for s in (watchlist.get("sectors") or []):
        sname = s.get("name") or ""
        for g in (s.get("groups") or []):
            gname = g.get("name") or ""
            for st in (g.get("stocks") or []):
                code = (st.get("code") or "").strip()
                nm = (st.get("name") or "").strip()
                if not code:
                    continue
                entry = {"code": code, "name": nm, "sector": sname, "group": gname}
                by_code.setdefault(code, []).append(entry)
                # 2글자 이하이거나 일반어와 겹치면 이름 매칭에서 제외
                if nm and len(nm) >= 3 and nm not in STOP_NAMES:
                    by_name.setdefault(nm, []).append(entry)
    return {"by_name": by_name, "by_code": by_code}


# 섹터 무관하게 반드시 띄워야 할 신호
ALERT_WORDS = [
    "유상증자", "무상증자", "자사주", "소각", "분할", "합병", "인수",
    "상장폐지", "거래정지", "감자", "전환사채", "공급계약", "수주",
    "임상", "승인", "허가", "특허", "횡령", "배임", "실적", "흑자전환",
    "적자전환", "어닝", "목표가", "투자의견",
]


def classify(items: list, index: dict) -> list:
    """
    기사마다 테마를 붙이고 점수를 매긴다.
    네이버 경로로 이미 종목이 확정된 건 그 코드를 그대로 쓰고,
    나머지는 제목·본문에서 종목명을 찾아 역으로 매칭.
    """
    by_name = index.get("by_name") or {}
    by_code = index.get("by_code") or {}

    for it in items:
        hits, themes = [], []

        # 1) 이미 확정된 코드
        for c in (it.get("codes") or []):
            hits.extend(by_code.get(c, []))

        # 2) 제목·본문에서 종목명 찾기
        text = (it.get("title") or "") + " " + (it.get("body") or "")
        for nm, entries in by_name.items():
            if nm in text:
                hits.extend(entries)

        seen = set()
        for h in hits:
            key = (h["sector"], h["group"])
            if key in seen:
                continue
            seen.add(key)
            themes.append({"sector": h["sector"], "group": h["group"],
                           "name": h["name"], "code": h["code"]})

        it["themes"] = themes[:4]
        it["matched"] = bool(themes)

        # 3) 점수 — 매체 수가 기본, 내 종목이면 가점, 신호어도 가점
        score = min(int(it.get("cluster") or 1), 20) * 3
        if themes:
            score += 12 + min(len(themes), 3) * 2
        alerts = [w for w in ALERT_WORDS if w in text]
        it["alerts"] = alerts[:3]
        score += min(len(alerts), 3) * 4
        if it.get("src") == "tele":
            score += 2
        it["score"] = score

    items.sort(key=lambda x: (-x.get("score", 0), x.get("ts") or datetime.now(KST)),
               reverse=False)
    items.sort(key=lambda x: -x.get("score", 0))
    return items


def dedupe(items: list) -> list:
    """제목이 거의 같은 기사를 묶고, 묶인 수를 cluster에 더한다."""
    def norm(t):
        t = re.sub(r"\[[^\]]*\]", "", t or "")
        t = re.sub(r"[^\w가-힣]", "", t)
        return t[:28]

    bucket = {}
    for it in items:
        k = norm(it.get("title"))
        if not k:
            continue
        if k in bucket:
            cur = bucket[k]
            cur["cluster"] = max(cur.get("cluster", 1), it.get("cluster", 1)) \
                             + 1
            offs = cur.setdefault("offices", [cur.get("office", "")])
            if it.get("office") and it["office"] not in offs:
                offs.append(it["office"])
            if not cur.get("codes") and it.get("codes"):
                cur["codes"] = it["codes"]
        else:
            it["offices"] = [it.get("office", "")]
            bucket[k] = it
    return list(bucket.values())

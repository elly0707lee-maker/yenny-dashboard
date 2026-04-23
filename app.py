from flask import Flask, jsonify, request, Response
import requests
import os
from datetime import datetime
from functools import wraps
import anthropic
import pg8000.native

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB

DATABASE_URL = os.environ.get("DATABASE_URL", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
KIS_APP_KEY = os.environ.get("KIS_APP_KEY", "")
KIS_APP_SECRET = os.environ.get("KIS_APP_SECRET", "")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "yenny2026")
API_SECRET = os.environ.get("API_SECRET", "moneyplus")

_kis_token_cache = {"token": "", "expires": 0}


def get_db():
    import urllib.parse as _up
    r = _up.urlparse(DATABASE_URL)
    return pg8000.native.Connection(
        host=r.hostname, port=r.port or 5432,
        database=r.path.lstrip('/'),
        user=r.username, password=r.password,
        ssl_context=True
    )

def init_db():
    conn = get_db()
    conn.run("""CREATE TABLE IF NOT EXISTS posts (
        id SERIAL PRIMARY KEY,
        type TEXT NOT NULL, content TEXT NOT NULL,
        date TEXT NOT NULL, created_at TEXT NOT NULL)""")
    try:
        conn.run("""CREATE TABLE IF NOT EXISTS pdfs (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL)""")
    except Exception:
        pass
    conn.close()

init_db()


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.password != DASHBOARD_PASSWORD:
            return Response("로그인 필요", 401,
                {"WWW-Authenticate": 'Basic realm="Yenny Dashboard"'})
        return f(*args, **kwargs)
    return decorated


def get_kis_token():
    import time
    if _kis_token_cache["token"] and time.time() < _kis_token_cache["expires"]:
        return _kis_token_cache["token"]
    try:
        r = requests.post(
            "https://openapi.koreainvestment.com:9443/oauth2/tokenP",
            json={"grant_type": "client_credentials",
                  "appkey": KIS_APP_KEY, "appsecret": KIS_APP_SECRET},
            timeout=6)
        data = r.json()
        token = data.get("access_token", "")
        _kis_token_cache["token"] = token
        _kis_token_cache["expires"] = time.time() + 3600 * 20  # 20시간
        return token
    except:
        return ""


def kis_get(path, tr_id, params):
    if not KIS_APP_KEY:
        return {}
    try:
        token = get_kis_token()
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": KIS_APP_KEY,
            "appsecret": KIS_APP_SECRET,
            "tr_id": tr_id,
            "Content-Type": "application/json"
        }
        r = requests.get(
            f"https://openapi.koreainvestment.com:9443{path}",
            headers=headers, params=params, timeout=6)
        return r.json()
    except:
        return {}


def get_yahoo_quote(symbol):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://finance.yahoo.com/",
        "Origin": "https://finance.yahoo.com",
    }
    for base in ["query1", "query2"]:
        for ver in ["v8", "v7"]:
            try:
                if ver == "v8":
                    url = f"https://{base}.finance.yahoo.com/v8/finance/chart/{symbol}"
                    r = requests.get(url, headers=headers, timeout=10)
                    meta = r.json()["chart"]["result"][0]["meta"]
                    price = round(meta.get("regularMarketPrice", 0), 2)
                    prev = meta.get("chartPreviousClose") or meta.get("previousClose", price)
                else:
                    url = f"https://{base}.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
                    r = requests.get(url, headers=headers, timeout=10)
                    q = r.json()["quoteResponse"]["result"][0]
                    price = round(q.get("regularMarketPrice", 0), 2)
                    prev = q.get("regularMarketPreviousClose", price)
                chg = round((price - prev) / prev * 100, 2) if prev else 0
                if price > 0:
                    return {"value": price, "change": chg}
            except:
                continue
    return {"value": None, "change": None}


def get_korean_market():
    result = {}
    for mkt, code in [("kospi", "0001"), ("kosdaq", "1001")]:
        d = kis_get("/uapi/domestic-stock/v1/quotations/inquire-index-price",
                    "FHPUP02100000",
                    {"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": code}).get("output", {})
        raw_chg = d.get("bstp_nmix_prdy_ctrt", None)
        try:
            chg_val = float(raw_chg) if raw_chg not in (None, "", "0") else None
        except:
            chg_val = None
        raw_val = d.get("bstp_nmix_prpr", None)
        try:
            idx_val = float(raw_val) if raw_val not in (None, "") else None
        except:
            idx_val = None
        result[mkt] = {
            "value": idx_val,
            "change": chg_val,
            "foreign": None, "institution": None
        }
        sup = kis_get("/uapi/domestic-stock/v1/quotations/inquire-index-investor",
                      "FHPST01710000",
                      {"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": code,
                       "FID_INPUT_DATE_1": datetime.now().strftime("%Y%m%d")}).get("output", [])
        if sup and isinstance(sup, list):
            result[mkt]["foreign"] = sup[0].get("frgn_ntby_qty", None)
            result[mkt]["institution"] = sup[0].get("orgn_ntby_qty", None)
            result[mkt]["individual"] = sup[0].get("indv_ntby_qty", None)

    result["futures_auto"] = None

    return result


# 코스피 업종 코드 → 이름
# 코스피 업종 ETF (Yahoo Finance 심볼)
SECTOR_ETFS = [
    ("반도체",   "091160.KS"),
    ("2차전지",  "305720.KS"),
    ("바이오",   "207920.KS"),
    ("금융",     "139270.KS"),
    ("에너지",   "117700.KS"),
    ("방산",     "471550.KS"),
    ("조선",     "466920.KS"),
    ("자동차",   "091180.KS"),
    ("건설",     "102960.KS"),
    ("IT",       "148020.KS"),
]

def get_sector_data():
    result = []
    for name, symbol in SECTOR_ETFS:
        q = get_yahoo_quote(symbol)
        if q["change"] is not None:
            result.append({"name": name, "change": q["change"]})
    result.sort(key=lambda x: x["change"], reverse=True)
    return {"top5": result[:5], "bot5": list(reversed(result[-5:]))}


def get_global_market():
    syms = {
        "nasdaq": "%5EIXIC", "dow": "%5EDJI", "sp500": "%5EGSPC",
        "wti": "CL%3DF", "brent": "BZ%3DF",
        "usdkrw": "USDKRW%3DX",
        "vix": "%5EVIX", "ewy": "EWY",
        "tnx": "%5ETNX", "sox": "%5ESOX",
        "dxy": "DX-Y.NYB", "gold": "GC%3DF", "dram": "SOXX"
    }
    return {k: get_yahoo_quote(v) for k, v in syms.items()}


def save_post(t, content, date):
    conn = get_db()
    conn.run(
        "INSERT INTO posts (type,content,date,created_at) VALUES (:t,:c,:d,:ca)",
        t=t, c=content, d=date, ca=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    conn.close()


def get_latest_post(t):
    conn = get_db()
    rows = conn.run("SELECT content,date FROM posts WHERE type=:t ORDER BY id DESC LIMIT 1", t=t)
    conn.close()
    return {"content": rows[0][0], "date": rows[0][1]} if rows else None


@app.route("/manifest.json")
def manifest():
    return Response(open("manifest.json").read(), mimetype="application/manifest+json")

@app.route("/service-worker.js")
def sw():
    return Response(open("service-worker.js").read(), mimetype="application/javascript")

@app.route("/")
@requires_auth
def index():
    return Response(get_html(), mimetype="text/html")


@app.route("/api/market")
@requires_auth
def api_market():
    g = get_global_market()
    k = get_korean_market()
    return jsonify({**g, **k})


@app.route("/api/sector")
@requires_auth
def api_sector():
    return jsonify(get_sector_data())


@app.route("/api/post/<pt>")
@requires_auth
def api_get_post(pt):
    valid = ("checkpoint", "closing", "briefing", "futures", "aftermarket", "report", "report_up", "report_dn", "report_feature", "note", "todo", "calendar", "memo", "report", "wdaebon")
    if pt not in valid:
        return jsonify({"error": "invalid"}), 400
    return jsonify(get_latest_post(pt) or {})


@app.route("/api/post/<pt>", methods=["POST"])
def api_save_post(pt):
    valid = ("checkpoint", "closing", "briefing", "futures", "aftermarket", "report", "report_up", "report_dn", "report_feature", "note", "todo", "calendar", "memo", "report", "wdaebon")
    if pt not in valid:
        return jsonify({"error": "invalid"}), 400
    # 대시보드 직접 저장은 인증 필요
    auth = request.authorization
    bot_secret = request.headers.get("X-API-Secret", "")
    if bot_secret != API_SECRET and (not auth or auth.password != DASHBOARD_PASSWORD):
        return jsonify({"error": "unauthorized"}), 401
    body = request.json or {}
    content = body.get("content", "")
    date = body.get("date", datetime.now().strftime("%Y-%m-%d"))
    if not content:
        return jsonify({"error": "content required"}), 400
    save_post(pt, content, date)
    return jsonify({"ok": True})


@app.route("/api/news")
@requires_auth
def api_news():
    import xml.etree.ElementTree as ET
    feeds = [
        ("한경 속보", "https://www.hankyung.com/feed/breaking-news"),
        ("한경 경제", "https://www.hankyung.com/feed/economy"),
        ("한경 증권", "https://www.hankyung.com/feed/stock"),
        ("한경 금융", "https://www.hankyung.com/feed/finance"),
        ("한경 국제", "https://www.hankyung.com/feed/international"),
        ("매일경제", "https://www.mk.co.kr/rss/30000001/"),
        ("매일경제 증권", "https://www.mk.co.kr/rss/30100041/"),
        ("파이낸셜뉴스", "https://www.fnnews.com/rss/fn_economy_rss.xml"),
        ("머니투데이", "https://rss.mt.co.kr/mt_finance.xml"),
        ("구글 경제뉴스", "https://news.google.com/rss/search?q=%EA%B2%BD%EC%A0%9C+%EC%A6%9D%EA%B6%8C&hl=ko&gl=KR&ceid=KR:ko"),
    ]
    items = []
    for source, url in feeds:
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            root = ET.fromstring(r.content)
            ns = {"dc": "http://purl.org/dc/elements/1.1/"}
            for item in root.findall(".//item")[:5]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                pub = item.findtext("pubDate", "").strip()
                if title and link:
                    items.append({"title": title, "link": link, "pub": pub, "source": source})
        except Exception as e:
            pass
    # Sort by pub date roughly (string sort works for RFC 2822)
    items.sort(key=lambda x: x["pub"], reverse=True)
    return jsonify({"items": items[:25]})


@app.route("/api/theme/prices")
@requires_auth
def theme_prices():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "테마명 없음"}), 400

    SHEET_ID = os.environ.get("SHEET_ID", "")
    if not SHEET_ID:
        return jsonify({"error": "SHEET_ID 없음"}), 500

    import csv, io as _io
    sheet_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    try:
        res = requests.get(sheet_url, timeout=10)
        res.encoding = "utf-8"
        data = list(csv.DictReader(_io.StringIO(res.text)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # 테마 포함 종목 (중복 제거)
    seen = set()
    stocks = []
    for r in data:
        if query in r.get("테마", ""):
            code = r.get("종목코드", "").strip()
            name = r.get("종목명", "").strip()
            theme = r.get("테마", "").strip()
            if code and name and code not in seen:
                seen.add(code)
                stocks.append({"code": code, "name": name, "theme": theme})

    if not stocks:
        return jsonify({"stocks": [], "query": query})

    # 시세 일괄 조회
    results = []
    for s in stocks:
        try:
            r = requests.get(
                f"https://m.stock.naver.com/api/stock/{s['code']}/basic",
                headers={"User-Agent": "Mozilla/5.0"}, timeout=4)
            if r.status_code == 200:
                d = r.json()
                price = d.get("closePrice") or d.get("currentPrice", "")
                pct = d.get("fluctuationsRatio", "")
                change = d.get("compareToPreviousClosePrice", "")
                try:
                    pct_f = float(str(pct).replace(",",""))
                    price_i = int(str(price).replace(",",""))
                    change_i = int(str(change).replace(",",""))
                    arrow = "▲" if pct_f >= 0 else "▼"
                    sign = "+" if pct_f >= 0 else ""
                    results.append({
                        "code": s["code"],
                        "name": s["name"],
                        "theme": s["theme"],
                        "price": f"{price_i:,}",
                        "change": f"{arrow} {abs(change_i):,}",
                        "pct": f"{sign}{pct_f:.2f}%",
                        "up": pct_f >= 0
                    })
                except:
                    results.append({"code": s["code"], "name": s["name"], "theme": s["theme"], "price": str(price), "change": "", "pct": "", "up": None})
        except:
            results.append({"code": s["code"], "name": s["name"], "theme": s["theme"], "price": "—", "change": "", "pct": "", "up": None})

    # 등락률 내림차순 정렬
    results.sort(key=lambda x: float(x["pct"].replace("%","").replace("+","") or 0), reverse=True)
    return jsonify({"stocks": results, "query": query, "count": len(results)})


@app.route("/api/kstock/search")
@requires_auth
def kstock_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "검색어 없음"}), 400

    SHEET_ID = os.environ.get("SHEET_ID", "")
    NAVER_ID = os.environ.get("NAVER_CLIENT_ID", "")
    NAVER_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")

    if not SHEET_ID:
        return jsonify({"error": "SHEET_ID 환경변수 없음"}), 500

    try:
        import csv, io as _io
        sheet_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
        res = requests.get(sheet_url, timeout=10)
        res.encoding = "utf-8"
        data = list(csv.DictReader(_io.StringIO(res.text)))

        stock_hits = [r for r in data if r.get("종목명", "").strip() == query.strip()]
        # 종목 검색 결과 있으면 테마 검색 생략 (삼성전자 검색 시 삼성전자향 등 안 나오게)
        if stock_hits:
            theme_hits = []
        else:
            theme_hits = [r for r in data if query in r.get("테마", "")]

        lines = []

        if stock_hits:
            from collections import OrderedDict
            grouped = OrderedDict()
            for r in stock_hits:
                name = r.get("종목명", "")
                if name not in grouped:
                    grouped[name] = []
                grouped[name].append(r)

            for name, rows in grouped.items():
                lines.append(f"📌 [{name}]")
                for r in rows:
                    theme = r.get("테마", "")
                    desc = r.get("특징", "").strip()
                    lines.append(f"☑️ {theme}")
                    if desc:
                        lines.append(f"➡️ {desc}")
                    lines.append("")

                code = rows[0].get("종목코드", "").strip()
                if code:
                    try:
                        pr = requests.get(
                            f"https://m.stock.naver.com/api/stock/{code}/basic",
                            headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                        pd = pr.json()
                        price = pd.get("closePrice") or pd.get("currentPrice", "")
                        change = pd.get("compareToPreviousClosePrice", "")
                        pct = pd.get("fluctuationsRatio", "")
                        if price:
                            arrow = "▲" if float(str(change).replace(",","") or 0) >= 0 else "▼"
                            lines.append(f"📊 {int(str(price).replace(',','')):,}원 {arrow} {pct}%")
                    except:
                        pass
                    lines.append(f"🔗 https://m.stock.naver.com/domestic/stock/{code}/total")
                lines.append("")

        if theme_hits:
            if stock_hits:
                lines.append("─" * 20)
            lines.append(f"🗂 [{query}] 관련 종목")
            for i, r in enumerate(theme_hits, 1):
                name = r.get("종목명", "")
                theme = r.get("테마", "")
                desc = r.get("특징", "").strip()
                line = f"{i}. {name}  ({theme})"
                if desc:
                    line += f"\n   ➡️ {desc}"
                lines.append(line)
            lines.append("")

        if NAVER_ID and (stock_hits or theme_hits):
            try:
                import re as _re
                def clean(t): return _re.sub(r"<[^>]+>","",t)
                nr_date = requests.get(
                    "https://openapi.naver.com/v1/search/news.json",
                    headers={"X-Naver-Client-Id": NAVER_ID, "X-Naver-Client-Secret": NAVER_SECRET},
                    params={"query": query, "display": 3, "sort": "date"}, timeout=8)
                news_date = nr_date.json().get("items", [])
                nr_sim = requests.get(
                    "https://openapi.naver.com/v1/search/news.json",
                    headers={"X-Naver-Client-Id": NAVER_ID, "X-Naver-Client-Secret": NAVER_SECRET},
                    params={"query": query, "display": 5, "sort": "sim"}, timeout=8)
                news_sim = nr_sim.json().get("items", [])
                date_links = {item["link"] for item in news_date}
                news_sim_unique = [n for n in news_sim if n["link"] not in date_links][:2]
                if news_date or news_sim_unique:
                    lines.append(f"📰 뉴스 ({query})")
                    lines.append("")
                    if news_date:
                        lines.append("🕐 최신순")
                        for i, item in enumerate(news_date, 1):
                            lines.append(f"{i}. {clean(item['title'])}")
                            lines.append(f"   🔗 {item['link']}")
                    if news_sim_unique:
                        lines.append("")
                        lines.append("🎯 관련도순")
                        for i, item in enumerate(news_sim_unique, 1):
                            lines.append(f"{i}. {clean(item['title'])}")
                            lines.append(f"   🔗 {item['link']}")
            except:
                pass

        if not stock_hits and not theme_hits:
            lines.append(f"❓ '{query}' — 등록된 종목/테마가 없어요.")

        # Get first stock code for chart (TradingView KRX format)
        first_code = None
        if stock_hits:
            from collections import OrderedDict
            raw_code = stock_hits[0].get("종목코드", "").strip()
            if raw_code:
                first_code = "KRX:" + raw_code
        # Extract price line for display
        price_display = None
        for line in lines:
            if "원" in line and ("▲" in line or "▼" in line):
                price_display = line.replace("📊 ", "")
                break
        return jsonify({"result": "\n".join(lines), "found": bool(stock_hits or theme_hits), "code": first_code, "price": price_display})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/todo/clear", methods=["POST"])
@requires_auth
def clear_todo():
    save_post("todo", "", datetime.now().strftime("%Y-%m-%d"))
    return jsonify({"ok": True})


@app.route("/api/encyclopedia/search")
@requires_auth
def encyclopedia_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "검색어 없음"}), 400

    ENC_SHEET_ID = "1_2hIjvp2MqjHNLcv0JTn1yWgC4vB5zIzwkUS_c4cqUs"
    import csv, io as _io, re
    terms = [t.strip() for t in re.split(r'[/,\s]+', query) if t.strip()]

    try:
        url = f"https://docs.google.com/spreadsheets/d/{ENC_SHEET_ID}/export?format=csv"
        r = requests.get(url, timeout=10)
        r.encoding = "utf-8"
        rows = list(csv.DictReader(_io.StringIO(r.text)))
        matched = []
        for row in rows:
            row_text = " ".join(str(v) for v in row.values())
            if all(term in row_text for term in terms):
                matched.append(row)
        return jsonify({"results": matched, "query": query})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/upload", methods=["POST"])
@requires_auth
def pdf_upload():
    from datetime import datetime as dt
    body = request.json or {}
    name = body.get("name", "report.pdf")
    data = body.get("data", "")
    if not data:
        return jsonify({"error": "파일 없음"}), 400
    conn = get_db()
    rows = conn.run("SELECT id FROM pdfs ORDER BY created_at ASC")
    if rows and len(rows) >= 3:
        conn.run("DELETE FROM pdfs WHERE id=:i", i=rows[0][0])
    conn.run("INSERT INTO pdfs (name, data, created_at) VALUES (:n,:d,:c)",
             n=name, d=data, c=dt.now().isoformat())
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/pdf/list")
@requires_auth
def pdf_list():
    conn = get_db()
    rows = conn.run("SELECT id, name, created_at FROM pdfs ORDER BY created_at DESC")
    conn.close()
    if not rows:
        return jsonify({"pdfs": []})
    return jsonify({"pdfs": [{"id": r[0], "name": r[1], "date": r[2][:10] if r[2] else ""} for r in rows]})


@app.route("/api/pdf/<int:pdf_id>")
@requires_auth
def pdf_get(pdf_id):
    conn = get_db()
    rows = conn.run("SELECT name, data FROM pdfs WHERE id=:i", i=pdf_id)
    conn.close()
    if not rows:
        return jsonify({"error": "없음"}), 404
    return jsonify({"name": rows[0][0], "data": rows[0][1]})


@app.route("/api/pdf/<int:pdf_id>/delete", methods=["POST"])
@requires_auth
def pdf_delete(pdf_id):
    conn = get_db()
    conn.run("DELETE FROM pdfs WHERE id=:i", i=pdf_id)
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/encyc/search")
@requires_auth
def encyc_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "검색어 없음"}), 400

    ENCYC_SHEET_ID = os.environ.get("ENCYC_SHEET_ID", "")
    if not ENCYC_SHEET_ID:
        return jsonify({"error": "ENCYC_SHEET_ID 없음"}), 500

    import csv, io as _io, re
    sheet_url = f"https://docs.google.com/spreadsheets/d/{ENCYC_SHEET_ID}/export?format=csv"
    terms = [t.strip() for t in re.split(r'[/,\s]+', query) if t.strip()]

    try:
        r = requests.get(sheet_url, timeout=10)
        r.encoding = "utf-8"
        rows = list(csv.DictReader(_io.StringIO(r.text)))
        matched = []
        for row in rows:
            row_text = " ".join(str(v) for v in row.values())
            if all(term in row_text for term in terms):
                matched.append(row)
        return jsonify({"results": matched, "query": query})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/guest/search")
@requires_auth
def guest_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "검색어 없음"}), 400

    GUEST_SHEET_ID = os.environ.get("GUEST_SHEET_ID", "")
    if not GUEST_SHEET_ID:
        return jsonify({"error": "GUEST_SHEET_ID 없음"}), 500

    import csv, io as _io
    base_url = f"https://docs.google.com/spreadsheets/d/{GUEST_SHEET_ID}/export?format=csv&gid="

    # Sheet GIDs - 탭 순서대로
    sheets = [
        ("Master", "437534302"),
        ("History", "1633570539"),
        ("골든픽", "1460063403"),
        ("오늘장전략", "1283113183"),
    ]

    # 공백이나 /로 구분된 복수 검색어 → AND 조건
    import re
    terms = [t.strip() for t in re.split(r'[/,\s]+', query) if t.strip()]

    results = {}
    for sheet_name, gid in sheets:
        try:
            r = requests.get(base_url + gid, timeout=10)
            r.encoding = "utf-8"
            rows = list(csv.DictReader(_io.StringIO(r.text)))
            matched = []
            for row in rows:
                row_text = " ".join(str(v) for v in row.values())
                if all(term in row_text for term in terms):
                    matched.append(row)
            if matched:
                # 날짜 기준 최신순 정렬
                def get_date_key(row):
                    date_val = row.get("날짜", "") or row.get("date", "")
                    return str(date_val)
                matched.sort(key=get_date_key, reverse=True)
                results[sheet_name] = matched
        except:
            pass

    return jsonify({"results": results, "query": query, "terms": terms})


@app.route("/api/calendar/parse", methods=["POST"])
@requires_auth
def calendar_parse():
    body = request.json or {}
    raw = body.get("content", "")
    if not raw:
        return jsonify({"error": "내용 없음"}), 400
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": f"""아래는 주간 증시 일정 텍스트입니다.
날짜별로 파싱해서 반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

{{
  "week_label": "4월 11일~17일",
  "days": [
    {{
      "date": "4월 11일 토요일",
      "day_key": "sat",
      "items": ["美-이란, 파키스탄서 협상 개시", "푸틴, 우크라 전쟁 부활절 휴전 선언"],
      "guests": ["반종민 소장 - 주도주를 만드는 이슈", "박종현 대표 - 가는 종목이 더 간다"]
    }}
  ]
}}

규칙:
- day_key는 mon/tue/wed/thu/fri/sat/sun 중 하나
- items: 경제·증권 일정만. 핵심 한 줄 요약. 세부내용 생략.
- guests: 출연자 이름과 주제가 있으면 guests 배열에. "이름 - 주제" 형식. 출연자가 없으면 빈 배열 [].
- 출연자처럼 보이는 항목(사람 이름 + 주제/소속)은 반드시 guests로 분류.

텍스트:
{raw}"""}]
        )
        import json
        text = msg.content[0].text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        save_post("calendar", json.dumps(data, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d"))
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/calendar/update", methods=["POST"])
@requires_auth
def calendar_update():
    import json
    body = request.json or {}
    data = body.get("data", {})
    save_post("calendar", json.dumps(data, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d"))
    return jsonify({"ok": True})


@app.route("/api/calendar/clear", methods=["POST"])
@requires_auth
def calendar_clear():
    save_post("calendar", "", datetime.now().strftime("%Y-%m-%d"))
    return jsonify({"ok": True})


@app.route("/api/note/clear", methods=["POST"])
@requires_auth
def clear_note():
    save_post("note", "", datetime.now().strftime("%Y-%m-%d"))
    return jsonify({"ok": True})


@app.route("/api/report/clear", methods=["POST"])
@requires_auth
def clear_report():
    for t in ("report_up","report_dn","report_feature"):
        save_post(t, "", datetime.now().strftime("%Y-%m-%d"))
    return jsonify({"ok": True})




@app.route("/api/briefing/generate", methods=["POST"])
@requires_auth
def generate_briefing():
    if not ANTHROPIC_API_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY 없음"}), 500
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        today = datetime.now().strftime("%m월 %d일")
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content":
                f"현지시각 {today} 미국 증시 브리핑 해줘. CNBC, Bloomberg, WSJ 반드시 웹서치해서 "
                f"시장 주도 재료와 지수 수치, 주요 뉴스, 특징주를 한국어로 정리해줘."}]
        )
        content = " ".join([b.text for b in msg.content if hasattr(b, "text") and b.text])
        date = datetime.now().strftime("%Y-%m-%d")
        save_post("briefing", content, date)
        return jsonify({"content": content, "date": date})
    except Exception as e:
        return jsonify({"error": str(e)}), 500





def get_html():
    return r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Yenny">
<meta name="theme-color" content="#1a1d23">
<link rel="manifest" href="/manifest.json">
<title>Yenny Dashboard</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=DM+Mono:wght@400;500&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Noto Sans KR',sans-serif;background:#f0f2f5;color:#1a1d23;min-height:100vh}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:#1a1d23;position:sticky;top:0;z-index:10;border-bottom:3px solid #e8b84b}
.topbar-title{font-size:16px;font-weight:700;color:#fff;letter-spacing:-.3px}
.topbar-title span{color:#e8b84b;font-weight:400;font-size:13px;margin-left:6px}
#clock{font-family:'DM Mono',monospace;font-size:13px;color:#e8b84b;letter-spacing:.05em}
.container{padding:20px;max-width:1100px;margin:0 auto}
.section-label{font-size:11px;font-weight:700;color:#7a8099;letter-spacing:.12em;text-transform:uppercase;margin:24px 0 10px;padding-left:2px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
@media(max-width:680px){.grid3{grid-template-columns:1fr 1fr}.grid4{grid-template-columns:1fr 1fr}}
.card{background:#fff;border-radius:14px;padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,.07),0 4px 16px rgba(0,0,0,.04)}
.metric-label{font-size:11px;font-weight:700;color:#7a8099;letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px}
.metric-val{font-size:26px;font-weight:700;color:#1a1d23;letter-spacing:-.5px;font-family:'DM Mono',monospace}
.metric-chg{font-size:13px;font-weight:600;margin-top:5px}
.metric-sup{font-size:12px;color:#7a8099;margin-top:8px;display:flex;gap:12px}
.up{color:#d63031}
.dn{color:#0984e3}
.flat{color:#b2bec3}
.loading{color:#b2bec3;font-size:20px}
.content-card{background:#fff;border-radius:14px;padding:18px 20px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.07),0 4px 16px rgba(0,0,0,.04)}
.content-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px}
.content-title{font-size:14px;font-weight:700;color:#1a1d23}
.content-date{font-size:11px;color:#b2bec3;font-family:'DM Mono',monospace}
.content-body{font-size:14px;color:#2d3436;line-height:1.8;white-space:pre-wrap;max-height:300px;overflow-y:auto}
.content-empty{font-size:13px;color:#b2bec3;font-style:italic}
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:8px;border:1.5px solid #dfe6e9;background:#fff;color:#636e72;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
.btn:hover{background:#f0f2f5;color:#1a1d23;border-color:#b2bec3}
.btn-primary{background:#1a1d23;border-color:#1a1d23;color:#e8b84b}
.btn-primary:hover{background:#2d3436;border-color:#2d3436}
.btn-green{background:#00b894;border-color:#00b894;color:#fff}
.btn-green:hover{background:#00a381}
.btn.ls{opacity:.5;pointer-events:none}
.refresh-dot{width:7px;height:7px;border-radius:50%;background:#e8b84b;display:inline-block;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.spinner{display:inline-block;width:13px;height:13px;border:2px solid #dfe6e9;border-top-color:#e8b84b;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.etf-row{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #f0f2f5;font-size:13px}
.etf-row:last-child{border-bottom:none}
.etf-name{color:#2d3436;font-weight:500}
.etf-chg{font-weight:700;font-family:'DM Mono',monospace}
textarea.input-area{width:100%;background:#f8f9fa;border:1.5px solid #dfe6e9;border-radius:10px;color:#2d3436;font-size:14px;padding:12px 14px;resize:vertical;min-height:100px;font-family:'Noto Sans KR',sans-serif;line-height:1.7}
textarea.input-area:focus{outline:none;border-color:#e8b84b;background:#fff}
/* 리치 에디터 */
.rich-editor{width:100%;background:#f8f9fa;border:1.5px solid #dfe6e9;border-radius:10px;color:#2d3436;font-size:14px;padding:12px 14px;min-height:100px;font-family:'Noto Sans KR',sans-serif;line-height:1.7;overflow-y:auto;outline:none}
.rich-editor:focus{border-color:#e8b84b;background:#fff}
.rich-editor:empty::before{content:attr(data-placeholder);color:#b2bec3;pointer-events:none}
.richtext-toolbar{display:flex;gap:4px;flex-wrap:wrap;padding:6px;background:#f0f2f5;border-radius:8px;margin-bottom:6px}
.richtext-toolbar button{width:30px;height:28px;border:1px solid #dfe6e9;background:white;color:#2d3436;border-radius:5px;cursor:pointer;font-size:13px;font-weight:600;display:inline-flex;align-items:center;justify-content:center;padding:0;transition:all .1s}
.richtext-toolbar button:hover{background:#e8b84b;color:white;border-color:#e8b84b}
.richtext-toolbar .rt-sep{width:1px;background:#dfe6e9;margin:2px 2px}
input.input-line{width:100%;background:#f8f9fa;border:1.5px solid #dfe6e9;border-radius:10px;color:#2d3436;font-size:15px;font-weight:600;padding:10px 14px;font-family:'DM Mono',monospace}
input.input-line:focus{outline:none;border-color:#e8b84b;background:#fff}
.input-row{display:flex;gap:8px;align-items:flex-start;margin-top:10px}
.saved-badge{font-size:11px;color:#00b894;font-weight:700;margin-left:8px;display:none}
.tab-bar{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:12px}
.tab{padding:5px 13px;border-radius:20px;border:1.5px solid #dfe6e9;background:#f0f2f5;color:#636e72;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
.tab.active{background:#1a1d23;border-color:#1a1d23;color:#e8b84b}
.tab:hover:not(.active){background:#fff;color:#1a1d23}
.futures-val{font-size:28px;font-weight:700;color:#1a1d23;font-family:'DM Mono',monospace;margin-bottom:12px}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-title">Yenny Dashboard</div>
  <div style="display:flex;align-items:center;gap:10px;">
    <span class="refresh-dot"></span>
    <span id="clock" style="font-size:12px;color:#666;"></span>
  </div>
</div>

<div class="container">

  <!-- 국내 시장 -->
  <div class="section-label">국내 시장</div>
  <div class="grid3">
    <div class="card">
      <div class="metric-label">코스피</div>
      <div class="metric-val" id="kospi-val"><span class="loading">—</span></div>
      <div class="metric-chg" id="kospi-chg"></div>
      <div class="metric-sup" id="kospi-sup"></div>
    </div>
    <div class="card">
      <div class="metric-label">코스닥</div>
      <div class="metric-val" id="kosdaq-val"><span class="loading">—</span></div>
      <div class="metric-chg" id="kosdaq-chg"></div>
      <div class="metric-sup" id="kosdaq-sup"></div>
    </div>
    <div class="card">
      <div class="metric-label">원/달러 (주간)</div>
      <div class="metric-val" id="usdkrw-val"><span class="loading">—</span></div>
      <div class="metric-chg" id="usdkrw-chg"></div>
    </div>
  </div>

  <!-- 야간선물 + 오늘의 할일 -->
  <div style="display:grid;grid-template-columns:1fr 2fr;gap:10px;margin-top:8px;">
    <div class="content-card" style="margin-bottom:0;">
      <div class="content-header">
        <span class="content-title">🌙 야간선물</span>
        <span class="saved-badge" id="futures-badge">✓ 저장됨</span>
      </div>
      <div id="futures-display" class="futures-val">—</div>
      <div id="futures-auto-val" style="font-size:11px;color:#b2bec3;margin-bottom:6px;"></div>
      <div class="input-row">
        <input class="input-line" id="futures-input" placeholder="예) +1.2%" style="flex:1;" />
        <button class="btn btn-green" onclick="saveFutures()">저장</button>
        <button class="btn" onclick="clearFutures()" style="color:#d63031;border-color:#fab1a0;">↺ 초기화</button>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:0;">
      <!-- 투두리스트 -->
      <div class="content-card" style="margin-bottom:0;">
        <div class="content-header">
          <span class="content-title">✅ 투두리스트</span>
          <span class="saved-badge" id="todo-badge">✓ 저장됨</span>
        </div>
        <div id="todo-list" style="margin-bottom:8px;"></div>
        <div style="display:flex;gap:6px;">
          <input id="todo-new-input" class="input-line" placeholder="할일 추가..." style="flex:1;font-size:13px;"
            onkeydown="if(event.key==='Enter')addTodoItem()"/>
          <button class="btn btn-green" onclick="addTodoItem()" style="padding:8px 12px;">+</button>
        </div>
      </div>
      <!-- 메모 -->
      <div class="content-card" style="margin-bottom:0;">
        <div class="content-header">
          <span class="content-title">📝 메모</span>
          <div style="display:flex;gap:6px;">
            <span class="saved-badge" id="memo-badge">✓ 저장됨</span>
            <button class="btn btn-green" onclick="saveMemo()">저장</button>
            <button class="btn" onclick="clearMemo()" style="color:#d63031;border-color:#fab1a0;">↺ 초기화</button>
          </div>
        </div>
        <textarea class="input-area" id="memo-input" placeholder="메모..." style="min-height:120px;"></textarea>
      </div>
    </div>
  </div>

  <!-- 미국·글로벌 -->
  <div class="section-label">미국·글로벌</div>
  <div class="grid4">
    <div class="card"><div class="metric-label">다우존스</div><div class="metric-val" id="dow-val"><span class="loading">—</span></div><div class="metric-chg" id="dow-chg"></div></div>
    <div class="card"><div class="metric-label">S&amp;P 500</div><div class="metric-val" id="sp500-val"><span class="loading">—</span></div><div class="metric-chg" id="sp500-chg"></div></div>
    <div class="card"><div class="metric-label">나스닥</div><div class="metric-val" id="nasdaq-val"><span class="loading">—</span></div><div class="metric-chg" id="nasdaq-chg"></div></div>
    <div class="card"><div class="metric-label">EWY</div><div class="metric-val" id="ewy-val"><span class="loading">—</span></div><div class="metric-chg" id="ewy-chg"></div></div>
  </div>
  <div class="grid4" style="margin-top:8px;">
    <div class="card"><div class="metric-label">미국 10년물 금리</div><div class="metric-val" id="tnx-val"><span class="loading">—</span></div><div class="metric-chg" id="tnx-chg"></div></div>
    <div class="card"><div class="metric-label">달러인덱스 (DXY)</div><div class="metric-val" id="dxy-val"><span class="loading">—</span></div><div class="metric-chg" id="dxy-chg"></div></div>
    <div class="card"><div class="metric-label">VIX</div><div class="metric-val" id="vix-val"><span class="loading">—</span></div><div class="metric-chg" id="vix-chg"></div></div>
    <div class="card"><div class="metric-label">필라델피아반도체</div><div class="metric-val" id="sox-val"><span class="loading">—</span></div><div class="metric-chg" id="sox-chg"></div></div>
  </div>
  <div class="grid4" style="margin-top:8px;">
    <div class="card"><div class="metric-label">WTI 유가</div><div class="metric-val" id="wti-val"><span class="loading">—</span></div><div class="metric-chg" id="wti-chg"></div></div>
    <div class="card"><div class="metric-label">브렌트유</div><div class="metric-val" id="brent-val"><span class="loading">—</span></div><div class="metric-chg" id="brent-chg"></div></div>
    <div class="card"><div class="metric-label">금</div><div class="metric-val" id="gold-val"><span class="loading">—</span></div><div class="metric-chg" id="gold-chg"></div></div>
    <div class="card"><div class="metric-label">DRAM ETF (SOXX)</div><div class="metric-val" id="dram-val"><span class="loading">—</span></div><div class="metric-chg" id="dram-chg"></div></div>
  </div>
  <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:8px;align-items:center;">
    <a href="https://www.bloomberg.com/asia" target="_blank" class="btn">📰 Bloomberg</a>
    <a href="https://finviz.com/" target="_blank" class="btn">📊 Finviz</a>
    <a href="https://www.cnbc.com/watchlist/" target="_blank" class="btn">📺 CNBC Watchlist</a>
    <button class="btn" onclick="loadAll()" id="refresh-btn"><span>↻</span> 새로고침</button>
  </div>

  <!-- 업종 등락률 -->
  <div class="section-label">업종 등락률 (코스피) / 마켓맵</div>
  <div class="grid2">
    <div class="content-card" style="margin-bottom:0;display:flex;flex-direction:column;gap:0;">
      <div class="tab-bar">
        <button class="tab active" onclick="sectorTab(this,'top')" id="tab-sector-top">📈 상승</button>
        <button class="tab" onclick="sectorTab(this,'bot')" id="tab-sector-bot">📉 하락</button>
      </div>
      <div id="sector-top"><span class="content-empty">로딩 중...</span></div>
      <div id="sector-bot" style="display:none;"><span class="content-empty">로딩 중...</span></div>
      <div style="border-top:1px solid #f0f2f5;margin-top:12px;padding-top:10px;">
        <div style="font-size:11px;font-weight:700;color:#7a8099;margin-bottom:8px;letter-spacing:.08em;">📰 증권 뉴스 (한국경제 · 연합뉴스 경제 · 세계)</div>
        <div id="news-list" style="max-height:300px;overflow-y:auto;">
          <span class="content-empty">뉴스 로딩 중...</span>
        </div>
        <div style="margin-top:6px;">
          <button class="btn" onclick="loadNews()" style="font-size:11px;padding:5px 10px;">↻ 새로고침</button>
        </div>
      </div>
    </div>
    <div class="content-card" style="margin-bottom:0;padding:12px 16px 0;overflow:hidden;">
      <div class="tab-bar">
        <button class="tab active" onclick="mapTab(this,'kospi')" id="tab-map-kospi">코스피</button>
        <button class="tab" onclick="mapTab(this,'kosdaq')" id="tab-map-kosdaq">코스닥</button>
      </div>
      <div style="display:flex;gap:6px;margin-bottom:8px;">
        <a id="map-link-kospi" href="https://markets.hankyung.com/marketmap/kospi" target="_blank" class="btn btn-primary" style="font-size:11px;padding:6px 10px;">🗺 바로가기</a>
        <a id="map-link-kosdaq" href="https://markets.hankyung.com/marketmap/kosdaq" target="_blank" class="btn" style="font-size:11px;padding:6px 10px;display:none;">🗺 바로가기</a>
      </div>
      <div style="width:100%;height:380px;overflow:hidden;border-radius:8px;position:relative;">
        <iframe id="map-frame" src="https://markets.hankyung.com/marketmap/kospi"
          style="width:250%;height:1100px;border:none;position:absolute;top:-220px;left:-75%;transform:scale(0.47);transform-origin:top center;"
          scrolling="no"></iframe>
      </div>
    </div>
  </div>

  <!-- K-Stock 검색 -->
  <div class="section-label">종목 · 테마 검색</div>
  <div class="content-card">
    <div class="content-header">
      <span class="content-title">🔍 K-Stock 검색</span>
      <span style="font-size:11px;color:#b2bec3;">종목명 또는 테마명 입력</span>
    </div>
    <div class="input-row">
      <input class="input-line" id="kstock-input" placeholder="예) 삼성전자 / 방산 / 2차전지" style="flex:1;" onkeydown="if(event.key==='Enter')searchKstock()"/>
      <button class="btn btn-primary" onclick="searchKstock()" id="kstock-btn">검색</button>
    </div>
    <div class="grid2" style="margin-top:14px;">
      <div id="kstock-result"></div>
      <div id="kstock-chart" style="display:none;">
        <iframe id="kstock-chart-frame" src="" style="width:100%;height:400px;border:none;border-radius:10px;"></iframe>
      </div>
    </div>
  </div>

  <!-- 테마 시세 -->
  <div class="section-label">📈 테마 시세</div>
  <div class="content-card">
    <div class="content-header">
      <span class="content-title">📈 테마별 종목 시세</span>
      <span style="font-size:11px;color:#b2bec3;">DB 기반 일괄 조회</span>
    </div>
    <div class="input-row">
      <input class="input-line" id="theme-input" placeholder="예) 방산 / 2차전지 / 반도체" style="flex:1;"
        onkeydown="if(event.key==='Enter')searchThemePrices()"/>
      <button class="btn btn-primary" onclick="searchThemePrices()" id="theme-price-btn">조회</button>
    </div>
    <div id="theme-price-result" style="margin-top:14px;"></div>
  </div>

  <!-- 체크포인트 + 노트 2분할 -->
  <div class="section-label">체크포인트 / 노트</div>
  <div class="grid2" style="align-items:start;margin-bottom:10px;">
    <!-- 왼쪽: 체크포인트 -->
    <div class="content-card" style="margin-bottom:0;">
      <div class="content-header">
        <span class="content-title">☑ 오늘 체크포인트</span>
        <span class="content-date" id="checkpoint-date"></span>
      </div>
      <div class="tab-bar" id="cp-tabs">
        <button class="tab active" onclick="cpTab(this,'all')">전체</button>
        <button class="tab" onclick="cpTab(this,'indicator')">📌지표</button>
        <button class="tab" onclick="cpTab(this,'sector')">📌섹터</button>
        <button class="tab" onclick="cpTab(this,'kospi')">📌코스피</button>
        <button class="tab" onclick="cpTab(this,'kosdaq')">📌코스닥</button>
        <button class="tab" onclick="cpTab(this,'after')">📌시간외</button>
      </div>
      <div class="content-body" id="checkpoint-body"><span class="content-empty">텔레그램 봇으로 체크포인트를 올리면 여기에 표시됩니다.</span></div>
    </div>
    <!-- 오른쪽: 노트 -->
    <div class="content-card" style="margin-bottom:0;">
      <div class="content-header">
        <span class="content-title">📓 오늘의 노트</span>
        <div style="display:flex;gap:6px;align-items:center;">
          <span class="saved-badge" id="note-badge">✓ 저장됨</span>
          <button class="btn btn-green" onclick="saveNote()">저장</button>
          <button class="btn" onclick="clearNote()" style="color:#d63031;border-color:#fab1a0;">↺ 초기화</button>
        </div>
      </div>
      <div class="richtext-toolbar" data-target="note-rich">
        <button onclick="rtCmd(this,'bold')" title="굵게 (Cmd/Ctrl+B)"><b>B</b></button>
        <button onclick="rtCmd(this,'italic')" title="기울임 (Cmd/Ctrl+I)"><i>I</i></button>
        <button onclick="rtCmd(this,'underline')" title="밑줄 (Cmd/Ctrl+U)"><u>U</u></button>
        <button onclick="rtCmd(this,'strikeThrough')" title="취소선"><s>S</s></button>
        <span class="rt-sep"></span>
        <button onclick="rtHighlight(this,'#fff3a0')" title="노란색 하이라이트 (Cmd/Ctrl+Shift+H)" style="background:#fff3a0;">H</button>
        <button onclick="rtHighlight(this,'#ffd6d6')" title="분홍색 하이라이트" style="background:#ffd6d6;">H</button>
        <button onclick="rtHighlight(this,'#d6f0ff')" title="파란색 하이라이트" style="background:#d6f0ff;">H</button>
        <button onclick="rtHighlight(this,'transparent')" title="하이라이트 제거" style="background:white;">✕</button>
        <span class="rt-sep"></span>
        <button onclick="rtColor(this,'#d63031')" title="빨간 글자 (Cmd/Ctrl+Shift+R)" style="color:#d63031;">A</button>
        <button onclick="rtColor(this,'#0984e3')" title="파란 글자 (Cmd/Ctrl+Shift+B)" style="color:#0984e3;">A</button>
        <button onclick="rtColor(this,'#00b894')" title="초록 글자 (Cmd/Ctrl+Shift+G)" style="color:#00b894;">A</button>
        <button onclick="rtColor(this,'#2d3436')" title="기본색">A</button>
        <span class="rt-sep"></span>
        <button onclick="rtSize(this,'5')" title="큰 글씨 (Cmd/Ctrl+Shift+L)" style="font-size:16px;">A⁺</button>
        <button onclick="rtSize(this,'3')" title="기본 크기">A</button>
        <button onclick="rtSize(this,'2')" title="작은 글씨" style="font-size:10px;">A⁻</button>
        <span style="flex:1;"></span>
        <span style="font-size:10px;color:#7a8099;align-self:center;padding-right:6px;">⌘/Ctrl + B/I/U · ⇧+H(노랑) ⇧+L(크게) ⇧+R(빨강) ⇧+B(파랑) ⇧+G(초록)</span>
      </div>
      <div class="rich-editor" id="note-rich" contenteditable="true" data-placeholder="새로운 뉴스, 메모, 아이디어 등 자유롭게..." style="min-height:300px;"></div>
    </div>
  </div>

  <!-- 완대본 플로우 -->
  <div class="section-label">🎙️ ON AIR</div>
  <div class="content-card">
    <div class="content-header">
      <span class="content-title">🎙️ ON AIR</span>
      <div style="display:flex;gap:6px;align-items:center;">
        <span class="saved-badge" id="wdb-badge">✓ 저장됨</span>
        <button class="btn btn-green" onclick="saveWdaebon()">저장</button>
        <button class="btn" onclick="clearWdaebon()" style="color:#d63031;border-color:#fab1a0;">↺ 초기화</button>
      </div>
    </div>
    <div style="font-size:11px;color:#7a8099;margin-bottom:8px;">
      💡 Claude에서 정리한 코너별 플로우를 아래에 붙여넣기 하세요. 각 코너는 <code style="background:#f0f2f5;padding:2px 4px;border-radius:3px;">#1 제목</code>, <code style="background:#f0f2f5;padding:2px 4px;border-radius:3px;">#2 제목</code> 형식으로 구분돼요. <b>탭 내용을 직접 편집할 수 있어요.</b>
    </div>
    <textarea class="input-area" id="wdb-input" placeholder="예시:
#1 오프닝
이예은 앵커 오프닝 멘트...

#2 미국 증시 브리핑  
김예림 - 뉴욕 증시 마감 브리핑

#3 앵커 브리핑
..." style="min-height:120px;font-family:monospace;font-size:12px;" oninput="renderWdb()"></textarea>
    <div id="wdb-tabs-container" style="margin-top:14px;"></div>
  </div>

  <!-- 마감일지 -->
  <div class="section-label" style="margin-top:24px;">마감일지 / 리서치 리포트</div>
  <div class="grid2" style="align-items:start;">
    <!-- 왼쪽: 마감일지 -->
    <div class="content-card" style="margin-bottom:0;">
    <div class="content-header">
      <span class="content-title">📋 마감일지</span>
      <span class="content-date" id="closing-date"></span>
    </div>
    <div class="tab-bar" id="cl-tabs">
      <button class="tab active" onclick="clTab(this,'all')">전체</button>
      <button class="tab" onclick="clTab(this,'figure')">마감수치</button>
      <button class="tab" onclick="clTab(this,'factor')">지수팩터</button>
      <button class="tab" onclick="clTab(this,'supply')">수급</button>
      <button class="tab" onclick="clTab(this,'sector')">특징업종</button>
      <button class="tab" onclick="clTab(this,'stock')">특징주</button>
      <button class="tab" onclick="clTab(this,'schedule')">내일일정</button>
    </div>
    <div class="content-body" id="closing-body"><span class="content-empty">텔레그램 봇으로 마감일지를 올리면 여기에 표시됩니다.</span></div>
    </div>
    <!-- 오른쪽: PDF 뷰어 -->
    <div class="content-card" style="margin-bottom:0;">
      <div class="content-header">
        <span class="content-title">📄 리서치 리포트</span>
        <div style="display:flex;gap:6px;">
          <label class="btn btn-primary" style="cursor:pointer;font-size:12px;padding:6px 12px;">
            + 업로드
            <input type="file" id="pdf-upload-input" accept=".pdf" multiple style="display:none;" onchange="uploadPDFs(this)"/>
          </label>
          <button class="btn" onclick="clearAllPDFs()" style="color:#d63031;border-color:#fab1a0;font-size:12px;padding:6px 12px;">↺ 전체삭제</button>
        </div>
      </div>
      <div class="tab-bar" id="pdf-tabs" style="flex-wrap:wrap;"></div>
      <div id="pdf-viewer" style="width:100%;height:500px;border-radius:8px;overflow:hidden;background:#f0f2f5;display:flex;align-items:center;justify-content:center;">
        <span class="content-empty">PDF를 업로드해주세요</span>
      </div>
    </div>
  </div>

  <!-- 주간 캘린더 -->
  <div class="section-label">📅 주간 일정 캘린더</div>
  <div class="content-card">
    <div class="content-header">
      <span class="content-title">📅 이번 주 주요 일정</span>
      <div style="display:flex;gap:6px;align-items:center;">
        <span class="saved-badge" id="cal-badge">✓ 저장됨</span>
        <button class="btn btn-primary" onclick="parseCalendar()" id="cal-btn">✦ AI 정리</button>
        <button class="btn" onclick="clearCalendar()" style="color:#d63031;border-color:#fab1a0;">↺ 초기화</button>
      </div>
    </div>
    <textarea class="input-area" id="cal-input" placeholder="주간 일정 텍스트 붙여넣기..." style="min-height:100px;"></textarea>
    <div id="cal-result" style="margin-top:14px;"></div>
  </div>

  <!-- 출연자 DB 검색 -->
  <div class="section-label">👤 출연자 DB 검색</div>
  <div class="content-card">
    <div class="content-header">
      <span class="content-title">👤 출연자 / 발언 검색</span>
      <a href="https://docs.google.com/spreadsheets/d/1PENAycUyJS0WDhvC8aXHesHxmaXTq724261aWDnsMHc/edit?gid=437534302" target="_blank" class="btn" style="font-size:12px;padding:6px 12px;">📊 DB 바로가기</a>
    </div>
    <div class="input-row">
      <input class="input-line" id="guest-input" placeholder="예) ㅇㅇㅇ / 삼성전자 / 반도체" style="flex:1;"
        onkeydown="if(event.key==='Enter')searchGuest()"/>
      <button class="btn btn-primary" onclick="searchGuest()" id="guest-btn">검색</button>
    </div>
    <div id="guest-result" style="margin-top:14px;"></div>
  </div>

<!-- 표현 사전 -->
  <div class="section-label">📖 Encyclopedia</div>
  <div class="content-card">
    <div class="content-header">
      <span class="content-title">📖 Encyclopedia</span>
      <a href="https://docs.google.com/spreadsheets/d/1_2hIjvp2MqjHNLcv0JTn1yWgC4vB5zIzwkUS_c4cqUs/edit" target="_blank" class="btn" style="font-size:12px;padding:6px 12px;">📊 사전 바로가기</a>
    </div>
    <div class="input-row">
      <input class="input-line" id="encyc-input" placeholder="예) 급락 / 금리인상 / 반도체" style="flex:1;"
        onkeydown="if(event.key==='Enter')searchEncyc()"/>
      <button class="btn btn-primary" onclick="searchEncyc()" id="encyc-btn">검색</button>
    </div>
    <div id="encyc-result" style="margin-top:14px;"></div>
  </div>

    <div style="height:32px;"></div>
</div>

<script>
function updateClock(){
  const kst=new Date(new Date().toLocaleString('en-US',{timeZone:'Asia/Seoul'}));
  const p=n=>String(n).padStart(2,'0');
  document.getElementById('clock').textContent='KST '+p(kst.getHours())+':'+p(kst.getMinutes())+':'+p(kst.getSeconds());
}
setInterval(updateClock,1000);updateClock();

function fmt(v,d=2){
  if(v===null||v===undefined)return'—';
  return Number(v).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});
}
function cls(c){return c>0?'up':c<0?'dn':'flat';}
function sgn(c){return c>=0?'+':'';}

function renderM(iv,ic,val,chg){
  const ve=document.getElementById(iv);
  const ce=document.getElementById(ic);
  if(!ve)return;
  ve.textContent=(val!==null&&val!==undefined)?fmt(val):'—';
  if(ce&&chg!==null&&chg!==undefined)
    ce.innerHTML='<span class="'+cls(chg)+'">'+sgn(chg)+fmt(chg)+'%</span>';
}

function fmtSup(v){
  if(v===null||v===undefined||v==='')return'—';
  const n=parseInt(v);if(isNaN(n))return String(v);
  const a=Math.abs(n);
  const s=a>=1000000?(a/1000000).toFixed(1)+'M':a>=1000?(a/1000).toFixed(0)+'K':String(a);
  return(n>=0?'+':'-')+s;
}

async function loadMarket(){
  try{
    const d=await fetch('/api/market').then(r=>r.json());
    renderM('kospi-val','kospi-chg',d.kospi?.value,parseFloat(d.kospi?.change));
    renderM('kosdaq-val','kosdaq-chg',d.kosdaq?.value,parseFloat(d.kosdaq?.change));
    renderM('nasdaq-val','nasdaq-chg',d.nasdaq?.value,d.nasdaq?.change);
    renderM('dow-val','dow-chg',d.dow?.value,d.dow?.change);
    renderM('sp500-val','sp500-chg',d.sp500?.value,d.sp500?.change);
    renderM('ewy-val','ewy-chg',d.ewy?.value,d.ewy?.change);
    renderM('wti-val','wti-chg',d.wti?.value,d.wti?.change);
    renderM('brent-val','brent-chg',d.brent?.value,d.brent?.change);
    renderM('vix-val','vix-chg',d.vix?.value,d.vix?.change);
    renderM('sox-val','sox-chg',d.sox?.value,d.sox?.change);
    // 10년물은 소수점 2자리
    const tnxEl=document.getElementById('tnx-val');
    const tnxChgEl=document.getElementById('tnx-chg');
    if(tnxEl&&d.tnx?.value!==null){
      tnxEl.textContent=fmt(d.tnx?.value)+'%';
      if(tnxChgEl&&d.tnx?.change!==null)
        tnxChgEl.innerHTML='<span class="'+cls(d.tnx.change)+'">'+sgn(d.tnx.change)+fmt(d.tnx.change)+'%p</span>';
    }
    renderM('usdkrw-val','usdkrw-chg',d.usdkrw?.value,d.usdkrw?.change);
    renderM('gold-val','gold-chg',d.gold?.value,d.gold?.change);
    renderM('dxy-val','dxy-chg',d.dxy?.value,d.dxy?.change);
    renderM('dram-val','dram-chg',d.dram?.value,d.dram?.change);
    ['kospi','kosdaq'].forEach(m=>{
      const el=document.getElementById(m+'-sup');if(!el)return;
      const fv=d[m]?.foreign,iv=d[m]?.institution;
      const fvn=parseInt(fv),ivn=parseInt(iv);
      const indv=d[m]?.individual,indvn=parseInt(indv);
      el.innerHTML='<span>개인 <b class="'+(indvn>0?'up':indvn<0?'dn':'flat')+'">'+fmtSup(indv)+'</b></span>'+
                   '<span>외인 <b class="'+(fvn>0?'up':fvn<0?'dn':'flat')+'">'+fmtSup(fv)+'</b></span>'+
                   '<span>기관 <b class="'+(ivn>0?'up':ivn<0?'dn':'flat')+'">'+fmtSup(iv)+'</b></span>';
    });
  }catch(e){console.error(e);}
}

async function loadSector(){
  try{
    const d=await fetch('/api/sector').then(r=>r.json());
    const render=(id,arr)=>{
      const el=document.getElementById(id);if(!el)return;
      if(!arr||!arr.length){el.innerHTML='<span class="content-empty">데이터 없음</span>';return;}
      el.innerHTML=arr.map(e=>'<div class="etf-row"><span class="etf-name">'+e.name+'</span>'+
        '<span class="etf-chg '+cls(e.change)+'">'+sgn(e.change)+fmt(e.change)+'%</span></div>').join('');
    };
    render('sector-top',d.top5);render('sector-bot',d.bot5);
  }catch(e){}
}

async function loadPost(type,bid,did){
  try{
    const d=await fetch('/api/post/'+type).then(r=>r.json());
    if(d.content){
      const b=document.getElementById(bid),dt=document.getElementById(did);
      if(dt)dt.textContent=d.date||'';
      if(b){
        b.textContent=d.content;
        if(type==='checkpoint') _cpRaw=d.content;
        if(type==='closing') _clRaw=d.content;
      }
    }
  }catch(e){}
}

async function loadFutures(){
  try{
    const d=await fetch('/api/post/futures').then(r=>r.json());
    if(d.content){
      const el=document.getElementById('futures-display');
      if(el)el.textContent=d.content;
      const inp=document.getElementById('futures-input');
      if(inp)inp.value=d.content;
    }
  }catch(e){}
}

async function loadAutoFutures(){
  try{
    const d=await fetch('/api/market').then(r=>r.json());
    if(d.futures_auto){
      const el=document.getElementById('futures-display');
      const inp=document.getElementById('futures-input');
      if(el && (!el.textContent || el.textContent==='—')) {
        el.textContent=d.futures_auto;
      }
      const autoEl=document.getElementById('futures-auto-val');
      if(autoEl) autoEl.textContent='KIS: '+d.futures_auto;
    }
  }catch(e){}
}

async function clearFutures(){
  await fetch('/api/post/futures',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({content:'',date:new Date().toISOString().slice(0,10)})});
  document.getElementById('futures-display').textContent='—';
  document.getElementById('futures-input').value='';
}

async function saveFutures(){
  const val=document.getElementById('futures-input').value.trim();
  if(!val)return;
  await fetch('/api/post/futures',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({content:val,date:new Date().toISOString().slice(0,10)})
  });
  document.getElementById('futures-display').textContent=val;
  const badge=document.getElementById('futures-badge');
  badge.style.display='inline';
  setTimeout(()=>badge.style.display='none',2000);
}







let _reportTab = 'up';

function reportTab(btn, key){
  document.querySelectorAll('#rtab-up,#rtab-dn,#rtab-feature').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  _reportTab = key;
  ['up','dn','feature'].forEach(k=>{
    const el=document.getElementById('report-'+k+'-input');
    if(el) el.style.display = k===key?'block':'none';
  });
}

async function saveReport(){
  const val=document.getElementById('report-input')?.value.trim();
  if(val===undefined) return;
  await fetch('/api/post/report',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({content:val,date:new Date().toISOString().slice(0,10)})});
  const badge=document.getElementById('report-badge');
  badge.style.display='inline';setTimeout(()=>badge.style.display='none',2000);
}

async function clearReport(){
  if(!confirm('리포트 전체 초기화할까요?')) return;
  await fetch('/api/report/clear',{method:'POST'});
  ['up','dn','feature'].forEach(k=>{
    const el=document.getElementById('report-'+k+'-input');
    if(el) el.value='';
  });
}

async function loadReport(){
  try{
    const d=await fetch('/api/post/report').then(r=>r.json());
    if(d.content){
      const el=document.getElementById('report-input');
      if(el) el.value=d.content;
    }
  }catch(e){}
}

async function searchKstock(){
  const q=document.getElementById('kstock-input').value.trim();
  if(!q)return;
  const btn=document.getElementById('kstock-btn');
  const result=document.getElementById('kstock-result');
  btn.classList.add('ls');btn.innerHTML='<span class="spinner"></span>';
  result.innerHTML='<span class="content-empty">검색 중...</span>';
  try{
    const d=await fetch('/api/kstock/search?q='+encodeURIComponent(q)).then(r=>r.json());
    if(d.error){
      result.innerHTML='<span class="content-empty">오류: '+d.error+'</span>';
    }else{
      result.innerHTML='<div class="content-body" style="max-height:400px;">'+d.result.replace(/\n/g,'<br>').replace(/🔗 (https?:\/\/[^\s<]+)/g,'🔗 <a href="$1" target="_blank" style="color:#0984e3;word-break:break-all;">$1</a>')+'</div>';
      const chartDiv=document.getElementById('kstock-chart');
      if(d.code && chartDiv){
        chartDiv.style.display='block';
        const rawCode = d.code.replace('KRX:','');
        chartDiv.style.display='block';
        const priceHtml = d.price ? '<div style=\"padding:14px 16px;background:#f8f9fa;border-radius:10px;margin-bottom:10px;\">'+
          '<div style=\"font-size:11px;font-weight:700;color:#7a8099;letter-spacing:.08em;margin-bottom:4px;\">현재가</div>'+
          '<div style=\"font-size:24px;font-weight:700;color:#1a1d23;\">'+d.price+'</div>'+
          '</div>' : '';
        chartDiv.innerHTML=priceHtml+
          '<a href=\"https://m.stock.naver.com/domestic/stock/'+rawCode+'/chart\" target=\"_blank\" class=\"btn btn-primary\" style=\"width:100%;justify-content:center;font-size:14px;padding:16px;margin-bottom:8px;display:flex;\">📈 네이버 증권 차트 →</a>'+
          '';
      } else if(chartDiv){ chartDiv.style.display='none'; }
    }
  }catch(e){result.innerHTML='<span class="content-empty">네트워크 오류</span>';}
  btn.classList.remove('ls');btn.innerHTML='검색';
}

// 투두리스트
let _todos = [];

function renderTodos(){
  const list = document.getElementById('todo-list');
  if(!list) return;
  if(!_todos.length){
    list.innerHTML='<div style="color:#b2bec3;font-size:13px;padding:4px 0;">할일이 없어요 😊</div>';
    return;
  }
  list.innerHTML = _todos.map((t,i)=>
    '<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #f0f2f5;">'+
    '<input type="checkbox" '+(t.done?'checked':'')+' onchange="toggleTodo('+i+')" style="width:16px;height:16px;cursor:pointer;accent-color:#00b894;"/>'+
    '<span style="flex:1;font-size:13px;'+(t.done?'text-decoration:line-through;color:#b2bec3;':'')+'" onclick="editTodo('+i+')" >'+t.text+'</span>'+
    '<button onclick="deleteTodo('+i+')" style="border:none;background:none;color:#dfe6e9;cursor:pointer;font-size:14px;">✕</button>'+
    '</div>'
  ).join('');
}

function toggleTodo(i){
  _todos[i].done = !_todos[i].done;
  saveTodoDB();
  renderTodos();
}

function deleteTodo(i){
  _todos.splice(i,1);
  saveTodoDB();
  renderTodos();
}

function editTodo(i){
  const newText = prompt('수정:', _todos[i].text);
  if(newText && newText.trim()){
    _todos[i].text = newText.trim();
    saveTodoDB();
    renderTodos();
  }
}

function addTodoItem(){
  const inp = document.getElementById('todo-new-input');
  const val = inp?.value.trim();
  if(!val) return;
  _todos.push({text:val, done:false});
  inp.value='';
  saveTodoDB();
  renderTodos();
}

async function saveTodoDB(){
  await fetch('/api/post/todo',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({content:JSON.stringify(_todos),date:new Date().toISOString().slice(0,10)})});
  const badge=document.getElementById('todo-badge');
  if(badge){badge.style.display='inline';setTimeout(()=>badge.style.display='none',1500);}
}

async function loadTodo(){
  try{
    const d=await fetch('/api/post/todo').then(r=>r.json());
    if(d.content){
      try{ _todos=JSON.parse(d.content); }catch(e){ _todos=[]; }
    }
    renderTodos();
  }catch(e){ renderTodos(); }
}

// 메모
async function saveMemo(){
  const val=document.getElementById('memo-input').value.trim();
  await fetch('/api/post/memo',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({content:val,date:new Date().toISOString().slice(0,10)})});
  const badge=document.getElementById('memo-badge');
  badge.style.display='inline';setTimeout(()=>badge.style.display='none',2000);
}
async function clearMemo(){
  if(!confirm('메모 초기화할까요?'))return;
  await fetch('/api/memo/clear',{method:'POST'});
  document.getElementById('memo-input').value='';
}
async function loadMemo(){
  try{
    const d=await fetch('/api/post/memo').then(r=>r.json());
    if(d.content) document.getElementById('memo-input').value=d.content;
  }catch(e){}
}
// 리치 텍스트 편집 명령
function rtGetTarget(btn){
  const tb = btn.closest('.richtext-toolbar');
  return document.getElementById(tb.dataset.target);
}
function rtCmd(btn, cmd){
  const el = rtGetTarget(btn);
  el.focus();
  document.execCommand(cmd, false, null);
}
function rtHighlight(btn, color){
  const el = rtGetTarget(btn);
  el.focus();
  document.execCommand('backColor', false, color);
}
function rtColor(btn, color){
  const el = rtGetTarget(btn);
  el.focus();
  document.execCommand('foreColor', false, color);
}
function rtSize(btn, size){
  const el = rtGetTarget(btn);
  el.focus();
  document.execCommand('fontSize', false, size);
}

// 단축키 등록
document.addEventListener('keydown', function(e){
  const active = document.activeElement;
  if(!active || !active.classList.contains('rich-editor')) return;
  const mod = e.metaKey || e.ctrlKey;
  if(!mod || !e.shiftKey) return;
  const key = e.key.toLowerCase();
  // Cmd+Shift+H = 노란 하이라이트
  if(key === 'h'){
    e.preventDefault();
    document.execCommand('backColor', false, '#fff3a0');
  }
  // Cmd+Shift+L = 큰 글자
  else if(key === 'l'){
    e.preventDefault();
    document.execCommand('fontSize', false, '5');
  }
  // Cmd+Shift+R = 빨간 글자
  else if(key === 'r'){
    e.preventDefault();
    document.execCommand('foreColor', false, '#d63031');
  }
  // Cmd+Shift+B = 파란 글자
  else if(key === 'b'){
    e.preventDefault();
    document.execCommand('foreColor', false, '#0984e3');
  }
  // Cmd+Shift+G = 초록 글자
  else if(key === 'g'){
    e.preventDefault();
    document.execCommand('foreColor', false, '#00b894');
  }
}, true);

async function saveNote(){
  const el = document.getElementById('note-rich');
  const val = el ? el.innerHTML : '';
  await fetch('/api/post/note',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({content:val,date:new Date().toISOString().slice(0,10)})});
  const badge=document.getElementById('note-badge');
  badge.style.display='inline';setTimeout(()=>badge.style.display='none',2000);
}

async function clearNote(){
  if(!confirm('노트 초기화할까요?'))return;
  await fetch('/api/note/clear',{method:'POST'});
  const el = document.getElementById('note-rich');
  if(el) el.innerHTML='';
}

async function loadNote(){
  try{
    const d=await fetch('/api/post/note').then(r=>r.json());
    if(d.content){
      const el = document.getElementById('note-rich');
      if(el) el.innerHTML = d.content;
    }
  }catch(e){}
}

let _calData = null;

async function saveCalendarDB(){
  if(!_calData) return;
  await fetch('/api/calendar/update',{
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({data: _calData})
  });
}

function renderCalendar(data){
  _calData = data;
  const result = document.getElementById('cal-result');
  if(!data || !data.days || !data.days.length){
    result.innerHTML='<span class="content-empty">일정이 없어요.</span>';
    return;
  }
  const weekLabel = data.week_label || '';
  let html = '';
  if(weekLabel){
    html += '<div style="font-size:12px;font-weight:700;color:#7a8099;margin-bottom:10px;">' + weekLabel + '</div>';
  }

  html += '<div class="tab-bar" id="cal-tabs">';
  data.days.forEach(function(day, i){
    const active = i===0 ? 'active' : '';
    const shortDate = day.date.match(/\d+일/) ? day.date.match(/\d+일/)[0] : day.date.slice(0,6);
    const dayName = day.date.match(/[월화수목금토일]요일/) ? day.date.match(/[월화수목금토일]요일/)[0] : '';
    html += '<button class="tab ' + active + '" onclick="calTab(this,\'cal-day-' + i + '\')">' + shortDate + ' ' + dayName + '</button>';
  });
  html += '</div>';

  data.days.forEach(function(day, i){
    const display = i===0 ? 'block' : 'none';
    html += '<div id="cal-day-' + i + '" style="display:' + display + ';">';
    html += '<div style="font-size:13px;font-weight:700;color:#2d3436;margin-bottom:8px;">' + day.date + '</div>';

    // Items
    html += '<div id="cal-items-' + i + '">';
    (day.items||[]).forEach(function(item,j){
      const safeItem = item.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
      html += '<div style="padding:6px 0;border-bottom:1px solid #f0f2f5;display:flex;align-items:flex-start;gap:6px;">';
      html += '<span style="color:#e8b84b;font-weight:700;font-size:13px;min-width:18px;">' + (j+1) + '.</span>';
      html += '<input value="' + safeItem + '" style="flex:1;border:none;background:transparent;font-size:13px;color:#2d3436;padding:0;" onchange="_calData.days[' + i + '].items[' + j + ']=this.value;saveCalendarDB()"/>';
      html += '<button onclick="deleteCalItem(' + i + ',' + j + ')" style="border:none;background:none;color:#b2bec3;cursor:pointer;font-size:14px;padding:0 2px;">✕</button>';
      html += '</div>';
    });
    html += '</div>';

    // Add item
    html += '<div style="margin-top:8px;">';
    html += '<input id="cal-new-' + i + '" class="input-area" placeholder="+ 일정 추가..." style="min-height:auto;padding:6px 10px;font-size:13px;" onkeydown="if(event.key===\'Enter\'){addCalItem(' + i + ');event.preventDefault();}"/>';
    html += '<button class="btn" onclick="addCalItem(' + i + ')" style="margin-top:4px;font-size:12px;padding:5px 10px;">+ 추가</button>';
    html += '</div>';

    // Guests
    html += '<div style="margin-top:12px;border-top:1px solid #f0f2f5;padding-top:10px;">';
    html += '<div style="font-size:11px;font-weight:700;color:#7a8099;margin-bottom:6px;">👤 출연자</div>';
    html += '<div id="cal-guests-' + i + '">';
    (day.guests||[]).forEach(function(guest,j){
      const safeGuest = guest.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
      html += '<div style="padding:5px 0;border-bottom:1px solid #f0f2f5;display:flex;align-items:center;gap:6px;">';
      html += '<span style="color:#0984e3;font-weight:700;font-size:12px;min-width:18px;">' + (j+1) + '.</span>';
      html += '<input value="' + safeGuest + '" style="flex:1;border:none;background:transparent;font-size:13px;color:#2d3436;padding:0;" onchange="_calData.days[' + i + '].guests[' + j + ']=this.value;saveCalendarDB()"/>';
      html += '<button onclick="deleteCalGuest(' + i + ',' + j + ')" style="border:none;background:none;color:#b2bec3;cursor:pointer;font-size:14px;padding:0 2px;">✕</button>';
      html += '</div>';
    });
    html += '</div>';
    html += '<div style="margin-top:6px;display:flex;gap:6px;">';
    html += '<input id="cal-new-guest-' + i + '" class="input-area" placeholder="+ 출연자 추가... (이름 - 주제)" style="min-height:auto;padding:6px 10px;font-size:13px;flex:1;" onkeydown="if(event.key===\'Enter\'){addCalGuest(' + i + ');event.preventDefault();}"/>';
    html += '<button class="btn" onclick="addCalGuest(' + i + ')" style="font-size:12px;padding:5px 10px;">+ 추가</button>';
    html += '</div>';
    html += '</div>';

    html += '</div>';
  });

  result.innerHTML = html;
}

function deleteCalGuest(dayIdx, guestIdx){
  if(!_calData) return;
  _calData.days[dayIdx].guests = _calData.days[dayIdx].guests || [];
  _calData.days[dayIdx].guests.splice(guestIdx, 1);
  saveCalendarDB();
  renderCalendar(_calData);
  const tabs = document.querySelectorAll('#cal-tabs .tab');
  if(tabs[dayIdx]) calTab(tabs[dayIdx], 'cal-day-'+dayIdx);
}

function addCalGuest(dayIdx){
  const inp = document.getElementById('cal-new-guest-'+dayIdx);
  const val = inp?.value.trim();
  if(!val || !_calData) return;
  _calData.days[dayIdx].guests = _calData.days[dayIdx].guests || [];
  _calData.days[dayIdx].guests.push(val);
  saveCalendarDB();
  renderCalendar(_calData);
  const tabs = document.querySelectorAll('#cal-tabs .tab');
  if(tabs[dayIdx]) calTab(tabs[dayIdx], 'cal-day-'+dayIdx);
}

function calTab(btn, panelId){
  document.querySelectorAll('#cal-tabs .tab').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#cal-result [id^="cal-day-"]').forEach(el=>el.style.display='none');
  const el=document.getElementById(panelId);
  if(el)el.style.display='block';
}

async function parseCalendar(){
  const raw=document.getElementById('cal-input').value.trim();
  if(!raw)return;
  const btn=document.getElementById('cal-btn');
  btn.classList.add('ls');btn.innerHTML='<span class="spinner"></span> AI 정리 중...';
  try{
    const d=await fetch('/api/calendar/parse',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({content:raw})
    }).then(r=>r.json());
    if(d.error){
      document.getElementById('cal-result').innerHTML='<span class="content-empty">오류: '+d.error+'</span>';
    } else {
      // Merge with existing data if exists
      if(_calData && _calData.days){
        d.days.forEach(newDay => {
          const existing = _calData.days.find(d2 => d2.day_key === newDay.day_key);
          if(existing){
            existing.items = [...(existing.items||[]), ...(newDay.items||[])];
          }
        });
        renderCalendar(_calData);
      } else {
        renderCalendar(d);
      }
      document.getElementById('cal-input').value='';
      const badge=document.getElementById('cal-badge');
      badge.style.display='inline';setTimeout(()=>badge.style.display='none',2000);
    }
  }catch(e){document.getElementById('cal-result').innerHTML='<span class="content-empty">오류 발생</span>';}
  btn.classList.remove('ls');btn.innerHTML='✦ AI 정리';
}

async function clearCalendar(){
  if(!confirm('캘린더 초기화할까요?'))return;
  await fetch('/api/calendar/clear',{method:'POST'});
  _calData = null;
  document.getElementById('cal-input').value='';
  document.getElementById('cal-result').innerHTML='';
}

// 완대본 플로우 (텍스트 붙여넣기 → 탭 자동 분리)
let _wdbActiveTab = 0;

function parseWdb(text){
  if(!text||!text.trim()) return [];
  // #1 제목, #2 제목 형식으로 분리
  const lines = text.split('\n');
  const corners = [];
  let current = null;
  for(const line of lines){
    const match = line.match(/^\s*#(\d+)\s*\.?\s*(.*)/);
    if(match){
      if(current) corners.push(current);
      current = {number:match[1], title:match[2].trim()||'코너'+match[1], body:[], guests:[]};
    } else if(current){
      current.body.push(line);
    } else if(line.trim()){
      if(!corners.length) corners.push({number:'0', title:'인트로', body:[line], guests:[]});
      else corners[0].body.push(line);
    }
  }
  if(current) corners.push(current);
  
  // 각 코너에서 출연자 추출 ("이름 | 직함" 형식) - 제목 + body 둘 다 검사
  corners.forEach(c=>{
    const seen = new Set();
    c.guests = [];
    // 검사 대상: title 줄 + body 전체
    const searchLines = [c.title, ...(c.body || [])];
    for(const line of searchLines){
      // 한 줄에 여러 명이 있을 수도 있으니 global 매칭
      const re = /([가-힣]{2,4})\s*[|｜]\s*([^|｜\n]+?)(?=(?:\s*[+＋]|\s*,|\s*\/|\s*$|\s{2,}))/g;
      let m;
      while((m = re.exec(line)) !== null){
        const name = m[1].trim();
        let title = m[2].trim();
        // 앞뒤 불필요한 기호 제거
        title = title.replace(/[—–\-]+$/, '').replace(/^[—–\-]+/, '').trim();
        // 뒤쪽 (전화연결) 같은 괄호는 유지하되, 그 뒤 잡 텍스트는 제거
        title = title.replace(/\s*\(([^)]+)\).*$/, ' ($1)');
        if(!title) continue;
        const key = name + '|' + title;
        if(!seen.has(key)){
          seen.add(key);
          c.guests.push({name, title});
        }
      }
      // fallback: 단일 "이름 | 직함" 
      if(!c.guests.length){
        const simple = line.match(/([가-힣]{2,4})\s*[|｜]\s*(.+?)(?:\s*[—–\-(]|\s*$)/);
        if(simple){
          const name = simple[1].trim();
          const title = simple[2].trim();
          const key = name + '|' + title;
          if(title && !seen.has(key)){
            seen.add(key);
            c.guests.push({name, title});
          }
        }
      }
    }
    c.guests = c.guests.slice(0, 4);
  });
  return corners;
}

function renderWdb(){
  const text = document.getElementById('wdb-input').value;
  const corners = parseWdb(text);
  const box = document.getElementById('wdb-tabs-container');
  if(!corners.length){
    box.innerHTML = '';
    return;
  }
  if(_wdbActiveTab >= corners.length) _wdbActiveTab = 0;
  let html = '<div class="tab-bar" style="flex-wrap:wrap;">';
  corners.forEach((c,i)=>{
    html += '<button class="tab'+(i===_wdbActiveTab?' active':'')+'" onclick="wdbShowTab('+i+')">#'+c.number+' '+c.title+'</button>';
  });
  html += '</div>';
  // 리치 툴바 + 에디터
  html += '<div class="richtext-toolbar" data-target="wdb-tab-edit">';
  html += '<button onclick="rtCmd(this,\'bold\')" title="굵게 (Cmd/Ctrl+B)"><b>B</b></button>';
  html += '<button onclick="rtCmd(this,\'italic\')" title="기울임 (Cmd/Ctrl+I)"><i>I</i></button>';
  html += '<button onclick="rtCmd(this,\'underline\')" title="밑줄 (Cmd/Ctrl+U)"><u>U</u></button>';
  html += '<button onclick="rtCmd(this,\'strikeThrough\')" title="취소선"><s>S</s></button>';
  html += '<span class="rt-sep"></span>';
  html += '<button onclick="rtHighlight(this,\'#fff3a0\')" title="노란 하이라이트 (Cmd+Shift+Y)" style="background:#fff3a0;">H</button>';
  html += '<button onclick="rtHighlight(this,\'#ffd6d6\')" title="분홍 하이라이트" style="background:#ffd6d6;">H</button>';
  html += '<button onclick="rtHighlight(this,\'#d6f0ff\')" title="파랑 하이라이트" style="background:#d6f0ff;">H</button>';
  html += '<button onclick="rtHighlight(this,\'transparent\')" title="하이라이트 제거" style="background:white;">✕</button>';
  html += '<span class="rt-sep"></span>';
  html += '<button onclick="rtColor(this,\'#d63031\')" title="빨간색 (Cmd+Shift+R)" style="color:#d63031;">A</button>';
  html += '<button onclick="rtColor(this,\'#0984e3\')" title="파랑색" style="color:#0984e3;">A</button>';
  html += '<button onclick="rtColor(this,\'#00b894\')" title="초록색" style="color:#00b894;">A</button>';
  html += '<button onclick="rtColor(this,\'#2d3436\')" title="기본색">A</button>';
  html += '<span class="rt-sep"></span>';
  html += '<button onclick="rtSize(this,\'5\')" title="큰 글씨 (Cmd+Shift+L)" style="font-size:16px;">A⁺</button>';
  html += '<button onclick="rtSize(this,\'3\')" title="기본 크기">A</button>';
  html += '<button onclick="rtSize(this,\'2\')" title="작은 글씨" style="font-size:10px;">A⁻</button>';
  html += '<span style="flex:1;"></span>';
  html += '<span style="font-size:10px;color:#7a8099;align-self:center;padding-right:6px;">⌘/Ctrl + B/I/U · ⇧+H(노랑) ⇧+L(크게) ⇧+R(빨강) ⇧+B(파랑) ⇧+G(초록)</span>';
  html += '</div>';
  // 출연자 카드
  const active = corners[_wdbActiveTab] || corners[0];
  if(active.guests && active.guests.length){
    html += '<div style="margin-bottom:10px;padding:10px 14px;background:linear-gradient(135deg,#fdfbf5,#fff);border-radius:10px;border:1.5px solid #e8b84b;display:flex;flex-wrap:wrap;gap:10px;align-items:center;">';
    html += '<span style="font-size:11px;font-weight:700;color:#e8b84b;letter-spacing:.05em;">👤 출연자</span>';
    active.guests.forEach(g=>{
      html += '<span style="display:inline-flex;align-items:center;gap:6px;padding:4px 10px;background:white;border-radius:20px;border:1px solid #e8b84b;">';
      html += '<span style="font-size:13px;font-weight:700;color:#1a1d23;">'+g.name+'</span>';
      if(g.title){
        html += '<span style="font-size:11px;color:#7a8099;">|</span>';
        html += '<span style="font-size:12px;color:#636e72;">'+g.title+'</span>';
      }
      html += '</span>';
    });
    html += '</div>';
  }
  // 에디터
  const activeText = (active.body || []).join('\n').replace(/^\s*\n|\n\s*$/g,'') || '';
  // 이미 저장된 html이 있으면 복원
  const savedHtml = _wdbTabHtml[_wdbActiveTab];
  const initialHtml = savedHtml || activeText.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
  html += '<div class="rich-editor" id="wdb-tab-edit" contenteditable="true" data-idx="'+_wdbActiveTab+'" '+
    'style="min-height:240px;font-size:13px;line-height:1.7;border-left:3px solid #e8b84b;background:#fdfbf5;" '+
    'oninput="onWdbTabEdit(this)" data-placeholder="이 코너 내용을 직접 편집하세요...">'+
    initialHtml + '</div>';
  box.innerHTML = html;
}

// 탭별 HTML 저장
let _wdbTabHtml = {};

function onWdbTabEdit(editor){
  const idx = parseInt(editor.dataset.idx);
  // HTML 저장
  _wdbTabHtml[idx] = editor.innerHTML;
  // 텍스트만 원본 textarea에 반영 (재파싱용)
  const plain = editor.innerText;
  const fullText = document.getElementById('wdb-input').value;
  const corners = parseWdb(fullText);
  if(!corners[idx]) return;
  corners[idx].body = plain.split('\n');
  const rebuilt = corners.map(c=>{
    const header = c.number === '0' ? '' : '#'+c.number+' '+c.title;
    const body = c.body.join('\n');
    return header ? header+'\n'+body : body;
  }).join('\n\n');
  document.getElementById('wdb-input').value = rebuilt;
}

function wdbShowTab(i){
  _wdbActiveTab = i;
  renderWdb();
}

async function saveWdaebon(){
  // 현재 편집 중인 탭의 HTML도 저장
  const currentEditor = document.getElementById('wdb-tab-edit');
  if(currentEditor){
    const idx = parseInt(currentEditor.dataset.idx);
    _wdbTabHtml[idx] = currentEditor.innerHTML;
  }
  const payload = {
    text: document.getElementById('wdb-input').value,
    tabHtml: _wdbTabHtml
  };
  await fetch('/api/post/wdaebon',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({content:JSON.stringify(payload),date:new Date().toISOString().slice(0,10)})
  });
  const badge=document.getElementById('wdb-badge');
  badge.style.display='inline';setTimeout(()=>badge.style.display='none',2000);
}

async function clearWdaebon(){
  if(!confirm('완대본 플로우 초기화할까요?'))return;
  await fetch('/api/post/wdaebon',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({content:'',date:new Date().toISOString().slice(0,10)})
  });
  document.getElementById('wdb-input').value='';
  document.getElementById('wdb-tabs-container').innerHTML='';
  _wdbTabHtml = {};
  _wdbActiveTab = 0;
}

async function loadWdaebon(){
  try{
    const d=await fetch('/api/post/wdaebon').then(r=>r.json());
    if(d.content){
      // JSON 형식이면 새 포맷, 아니면 구버전 plaintext
      let text = d.content;
      try{
        const payload = JSON.parse(d.content);
        if(payload && typeof payload === 'object' && payload.text !== undefined){
          text = payload.text;
          _wdbTabHtml = payload.tabHtml || {};
        }
      }catch(e){}
      document.getElementById('wdb-input').value = text;
      renderWdb();
    }
  }catch(e){}
}

async function loadCalendar(){
  try{
    const d=await fetch('/api/post/calendar').then(r=>r.json());
    if(d.content){
      const data=JSON.parse(d.content);
      renderCalendar(data);
    }
  }catch(e){}
}

async function searchEncyclopedia(){
  const q = document.getElementById('enc-input').value.trim();
  if(!q) return;
  const btn = document.getElementById('enc-btn');
  const result = document.getElementById('enc-result');
  btn.classList.add('ls'); btn.innerHTML='<span class="spinner"></span>';
  result.innerHTML='<span class="content-empty">검색 중...</span>';
  try{
    const d = await fetch('/api/encyclopedia/search?q='+encodeURIComponent(q)).then(r=>r.json());
    if(d.error){
      result.innerHTML='<span class="content-empty">오류: '+d.error+'</span>';
      return;
    }
    if(!d.results || !d.results.length){
      result.innerHTML='<span class="content-empty">검색 결과가 없어요.</span>';
      return;
    }
    let html = '<div style="font-size:11px;color:#7a8099;margin-bottom:10px;">'+d.results.length+'건 검색됨</div>';
    d.results.forEach(row=>{
      html += '<div style="padding:12px 14px;background:#f8f9fa;border-radius:10px;margin-bottom:8px;border-left:3px solid #0984e3;">';
      const 상황 = row['상황'] || '';
      const 주제 = row['주제(시장/섹터/종목)'] || row['주제'] || '';
      const 표현 = row['표현'] || '';
      if(상황) html += '<div style="font-size:11px;font-weight:700;color:#7a8099;margin-bottom:4px;">📌 '+상황+(주제?' · '+주제:'')+'</div>';
      if(표현) html += '<div style="font-size:14px;color:#1a1d23;line-height:1.7;">'+표현+'</div>';
      html += '</div>';
    });
    result.innerHTML = html;
  }catch(e){
    result.innerHTML='<span class="content-empty">네트워크 오류</span>';
  }
  btn.classList.remove('ls'); btn.innerHTML='검색';
}

// PDF functions
async function uploadPDFs(input){
  const files = Array.from(input.files);
  for(const file of files){
    const reader = new FileReader();
    reader.onload = async(e)=>{
      const base64 = e.target.result.split(',')[1];
      await fetch('/api/pdf/upload',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({name: file.name, data: base64})
      });
      loadPDFList();
    };
    reader.readAsDataURL(file);
  }
  input.value='';
}

async function loadPDFList(){
  const d = await fetch('/api/pdf/list').then(r=>r.json());
  const tabs = document.getElementById('pdf-tabs');
  if(!d.pdfs||!d.pdfs.length){
    tabs.innerHTML='';
    document.getElementById('pdf-viewer').innerHTML='<span class="content-empty">PDF를 업로드해주세요</span>';
    return;
  }
  tabs.innerHTML = d.pdfs.map((p,i)=>
    '<div style="display:flex;align-items:center;gap:2px;">'+
    '<button class="tab'+(i===0?' active':'')+'" onclick="showPDF('+p.id+',this)" id="pdf-tab-'+p.id+'">'+p.name.replace('.pdf','').slice(0,15)+'</button>'+
    '<button onclick="deletePDF('+p.id+')" style="border:none;background:none;color:#b2bec3;cursor:pointer;font-size:12px;padding:0 2px;">✕</button>'+
    '</div>'
  ).join('');
  if(d.pdfs.length) showPDF(d.pdfs[0].id, document.querySelector('#pdf-tabs .tab'));
}

async function showPDF(id, btn){
  document.querySelectorAll('#pdf-tabs .tab').forEach(b=>b.classList.remove('active'));
  if(btn) btn.classList.add('active');
  const viewer = document.getElementById('pdf-viewer');
  viewer.innerHTML='<span class="content-empty">로딩 중...</span>';
  const d = await fetch('/api/pdf/'+id).then(r=>r.json());
  if(d.data){
    viewer.innerHTML='<iframe src="data:application/pdf;base64,'+d.data+'" style="width:100%;height:500px;border:none;"></iframe>';
  }
}

async function clearAllPDFs(){
  if(!confirm('리포트 전체 삭제할까요?')) return;
  const d = await fetch('/api/pdf/list').then(r=>r.json());
  for(const p of (d.pdfs||[])){
    await fetch('/api/pdf/'+p.id+'/delete',{method:'POST'});
  }
  loadPDFList();
}

async function deletePDF(id){
  await fetch('/api/pdf/'+id+'/delete',{method:'POST'});
  loadPDFList();
}

async function searchThemePrices(){
  const q = document.getElementById('theme-input').value.trim();
  if(!q) return;
  const btn = document.getElementById('theme-price-btn');
  const result = document.getElementById('theme-price-result');
  btn.classList.add('ls'); btn.innerHTML='<span class="spinner"></span> 조회 중...';
  result.innerHTML='<span class="content-empty">시세 불러오는 중... (종목 수에 따라 10~20초 소요)</span>';
  try{
    const d = await fetch('/api/theme/prices?q='+encodeURIComponent(q)).then(r=>r.json());
    if(d.error){
      result.innerHTML='<span class="content-empty">오류: '+d.error+'</span>';
      return;
    }
    if(!d.stocks||!d.stocks.length){
      result.innerHTML='<span class="content-empty">"'+q+'" 테마 종목이 없어요.</span>';
      return;
    }
    let html = '<div style="font-size:11px;color:#7a8099;margin-bottom:10px;">'+d.query+' · '+d.count+'종목</div>';
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;">';
    d.stocks.forEach(s=>{
      const color = s.up === true ? '#d63031' : s.up === false ? '#0984e3' : '#636e72';
      html += '<div style="padding:10px 12px;background:#f8f9fa;border-radius:10px;border-top:3px solid '+color+';">';
      html += '<div style="font-size:13px;font-weight:700;color:#1a1d23;margin-bottom:4px;">'+s.name+'</div>';
      html += '<div style="font-size:16px;font-weight:700;color:#1a1d23;font-family:DM Mono,monospace;">'+s.price+'</div>';
      html += '<div style="font-size:12px;color:'+color+';font-weight:600;">'+s.change+' ('+s.pct+')</div>';
      html += '<a href="https://m.stock.naver.com/domestic/stock/'+s.code+'/chart" target="_blank" style="font-size:10px;color:#b2bec3;">차트 →</a>';
      html += '</div>';
    });
    html += '</div>';
    result.innerHTML = html;
  }catch(e){
    result.innerHTML='<span class="content-empty">네트워크 오류</span>';
  }
  btn.classList.remove('ls'); btn.innerHTML='조회';
}

async function searchEncyc(){
  const q = document.getElementById('encyc-input').value.trim();
  if(!q) return;
  const btn = document.getElementById('encyc-btn');
  const result = document.getElementById('encyc-result');
  btn.classList.add('ls'); btn.innerHTML='<span class="spinner"></span>';
  result.innerHTML='<span class="content-empty">검색 중...</span>';
  try{
    const d = await fetch('/api/encyc/search?q='+encodeURIComponent(q)).then(r=>r.json());
    if(d.error){
      result.innerHTML='<span class="content-empty">오류: '+d.error+'</span>';
      return;
    }
    if(!d.results||!d.results.length){
      result.innerHTML='<span class="content-empty">검색 결과가 없어요.</span>';
      return;
    }
    let html = '<div style="font-size:11px;color:#7a8099;margin-bottom:10px;">'+d.results.length+'건</div>';
    d.results.forEach(row=>{
      html += '<div style="padding:12px 14px;background:#f8f9fa;border-radius:10px;margin-bottom:8px;border-left:3px solid #0984e3;">';
      const situation = row['상황'] || '';
      const topic = row['주제(시장/섹터/종목)'] || row['주제'] || '';
      const expr = row['표현'] || '';
      if(situation) html += '<div style="font-size:11px;font-weight:700;color:#7a8099;margin-bottom:4px;">📌 '+situation+'</div>';
      if(topic) html += '<div style="font-size:12px;color:#0984e3;font-weight:600;margin-bottom:6px;">'+topic+'</div>';
      if(expr) html += '<div style="font-size:14px;color:#1a1d23;line-height:1.7;">'+expr+'</div>';
      html += '</div>';
    });
    result.innerHTML = html;
  }catch(e){
    result.innerHTML='<span class="content-empty">네트워크 오류</span>';
  }
  btn.classList.remove('ls'); btn.innerHTML='검색';
}

async function searchGuest(){
  const q = document.getElementById('guest-input').value.trim();
  if(!q) return;
  const btn = document.getElementById('guest-btn');
  const result = document.getElementById('guest-result');
  btn.classList.add('ls'); btn.innerHTML='<span class="spinner"></span>';
  result.innerHTML='<span class="content-empty">검색 중...</span>';
  try{
    const d = await fetch('/api/guest/search?q='+encodeURIComponent(q)).then(r=>r.json());
    if(d.error){
      result.innerHTML='<span class="content-empty">오류: '+d.error+'</span>';
      return;
    }
    const sheets = Object.keys(d.results||{});
    if(!sheets.length){
      result.innerHTML='<span class="content-empty">검색 결과가 없어요.</span>';
      return;
    }
    let html = '';
    sheets.forEach(sheet=>{
      const rows = d.results[sheet];
      html += '<div style="margin-bottom:20px;">';
      html += '<div style="font-size:11px;font-weight:700;color:#e8b84b;letter-spacing:.08em;margin-bottom:10px;padding-bottom:6px;border-bottom:2px solid #e8b84b;">📋 '+sheet+' · '+rows.length+'건</div>';
      rows.forEach(row=>{
        html += '<div style="padding:12px 14px;background:#f8f9fa;border-radius:10px;margin-bottom:8px;border-left:3px solid #e8b84b;">';
        const entries = Object.entries(row).filter(([k,v])=>v&&v.trim());
        // 날짜, 이름, 코너 먼저
        const priority = ['날짜','이름','코너'];
        const header = priority.map(k=>{
          const e = entries.find(([ek])=>ek===k);
          return e ? '<span style="font-size:12px;font-weight:700;color:#1a1d23;">'+e[1]+'</span>' : '';
        }).filter(Boolean).join(' · ');
        if(header) html += '<div style="margin-bottom:6px;">'+header+'</div>';
        // 나머지 내용
        entries.forEach(([k,v])=>{
          if(priority.includes(k)) return;
          html += '<div style="margin-bottom:3px;">';
          html += '<span style="font-size:11px;color:#7a8099;font-weight:700;margin-right:6px;">'+k+'</span>';
          if(v.startsWith('http')){
            html += '<a href="'+v+'" target="_blank" style="font-size:12px;color:#0984e3;">🔗 링크</a>';
          } else {
            html += '<span style="font-size:13px;color:#2d3436;">'+v+'</span>';
          }
          html += '</div>';
        });
        html += '</div>';
      });
      html += '</div>';
    });
    result.innerHTML = html;
  }catch(e){
    result.innerHTML='<span class="content-empty">네트워크 오류</span>';
  }
  btn.classList.remove('ls'); btn.innerHTML='검색';
}

























// 체크포인트 파싱
const CP_SECTIONS = {
  indicator: ['📌지표'],
  sector: ['📌Sector','📌sector'],
  kospi: ['📌코스피'],
  kosdaq: ['📌코스닥'],
  after: ['📌시간외','📌NXT']
};
const CL_SECTIONS = {
  figure: ['📌 마감수치','📌마감수치'],
  factor: ['📌 지수 팩터','📌지수 팩터','📌 지수팩터'],
  supply: ['📌 수급','📌수급'],
  sector: ['📌 특징 업종','📌특징 업종'],
  stock: ['📌 특징주','📌특징주'],
  schedule: ['📌 내일 일정','📌내일 일정']
};

function parseSection(text, headers){
  if(!text) return null;
  const lines = text.split('\n');
  let capturing = false, result = [];
  for(let i=0;i<lines.length;i++){
    const l = lines[i];
    const isHeader = headers.some(h=>l.includes(h));
    const isOtherHeader = l.match(/^📌/) && !isHeader;
    if(isHeader){ capturing=true; result.push(l); continue; }
    if(capturing){
      if(isOtherHeader) break;
      result.push(l);
    }
  }
  return result.length ? result.join('\n') : null;
}

let _cpRaw = '', _clRaw = '';

function cpTab(btn, key){
  document.querySelectorAll('#cp-tabs .tab').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  const el = document.getElementById('checkpoint-body');
  if(!_cpRaw){ return; }
  if(key==='all'){ el.textContent=_cpRaw; return; }
  const sec = parseSection(_cpRaw, CP_SECTIONS[key]||[]);
  el.textContent = sec || '해당 섹션 없음';
}

function clTab(btn, key){
  document.querySelectorAll('#cl-tabs .tab').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  const el = document.getElementById('closing-body');
  if(!_clRaw){ return; }
  if(key==='all'){ el.textContent=_clRaw; return; }
  const sec = parseSection(_clRaw, CL_SECTIONS[key]||[]);
  el.textContent = sec || '해당 섹션 없음';
}

function mapTab(btn, key){
  document.querySelectorAll('#tab-map-kospi,#tab-map-kosdaq').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  const isKospi = key==='kospi';
  document.getElementById('map-frame').src = isKospi
    ? 'https://markets.hankyung.com/marketmap/kospi'
    : 'https://markets.hankyung.com/marketmap/kosdaq';
  document.getElementById('map-link-kospi').style.display = isKospi ? 'inline-flex' : 'none';
  document.getElementById('map-link-kosdaq').style.display = isKospi ? 'none' : 'inline-flex';
}

function sectorTab(btn, key){
  document.querySelectorAll('#tab-sector-top,#tab-sector-bot').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('sector-top').style.display = key==='top' ? 'block' : 'none';
  document.getElementById('sector-bot').style.display = key==='bot' ? 'block' : 'none';
}

async function loadNews(){
  const el = document.getElementById('news-list');
  if(!el) return;
  el.innerHTML = '<span class="content-empty">로딩 중...</span>';
  try{
    const d = await fetch('/api/news').then(r=>r.json());
    if(!d.items || !d.items.length){
      el.innerHTML='<span class="content-empty">뉴스를 불러오지 못했어요.</span>';
      return;
    }
    el.innerHTML = d.items.map(item=>`
      <div style="padding:8px 0;border-bottom:1px solid #f0f2f5;">
        <div style="font-size:10px;color:#b2bec3;margin-bottom:3px;">${item.source}</div>
        <a href="${item.link}" target="_blank" style="font-size:12px;color:#2d3436;line-height:1.5;text-decoration:none;font-weight:500;">${item.title}</a>
      </div>`).join('');
  }catch(e){
    el.innerHTML='<span class="content-empty">오류가 발생했어요.</span>';
  }
}

async function loadAll(){
  const btn=document.getElementById('refresh-btn');
  if(btn)btn.innerHTML='<span class="spinner"></span>';
  await Promise.all([loadMarket(),loadSector()]);
  if(btn)btn.innerHTML='<span>↻</span> 새로고침';
}

// 초기 로드
loadAll();
loadFutures();
loadAutoFutures();
loadReport();
loadNote();
loadTodo();
loadMemo();
loadNews();
loadCalendar();
loadPDFList();
loadWdaebon();
loadPost('checkpoint','checkpoint-body','checkpoint-date');
loadPost('closing','closing-body','closing-date');
loadPost('briefing','briefing-body','briefing-date');
setInterval(loadAll,5*60*1000);
// 체크포인트/마감일지/특징리포트 자동 새로고침 (30초)
setInterval(()=>{
  loadPost('checkpoint','checkpoint-body','checkpoint-date');
  loadPost('closing','closing-body','closing-date');
  loadPost('briefing','briefing-body','briefing-date');
},30*1000);
</script>
<script>
if('serviceWorker' in navigator){
  navigator.serviceWorker.register('/service-worker.js');
}
</script>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

from flask import Flask, jsonify, request, Response
import requests
import os
from datetime import datetime
from functools import wraps
import anthropic
import pg8000.native

app = Flask(__name__)

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
    valid = ("checkpoint", "closing", "briefing", "futures", "aftermarket", "report", "report_up", "report_dn", "report_feature", "note", "todo")
    if pt not in valid:
        return jsonify({"error": "invalid"}), 400
    return jsonify(get_latest_post(pt) or {})


@app.route("/api/post/<pt>", methods=["POST"])
def api_save_post(pt):
    valid = ("checkpoint", "closing", "briefing", "futures", "aftermarket", "report", "report_up", "report_dn", "report_feature", "note", "todo")
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

        stock_hits = [r for r in data if query in r.get("종목명", "")]
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
                    lines.append(f"🔗 https://finance.naver.com/item/main.naver?code={code}")
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

        # Get first stock code for chart
        first_code = None
        if stock_hits:
            from collections import OrderedDict
            first_code = stock_hits[0].get("종목코드", "").strip() or None
        return jsonify({"result": "\n".join(lines), "found": bool(stock_hits or theme_hits), "code": first_code})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/todo/clear", methods=["POST"])
@requires_auth
def clear_todo():
    save_post("todo", "", datetime.now().strftime("%Y-%m-%d"))
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
            model="claude-sonnet-4-20250514",
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
<meta name="viewport" content="width=device-width, initial-scale=1.0">
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
      <div class="input-row">
        <input class="input-line" id="futures-input" placeholder="예) +1.2%" style="flex:1;" />
        <button class="btn btn-green" onclick="saveFutures()">저장</button>
      </div>
    </div>
    <div class="content-card" style="margin-bottom:0;">
      <div class="content-header">
        <span class="content-title">✅ 오늘의 할일</span>
        <div style="display:flex;gap:6px;align-items:center;">
          <span class="saved-badge" id="todo-badge">✓ 저장됨</span>
          <button class="btn btn-green" onclick="saveTodo()">저장</button>
          <button class="btn" onclick="clearTodo()" style="color:#d63031;border-color:#fab1a0;">↺ 초기화</button>
        </div>
      </div>
      <textarea class="input-area" id="todo-input" placeholder="오늘 할일, 리마인더, 메모..." style="min-height:90px;"></textarea>
    </div>
  </div>

  <!-- 미국·글로벌 -->
  <div class="section-label">미국·글로벌</div>
  <div class="grid4">
    <div class="card"><div class="metric-label">나스닥</div><div class="metric-val" id="nasdaq-val"><span class="loading">—</span></div><div class="metric-chg" id="nasdaq-chg"></div></div>
    <div class="card"><div class="metric-label">다우존스</div><div class="metric-val" id="dow-val"><span class="loading">—</span></div><div class="metric-chg" id="dow-chg"></div></div>
    <div class="card"><div class="metric-label">S&amp;P 500</div><div class="metric-val" id="sp500-val"><span class="loading">—</span></div><div class="metric-chg" id="sp500-chg"></div></div>
    <div class="card"><div class="metric-label">EWY</div><div class="metric-val" id="ewy-val"><span class="loading">—</span></div><div class="metric-chg" id="ewy-chg"></div></div>
  </div>
  <div class="grid4" style="margin-top:8px;">
    <div class="card"><div class="metric-label">WTI 유가</div><div class="metric-val" id="wti-val"><span class="loading">—</span></div><div class="metric-chg" id="wti-chg"></div></div>
    <div class="card"><div class="metric-label">브렌트유</div><div class="metric-val" id="brent-val"><span class="loading">—</span></div><div class="metric-chg" id="brent-chg"></div></div>
    <div class="card"><div class="metric-label">금</div><div class="metric-val" id="gold-val"><span class="loading">—</span></div><div class="metric-chg" id="gold-chg"></div></div>
    <div class="card"><div class="metric-label">VIX</div><div class="metric-val" id="vix-val"><span class="loading">—</span></div><div class="metric-chg" id="vix-chg"></div></div>
  </div>
  <div class="grid4" style="margin-top:8px;">
    <div class="card"><div class="metric-label">미국 10년물 금리</div><div class="metric-val" id="tnx-val"><span class="loading">—</span></div><div class="metric-chg" id="tnx-chg"></div></div>
    <div class="card"><div class="metric-label">필라델피아반도체</div><div class="metric-val" id="sox-val"><span class="loading">—</span></div><div class="metric-chg" id="sox-chg"></div></div>
    <div class="card"><div class="metric-label">달러인덱스 (DXY)</div><div class="metric-val" id="dxy-val"><span class="loading">—</span></div><div class="metric-chg" id="dxy-chg"></div></div>
    <div class="card"><div class="metric-label">DRAM ETF (SOXX)</div><div class="metric-val" id="dram-val"><span class="loading">—</span></div><div class="metric-chg" id="dram-chg"></div></div>
  </div>
  <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:8px;align-items:center;">
    <a href="https://www.cnbc.com/watchlist/" target="_blank" class="btn">📺 CNBC Watchlist</a>
    <button class="btn" onclick="loadAll()" id="refresh-btn"><span>↻</span> 새로고침</button>
  </div>

  <!-- 업종 등락률 -->
  <div class="section-label">업종 등락률 (코스피)</div>
  <div class="grid2">
    <div class="content-card">
      <div class="content-header"><span class="content-title">📈 상위 5</span></div>
      <div id="sector-top"><span class="content-empty">로딩 중...</span></div>
    </div>
    <div class="content-card">
      <div class="content-header"><span class="content-title">📉 하위 5</span></div>
      <div id="sector-bot"><span class="content-empty">로딩 중...</span></div>
    </div>
  </div>

  <!-- 미증시 브리핑 -->
  <div class="section-label">미증시 브리핑</div>
  <div class="content-card">
    <div class="content-header">
      <span class="content-title">📅 시황 브리핑</span>
      <button class="btn btn-primary" onclick="generateBriefing()" id="briefing-btn">✦ 브리핑 생성</button>
    </div>
    <div id="briefing-date" class="content-date" style="margin-bottom:8px;"></div>
    <div class="content-body" id="briefing-body"><span class="content-empty">버튼을 누르면 Claude가 CNBC·Bloomberg·WSJ를 참조해서 브리핑을 생성합니다.</span></div>
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

  <!-- 체크포인트 -->
  <div class="section-label">체크포인트</div>
  <div class="content-card">
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

  <!-- 노트 + 리포트 -->
  <div class="section-label">노트 / 특징 리포트</div>
  <div class="grid2" style="margin-bottom:10px;">
    <div class="content-card" style="margin-bottom:0;">
      <div class="content-header">
        <span class="content-title">📓 오늘의 노트</span>
        <div style="display:flex;gap:6px;align-items:center;">
          <span class="saved-badge" id="note-badge">✓ 저장됨</span>
          <button class="btn btn-green" onclick="saveNote()">저장</button>
          <button class="btn" onclick="clearNote()" style="color:#d63031;border-color:#fab1a0;">↺ 초기화</button>
        </div>
      </div>
      <textarea class="input-area" id="note-input" placeholder="새로운 뉴스, 메모, 아이디어 등 자유롭게..." style="min-height:140px;"></textarea>
    </div>
    <div class="content-card" style="margin-bottom:0;">
      <div class="content-header">
        <span class="content-title">📝 특징 리포트</span>
        <div style="display:flex;gap:6px;align-items:center;">
          <span class="saved-badge" id="report-badge">✓ 저장됨</span>
          <button class="btn btn-green" onclick="saveReportTab()">저장</button>
          <button class="btn" onclick="clearReport()" style="color:#f87171;border-color:#3a1a1a;">↺ 초기화</button>
        </div>
      </div>
      <div class="tab-bar">
        <button class="tab active" onclick="reportTab(this,'up')" id="rtab-up">📈 상승</button>
        <button class="tab" onclick="reportTab(this,'dn')" id="rtab-dn">📉 하락</button>
        <button class="tab" onclick="reportTab(this,'feature')" id="rtab-feature">⭐ 특징</button>
      </div>
      <textarea class="input-area" id="report-up-input" placeholder="상승 내용 입력..." style="min-height:120px;"></textarea>
      <textarea class="input-area" id="report-dn-input" placeholder="하락 내용 입력..." style="min-height:120px;display:none;"></textarea>
      <textarea class="input-area" id="report-feature-input" placeholder="특징 내용 입력..." style="min-height:120px;display:none;"></textarea>
    </div>
  </div>

  </div>
  <!-- 마감일지 -->
  <div class="section-label" style="margin-top:16px;">마감일지</div>
  <div class="content-card">
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

async function saveReportTab(){
  const key = _reportTab;
  const val = document.getElementById('report-'+key+'-input').value.trim();
  if(!val) return;
  await fetch('/api/post/report_'+key,{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({content:val,date:new Date().toISOString().slice(0,10)})
  });
  const badge=document.getElementById('report-badge');
  badge.style.display='inline';
  setTimeout(()=>badge.style.display='none',2000);
}

async function clearReport(){
  if(!confirm('리포트 전체 초기화할까요?')) return;
  await fetch('/api/report/clear',{method:'POST'});
  ['up','dn','feature'].forEach(k=>{
    const el=document.getElementById('report-'+k+'-input');
    if(el) el.value='';
  });
}

async function loadReportTabs(){
  for(const k of ['up','dn','feature']){
    try{
      const d=await fetch('/api/post/report_'+k).then(r=>r.json());
      if(d.content){
        const el=document.getElementById('report-'+k+'-input');
        if(el) el.value=d.content;
      }
    }catch(e){}
  }
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
    }
  }catch(e){result.innerHTML='<span class="content-empty">네트워크 오류</span>';}
  btn.classList.remove('ls');btn.innerHTML='검색';
}

async function saveTodo(){
  const val=document.getElementById('todo-input').value.trim();
  if(!val)return;
  await fetch('/api/post/todo',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({content:val,date:new Date().toISOString().slice(0,10)})});
  const badge=document.getElementById('todo-badge');
  badge.style.display='inline';setTimeout(()=>badge.style.display='none',2000);
}
async function clearTodo(){
  if(!confirm('할일 초기화할까요?'))return;
  await fetch('/api/todo/clear',{method:'POST'});
  document.getElementById('todo-input').value='';
}
async function loadTodo(){
  try{
    const d=await fetch('/api/post/todo').then(r=>r.json());
    if(d.content) document.getElementById('todo-input').value=d.content;
  }catch(e){}
}
async function saveNote(){
  const val=document.getElementById('note-input').value.trim();
  if(!val)return;
  await fetch('/api/post/note',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({content:val,date:new Date().toISOString().slice(0,10)})});
  const badge=document.getElementById('note-badge');
  badge.style.display='inline';setTimeout(()=>badge.style.display='none',2000);
}

async function clearNote(){
  if(!confirm('노트 초기화할까요?'))return;
  await fetch('/api/note/clear',{method:'POST'});
  document.getElementById('note-input').value='';
}

async function loadNote(){
  try{
    const d=await fetch('/api/post/note').then(r=>r.json());
    if(d.content){document.getElementById('note-input').value=d.content;}
  }catch(e){}
}

async function generateBriefing(){
  const btn=document.getElementById('briefing-btn');
  const body=document.getElementById('briefing-body');
  btn.classList.add('ls');btn.innerHTML='<span class="spinner"></span> 생성 중...';
  body.innerHTML='<span class="content-empty">Claude가 CNBC·Bloomberg·WSJ를 검색 중입니다...</span>';
  try{
    const d=await fetch('/api/briefing/generate',{method:'POST'}).then(r=>r.json());
    if(d.content){body.textContent=d.content;document.getElementById('briefing-date').textContent=d.date||'';}
    else body.innerHTML='<span class="content-empty">오류: '+(d.error||'알 수 없는 오류')+'</span>';
  }catch(e){body.innerHTML='<span class="content-empty">네트워크 오류</span>';}
  btn.classList.remove('ls');btn.innerHTML='✦ 브리핑 생성';
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

async function loadAll(){
  const btn=document.getElementById('refresh-btn');
  if(btn)btn.innerHTML='<span class="spinner"></span>';
  await Promise.all([loadMarket(),loadSector()]);
  if(btn)btn.innerHTML='<span>↻</span> 새로고침';
}

// 초기 로드
loadAll();
loadFutures();
loadReportTabs();
loadNote();
loadTodo();
loadPost('checkpoint','checkpoint-body','checkpoint-date');
loadPost('closing','closing-body','closing-date');
loadPost('briefing','briefing-body','briefing-date');
setInterval(loadAll,5*60*1000);
</script>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

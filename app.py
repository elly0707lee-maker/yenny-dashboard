from flask import Flask, jsonify, request, Response
import requests
import sqlite3
import os
import json
from datetime import datetime
from functools import wraps
import anthropic

app = Flask(__name__)

DB_PATH = "dashboard.db"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
KIS_APP_KEY = os.environ.get("KIS_APP_KEY", "")
KIS_APP_SECRET = os.environ.get("KIS_APP_SECRET", "")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "yenny2026")
API_SECRET = os.environ.get("API_SECRET", "moneyplus")  # 봇에서 데이터 올릴 때 사용


# ── DB 초기화 ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            date TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()


# ── 기본 인증 ──────────────────────────────────────────────
def check_auth(password):
    return password == DASHBOARD_PASSWORD

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.password):
            return Response(
                "로그인이 필요합니다", 401,
                {"WWW-Authenticate": 'Basic realm="Yenny Dashboard"'}
            )
        return f(*args, **kwargs)
    return decorated


# ── KIS 토큰 발급 ──────────────────────────────────────────
def get_kis_token():
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET
    }
    try:
        res = requests.post(url, json=body, timeout=5)
        return res.json().get("access_token", "")
    except:
        return ""


# ── 국내 지수 (KIS) ───────────────────────────────────────
def get_korean_market():
    result = {}
    if not KIS_APP_KEY:
        return {"kospi": None, "kosdaq": None, "futures": None}
    try:
        token = get_kis_token()
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": KIS_APP_KEY,
            "appsecret": KIS_APP_SECRET,
            "tr_id": "FHPUP02100000",
            "Content-Type": "application/json"
        }
        base = "https://openapi.koreainvestment.com:9443"

        # 코스피
        r = requests.get(f"{base}/uapi/domestic-stock/v1/quotations/inquire-index-price",
                         headers={**headers, "tr_id": "FHPUP02100000"},
                         params={"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": "0001"},
                         timeout=5)
        d = r.json().get("output", {})
        result["kospi"] = {
            "value": d.get("bstp_nmix_prpr", "-"),
            "change": d.get("bstp_nmix_prdy_ctrt", "-")
        }

        # 코스닥
        r2 = requests.get(f"{base}/uapi/domestic-stock/v1/quotations/inquire-index-price",
                          headers={**headers, "tr_id": "FHPUP02100000"},
                          params={"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": "1001"},
                          timeout=5)
        d2 = r2.json().get("output", {})
        result["kosdaq"] = {
            "value": d2.get("bstp_nmix_prpr", "-"),
            "change": d2.get("bstp_nmix_prdy_ctrt", "-")
        }
    except Exception as e:
        result["kospi"] = None
        result["kosdaq"] = None

    result["futures"] = None
    return result


# ── 해외 지수 / 원자재 (Yahoo Finance 직접 호출) ──────────
def get_yahoo_quote(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=8)
        data = r.json()
        meta = data["chart"]["result"][0]["meta"]
        price = round(meta.get("regularMarketPrice", 0), 2)
        prev = meta.get("chartPreviousClose") or meta.get("previousClose", price)
        chg = round((price - prev) / prev * 100, 2) if prev else 0
        return {"value": price, "change": chg}
    except:
        return {"value": None, "change": None}

def get_global_market():
    tickers = {
        "nasdaq": "%5EIXIC",
        "dow": "%5EDJI",
        "sp500": "%5EGSPC",
        "wti": "CL%3DF",
        "usdkrw": "KRW%3DX",
        "vix": "%5EVIX"
    }
    result = {}
    for key, symbol in tickers.items():
        result[key] = get_yahoo_quote(symbol)
    return result


# ── DB 저장 / 조회 ─────────────────────────────────────────
def save_post(post_type, content, date):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO posts (type, content, date, created_at) VALUES (?, ?, ?, ?)",
        (post_type, content, date, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def get_latest_post(post_type):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT content, date, created_at FROM posts WHERE type=? ORDER BY id DESC LIMIT 1",
        (post_type,)
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {"content": row[0], "date": row[1], "created_at": row[2]}
    return None


# ── 라우트 ────────────────────────────────────────────────
@app.route("/")
@requires_auth
def index():
    return Response(get_html(), mimetype="text/html")


def get_html():
    return """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Yenny Dashboard · 머니플러스</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif; background: #0f0f13; color: #e8e8ec; min-height: 100vh; }
  .topbar { display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; border-bottom: 1px solid #1e1e28; background: #0f0f13; position: sticky; top: 0; z-index: 10; }
  .topbar-title { font-size: 15px; font-weight: 600; color: #fff; letter-spacing: -0.3px; }
  #clock { font-size: 13px; color: #888; }
  .container { padding: 16px; max-width: 900px; margin: 0 auto; }
  .section-label { font-size: 11px; color: #555; letter-spacing: 0.06em; text-transform: uppercase; margin: 20px 0 10px; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
  .grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  @media (max-width: 600px) { .grid3 { grid-template-columns: 1fr 1fr; } .grid4 { grid-template-columns: 1fr 1fr; } }
  .card { background: #17171f; border: 1px solid #1e1e28; border-radius: 12px; padding: 14px; }
  .metric-label { font-size: 11px; color: #555; margin-bottom: 6px; }
  .metric-val { font-size: 20px; font-weight: 600; color: #f0f0f4; letter-spacing: -0.5px; }
  .metric-chg { font-size: 12px; margin-top: 4px; }
  .up { color: #4ade80; } .dn { color: #f87171; } .flat { color: #888; }
  .loading { color: #444; font-size: 13px; }
  .content-card { background: #17171f; border: 1px solid #1e1e28; border-radius: 12px; padding: 16px; margin-bottom: 10px; }
  .content-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .content-title { font-size: 13px; font-weight: 600; color: #ccc; }
  .content-date { font-size: 11px; color: #555; }
  .content-body { font-size: 13px; color: #999; line-height: 1.7; white-space: pre-wrap; max-height: 280px; overflow-y: auto; }
  .content-empty { font-size: 13px; color: #444; font-style: italic; }
  .btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 8px; border: 1px solid #2a2a38; background: #1e1e2a; color: #aaa; font-size: 13px; cursor: pointer; transition: all 0.15s; }
  .btn:hover { background: #252535; color: #fff; }
  .btn-primary { background: #2d2d6b; border-color: #3d3d8b; color: #aaaaff; }
  .btn-primary:hover { background: #35358a; color: #ccccff; }
  .btn.loading-state { opacity: 0.5; pointer-events: none; }
  .refresh-dot { width: 6px; height: 6px; border-radius: 50%; background: #4ade80; display: inline-block; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #333; border-top-color: #aaaaff; border-radius: 50%; animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-title">Yenny Dashboard <span style="color:#444;font-weight:400">· 머니플러스</span></div>
  <div style="display:flex;align-items:center;gap:12px;">
    <span class="refresh-dot"></span>
    <span id="clock"></span>
  </div>
</div>
<div class="container">
  <div class="section-label">국내 시장</div>
  <div class="grid3">
    <div class="card"><div class="metric-label">코스피</div><div class="metric-val" id="kospi-val"><span class="loading">—</span></div><div class="metric-chg" id="kospi-chg"></div></div>
    <div class="card"><div class="metric-label">코스닥</div><div class="metric-val" id="kosdaq-val"><span class="loading">—</span></div><div class="metric-chg" id="kosdaq-chg"></div></div>
    <div class="card"><div class="metric-label">원/달러</div><div class="metric-val" id="usdkrw-val"><span class="loading">—</span></div><div class="metric-chg" id="usdkrw-chg"></div></div>
  </div>
  <div class="section-label">미국·글로벌</div>
  <div class="grid4">
    <div class="card"><div class="metric-label">나스닥</div><div class="metric-val" id="nasdaq-val"><span class="loading">—</span></div><div class="metric-chg" id="nasdaq-chg"></div></div>
    <div class="card"><div class="metric-label">다우존스</div><div class="metric-val" id="dow-val"><span class="loading">—</span></div><div class="metric-chg" id="dow-chg"></div></div>
    <div class="card"><div class="metric-label">S&P 500</div><div class="metric-val" id="sp500-val"><span class="loading">—</span></div><div class="metric-chg" id="sp500-chg"></div></div>
    <div class="card"><div class="metric-label">WTI 유가</div><div class="metric-val" id="wti-val"><span class="loading">—</span></div><div class="metric-chg" id="wti-chg"></div></div>
  </div>
  <div class="grid2" style="margin-top:8px;">
    <div class="card"><div class="metric-label">VIX</div><div class="metric-val" id="vix-val"><span class="loading">—</span></div><div class="metric-chg" id="vix-chg"></div></div>
    <div class="card" style="display:flex;align-items:center;justify-content:center;"><button class="btn" onclick="loadMarket()" id="refresh-btn"><span>↻</span> 새로고침</button></div>
  </div>
  <div class="section-label" style="margin-top:24px;">미증시 브리핑</div>
  <div class="content-card">
    <div class="content-header">
      <span class="content-title">📅 시황 브리핑</span>
      <button class="btn btn-primary" onclick="generateBriefing()" id="briefing-btn">✦ 브리핑 생성</button>
    </div>
    <div id="briefing-date" class="content-date" style="margin-bottom:8px;"></div>
    <div class="content-body" id="briefing-body"><span class="content-empty">버튼을 누르면 Claude가 CNBC·Bloomberg·WSJ를 참조해서 브리핑을 생성합니다.</span></div>
  </div>
  <div class="section-label">체크포인트</div>
  <div class="content-card">
    <div class="content-header"><span class="content-title">☑ 오늘 체크포인트</span><span class="content-date" id="checkpoint-date"></span></div>
    <div class="content-body" id="checkpoint-body"><span class="content-empty">텔레그램 봇으로 체크포인트를 올리면 여기에 표시됩니다.</span></div>
  </div>
  <div class="section-label">마감일지</div>
  <div class="content-card">
    <div class="content-header"><span class="content-title">📋 마감일지</span><span class="content-date" id="closing-date"></span></div>
    <div class="content-body" id="closing-body"><span class="content-empty">텔레그램 봇으로 마감일지를 올리면 여기에 표시됩니다.</span></div>
  </div>
  <div style="height:32px;"></div>
</div>
<script>
function updateClock() {
  const now = new Date();
  const kst = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  const h = String(kst.getHours()).padStart(2,'0');
  const m = String(kst.getMinutes()).padStart(2,'0');
  const s = String(kst.getSeconds()).padStart(2,'0');
  document.getElementById('clock').textContent = 'KST ' + h + ':' + m + ':' + s;
}
setInterval(updateClock, 1000); updateClock();

function fmtVal(v, d=2) {
  if (v === null || v === undefined) return '—';
  return Number(v).toLocaleString('ko-KR', {minimumFractionDigits:d, maximumFractionDigits:d});
}
function renderMetric(idVal, idChg, val, chg) {
  const vEl = document.getElementById(idVal);
  const cEl = document.getElementById(idChg);
  if (!vEl) return;
  if (val === null || val === undefined) { vEl.innerHTML = '<span class="loading">—</span>'; return; }
  vEl.textContent = fmtVal(val);
  if (cEl && chg !== null && chg !== undefined) {
    const sign = chg >= 0 ? '+' : '';
    const cls = chg > 0 ? 'up' : chg < 0 ? 'dn' : 'flat';
    cEl.innerHTML = '<span class="' + cls + '">' + sign + fmtVal(chg) + '%</span>';
  }
}
async function loadMarket() {
  const btn = document.getElementById('refresh-btn');
  if (btn) btn.innerHTML = '<span class="spinner"></span> 로딩 중';
  try {
    const res = await fetch('/api/market');
    const d = await res.json();
    renderMetric('kospi-val','kospi-chg', d.kospi?.value, d.kospi?.change);
    renderMetric('kosdaq-val','kosdaq-chg', d.kosdaq?.value, d.kosdaq?.change);
    renderMetric('nasdaq-val','nasdaq-chg', d.nasdaq?.value, d.nasdaq?.change);
    renderMetric('dow-val','dow-chg', d.dow?.value, d.dow?.change);
    renderMetric('sp500-val','sp500-chg', d.sp500?.value, d.sp500?.change);
    renderMetric('wti-val','wti-chg', d.wti?.value, d.wti?.change);
    renderMetric('usdkrw-val','usdkrw-chg', d.usdkrw?.value, d.usdkrw?.change);
    renderMetric('vix-val','vix-chg', d.vix?.value, d.vix?.change);
  } catch(e) { console.error(e); }
  if (btn) btn.innerHTML = '<span>↻</span> 새로고침';
}
async function loadPost(type, bodyId, dateId) {
  try {
    const res = await fetch('/api/post/' + type);
    const d = await res.json();
    const bodyEl = document.getElementById(bodyId);
    const dateEl = document.getElementById(dateId);
    if (d.content) {
      if (bodyEl) bodyEl.textContent = d.content;
      if (dateEl) dateEl.textContent = d.date || '';
    }
  } catch(e) {}
}
async function generateBriefing() {
  const btn = document.getElementById('briefing-btn');
  const body = document.getElementById('briefing-body');
  btn.classList.add('loading-state');
  btn.innerHTML = '<span class="spinner"></span> 생성 중...';
  body.innerHTML = '<span class="content-empty">Claude가 CNBC·Bloomberg·WSJ를 검색 중입니다...</span>';
  try {
    const res = await fetch('/api/briefing/generate', { method: 'POST' });
    const d = await res.json();
    if (d.content) {
      body.textContent = d.content;
      document.getElementById('briefing-date').textContent = d.date || '';
    } else {
      body.innerHTML = '<span class="content-empty">오류: ' + (d.error || '알 수 없는 오류') + '</span>';
    }
  } catch(e) {
    body.innerHTML = '<span class="content-empty">네트워크 오류가 발생했습니다.</span>';
  }
  btn.classList.remove('loading-state');
  btn.innerHTML = '✦ 브리핑 생성';
}
loadMarket();
loadPost('checkpoint','checkpoint-body','checkpoint-date');
loadPost('closing','closing-body','closing-date');
loadPost('briefing','briefing-body','briefing-date');
setInterval(loadMarket, 5 * 60 * 1000);
</script>
</body>
</html>"""


@app.route("/api/market")
@requires_auth
def api_market():
    global_data = get_global_market()
    korean_data = get_korean_market()
    return jsonify({**global_data, **korean_data})


@app.route("/api/post/<post_type>")
@requires_auth
def api_get_post(post_type):
    if post_type not in ("checkpoint", "closing", "briefing"):
        return jsonify({"error": "invalid type"}), 400
    data = get_latest_post(post_type)
    return jsonify(data or {})


# 봇에서 데이터 올리는 엔드포인트
@app.route("/api/post/<post_type>", methods=["POST"])
def api_save_post(post_type):
    if post_type not in ("checkpoint", "closing", "briefing"):
        return jsonify({"error": "invalid type"}), 400
    secret = request.headers.get("X-API-Secret", "")
    if secret != API_SECRET:
        return jsonify({"error": "unauthorized"}), 401
    body = request.json or {}
    content = body.get("content", "")
    date = body.get("date", datetime.now().strftime("%Y-%m-%d"))
    if not content:
        return jsonify({"error": "content required"}), 400
    save_post(post_type, content, date)
    return jsonify({"ok": True})


# 미증시 브리핑 생성
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
            messages=[{
                "role": "user",
                "content": f"현지시각 {today} 미국 증시 브리핑 해줘. CNBC, Bloomberg, WSJ 반드시 웹서치해서 시장 주도 재료와 지수 수치, 주요 뉴스, 특징주를 한국어로 정리해줘."
            }]
        )
        content = " ".join([b.text for b in msg.content if hasattr(b, "text") and b.text])
        date = datetime.now().strftime("%Y-%m-%d")
        save_post("briefing", content, date)
        return jsonify({"content": content, "date": date})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

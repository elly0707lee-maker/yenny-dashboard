from flask import Flask, jsonify, request, render_template, Response
import yfinance as yf
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


# ── 해외 지수 / 원자재 (yfinance) ─────────────────────────
def get_global_market():
    tickers = {
        "nasdaq": "^IXIC",
        "dow": "^DJI",
        "sp500": "^GSPC",
        "wti": "CL=F",
        "usdkrw": "KRW=X",
        "vix": "^VIX"
    }
    result = {}
    for key, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            info = t.fast_info
            price = round(info.last_price, 2)
            prev = info.previous_close
            chg = round((price - prev) / prev * 100, 2) if prev else 0
            result[key] = {"value": price, "change": chg}
        except:
            result[key] = {"value": None, "change": None}
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
    return render_template("index.html")


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
            messages=[{
                "role": "user",
                "content": f"현지시각 {today} 미국 증시 브리핑 해줘. CNBC, Bloomberg, WSJ 참조해서 ① 시장 주도 재료 ② 글로벌 주요 뉴스 ③ 특징주 순서로 정리해줘."
            }]
        )
        content = msg.content[0].text
        date = datetime.now().strftime("%Y-%m-%d")
        save_post("briefing", content, date)
        return jsonify({"content": content, "date": date})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

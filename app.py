from flask import Flask, jsonify, request, Response
import requests
import sqlite3
import os
from datetime import datetime
from functools import wraps
import anthropic

app = Flask(__name__)

DB_PATH = "dashboard.db"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
KIS_APP_KEY = os.environ.get("KIS_APP_KEY", "")
KIS_APP_SECRET = os.environ.get("KIS_APP_SECRET", "")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "yenny2026")
API_SECRET = os.environ.get("API_SECRET", "moneyplus")

_kis_token_cache = {"token": ""}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL, content TEXT NOT NULL,
        date TEXT NOT NULL, created_at TEXT NOT NULL)""")
    conn.commit(); conn.close()

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
    if _kis_token_cache["token"]:
        return _kis_token_cache["token"]
    try:
        r = requests.post(
            "https://openapi.koreainvestment.com:9443/oauth2/tokenP",
            json={"grant_type": "client_credentials",
                  "appkey": KIS_APP_KEY, "appsecret": KIS_APP_SECRET},
            timeout=6)
        token = r.json().get("access_token", "")
        _kis_token_cache["token"] = token
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
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        meta = r.json()["chart"]["result"][0]["meta"]
        price = round(meta.get("regularMarketPrice", 0), 2)
        prev = meta.get("chartPreviousClose") or meta.get("previousClose", price)
        chg = round((price - prev) / prev * 100, 2) if prev else 0
        return {"value": price, "change": chg}
    except:
        return {"value": None, "change": None}


def get_korean_market():
    result = {}
    for mkt, code in [("kospi", "0001"), ("kosdaq", "1001")]:
        d = kis_get("/uapi/domestic-stock/v1/quotations/inquire-index-price",
                    "FHPUP02100000",
                    {"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": code}).get("output", {})
        result[mkt] = {
            "value": d.get("bstp_nmix_prpr", None),
            "change": d.get("bstp_nmix_prdy_ctrt", None),
            "foreign": None, "institution": None
        }
        sup = kis_get("/uapi/domestic-stock/v1/quotations/inquire-index-investor",
                      "FHPST01710000",
                      {"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": code,
                       "FID_INPUT_DATE_1": datetime.now().strftime("%Y%m%d")}).get("output", [])
        if sup and isinstance(sup, list):
            result[mkt]["foreign"] = sup[0].get("frgn_ntby_qty", None)
            result[mkt]["institution"] = sup[0].get("orgn_ntby_qty", None)
    return result


SECTOR_ETFS = [
    ("반도체", "091160"), ("2차전지", "305720"), ("바이오", "207920"),
    ("금융", "139270"), ("에너지", "117700"), ("방산", "471550"),
    ("조선", "466920"), ("자동차", "091180"), ("건설", "102960"),
    ("IT", "148020"),
]


def get_sector_etf():
    result = []
    for name, code in SECTOR_ETFS:
        d = kis_get("/uapi/domestic-stock/v1/quotations/inquire-price",
                    "FHKST01010100",
                    {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}).get("output", {})
        try:
            chg_f = float(d.get("prdy_ctrt", ""))
            result.append({"name": name, "change": chg_f})
        except:
            pass
    result.sort(key=lambda x: x["change"], reverse=True)
    return {"top5": result[:5], "bot5": list(reversed(result[-5:]))}


def get_global_market():
    syms = {
        "nasdaq": "%5EIXIC", "dow": "%5EDJI", "sp500": "%5EGSPC",
        "wti": "CL%3DF", "usdkrw": "KRW%3DX", "vix": "%5EVIX", "ewy": "EWY"
    }
    return {k: get_yahoo_quote(v) for k, v in syms.items()}


def save_post(t, content, date):
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute(
        "INSERT INTO posts (type,content,date,created_at) VALUES (?,?,?,?)",
        (t, content, date, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()


def get_latest_post(t):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT content,date FROM posts WHERE type=? ORDER BY id DESC LIMIT 1", (t,))
    row = c.fetchone(); conn.close()
    return {"content": row[0], "date": row[1]} if row else None


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
    return jsonify(get_sector_etf())


@app.route("/api/post/<pt>")
@requires_auth
def api_get_post(pt):
    if pt not in ("checkpoint", "closing", "briefing"):
        return jsonify({"error": "invalid"}), 400
    return jsonify(get_latest_post(pt) or {})


@app.route("/api/post/<pt>", methods=["POST"])
def api_save_post(pt):
    if pt not in ("checkpoint", "closing", "briefing"):
        return jsonify({"error": "invalid"}), 400
    if request.headers.get("X-API-Secret", "") != API_SECRET:
        return jsonify({"error": "unauthorized"}), 401
    body = request.json or {}
    content = body.get("content", "")
    date = body.get("date", datetime.now().strftime("%Y-%m-%d"))
    if not content:
        return jsonify({"error": "content required"}), 400
    save_post(pt, content, date)
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
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo',sans-serif;background:#0f0f13;color:#e8e8ec;min-height:100vh}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;border-bottom:1px solid #1e1e28;background:#0f0f13;position:sticky;top:0;z-index:10}
.topbar-title{font-size:15px;font-weight:600;color:#fff}
.container{padding:16px;max-width:960px;margin:0 auto}
.section-label{font-size:11px;color:#555;letter-spacing:.06em;text-transform:uppercase;margin:20px 0 10px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
@media(max-width:640px){.grid3{grid-template-columns:1fr 1fr}.grid4{grid-template-columns:1fr 1fr}}
.card{background:#17171f;border:1px solid #1e1e28;border-radius:12px;padding:14px}
.metric-label{font-size:11px;color:#555;margin-bottom:6px}
.metric-val{font-size:20px;font-weight:600;color:#f0f0f4;letter-spacing:-.5px}
.metric-chg{font-size:12px;margin-top:4px}
.metric-sup{font-size:11px;color:#666;margin-top:6px;display:flex;gap:10px}
.up{color:#e84c4c}
.dn{color:#4c7ee8}
.flat{color:#888}
.loading{color:#444}
.content-card{background:#17171f;border:1px solid #1e1e28;border-radius:12px;padding:16px;margin-bottom:10px}
.content-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.content-title{font-size:13px;font-weight:600;color:#ccc}
.content-date{font-size:11px;color:#555}
.content-body{font-size:13px;color:#999;line-height:1.7;white-space:pre-wrap;max-height:260px;overflow-y:auto}
.content-empty{font-size:13px;color:#444;font-style:italic}
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:8px;border:1px solid #2a2a38;background:#1e1e2a;color:#aaa;font-size:12px;cursor:pointer;transition:all .15s}
.btn:hover{background:#252535;color:#fff}
.btn-primary{background:#2d2d6b;border-color:#3d3d8b;color:#aaaaff}
.btn-primary:hover{background:#35358a;color:#ccccff}
.btn.ls{opacity:.5;pointer-events:none}
.refresh-dot{width:6px;height:6px;border-radius:50%;background:#4ade80;display:inline-block;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.spinner{display:inline-block;width:13px;height:13px;border:2px solid #333;border-top-color:#aaaaff;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.etf-row{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #1e1e28;font-size:12px}
.etf-row:last-child{border-bottom:none}
.etf-name{color:#aaa}
.etf-chg{font-weight:600}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-title">Yenny Dashboard <span style="color:#444;font-weight:400">· 머니플러스</span></div>
  <div style="display:flex;align-items:center;gap:10px;">
    <span class="refresh-dot"></span>
    <span id="clock" style="font-size:12px;color:#666;"></span>
  </div>
</div>
<div class="container">

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

  <div class="section-label">미국·글로벌</div>
  <div class="grid4">
    <div class="card"><div class="metric-label">나스닥</div><div class="metric-val" id="nasdaq-val"><span class="loading">—</span></div><div class="metric-chg" id="nasdaq-chg"></div></div>
    <div class="card"><div class="metric-label">다우존스</div><div class="metric-val" id="dow-val"><span class="loading">—</span></div><div class="metric-chg" id="dow-chg"></div></div>
    <div class="card"><div class="metric-label">S&amp;P 500</div><div class="metric-val" id="sp500-val"><span class="loading">—</span></div><div class="metric-chg" id="sp500-chg"></div></div>
    <div class="card"><div class="metric-label">EWY</div><div class="metric-val" id="ewy-val"><span class="loading">—</span></div><div class="metric-chg" id="ewy-chg"></div></div>
  </div>
  <div class="grid2" style="margin-top:8px;">
    <div class="card"><div class="metric-label">WTI 유가</div><div class="metric-val" id="wti-val"><span class="loading">—</span></div><div class="metric-chg" id="wti-chg"></div></div>
    <div class="card"><div class="metric-label">VIX</div><div class="metric-val" id="vix-val"><span class="loading">—</span></div><div class="metric-chg" id="vix-chg"></div></div>
  </div>
  <div style="display:flex;justify-content:flex-end;margin-top:8px;">
    <button class="btn" onclick="loadAll()" id="refresh-btn"><span>↻</span> 새로고침</button>
  </div>

  <div class="section-label">섹터 ETF 등락률</div>
  <div class="grid2">
    <div class="content-card">
      <div class="content-header"><span class="content-title">📈 상위 5</span></div>
      <div id="etf-top"><span class="content-empty">로딩 중...</span></div>
    </div>
    <div class="content-card">
      <div class="content-header"><span class="content-title">📉 하위 5</span></div>
      <div id="etf-bot"><span class="content-empty">로딩 중...</span></div>
    </div>
  </div>

  <div class="section-label">미증시 브리핑</div>
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
    renderM('vix-val','vix-chg',d.vix?.value,d.vix?.change);
    renderM('usdkrw-val','usdkrw-chg',d.usdkrw?.value,d.usdkrw?.change);
    ['kospi','kosdaq'].forEach(m=>{
      const el=document.getElementById(m+'-sup');if(!el)return;
      const fv=d[m]?.foreign,iv=d[m]?.institution;
      const fvn=parseInt(fv),ivn=parseInt(iv);
      el.innerHTML='<span>외인 <b class="'+(fvn>0?'up':fvn<0?'dn':'flat')+'">'+fmtSup(fv)+'</b></span>'+
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
    render('etf-top',d.top5);render('etf-bot',d.bot5);
  }catch(e){}
}

async function loadPost(type,bid,did){
  try{
    const d=await fetch('/api/post/'+type).then(r=>r.json());
    if(d.content){
      const b=document.getElementById(bid),dt=document.getElementById(did);
      if(b)b.textContent=d.content;if(dt)dt.textContent=d.date||'';
    }
  }catch(e){}
}

async function generateBriefing(){
  const btn=document.getElementById('briefing-btn');
  const body=document.getElementById('briefing-body');
  btn.classList.add('ls');
  btn.innerHTML='<span class="spinner"></span> 생성 중...';
  body.innerHTML='<span class="content-empty">Claude가 CNBC·Bloomberg·WSJ를 검색 중입니다...</span>';
  try{
    const d=await fetch('/api/briefing/generate',{method:'POST'}).then(r=>r.json());
    if(d.content){body.textContent=d.content;document.getElementById('briefing-date').textContent=d.date||'';}
    else body.innerHTML='<span class="content-empty">오류: '+(d.error||'알 수 없는 오류')+'</span>';
  }catch(e){body.innerHTML='<span class="content-empty">네트워크 오류</span>';}
  btn.classList.remove('ls');btn.innerHTML='✦ 브리핑 생성';
}

async function loadAll(){
  const btn=document.getElementById('refresh-btn');
  if(btn)btn.innerHTML='<span class="spinner"></span>';
  await Promise.all([loadMarket(),loadSector()]);
  if(btn)btn.innerHTML='<span>↻</span> 새로고침';
}

loadAll();
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

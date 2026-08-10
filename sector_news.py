"""
섹터별 뉴스 (/sector-news)
- 구글 뉴스 RSS 검색 endpoint으로 섹터별 뉴스 병렬 fetch
- Claude 요약 (선택적)
"""
import asyncio
import aiohttp
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# 예니가 방송에서 자주 다루는 섹터 리스트
SECTORS = [
    {"key": "semi",       "name": "반도체",     "icon": "🔬", "q": "반도체 삼성전자 SK하이닉스 HBM"},
    {"key": "ai",         "name": "AI",         "icon": "🤖", "q": "AI 인공지능 챗GPT 엔비디아"},
    {"key": "battery",    "name": "2차전지",    "icon": "🔋", "q": "2차전지 배터리 LG에너지솔루션 삼성SDI"},
    {"key": "bio",        "name": "바이오",     "icon": "💊", "q": "바이오 제약 신약 셀트리온 삼성바이오"},
    {"key": "defense",    "name": "방산",       "icon": "🛡️", "q": "방산 한화에어로스페이스 K9 KAI"},
    {"key": "ship",       "name": "조선",       "icon": "🚢", "q": "조선 HD현대 삼성중공업 한화오션"},
    {"key": "nuclear",    "name": "원전",       "icon": "⚛️", "q": "원전 원자력 두산에너빌리티"},
    {"key": "finance",    "name": "금융",       "icon": "🏦", "q": "은행 금융지주 KB금융 신한금융"},
    {"key": "auto",       "name": "자동차",     "icon": "🚗", "q": "현대차 기아 자동차 전기차"},
    {"key": "robot",      "name": "로봇",       "icon": "🦾", "q": "로봇 로보틱스 두산로보틱스"},
    {"key": "space",      "name": "우주항공",   "icon": "🚀", "q": "우주 항공 위성 발사체"},
    {"key": "telco",      "name": "통신",       "icon": "📡", "q": "5G SKT KT LG유플러스"},
    {"key": "game",       "name": "게임",       "icon": "🎮", "q": "게임 넥슨 크래프톤 엔씨"},
    {"key": "enter",      "name": "엔터",       "icon": "🎬", "q": "엔터 하이브 SM엔터 JYP"},
    {"key": "cosmetic",   "name": "화장품",     "icon": "💄", "q": "화장품 K뷰티 아모레퍼시픽 LG생활건강"},
]

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


async def fetch_sector_rss(sector: dict, limit: int = 8) -> dict:
    """한 섹터의 구글 뉴스 RSS 검색."""
    q = sector["q"] + " 주가 OR 실적 OR 급등 OR 급락 OR 계약 OR 수주"
    encoded = urllib.parse.quote(q)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"

    items = []
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers={"User-Agent": UA},
                             timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status != 200:
                    return {"sector": sector, "items": [], "error": f"HTTP {r.status}"}
                text = await r.text()
                try:
                    root = ET.fromstring(text)
                except ET.ParseError:
                    return {"sector": sector, "items": [], "error": "XML 파싱 실패"}

                # 24시간 이내만 (더 넉넉하게 48시간)
                cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

                for it in root.findall(".//item")[:limit * 2]:
                    title = (it.findtext("title") or "").strip()
                    link = (it.findtext("link") or "").strip()
                    pub = (it.findtext("pubDate") or "").strip()
                    src_el = it.find("source")
                    source = (src_el.text or "").strip() if src_el is not None else ""

                    # 매체명 제거 ("XXX 뉴스 - 매체명" 형태)
                    title = re.sub(r"\s*-\s*[^-]+$", "", title).strip()

                    # 시간 파싱
                    try:
                        dt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z")
                        dt = dt.replace(tzinfo=timezone.utc)
                        if dt < cutoff:
                            continue
                        rel = _rel_time(dt)
                    except Exception:
                        rel = ""

                    items.append({
                        "title": title,
                        "link": link,
                        "source": source,
                        "time": rel,
                    })
                    if len(items) >= limit:
                        break

    except Exception as e:
        return {"sector": sector, "items": [], "error": str(e)[:100]}

    return {"sector": sector, "items": items}


def _rel_time(dt: datetime) -> str:
    """상대 시간 (예: '3시간 전')"""
    now = datetime.now(timezone.utc)
    diff = now - dt
    hours = int(diff.total_seconds() / 3600)
    if hours < 1:
        mins = int(diff.total_seconds() / 60)
        return f"{mins}분 전" if mins > 0 else "방금"
    if hours < 24:
        return f"{hours}시간 전"
    days = int(hours / 24)
    return f"{days}일 전"


async def fetch_all_sectors(limit: int = 8) -> list:
    """모든 섹터 병렬 fetch"""
    tasks = [fetch_sector_rss(s, limit) for s in SECTORS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r if isinstance(r, dict) else {"sector": SECTORS[i], "items": [], "error": str(r)[:80]}
            for i, r in enumerate(results)]


def fetch_all_sectors_sync(limit: int = 8) -> list:
    """Flask 동기 wrapper"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(fetch_all_sectors(limit))
    finally:
        try: loop.close()
        except Exception: pass


# ── HTML 페이지 ──────────────────────────────────
def get_sector_news_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>섹터 뉴스 · Yenny Dashboard</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2280%22>📰</text></svg>">
<link rel="stylesheet" href="https://webfontworld.github.io/gmarket/GmarketSans.css">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:'GmarketSans','GmarketSansMedium',-apple-system,'Segoe UI','Noto Sans KR',sans-serif;
  background:#f8f9fa;color:#1a1d23;min-height:100vh;
  font-weight:500;letter-spacing:-0.01em;
}
.topbar{background:#1a1d23;color:#fff;padding:14px 24px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}
.topbar-title{font-size:18px;font-weight:700}
.topbar-actions{display:flex;gap:8px;align-items:center}
.btn{background:#fff;border:1px solid #e5e7eb;color:#1a1d23;padding:8px 14px;border-radius:8px;font-size:13px;cursor:pointer;font-weight:500;font-family:inherit;transition:all .12s}
.btn:hover{background:#f1f3f5;border-color:#1a1d23}
.btn-primary{background:#1a1d23;color:#fff;border-color:#1a1d23}
a.btn{text-decoration:none;display:inline-flex;align-items:center;gap:4px}
.wrap{max-width:1600px;margin:0 auto;padding:24px}
.header-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px}
.header-title{font-size:22px;font-weight:700}
.header-meta{font-size:12px;color:#7a8099}
.filter-bar{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid #e5e7eb}
.filter-chip{background:#fff;border:1px solid #e5e7eb;color:#1a1d23;padding:6px 12px;border-radius:16px;font-size:12px;cursor:pointer;font-family:inherit;transition:all .12s}
.filter-chip:hover{background:#f1f3f5}
.filter-chip.active{background:#1a1d23;color:#fff;border-color:#1a1d23}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px}
.sector-card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px 18px;transition:all .15s}
.sector-card:hover{border-color:#1a1d23;box-shadow:0 2px 8px rgba(0,0,0,0.06)}
.sector-header{display:flex;align-items:center;gap:8px;margin-bottom:12px;padding-bottom:8px;border-bottom:1.5px solid #1a1d23}
.sector-icon{font-size:20px}
.sector-name{font-size:16px;font-weight:700}
.sector-count{margin-left:auto;font-size:11px;color:#7a8099}
.news-item{display:block;padding:8px 0;border-bottom:1px dashed #e5e7eb;font-size:13px;line-height:1.5;color:#2d3436;text-decoration:none;transition:background .1s}
.news-item:hover{background:#f8f9fa}
.news-item:last-child{border-bottom:none}
.news-title{font-weight:500;color:#1a1d23;margin-bottom:3px}
.news-item:hover .news-title{color:#0984e3}
.news-meta{font-size:10.5px;color:#7a8099;display:flex;gap:8px}
.news-source{font-weight:600}
.card-empty{color:#b2bec3;font-style:italic;font-size:12px;padding:16px 0}
.loading{text-align:center;padding:80px;color:#7a8099;font-size:14px}
.spinner{display:inline-block;width:20px;height:20px;border:2px solid #e5e7eb;border-top-color:#1a1d23;border-radius:50%;animation:spin 1s linear infinite;margin-right:8px;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-title">📰 섹터 뉴스</div>
  <div class="topbar-actions">
    <a href="/" class="btn">← 대시보드</a>
    <button class="btn btn-primary" onclick="loadNews()" id="refresh-btn">🔄 새로고침</button>
  </div>
</div>

<div class="wrap">
  <div class="header-row">
    <div class="header-title">지금 섹터별 뉴스</div>
    <div class="header-meta" id="updated"></div>
  </div>
  <div class="filter-bar" id="filter-bar">
    <button class="filter-chip active" onclick="filterBy(this,'all')">전체</button>
  </div>
  <div id="news-body">
    <div class="loading"><span class="spinner"></span>불러오는 중...</div>
  </div>
</div>

<script>
(function(){
  const orig = window.fetch;
  window.fetch = function(url, opts){
    opts = opts || {};
    opts.headers = opts.headers || {};
    if(typeof url === 'string' && url.startsWith('/api')){
      opts.headers['X-API-Secret'] = window._API_SECRET || '';
      opts.credentials = 'include';
    }
    return orig(url, opts);
  };
})();

let _data = [];
let _filter = 'all';

function esc(s){ return String(s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

async function loadNews(){
  const btn = document.getElementById('refresh-btn');
  btn.disabled = true; btn.textContent = '⏳ 로딩...';
  document.getElementById('news-body').innerHTML = '<div class="loading"><span class="spinner"></span>15개 섹터 뉴스 병렬 수집 중...</div>';
  try {
    const res = await fetch('/api/sector-news');
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    _data = data.sectors || [];
    document.getElementById('updated').textContent = '갱신 ' + (data.generated_at || '');
    renderFilters();
    render();
  } catch(e){
    document.getElementById('news-body').innerHTML = '<div class="loading">⚠️ 오류: ' + esc(e.message) + '</div>';
  } finally {
    btn.disabled = false; btn.textContent = '🔄 새로고침';
  }
}

function renderFilters(){
  const bar = document.getElementById('filter-bar');
  bar.innerHTML = '<button class="filter-chip ' + (_filter==='all'?'active':'') + '" onclick="filterBy(this,\'all\')">전체</button>';
  for(const s of _data){
    const sk = s.sector.key;
    const active = _filter === sk;
    bar.innerHTML += '<button class="filter-chip ' + (active?'active':'') + '" onclick="filterBy(this,\'' + sk + '\')">' + s.sector.icon + ' ' + esc(s.sector.name) + '</button>';
  }
}

function filterBy(el, key){
  document.querySelectorAll('.filter-chip').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
  _filter = key;
  render();
}

function render(){
  const body = document.getElementById('news-body');
  const list = _filter === 'all' ? _data : _data.filter(s => s.sector.key === _filter);
  if(!list.length){
    body.innerHTML = '<div class="loading">데이터 없음</div>';
    return;
  }
  let html = '<div class="grid">';
  for(const s of list){
    const sec = s.sector;
    const items = s.items || [];
    html += '<div class="sector-card">';
    html += '<div class="sector-header"><span class="sector-icon">' + sec.icon + '</span><span class="sector-name">' + esc(sec.name) + '</span><span class="sector-count">' + items.length + '건</span></div>';
    if(s.error){
      html += '<div class="card-empty">⚠️ ' + esc(s.error) + '</div>';
    } else if(!items.length){
      html += '<div class="card-empty">최근 뉴스 없음</div>';
    } else {
      for(const it of items){
        html += '<a class="news-item" href="' + esc(it.link) + '" target="_blank">';
        html += '<div class="news-title">' + esc(it.title) + '</div>';
        html += '<div class="news-meta"><span class="news-source">' + esc(it.source || '뉴스') + '</span><span>' + esc(it.time || '') + '</span></div>';
        html += '</a>';
      }
    }
    html += '</div>';
  }
  html += '</div>';
  body.innerHTML = html;
}

loadNews();
</script>
</body>
</html>
"""

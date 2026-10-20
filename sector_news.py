"""
뉴스 허브 화면 (/sector-news)

고정 섹터로 검색하던 방식을 버리고,
섹션 RSS + 네이버 종목뉴스 + 텔레그램을 모아
예니 워치리스트로 분류해 보여준다.
"""


def get_sector_news_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📰 뉴스 허브 · Yenny Dashboard</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2280%22>📰</text></svg>">
<link rel="stylesheet" href="https://webfontworld.github.io/gmarket/GmarketSans.css">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:'GmarketSans','GmarketSansMedium',-apple-system,'Segoe UI','Noto Sans KR',sans-serif;
  background:#f8f9fa;color:#1a1d23;min-height:100vh;font-weight:500;letter-spacing:-0.01em;
}
.topbar{background:#1a1d23;color:#fff;padding:14px 24px;display:flex;
  justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}
.topbar-title{font-size:18px;font-weight:700}
.topbar-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.btn{background:#fff;border:1px solid #e5e7eb;color:#1a1d23;padding:8px 14px;
  border-radius:8px;font-size:13px;cursor:pointer;font-weight:500;font-family:inherit;transition:all .12s}
.btn:hover{background:#f1f3f5;border-color:#1a1d23}
.btn-primary{background:#1a1d23;color:#fff;border-color:#1a1d23}
.btn:disabled{opacity:.5;cursor:default}
a.btn{text-decoration:none;display:inline-flex;align-items:center;gap:4px}

.controlbar{background:#fff;border-bottom:1px solid #e5e7eb;padding:9px 24px;
  display:flex;gap:14px;align-items:center;flex-wrap:wrap;position:sticky;top:57px;z-index:90}
.ctrl-label{font-size:10.5px;color:#7a8099;font-weight:600;margin-right:3px}
.ctrl-group{display:flex;gap:3px;align-items:center}
.seg{padding:5px 11px;border:1px solid #e5e7eb;border-radius:7px;background:#fff;
  color:#1a1d23;font-size:11.5px;font-weight:500;cursor:pointer;font-family:inherit;
  transition:all .12s;white-space:nowrap}
.seg:hover{background:#f1f3f5;border-color:#1a1d23}
.seg.active{background:#1a1d23;color:#fff;border-color:#1a1d23}
.search-box{padding:5px 12px;border:1px solid #e5e7eb;border-radius:16px;
  font-size:11.5px;font-family:inherit;outline:none;width:180px;background:#f8f9fa}
.search-box:focus{border-color:#1a1d23;background:#fff;width:240px}
.meta{font-size:11px;color:#a8b0bd;margin-left:auto;font-style:italic}

.wrap{max-width:1500px;margin:0 auto;padding:16px 24px 60px}

/* 테마 칩 */
.themes{display:flex;gap:6px;flex-wrap:wrap;padding-bottom:12px;
  border-bottom:1.5px solid #e5e7eb;margin-bottom:16px}
.chip{display:inline-flex;align-items:center;gap:5px;padding:6px 13px;
  border:1px solid #e5e7eb;border-radius:18px;background:#fff;font-size:12px;
  cursor:pointer;font-family:inherit;transition:all .12s;white-space:nowrap}
.chip:hover{border-color:#1a1d23;background:#f8f9fa}
.chip.active{background:#1a1d23;color:#fff;border-color:#1a1d23}
.chip-n{font-size:10px;opacity:.65;font-variant-numeric:tabular-nums}
.chip.unmatched{border-style:dashed;color:#e17055;border-color:#ffd9c4}
.chip.unmatched.active{background:#e17055;color:#fff;border-color:#e17055}

/* 기사 */
.list{display:flex;flex-direction:column;gap:2px}
.item{display:block;background:#fff;border:1px solid #eceff1;border-radius:10px;
  padding:12px 15px;text-decoration:none;color:inherit;transition:all .12s}
.item:hover{border-color:#c5ccd6;box-shadow:0 2px 10px rgba(0,0,0,.05)}
.item.hot{border-left:3px solid #d63031}
.item.warm{border-left:3px solid #e17055}
.it-head{display:flex;align-items:center;gap:7px;margin-bottom:5px;flex-wrap:wrap}
.strength{font-size:11px;font-weight:700;padding:1px 8px;border-radius:9px;
  white-space:nowrap;font-variant-numeric:tabular-nums}
.s-hot{background:#ffe7e4;color:#d63031}
.s-warm{background:#fff2e8;color:#e17055}
.s-cool{background:#f1f3f5;color:#7a8099}
.it-title{font-size:14px;font-weight:700;line-height:1.45;flex:1;min-width:200px}
.item:hover .it-title{color:#0984e3}
.it-body{font-size:12px;color:#7a8099;line-height:1.55;margin:4px 0 6px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.it-foot{display:flex;align-items:center;gap:7px;flex-wrap:wrap;font-size:10.5px;color:#a8b0bd}
.tag{padding:1px 7px;border-radius:8px;font-size:10px;font-weight:600;white-space:nowrap}
.tag-theme{background:#e8f4fd;color:#0277bd}
.tag-alert{background:#fff8e1;color:#a06d00}
.tag-src{background:#f1f3f5;color:#7a8099}
.office{font-weight:600;color:#7a8099}

.empty{text-align:center;padding:60px 20px;color:#b2bec3;font-style:italic}
.loading{text-align:center;padding:60px 20px;color:#7a8099}
.spin{display:inline-block;animation:sp 1s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.hint{background:#fff8f3;border:1px solid #ffd9c4;border-radius:9px;
  padding:10px 14px;font-size:12px;color:#a0522d;margin-bottom:14px}
.hint b{color:#e17055}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-title">📰 뉴스 허브</div>
  <div class="topbar-actions">
    <a href="/" class="btn">← 대시보드</a>
    <a href="/watchlist" class="btn">📊 관심종목</a>
    <a href="/watchlist/fav" class="btn">⭐ 즐겨찾기</a>
    <button class="btn btn-primary" onclick="load(true)" id="refresh-btn">🔄 새로고침</button>
  </div>
</div>

<div class="controlbar">
  <div class="ctrl-group">
    <span class="ctrl-label">보기</span>
    <button class="seg active" data-view="all" onclick="setView('all')">전체</button>
    <button class="seg" data-view="mine" onclick="setView('mine')">내 종목</button>
    <button class="seg" data-view="alert" onclick="setView('alert')">🔔 신호</button>
    <button class="seg" data-view="new" onclick="setView('new')">미분류</button>
  </div>
  <div class="ctrl-group">
    <span class="ctrl-label">기간</span>
    <button class="seg" data-h="6" onclick="setHours(6)">6h</button>
    <button class="seg active" data-h="12" onclick="setHours(12)">12h</button>
    <button class="seg" data-h="24" onclick="setHours(24)">24h</button>
  </div>
  <div class="ctrl-group">
    <input type="text" class="search-box" id="q" placeholder="🔎 기사 검색"
           oninput="render()" oncompositionstart="_ime=true"
           oncompositionend="_ime=false;render()"/>
  </div>
  <span class="meta" id="meta"></span>
</div>

<div class="wrap">
  <div class="themes" id="themes"></div>
  <div id="body"><div class="loading"><span class="spin">⏳</span> 뉴스 모으는 중...</div></div>
</div>

<script>
let _items = [], _view = 'all', _theme = null, _hours = 12, _ime = false, _loading = false;

function esc(s){ return String(s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

async function load(force){
  if(_loading) return;
  _loading = true;
  const b = document.getElementById('refresh-btn');
  if(b){ b.disabled = true; b.textContent = '⏳ 수집 중...'; }
  document.getElementById('body').innerHTML =
    '<div class="loading"><span class="spin">⏳</span> 뉴스 모으는 중...</div>';
  try {
    const r = await fetch('/api/news-hub?hours=' + _hours + (force ? '&force=1' : ''));
    const d = await r.json();
    if(!d.ok){
      document.getElementById('body').innerHTML =
        '<div class="empty">⚠️ ' + esc(d.error || '불러오기 실패') + '</div>';
      return;
    }
    _items = d.items || [];
    document.getElementById('meta').textContent =
      d.total + '건 · ' + (d.sources || '') + ' · ' + new Date().toLocaleTimeString('ko-KR');
    renderThemes();
    render();
  } catch(e){
    document.getElementById('body').innerHTML =
      '<div class="empty">⚠️ ' + esc(e.message || e) + '</div>';
  } finally {
    _loading = false;
    if(b){ b.disabled = false; b.textContent = '🔄 새로고침'; }
  }
}

function setView(v){
  _view = v;
  document.querySelectorAll('.seg[data-view]').forEach(x =>
    x.classList.toggle('active', x.getAttribute('data-view') === v));
  render();
}

function setHours(h){
  _hours = h;
  document.querySelectorAll('.seg[data-h]').forEach(x =>
    x.classList.toggle('active', +x.getAttribute('data-h') === h));
  load(true);
}

function renderThemes(){
  const cnt = {};
  let unmatched = 0;
  for(const it of _items){
    if(!it.themes || !it.themes.length){ unmatched++; continue; }
    const seen = new Set();
    for(const t of it.themes){
      const k = t.sector;
      if(seen.has(k)) continue;
      seen.add(k);
      cnt[k] = (cnt[k] || 0) + 1;
    }
  }
  const rows = Object.entries(cnt).sort((a,b) => b[1] - a[1]);
  let html = '<button class="chip' + (_theme === null ? ' active' : '') +
             '" onclick="pickTheme(null)">전체 <span class="chip-n">' +
             _items.length + '</span></button>';
  html += rows.map(([k,v]) =>
    '<button class="chip' + (_theme === k ? ' active' : '') + '" onclick="pickTheme(\'' +
    esc(k).replace(/'/g,"\\'") + '\')">' + esc(k) +
    ' <span class="chip-n">' + v + '</span></button>').join('');
  if(unmatched){
    html += '<button class="chip unmatched' + (_theme === '__new__' ? ' active' : '') +
            '" onclick="pickTheme(\'__new__\')">📌 미분류 <span class="chip-n">' +
            unmatched + '</span></button>';
  }
  document.getElementById('themes').innerHTML = html;
}

function pickTheme(t){ _theme = t; renderThemes(); render(); }

function render(){
  if(_ime) return;
  const q = (document.getElementById('q').value || '').trim().toLowerCase();
  let rows = _items.slice();

  if(_view === 'mine')  rows = rows.filter(x => x.themes && x.themes.length);
  if(_view === 'alert') rows = rows.filter(x => x.alerts && x.alerts.length);
  if(_view === 'new')   rows = rows.filter(x => !x.themes || !x.themes.length);

  if(_theme === '__new__') rows = rows.filter(x => !x.themes || !x.themes.length);
  else if(_theme) rows = rows.filter(x => (x.themes||[]).some(t => t.sector === _theme));

  if(q) rows = rows.filter(x =>
    (x.title||'').toLowerCase().includes(q) || (x.body||'').toLowerCase().includes(q));

  const body = document.getElementById('body');
  if(!rows.length){
    body.innerHTML = '<div class="empty">조건에 맞는 기사가 없습니다</div>';
    return;
  }

  let html = '';
  if(_view === 'new' || _theme === '__new__'){
    html += '<div class="hint"><b>📌 미분류</b> — 워치리스트에 없는 종목·주제입니다. ' +
            '여기서 새 테마를 발견하면 관심종목에 추가해두세요. 다음부터 자동으로 분류됩니다.</div>';
  }

  html += '<div class="list">' + rows.slice(0, 200).map(it => {
    const c = it.cluster || 1;
    const cls = c >= 8 ? 'hot' : (c >= 3 ? 'warm' : '');
    const scls = c >= 8 ? 's-hot' : (c >= 3 ? 's-warm' : 's-cool');
    const strength = c >= 3 ? '<span class="strength ' + scls + '">' +
                     (c >= 8 ? '🔥 ' : '⚡ ') + c + '곳</span>' : '';
    const themes = (it.themes || []).slice(0,3).map(t =>
      '<span class="tag tag-theme">' + esc(t.sector) + ' › ' + esc(t.group) + '</span>').join('');
    const alerts = (it.alerts || []).map(a =>
      '<span class="tag tag-alert">' + esc(a) + '</span>').join('');
    const srcTag = it.src === 'tele' ? '<span class="tag tag-src">✈️ 텔레</span>' :
                   (it.src === 'naver' ? '<span class="tag tag-src">📊 종목</span>' : '');
    const offices = (it.offices && it.offices.length > 1)
      ? it.offices.slice(0,3).filter(Boolean).join(' · ')
      : (it.office || '');
    return '<a class="item ' + cls + '" href="' + esc(it.link || '#') + '" target="_blank">' +
      '<div class="it-head">' + strength +
        '<span class="it-title">' + esc(it.title) + '</span></div>' +
      (it.body ? '<div class="it-body">' + esc(it.body) + '</div>' : '') +
      '<div class="it-foot">' + themes + alerts + srcTag +
        '<span class="office">' + esc(offices) + '</span>' +
        '<span>' + esc(it.ago || '') + '</span>' +
      '</div></a>';
  }).join('') + '</div>';

  body.innerHTML = html;
}

load();
setInterval(() => { if(!document.hidden && !_loading) load(); }, 300000);
</script>
</body>
</html>
"""

"""
⭐ 즐겨찾기 워치리스트 (/watchlist/fav)

창고형 /watchlist 와 완전히 분리된 가벼운 리스트.
- 저장 위치: posts 테이블의 type='watchlist_fav'  (창고는 'watchlist')
- 구조: TODAY(그룹 없음) + 일반 섹터(그룹 있음)
- 종목마다 한 줄 메모
"""


def get_fav_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⭐ 즐겨찾기 · Yenny Dashboard</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2280%22>⭐</text></svg>">
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
.topbar-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.btn{background:#fff;border:1px solid #e5e7eb;color:#1a1d23;padding:8px 14px;border-radius:8px;font-size:13px;cursor:pointer;font-weight:500;font-family:inherit;transition:all .12s}
.btn:hover{background:#f1f3f5;border-color:#1a1d23}
.btn-primary{background:#1a1d23;color:#fff;border-color:#1a1d23}
.btn-primary:hover{background:#2a2d33}
.btn-danger{color:#d63031;border-color:#fab1a0}
.btn-danger:hover{background:#ffe7e4}
.btn-mini{padding:4px 8px;font-size:11px}
a.btn{text-decoration:none;display:inline-flex;align-items:center;gap:4px}

.controlbar{
  background:#fff;border-bottom:1px solid #e5e7eb;
  padding:8px 24px;display:flex;gap:14px;align-items:center;flex-wrap:wrap;
  position:sticky;top:57px;z-index:90;
}
.ctrl-group{display:flex;gap:3px;align-items:center}
.ctrl-label{font-size:10.5px;color:#7a8099;font-weight:600;margin-right:3px}
.seg{
  padding:4px 9px;border:1px solid #e5e7eb;border-radius:6px;
  background:#fff;color:#1a1d23;font-size:11px;font-weight:500;
  cursor:pointer;font-family:inherit;transition:all .12s;white-space:nowrap;
}
.seg:hover{background:#f1f3f5;border-color:#1a1d23}
.seg.active{background:#1a1d23;color:#fff;border-color:#1a1d23}
.market-hint{font-size:11px;color:#7a8099;font-style:italic}

.wrap{max-width:1400px;margin:0 auto;padding:16px 24px}
.updated{font-size:11px;color:#7a8099;margin-bottom:12px}

/* 섹터 탭 */
.sector-tabs{
  display:flex;gap:6px;flex-wrap:wrap;padding-bottom:12px;
  border-bottom:1.5px solid #e5e7eb;margin-bottom:16px;align-items:center;
}
.sector-tab{
  display:flex;align-items:center;gap:6px;
  padding:8px 14px;border:1px solid #e5e7eb;border-radius:20px;
  background:#fff;color:#1a1d23;font-size:13px;font-weight:500;
  cursor:pointer;font-family:inherit;transition:all .12s;white-space:nowrap;
}
.sector-tab:hover{background:#f1f3f5;border-color:#1a1d23}
.sector-tab.active{background:#1a1d23;color:#fff;border-color:#1a1d23}
.sector-tab.today{border-color:#e17055;color:#e17055;font-weight:700}
.sector-tab.today.active{background:#e17055;color:#fff;border-color:#e17055}
.tab-icon-btn{
  background:transparent;border:0;cursor:pointer;padding:1px 3px;
  font-size:11px;line-height:1;opacity:0.75;font-family:inherit;border-radius:4px;
}
.tab-icon-btn:hover{opacity:1;background:rgba(255,255,255,0.2)}
.sector-add{
  width:34px;height:34px;border-radius:20px;border:1px dashed #999;
  background:transparent;color:#666;font-size:16px;font-weight:700;
  cursor:pointer;font-family:inherit;
}
.sector-add:hover{background:#fff;color:#1a1d23;border-color:#1a1d23;border-style:solid}

/* 그룹 */
.group{margin-bottom:22px}
.group-header{
  display:flex;align-items:center;gap:8px;
  padding:8px 0;margin-bottom:4px;border-bottom:1.5px solid #1a1d23;
  font-size:14px;font-weight:700;
}
.group-actions{margin-left:auto;display:flex;gap:4px}

/* 표 */
.stock-table{width:100%;border-collapse:collapse}
.stock-table th{
  text-align:left;padding:7px 10px;font-size:10.5px;color:#7a8099;
  font-weight:600;border-bottom:1px solid #e5e7eb;
}
.stock-table th.num{text-align:right}
.stock-row{border-bottom:1px solid #f1f3f5;transition:background .1s}
.stock-row:hover{background:#f8f9fa}
.stock-row td{padding:8px 10px;font-size:13px;vertical-align:middle}
.stock-row td.num{text-align:right;font-variant-numeric:tabular-nums}
.stock-name{font-weight:600}
.stock-code{font-size:10px;color:#a8b0bd;margin-left:4px}
.up{color:#d63031}
.down{color:#0984e3}
.flat{color:#7a8099}
.hot{
  display:inline-block;padding:1px 6px;border-radius:8px;
  background:#ffe7e4;color:#d63031;font-size:10px;font-weight:700;
  margin-left:6px;vertical-align:middle;
}
.mkt-badge{
  display:inline-block;padding:1px 5px;border-radius:4px;
  font-size:9.5px;font-weight:700;margin-left:5px;vertical-align:middle;
}
.mkt-badge.krx{background:#e3f2fd;color:#0277bd}
.mkt-badge.nxt{background:#f3e5f5;color:#7b1fa2}
.mkt-badge.un{background:#f1f3f5;color:#616161}

/* 메모 */
.memo-cell{max-width:320px}
.memo-input{
  width:100%;border:1px solid transparent;border-radius:6px;
  padding:4px 8px;font-size:12px;font-family:inherit;
  background:transparent;color:#636e72;outline:none;transition:all .12s;
}
.memo-input:hover{background:#f1f3f5}
.memo-input:focus{background:#fff;border-color:#1a1d23;color:#1a1d23}
.memo-input::placeholder{color:#c5ccd6;font-style:italic}

/* 🏷️ 테마 패널 */
.theme-bar{
  display:flex;gap:5px;align-items:center;flex-wrap:wrap;
  padding-bottom:12px;margin-bottom:14px;border-bottom:1.5px solid #e5e7eb;
}
.theme-search{
  padding:5px 11px;border:1px solid #e5e7eb;border-radius:16px;
  font-size:11.5px;font-family:inherit;outline:none;width:150px;
  background:#f8f9fa;margin-left:10px;
}
.theme-search:focus{border-color:#1a1d23;background:#fff;width:200px}
.theme-meta{font-size:11px;color:#a8b0bd;margin-left:auto}
.theme-list{display:flex;flex-direction:column;gap:5px}
.theme-row{
  background:#fff;border:1px solid #e5e7eb;border-radius:10px;
  padding:11px 15px;cursor:pointer;transition:all .12s;
  display:flex;align-items:center;gap:11px;
}
.theme-row:hover{border-color:#1a1d23;box-shadow:0 2px 8px rgba(0,0,0,0.06)}
.theme-row.open{border-color:#1a1d23}
.th-idx{font-size:11px;font-weight:700;color:#a8b0bd;min-width:20px;text-align:right}
.th-caret{font-size:10px;color:#a8b0bd;transition:transform .15s}
.theme-row.open .th-caret{transform:rotate(90deg);color:#1a1d23}
.th-name{font-size:14px;font-weight:700;white-space:nowrap}
.th-cnt{font-size:10.5px;color:#a8b0bd;white-space:nowrap}
.th-updown{font-size:10.5px;white-space:nowrap}
.th-main{
  flex:1;font-size:11.5px;color:#7a8099;min-width:0;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.th-pct{font-size:15px;font-weight:700;min-width:74px;text-align:right;
  font-variant-numeric:tabular-nums}
.th-period{font-size:11px;min-width:64px;text-align:right;
  font-variant-numeric:tabular-nums;color:#a8b0bd}
.theme-stocks{
  margin:2px 0 8px 26px;padding-left:14px;border-left:2px dashed #e5e7eb;
}
.theme-stocks .stock-table th{font-size:10px;padding:5px 8px}
.theme-stocks .stock-row td{padding:6px 8px;font-size:12px}
.th-star{
  background:transparent;border:0;cursor:pointer;font-size:15px;
  color:#d7dce3;padding:0 2px;transition:all .12s;
}
.th-star:hover{color:#f0b429;transform:scale(1.2)}
.th-star.on{color:#f0b429}

.stock-name.clickable{cursor:pointer;border-bottom:1px dashed transparent}
.stock-name.clickable:hover{color:#0984e3;border-bottom-color:#0984e3}
.today-header{
  border-bottom:1.5px solid #e17055 !important;color:#e17055;
  margin-top:18px;font-size:13px;
}

/* 모달 */
.modal-overlay{
  display:none;position:fixed;inset:0;background:rgba(0,0,0,0.45);
  z-index:300;align-items:center;justify-content:center;padding:20px;
}
.modal-overlay.open{display:flex}
.modal{
  background:#fff;border-radius:14px;width:100%;max-width:600px;
  max-height:88vh;display:flex;flex-direction:column;
  box-shadow:0 12px 40px rgba(0,0,0,0.25);
}
.modal-head{
  display:flex;justify-content:space-between;align-items:center;
  padding:16px 20px;border-bottom:1px solid #e5e7eb;
}
.modal-title{font-size:16px;font-weight:700}
.modal-body{padding:16px 20px;overflow-y:auto;flex:1}
.modal-foot{display:flex;justify-content:flex-end;gap:8px;padding:12px 20px;border-top:1px solid #e5e7eb}
.stock-quote{
  display:flex;gap:18px;flex-wrap:wrap;
  background:#f8f9fa;border-radius:8px;padding:12px 14px;margin-bottom:14px;
}
.sq-item{font-size:14px;font-weight:700;font-variant-numeric:tabular-nums}
.sq-item b{display:block;font-size:10px;color:#7a8099;font-weight:600;margin-bottom:2px}
.stock-section{
  font-size:11.5px;color:#7a8099;font-weight:700;
  margin:14px 0 7px;padding-bottom:5px;border-bottom:1px solid #e5e7eb;
}
.stock-places{display:flex;flex-direction:column;gap:5px}
.stock-place{
  background:#fff;border:1px solid #e5e7eb;border-radius:8px;
  padding:9px 13px;font-size:12.5px;font-weight:600;
}
.db-entry{background:#fafbfc;border:1px solid #eceff1;border-radius:8px;padding:10px 13px;margin-bottom:6px}
.db-theme{
  display:inline-block;font-size:11px;font-weight:700;
  background:#e8f4fd;color:#0277bd;padding:2px 9px;border-radius:10px;margin-bottom:6px;
}
.db-desc{font-size:12.5px;line-height:1.6;color:#2d3436}
.stock-empty{font-size:12px;color:#a8b0bd;font-style:italic;padding:10px 2px}

.row-actions{display:none;gap:2px}
.stock-row:hover .row-actions{display:inline-flex}

/* 종목 추가 */
.add-stock{display:flex;gap:6px;padding:10px 0}
.ac-wrap{position:relative;flex:1}
.ac-wrap input{
  width:100%;padding:7px 11px;border:1px solid #e5e7eb;border-radius:7px;
  font-size:12.5px;font-family:inherit;outline:none;
}
.ac-wrap input:focus{border-color:#1a1d23}
.ac-list{
  display:none;position:absolute;top:calc(100% + 2px);left:0;right:0;
  background:#fff;border:1px solid #e5e7eb;border-radius:8px;
  box-shadow:0 4px 16px rgba(0,0,0,0.1);z-index:50;
  max-height:260px;overflow-y:auto;
}
.ac-list.open{display:block}
.ac-item{
  padding:8px 12px;font-size:12.5px;cursor:pointer;
  display:flex;align-items:center;gap:8px;border-bottom:1px solid #f1f3f5;
}
.ac-item:last-child{border-bottom:none}
.ac-item:hover,.ac-item.sel{background:#f1f3f5}
.ac-item-name{font-weight:600}
.ac-item-code{font-size:10.5px;color:#a8b0bd}
.ac-empty,.ac-loading{padding:10px 12px;font-size:12px;color:#a8b0bd}
.add-group-btn{
  padding:8px 14px;border:1px dashed #999;border-radius:8px;
  background:transparent;color:#666;font-size:12px;cursor:pointer;
  font-family:inherit;margin-top:8px;
}
.add-group-btn:hover{background:#fff;color:#1a1d23;border-color:#1a1d23}

.content-empty{color:#b2bec3;font-style:italic;padding:40px 20px;text-align:center;display:block}
.save-indicator{
  position:fixed;bottom:24px;right:24px;background:#1a1d23;color:#fff;
  padding:10px 18px;border-radius:24px;font-size:12px;font-weight:500;
  opacity:0;transition:opacity .3s;pointer-events:none;z-index:200;
  box-shadow:0 4px 12px rgba(0,0,0,0.15);
}
.save-indicator.visible{opacity:1}

.today-note{
  background:#fff8f3;border:1px solid #ffd9c4;border-radius:8px;
  padding:9px 14px;font-size:12px;color:#a0522d;margin-bottom:12px;
  display:flex;align-items:center;gap:10px;
}
.today-note b{color:#e17055}

@media print{
  @page{size:A4 landscape;margin:8mm}
  .topbar,.controlbar,.sector-add,.row-actions,.add-stock,.add-group-btn,
  .save-indicator,.tab-icon-btn,.today-note{display:none !important}
  body{background:#fff}
  .sector-tab:not(.active){display:none}
  .memo-input{border:none;background:none}
  *{-webkit-print-color-adjust:exact !important;print-color-adjust:exact !important}
}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-title">⭐ 즐겨찾기</div>
  <div class="topbar-actions">
    <a href="/" class="btn">← 대시보드</a>
    <a href="/watchlist" class="btn">📊 전체 관심종목</a>
    <button class="btn" onclick="toggleThemeView()" id="theme-btn">🏷️ 테마</button>
    <button class="btn" onclick="toggleEdit()" id="edit-btn">⚙️ 편집</button>
    <button class="btn btn-primary" onclick="refreshQuotes({force:true})" id="refresh-btn">🔄 시세 갱신</button>
    <button class="btn" onclick="window.print()">🖨️ 인쇄</button>
  </div>
</div>

<div class="controlbar">
  <div class="ctrl-group">
    <span class="ctrl-label">시장</span>
    <button class="seg" data-mkt="UN" onclick="setMarket('UN')">통합</button>
    <button class="seg" data-mkt="J" onclick="setMarket('J')">KRX</button>
    <button class="seg" data-mkt="NX" onclick="setMarket('NX')">NXT</button>
  </div>
  <div class="ctrl-group" id="sess-wrap" style="display:none">
    <span class="ctrl-label">세션</span>
    <button class="seg" data-sess="auto" onclick="setSession('auto')">자동</button>
    <button class="seg" data-sess="pre" onclick="setSession('pre')">🌅 프리</button>
    <button class="seg" data-sess="after" onclick="setSession('after')">🌙 애프터</button>
  </div>
  <div class="ctrl-group">
    <span class="ctrl-label">정렬</span>
    <button class="seg" data-sort="manual" onclick="setSort('manual')">기본</button>
    <button class="seg" data-sort="chg_desc" onclick="setSort('chg_desc')">등락률 ↓</button>
    <button class="seg" data-sort="chg_asc" onclick="setSort('chg_asc')">등락률 ↑</button>
  </div>
  <div class="ctrl-group" style="margin-left:auto">
    <span class="market-hint" id="market-hint"></span>
  </div>
</div>

<div class="wrap">
  <div class="updated" id="updated"></div>

  <!-- 🏷️ 테마 (인포스탁) -->
  <div id="theme-panel" style="display:none">
    <div class="theme-bar">
      <span class="ctrl-label">기간</span>
      <button class="seg active" data-days="1" onclick="setThemeDays(1)">1일</button>
      <button class="seg" data-days="5" onclick="setThemeDays(5)">5일</button>
      <button class="seg" data-days="20" onclick="setThemeDays(20)">20일</button>
      <span class="ctrl-label" style="margin-left:10px">정렬</span>
      <button class="seg active" data-tsort="up" onclick="setThemeSort('up')">등락률 ↓</button>
      <button class="seg" data-tsort="down" onclick="setThemeSort('down')">등락률 ↑</button>
      <input type="text" id="theme-search" class="theme-search" placeholder="🔎 테마 검색"
             oninput="renderThemes()" oncompositionstart="_composing=true"
             oncompositionend="_composing=false;renderThemes()"/>
      <button class="btn btn-mini" onclick="loadThemes(true)">🔄 갱신</button>
      <span class="theme-meta" id="theme-meta"></span>
    </div>
    <div id="theme-list"><div class="content-empty">불러오는 중...</div></div>
  </div>

  <div id="fav-main">
    <div class="sector-tabs" id="sector-tabs"></div>
    <div id="fav-body"><div class="content-empty">불러오는 중...</div></div>
  </div>
</div>

<div id="save-indicator" class="save-indicator">💾 저장됨</div>

<!-- 📈 종목 상세 -->
<div id="stock-overlay" class="modal-overlay" onclick="if(event.target===this)closeStock()">
  <div class="modal">
    <div class="modal-head">
      <span class="modal-title" id="stock-title">종목</span>
      <button class="btn btn-mini" onclick="closeStock()">✕</button>
    </div>
    <div class="modal-body" id="stock-body"></div>
    <div class="modal-foot"><button class="btn" onclick="closeStock()">닫기</button></div>
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

const TODAY_ID = 'today';
let _data = {sectors: [], currentSectorId: null};
let _quotes = {};
let _saveTimer = null;
let _editing = false;
let _market = 'UN';
let _session = 'auto';
let _sort = 'manual';
let _fetching = false;
let _composing = false;
let _autoTimer = null;

function genId(){ return 'f' + Math.random().toString(36).slice(2, 10); }
function esc(s){ return String(s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function num(n){ return (n === undefined || n === null) ? '—' : Number(n).toLocaleString('ko-KR'); }

const MKT_LABEL = {'UN':'통합','J':'KRX','NX':'NXT'};
const MKT_CLASS = {'UN':'un','J':'krx','NX':'nxt'};

// ── 세션 / 괴리 ─────────────────────────
function effectiveSession(){
  if(_session !== 'auto') return _session;
  const n = new Date();
  return (n.getHours()*60 + n.getMinutes() < 9*60) ? 'pre' : 'after';
}
function isOffHour(){
  if(_session !== 'auto') return true;
  const n = new Date();
  const t = n.getHours()*60 + n.getMinutes();
  return !(t >= 9*60 && t < 15*60+40);
}
function gapMode(){ return _market === 'NX' && isOffHour(); }
function gapOf(q){
  if(!q) return {gap:null, pct:null, base:0};
  const base = q.krx_close || 0;
  if(q.gap_pct !== undefined && q.gap_pct !== null) return {gap:q.gap, pct:q.gap_pct, base:base};
  if(base && q.price){
    const g = q.price - base;
    return {gap:g, pct: Math.round(g/base*10000)/100, base:base};
  }
  return {gap:null, pct:null, base:base};
}
function pctOf(code){
  const q = _quotes[code];
  if(!q) return undefined;
  if(gapMode()){
    const g = gapOf(q);
    return g.pct === null ? undefined : g.pct;
  }
  return q.chg_pct;
}

function updateHint(){
  const n = new Date();
  const t = n.getHours()*60 + n.getMinutes();
  let phase = '';
  if(t >= 8*60 && t < 9*60) phase = '프리마켓';
  else if(t >= 9*60 && t < 15*60+30) phase = '정규장';
  else if(t >= 15*60+30 && t < 16*60) phase = '장 마감 정리';
  else if(t >= 16*60 && t < 20*60) phase = '애프터마켓';
  else phase = '장외 시간';
  let extra = '';
  if(_market === 'NX'){
    const es = effectiveSession();
    extra = ' · ' + (es === 'pre' ? '🌅 프리 (전일 마감가 대비)' : '🌙 애프터 (당일 마감가 대비)');
  }
  const el = document.getElementById('market-hint');
  if(el) el.textContent = '🕐 ' + phase + ' · ' + MKT_LABEL[_market] + extra;
}

// ── 저장 / 로드 ─────────────────────────
function scheduleSave(){
  if(_saveTimer) clearTimeout(_saveTimer);
  _saveTimer = setTimeout(saveNow, 800);
}
async function saveNow(){
  try {
    const res = await fetch('/api/post/watchlist_fav', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: JSON.stringify(_data),
                            date: new Date().toISOString().slice(0,10)})
    });
    if(res.ok) showSaved();
    else showSaved('⚠️ 저장 실패 HTTP ' + res.status);
  } catch(e){ showSaved('⚠️ 저장 오류'); }
}
function showSaved(msg){
  const el = document.getElementById('save-indicator');
  el.textContent = msg || ('💾 저장됨 ' + new Date().toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit'}));
  el.classList.add('visible');
  setTimeout(() => el.classList.remove('visible'), 1800);
}

async function loadData(){
  try {
    const res = await fetch('/api/post/watchlist_fav');
    const data = res.ok ? await res.json() : null;
    if(data && data.content){
      try { _data = JSON.parse(data.content); } catch(e){ _data = null; }
    } else { _data = null; }
  } catch(e){ _data = null; }

  if(!_data || !_data.sectors || !_data.sectors.length) initEmpty();
  // TODAY는 항상 존재하도록 보정 (창고에서 담을 때 기본 대상)
  if(!_data.sectors.some(s => s.id === TODAY_ID)){
    _data.sectors.unshift({id: TODAY_ID, name: '🔥 TODAY',
                           groups: [{id: genId(), name: '', stocks: []}]});
  }
  if(!_data.currentSectorId || !_data.sectors.find(s => s.id === _data.currentSectorId)){
    _data.currentSectorId = _data.sectors[0].id;
  }
  render();
  refreshQuotes();
}

function initEmpty(){
  _data = {
    sectors: [
      {id: TODAY_ID, name: '🔥 TODAY', groups: [{id: genId(), name: '', stocks: []}]},
    ],
    currentSectorId: TODAY_ID,
  };
}

// ── 렌더 ────────────────────────────────
function currentSector(){ return _data.sectors.find(s => s.id === _data.currentSectorId); }
function isToday(s){ return s && s.id === TODAY_ID; }

function render(){ renderTabs(); renderBody(); }

function renderTabs(){
  const el = document.getElementById('sector-tabs');
  el.innerHTML = _data.sectors.map(s => {
    const active = s.id === _data.currentSectorId;
    const today = s.id === TODAY_ID;
    return '<button class="sector-tab ' + (active?'active ':'') + (today?'today':'') +
      '" onclick="switchSector(\'' + s.id + '\')">' +
      '<span>' + esc(s.name) + '</span>' +
      (active && _editing && !today
        ? ' <button class="tab-icon-btn" onclick="event.stopPropagation();renameSector(\'' + s.id + '\')">✏️</button>' +
          ' <button class="tab-icon-btn" onclick="event.stopPropagation();deleteSector(\'' + s.id + '\')">✕</button>'
        : '') +
      '</button>';
  }).join('');
  if(_editing){
    el.innerHTML += '<button class="sector-add" onclick="addSector()" title="새 섹터">+</button>';
  }
}

function sortStocks(stocks){
  const arr = (stocks || []).slice();
  if(_sort === 'manual') return arr;
  arr.sort((a,b) => {
    const pa = pctOf(a.code), pb = pctOf(b.code);
    if(_sort === 'chg_desc') return (pb ?? -999) - (pa ?? -999);
    if(_sort === 'chg_asc')  return (pa ??  999) - (pb ??  999);
    return 0;
  });
  return arr;
}

function renderBody(){
  const body = document.getElementById('fav-body');
  const s = currentSector();
  if(!s){ body.innerHTML = '<span class="content-empty">섹터가 없습니다</span>'; return; }

  let html = '';
  if(isToday(s)){
    html += '<div class="today-note">' +
      '<b>🔥 TODAY</b> 오늘 볼 종목. 구분을 넣어 나눌 수 있습니다.' +
      '<button class="btn btn-mini" style="margin-left:auto" onclick="addTodayHeader()">+ 구분 추가</button>' +
      (_editing ? ' <button class="btn btn-mini btn-danger" onclick="clearToday()">🗑 전체 비우기</button>' : '') +
      '</div>';
    if(!s.groups.length) s.groups = [{id: genId(), name: '', stocks: []}];
    // 첫 그룹은 헤더 없이, 나머지는 구분 헤더와 함께
    s.groups.forEach((g, i) => {
      html += renderGroup(g, i === 0 && !g.name, true);
    });
  } else {
    if(!s.groups.length){
      html += '<span class="content-empty">그룹이 없습니다' + (_editing ? '' : ' · 편집 모드에서 추가하세요') + '</span>';
    } else {
      for(const g of s.groups) html += renderGroup(g, false);
    }
    if(_editing){
      html += '<div style="text-align:center"><button class="add-group-btn" onclick="addGroup()">+ 새 그룹</button></div>';
    }
  }
  body.innerHTML = html;
}

function renderGroup(g, hideHeader, inToday){
  const isNxt = gapMode();
  const stocks = sortStocks(g.stocks);
  let head = '';
  if(!hideHeader){
    const vals = (g.stocks||[]).map(x => pctOf(x.code)).filter(v => v !== undefined && v !== null);
    let avgHtml = '';
    if(vals.length){
      const avg = vals.reduce((a,b)=>a+b,0)/vals.length;
      const cls = avg > 0 ? 'up' : (avg < 0 ? 'down' : 'flat');
      avgHtml = '<span style="margin-left:8px;font-size:11.5px;" class="' + cls + '">평균 ' +
                (avg>0?'+':'') + avg.toFixed(2) + '%</span>';
    }
    const icon = inToday ? '▸' : '📌';
    const showBtns = inToday || _editing;
    head = '<div class="group-header' + (inToday ? ' today-header' : '') + '">' +
      icon + ' <span>' + esc(g.name || (inToday ? '구분' : '그룹')) + '</span>' + avgHtml +
      (showBtns ? '<span class="group-actions">' +
        '<button class="btn btn-mini" onclick="renameGroup(\'' + g.id + '\')">✏️</button>' +
        '<button class="btn btn-mini btn-danger" onclick="deleteGroup(\'' + g.id + '\')">🗑</button></span>' : '') +
      '</div>';
  }

  let rows = '';
  if(stocks.length){
    rows = '<table class="stock-table"><thead><tr>' +
      '<th>종목명</th>' +
      (isNxt ? '<th class="num">KRX 마감가</th>' : '') +
      '<th class="num">' + (isNxt ? 'NXT 현재가' : '현재가') + '</th>' +
      (isNxt ? '<th class="num">괴리</th><th class="num">괴리율</th>'
             : '<th class="num">등락</th><th class="num">등락률</th>') +
      '<th class="num">거래량</th><th>메모</th><th></th>' +
      '</tr></thead><tbody>' +
      stocks.map(st => renderRow(g.id, st, isNxt)).join('') +
      '</tbody></table>';
  } else {
    rows = '<div class="content-empty" style="padding:24px">종목 없음 · 아래에서 검색해 추가하세요</div>';
  }

  return '<div class="group" data-group-id="' + g.id + '">' + head + rows +
    '<div class="add-stock">' +
      '<div class="ac-wrap">' +
        '<input type="text" placeholder="종목명 검색해서 추가 (예: 두산에너빌리티)" ' +
          'id="ac-' + g.id + '" autocomplete="off" ' +
          'oninput="acSearch(\'' + g.id + '\', this.value)" ' +
          'oncompositionstart="_composing=true" ' +
          'oncompositionend="_composing=false;acSearch(\'' + g.id + '\', this.value)" ' +
          'onkeydown="acKey(event, \'' + g.id + '\')" ' +
          'onblur="setTimeout(()=>acClose(\'' + g.id + '\'), 200)"/>' +
        '<div class="ac-list" id="acl-' + g.id + '"></div>' +
      '</div>' +
    '</div>' +
    '</div>';
}

function renderRow(gid, st, isNxt){
  const q = _quotes[st.code] || {};
  const has = q.price !== undefined;
  const mkt = q.market || _market;
  const badge = has ? '<span class="mkt-badge ' + (MKT_CLASS[mkt]||'un') + '">' + (MKT_LABEL[mkt]||mkt) + '</span>' : '';
  const v = pctOf(st.code);
  const hot = (v !== undefined && Math.abs(v) >= (isNxt ? 3 : 5)) ? '<span class="hot">🔥</span>' : '';

  let cols;
  if(isNxt){
    const g = gapOf(q);
    const cls = g.pct > 0 ? 'up' : (g.pct < 0 ? 'down' : 'flat');
    const noNxt = q.no_nxt ? '<span class="hot" style="background:#f1f3f5;color:#7a8099">시간외X</span>' : '';
    cols =
      '<td class="num" style="color:#7a8099">' + (g.base ? num(g.base) : '—') + '</td>' +
      '<td class="num">' + (has ? num(q.price) : '—') + noNxt + '</td>' +
      '<td class="num ' + cls + '">' + (g.gap !== null ? (g.gap>0?'+':'') + num(g.gap) : '—') + '</td>' +
      '<td class="num ' + cls + '" style="font-weight:700">' +
        (g.pct !== null ? (g.pct>0?'+':'') + g.pct.toFixed(2) + '%' : '—') + '</td>';
  } else {
    const cls = q.chg_pct > 0 ? 'up' : (q.chg_pct < 0 ? 'down' : 'flat');
    cols =
      '<td class="num">' + (has ? num(q.price) : '—') + '</td>' +
      '<td class="num ' + cls + '">' + (q.chg !== undefined ? (q.chg>0?'+':'') + num(q.chg) : '') + '</td>' +
      '<td class="num ' + cls + '">' + (q.chg_pct !== undefined ? (q.chg_pct>0?'+':'') + q.chg_pct.toFixed(2) + '%' : '') + '</td>';
  }

  return '<tr class="stock-row">' +
    '<td><span class="stock-name clickable" onclick="openStock(\'' + st.code + '\',\'' +
      esc(st.name).replace(/'/g, "\\'") + '\')">' + esc(st.name) + '</span>' +
      '<span class="stock-code">' + esc(st.code) + '</span>' + badge + hot + '</td>' +
    cols +
    '<td class="num">' + num(q.volume) + '</td>' +
    '<td class="memo-cell"><input class="memo-input" placeholder="메모..." ' +
      'value="' + esc(st.memo || '') + '" ' +
      'oninput="setMemo(\'' + gid + '\',\'' + st.code + '\', this.value)"/></td>' +
    '<td><span class="row-actions"><button class="btn btn-mini btn-danger" ' +
      'onclick="delStock(\'' + gid + '\',\'' + st.code + '\')">✕</button></span></td>' +
    '</tr>';
}

// ── 편집 ────────────────────────────────
function toggleEdit(){
  _editing = !_editing;
  const b = document.getElementById('edit-btn');
  b.textContent = _editing ? '✓ 편집 완료' : '⚙️ 편집';
  b.classList.toggle('btn-primary', _editing);
  render();
}

function switchSector(id){
  if(_data.currentSectorId === id) return;
  _data.currentSectorId = id;
  render();
  scheduleSave();
  const missing = allCodes().filter(c => !_quotes[c]);
  if(missing.length) refreshQuotes();
}

function addSector(){
  const v = prompt('새 섹터 이름 (이모지 가능)', '새 섹터');
  if(v === null) return;
  const name = v.trim().slice(0,30);
  if(!name) return;
  const s = {id: genId(), name: name, groups: [{id: genId(), name: '기본', stocks: []}]};
  _data.sectors.push(s);
  _data.currentSectorId = s.id;
  render(); scheduleSave();
}

function renameSector(id){
  const s = _data.sectors.find(x => x.id === id);
  if(!s) return;
  const v = prompt('섹터 이름', s.name);
  if(v === null) return;
  const name = v.trim().slice(0,30);
  if(!name) return;
  s.name = name; render(); scheduleSave();
}

function deleteSector(id){
  if(id === TODAY_ID){ alert('TODAY는 삭제할 수 없습니다'); return; }
  const s = _data.sectors.find(x => x.id === id);
  if(!s) return;
  const cnt = (s.groups||[]).reduce((a,g)=>a+(g.stocks||[]).length, 0);
  if(!confirm('"' + s.name + '" 삭제할까요?' + (cnt ? '\n종목 ' + cnt + '개 함께 삭제' : ''))) return;
  const i = _data.sectors.findIndex(x => x.id === id);
  _data.sectors.splice(i, 1);
  _data.currentSectorId = _data.sectors[Math.max(0,i-1)].id;
  render(); scheduleSave();
}

function addGroup(){
  const s = currentSector(); if(!s) return;
  s.groups.push({id: genId(), name: '새 그룹', stocks: []});
  render(); scheduleSave();
}
function renameGroup(id){
  const s = currentSector(); if(!s) return;
  const g = s.groups.find(x => x.id === id); if(!g) return;
  const v = prompt('그룹 이름', g.name);
  if(v === null) return;
  const name = v.trim().slice(0,30);
  if(!name) return;
  g.name = name; render(); scheduleSave();
}
function deleteGroup(id){
  const s = currentSector(); if(!s) return;
  const g = s.groups.find(x => x.id === id); if(!g) return;
  if(!confirm('"' + g.name + '" 그룹 삭제할까요?' + ((g.stocks||[]).length ? '\n종목 ' + g.stocks.length + '개 함께 삭제' : ''))) return;
  s.groups = s.groups.filter(x => x.id !== id);
  render(); scheduleSave();
}

function clearToday(){
  const s = _data.sectors.find(x => x.id === TODAY_ID);
  if(!s) return;
  const cnt = (s.groups[0] && s.groups[0].stocks || []).length;
  if(!cnt){ alert('이미 비어 있습니다'); return; }
  if(!confirm('TODAY의 ' + cnt + '종목을 모두 비울까요?')) return;
  s.groups[0].stocks = [];
  render(); scheduleSave();
  showSaved('🗑 TODAY 비움');
}

// TODAY에 구분 헤더 추가
function addTodayHeader(){
  const s = _data.sectors.find(x => x.id === TODAY_ID);
  if(!s) return;
  const v = prompt('구분 이름 (예: 오프닝, 대담 1부, 마감)', '');
  if(v === null) return;
  const name = v.trim().slice(0,30);
  if(!name) return;
  s.groups = s.groups || [];
  s.groups.push({id: genId(), name: name, stocks: []});
  render(); scheduleSave();
  showSaved('▸ "' + name + '" 구분 추가됨');
}

// ── 📈 종목 상세 (창고 섹터 위치 + K-Stock DB) ────
let _detailOpen = null;

async function openStock(code, name){
  _detailOpen = {code, name};
  const ov = document.getElementById('stock-overlay');
  const body = document.getElementById('stock-body');
  document.getElementById('stock-title').textContent = name + '  ' + code;
  ov.classList.add('open');

  const q = _quotes[code] || {};
  const v = pctOf(code);
  const cls = v > 0 ? 'up' : (v < 0 ? 'down' : 'flat');
  const pct = (v === undefined || v === null) ? '—' : (v > 0 ? '+' : '') + v.toFixed(2) + '%';
  const isNxt = gapMode();

  let html = '';
  if(q.price){
    const g = gapOf(q);
    html += '<div class="stock-quote">' +
      (isNxt && g.base
        ? '<span class="sq-item"><b>KRX 마감</b>' + num(g.base) + '</span>' +
          '<span class="sq-item"><b>NXT</b>' + num(q.price) + '</span>' +
          '<span class="sq-item ' + cls + '"><b>괴리율</b>' + pct + '</span>'
        : '<span class="sq-item"><b>현재가</b>' + num(q.price) + '</span>' +
          '<span class="sq-item ' + cls + '"><b>등락률</b>' + pct + '</span>') +
      '<span class="sq-item"><b>거래량</b>' + num(q.volume || 0) + '</span>' +
      '</div>';
  }
  html += '<div class="stock-section">📁 전체 관심종목에서의 위치</div>' +
          '<div id="stock-places"><div class="stock-empty">확인 중...</div></div>' +
          '<div class="stock-section">📚 K-Stock DB</div>' +
          '<div id="stock-db"><div class="stock-empty">불러오는 중...</div></div>';
  body.innerHTML = html;

  // 창고(전체 관심종목) 위치
  try {
    const res = await fetch('/api/post/watchlist');
    const el = document.getElementById('stock-places');
    if(el){
      let places = [];
      if(res.ok){
        const d = await res.json();
        if(d && d.content){
          try {
            const wl = JSON.parse(d.content);
            for(const s of (wl.sectors || [])){
              for(const g of (s.groups || [])){
                if((g.stocks || []).some(x => x.code === code)){
                  places.push(s.name + ' › ' + g.name);
                }
              }
            }
          } catch(e){}
        }
      }
      el.innerHTML = places.length
        ? '<div class="stock-places">' + places.map(p =>
            '<div class="stock-place">' + esc(p) + '</div>').join('') + '</div>'
        : '<div class="stock-empty">전체 관심종목에는 없습니다</div>';
    }
  } catch(e){
    const el = document.getElementById('stock-places');
    if(el) el.innerHTML = '<div class="stock-empty">확인 실패</div>';
  }

  // K-Stock DB
  try {
    const res = await fetch('/api/watchlist/stock-info?code=' + encodeURIComponent(code));
    const d = await res.json();
    const el = document.getElementById('stock-db');
    if(!el) return;
    const entries = d.entries || [];
    el.innerHTML = entries.length
      ? entries.map(e => '<div class="db-entry">' +
          (e.theme ? '<div class="db-theme">' + esc(e.theme) + '</div>' : '') +
          (e.desc ? '<div class="db-desc">' + esc(e.desc) + '</div>' : '') +
          '</div>').join('')
      : '<div class="stock-empty">DB에 등록된 정보가 없습니다' +
        (d.db_size ? ' (' + d.db_size + '종목 중)' : '') + '</div>';
  } catch(e){
    const el = document.getElementById('stock-db');
    if(el) el.innerHTML = '<div class="stock-empty">⚠️ ' + esc(String(e.message || e)) + '</div>';
  }
}

function closeStock(){
  document.getElementById('stock-overlay').classList.remove('open');
}

document.addEventListener('keydown', (e) => {
  if(e.key === 'Escape'){
    const ov = document.getElementById('stock-overlay');
    if(ov && ov.classList.contains('open')) closeStock();
  }
});

// ── 🏷️ 인포스탁 테마 ─────────────────────
let _themeView = false;
let _themes = [];
let _themeDays = 1;
let _themeSort = 'up';
let _openThemes = {};
let _themeStocks = {};   // {code: [종목]}

function toggleThemeView(){
  _themeView = !_themeView;
  document.getElementById('theme-panel').style.display = _themeView ? '' : 'none';
  document.getElementById('fav-main').style.display = _themeView ? 'none' : '';
  const b = document.getElementById('theme-btn');
  b.classList.toggle('btn-primary', _themeView);
  if(_themeView && !_themes.length) loadThemes();
}

function setThemeDays(d){
  _themeDays = d;
  document.querySelectorAll('.seg[data-days]').forEach(b =>
    b.classList.toggle('active', +b.getAttribute('data-days') === d));
  _themeStocks = {};
  loadThemes(true);
}

function setThemeSort(s){
  _themeSort = s;
  document.querySelectorAll('.seg[data-tsort]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-tsort') === s));
  renderThemes();
}

async function loadThemes(force){
  const list = document.getElementById('theme-list');
  list.innerHTML = '<div class="content-empty">테마 불러오는 중...</div>';
  try {
    const url = '/api/kiwoom/themes?days=' + _themeDays + (force ? '&force=1' : '');
    const res = await fetch(url);
    const d = await res.json();
    if(!d.ok){
      list.innerHTML = '<div class="content-empty">⚠️ ' + esc(d.error || '불러오기 실패') + '</div>';
      return;
    }
    _themes = d.items || [];
    document.getElementById('theme-meta').textContent =
      _themes.length + '개 테마 · ' + new Date().toLocaleTimeString('ko-KR');
    renderThemes();
  } catch(e){
    list.innerHTML = '<div class="content-empty">⚠️ ' + esc(e.message || e) + '</div>';
  }
}

function renderThemes(){
  if(_composing) return;
  const list = document.getElementById('theme-list');
  if(!list) return;
  const q = (document.getElementById('theme-search').value || '')
              .trim().toLowerCase().replace(/\s/g,'');
  let rows = _themes.slice();
  if(q){
    rows = rows.filter(t =>
      (t.name||'').toLowerCase().replace(/\s/g,'').includes(q) ||
      (t.main||'').toLowerCase().replace(/\s/g,'').includes(q));
  }
  rows.sort((a,b) => _themeSort === 'up'
    ? (b.chg_pct - a.chg_pct) : (a.chg_pct - b.chg_pct));

  if(!rows.length){
    list.innerHTML = '<div class="content-empty">' +
      (q ? '「' + esc(q) + '」 해당 테마 없음' : '테마 없음') + '</div>';
    return;
  }

  let html = '<div class="theme-list">';
  rows.forEach((t, i) => {
    const open = !!_openThemes[t.code];
    const cls = t.chg_pct > 0 ? 'up' : (t.chg_pct < 0 ? 'down' : 'flat');
    const pcls = t.period_pct > 0 ? 'up' : (t.period_pct < 0 ? 'down' : 'flat');
    html += '<div class="theme-row ' + (open?'open':'') + '" onclick="toggleTheme(\'' + t.code + '\')">' +
      '<span class="th-idx">' + (i+1) + '</span>' +
      '<span class="th-caret">▶</span>' +
      '<button class="th-star" onclick="event.stopPropagation();favTheme(\'' + t.code + '\', this)" ' +
        'title="이 테마를 즐겨찾기로">★</button>' +
      '<span class="th-name">' + esc(t.name) + '</span>' +
      '<span class="th-cnt">' + t.count + '종목</span>' +
      '<span class="th-updown"><span class="up">▲' + t.up + '</span> ' +
        '<span class="down">▼' + t.down + '</span></span>' +
      '<span class="th-main">' + esc(t.main) + '</span>' +
      '<span class="th-period ' + pcls + '">' + (t.period_pct>0?'+':'') + t.period_pct.toFixed(2) + '%</span>' +
      '<span class="th-pct ' + cls + '">' + (t.chg_pct>0?'+':'') + t.chg_pct.toFixed(2) + '%</span>' +
      '</div>';
    if(open) html += renderThemeStocks(t.code);
  });
  html += '</div>';
  list.innerHTML = html;
}

function renderThemeStocks(code){
  const st = _themeStocks[code];
  if(st === undefined) return '<div class="theme-stocks"><div class="content-empty" style="padding:14px">종목 불러오는 중...</div></div>';
  if(!st.length) return '<div class="theme-stocks"><div class="content-empty" style="padding:14px">종목 없음</div></div>';
  return '<div class="theme-stocks" onclick="event.stopPropagation()">' +
    '<table class="stock-table"><thead><tr>' +
    '<th>종목명</th><th class="num">현재가</th><th class="num">등락률</th><th class="num">거래량</th><th></th>' +
    '</tr></thead><tbody>' +
    st.map(s => {
      const cls = s.chg_pct > 0 ? 'up' : (s.chg_pct < 0 ? 'down' : 'flat');
      return '<tr class="stock-row">' +
        '<td><button class="th-star' + (isFavCode(s.code) ? ' on' : '') + '" ' +
          'onclick="favStock(\'' + s.code + '\',\'' + esc(s.name).replace(/'/g,"\\'") + '\', this)">★</button>' +
          '<span class="stock-name clickable" onclick="openStock(\'' + s.code + '\',\'' +
          esc(s.name).replace(/'/g,"\\'") + '\')">' + esc(s.name) + '</span>' +
          '<span class="stock-code">' + esc(s.code) + '</span></td>' +
        '<td class="num">' + num(s.price) + '</td>' +
        '<td class="num ' + cls + '">' + (s.chg_pct>0?'+':'') + s.chg_pct.toFixed(2) + '%</td>' +
        '<td class="num">' + num(s.volume) + '</td>' +
        '<td></td></tr>';
    }).join('') + '</tbody></table></div>';
}

async function toggleTheme(code){
  _openThemes[code] = !_openThemes[code];
  renderThemes();
  if(_openThemes[code] && _themeStocks[code] === undefined){
    try {
      const res = await fetch('/api/kiwoom/theme-stocks?code=' + encodeURIComponent(code) +
                              '&days=' + _themeDays);
      const d = await res.json();
      _themeStocks[code] = d.ok ? (d.items || []) : [];
    } catch(e){ _themeStocks[code] = []; }
    renderThemes();
  }
}

// 즐겨찾기에 이미 있는지
function isFavCode(code){
  for(const s of (_data.sectors || [])){
    for(const g of (s.groups || [])){
      if((g.stocks || []).some(x => x.code === code)) return true;
    }
  }
  return false;
}

// 테마 종목 하나 → TODAY
function favStock(code, name, btn){
  const s = _data.sectors.find(x => x.id === TODAY_ID);
  if(!s) return;
  if(!s.groups || !s.groups.length) s.groups = [{id: genId(), name: '', stocks: []}];
  const g = s.groups[0];
  g.stocks = g.stocks || [];
  if(g.stocks.some(x => x.code === code)){
    g.stocks = g.stocks.filter(x => x.code !== code);
    if(btn) btn.classList.remove('on');
    showSaved('☆ 뺌: ' + name);
  } else {
    g.stocks.push({code, name, memo: ''});
    if(btn) btn.classList.add('on');
    showSaved('⭐ TODAY에 담김: ' + name);
  }
  scheduleSave();
}

// 테마 통째로 → 그 이름의 섹터
async function favTheme(code, btn){
  const t = _themes.find(x => x.code === code);
  if(!t) return;
  let stocks = _themeStocks[code];
  if(stocks === undefined){
    showSaved('⏳ 종목 불러오는 중...');
    try {
      const res = await fetch('/api/kiwoom/theme-stocks?code=' + encodeURIComponent(code) +
                              '&days=' + _themeDays);
      const d = await res.json();
      stocks = _themeStocks[code] = d.ok ? (d.items || []) : [];
    } catch(e){ stocks = _themeStocks[code] = []; }
  }
  if(!stocks.length){ showSaved('⚠️ 구성 종목을 못 가져옴'); return; }

  const name = '🏷️ ' + t.name;
  let fs = _data.sectors.find(x => x.name === name);
  if(!fs){
    fs = {id: genId(), name: name, groups: [{id: genId(), name: '', stocks: []}]};
    _data.sectors.push(fs);
  }
  if(!fs.groups || !fs.groups.length) fs.groups = [{id: genId(), name: '', stocks: []}];
  const g = fs.groups[0];
  g.stocks = g.stocks || [];
  const have = new Set(g.stocks.map(x => x.code));
  let added = 0;
  for(const s of stocks){
    if(have.has(s.code)) continue;
    g.stocks.push({code: s.code, name: s.name, memo: ''});
    have.add(s.code);
    added++;
  }
  if(btn) btn.classList.add('on');
  scheduleSave();
  render();
  showSaved('⭐ 「' + t.name + '」 ' + added + '종목 담김');
}

function setMemo(gid, code, val){
  const s = currentSector(); if(!s) return;
  const g = s.groups.find(x => x.id === gid); if(!g) return;
  const st = (g.stocks||[]).find(x => x.code === code); if(!st) return;
  st.memo = val;
  scheduleSave();
}

function delStock(gid, code){
  const s = currentSector(); if(!s) return;
  const g = s.groups.find(x => x.id === gid); if(!g) return;
  const st = (g.stocks||[]).find(x => x.code === code);
  if(!confirm('"' + (st ? st.name : code) + '" 삭제할까요?')) return;
  g.stocks = g.stocks.filter(x => x.code !== code);
  render(); scheduleSave();
}

function addStock(gid, code, name){
  const s = currentSector(); if(!s) return;
  const g = s.groups.find(x => x.id === gid); if(!g) return;
  if((g.stocks||[]).some(x => x.code === code)){
    showSaved('⚠️ 이미 있는 종목: ' + name);
    return;
  }
  g.stocks = g.stocks || [];
  g.stocks.push({code: code, name: name, memo: ''});
  render(); scheduleSave();
  refreshQuotes({force:true});
  showSaved('⭐ ' + name + ' 추가됨');
  setTimeout(() => {
    const el = document.getElementById('ac-' + gid);
    if(el){ el.value = ''; el.focus(); }
  }, 60);
}

// ── 종목 검색 ────────────────────────────
const _ac = {};
function acSearch(gid, q){
  if(_composing) return;
  q = (q||'').trim();
  const list = document.getElementById('acl-' + gid);
  if(!list) return;
  const st = _ac[gid] = _ac[gid] || {};
  if(st.timer) clearTimeout(st.timer);
  if(!q){ acClose(gid); return; }
  if(/^\d{6}$/.test(q)){
    list.innerHTML = '<div class="ac-item" onclick="addStock(\'' + gid + '\',\'' + q + '\',\'' + q + '\')">' +
      '<span class="ac-item-name">종목코드 ' + q + '</span><span class="ac-item-code">직접 추가</span></div>';
    list.classList.add('open');
    return;
  }
  list.innerHTML = '<div class="ac-loading">검색 중...</div>';
  list.classList.add('open');
  st.timer = setTimeout(async () => {
    try {
      const r = await fetch('/api/watchlist/search?q=' + encodeURIComponent(q));
      const d = await r.json();
      const items = d.items || [];
      st.items = items; st.sel = -1;
      if(!items.length){
        list.innerHTML = '<div class="ac-empty">검색 결과 없음 · 6자리 코드로 직접 입력 가능</div>';
        return;
      }
      list.innerHTML = items.map((it,i) =>
        '<div class="ac-item" data-i="' + i + '" onclick="acPick(\'' + gid + '\',' + i + ')">' +
        '<span class="ac-item-name">' + esc(it.name) + '</span>' +
        '<span class="ac-item-code">' + esc(it.code) + '</span></div>').join('');
    } catch(e){
      list.innerHTML = '<div class="ac-empty">검색 실패 · 6자리 코드로 직접 입력 가능</div>';
    }
  }, 300);
}
function acKey(e, gid){
  if(_composing || e.isComposing || e.keyCode === 229) return;
  const st = _ac[gid];
  const list = document.getElementById('acl-' + gid);
  if(!st || !st.items || !st.items.length || !list || !list.classList.contains('open')){
    if(e.key === 'Enter'){
      const v = (document.getElementById('ac-' + gid).value || '').trim();
      if(/^\d{6}$/.test(v)) addStock(gid, v, v);
    }
    return;
  }
  if(e.key === 'ArrowDown'){ e.preventDefault(); st.sel = Math.min((st.sel ?? -1)+1, st.items.length-1); acHi(gid); }
  else if(e.key === 'ArrowUp'){ e.preventDefault(); st.sel = Math.max((st.sel ?? 0)-1, 0); acHi(gid); }
  else if(e.key === 'Enter'){ e.preventDefault(); acPick(gid, (st.sel ?? -1) < 0 ? 0 : st.sel); }
  else if(e.key === 'Escape'){ acClose(gid); }
}
function acHi(gid){
  const st = _ac[gid];
  const list = document.getElementById('acl-' + gid);
  if(!list) return;
  list.querySelectorAll('.ac-item').forEach(el => el.classList.remove('sel'));
  const t = list.querySelector('[data-i="' + st.sel + '"]');
  if(t){ t.classList.add('sel'); t.scrollIntoView({block:'nearest'}); }
}
function acPick(gid, i){
  const st = _ac[gid];
  if(!st || !st.items || !st.items[i]) return;
  const it = st.items[i];
  addStock(gid, it.code, it.name);
  acClose(gid);
}
function acClose(gid){
  const list = document.getElementById('acl-' + gid);
  if(list) list.classList.remove('open');
}

// ── 시세 ────────────────────────────────
function allCodes(){
  const s = currentSector();
  const out = [];
  if(s) for(const g of (s.groups||[])) for(const st of (g.stocks||[])) out.push(st.code);
  return out;
}

async function refreshQuotes(opts){
  opts = opts || {};
  if(_fetching && !opts.force) return;
  const codes = allCodes();
  if(!codes.length) return;
  const btn = document.getElementById('refresh-btn');
  _fetching = true;
  if(btn){ btn.disabled = true; btn.textContent = '⏳ 조회 중...'; }
  const t0 = performance.now();
  try {
    const res = await fetch('/api/watchlist/quotes', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({codes: codes, market: _market,
                            session: effectiveSession(), force: !!opts.force})
    });
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    Object.assign(_quotes, data.quotes || {});
    // 이름이 코드로만 있는 종목 보정
    let renamed = false;
    for(const s of _data.sectors){
      for(const g of (s.groups||[])){
        for(const st of (g.stocks||[])){
          const q = _quotes[st.code];
          if(q && q.api_name && (st.name === st.code || !st.name)){ st.name = q.api_name; renamed = true; }
        }
      }
    }
    if(renamed) scheduleSave();
    const ms = Math.round(performance.now() - t0);
    document.getElementById('updated').textContent =
      '📊 ' + MKT_LABEL[_market] + ' 시세 · ' + new Date().toLocaleTimeString('ko-KR') +
      ' · ' + Object.keys(data.quotes||{}).length + '/' + codes.length + '종목 · ' + ms + 'ms';
    updateHint();
    renderBody();
  } catch(e){
    document.getElementById('updated').textContent = '⚠️ 시세 조회 실패: ' + e.message;
  } finally {
    _fetching = false;
    if(btn){ btn.disabled = false; btn.textContent = '🔄 시세 갱신'; }
  }
}

function isTyping(){
  const el = document.activeElement;
  if(!el) return false;
  const t = (el.tagName||'').toLowerCase();
  return t === 'input' || t === 'textarea';
}

// 다른 탭(창고)에서 담은 종목을 반영하기 위해 주기적으로 다시 읽음
async function syncFromServer(){
  if(_editing || isTyping()) return;
  try {
    const res = await fetch('/api/post/watchlist_fav');
    if(!res.ok) return;
    const d = await res.json();
    if(!d || !d.content) return;
    let fresh;
    try { fresh = JSON.parse(d.content); } catch(e){ return; }
    if(JSON.stringify(fresh) === JSON.stringify(_data)) return;
    const keep = _data.currentSectorId;
    _data = fresh;
    if(!_data.sectors.some(s => s.id === TODAY_ID)){
      _data.sectors.unshift({id: TODAY_ID, name: '🔥 TODAY',
                             groups: [{id: genId(), name: '', stocks: []}]});
    }
    if(_data.sectors.some(s => s.id === keep)) _data.currentSectorId = keep;
    render();
    refreshQuotes();
    showSaved('🔄 다른 탭 변경 반영');
  } catch(e){}
}

function startAuto(){
  if(_autoTimer) clearInterval(_autoTimer);
  _autoTimer = setInterval(() => {
    if(document.hidden || _editing || isTyping()) return;
    refreshQuotes();
  }, 30000);
  // 서버 동기화는 20초마다
  setInterval(() => { if(!document.hidden) syncFromServer(); }, 20000);
}

// ── 컨트롤 ──────────────────────────────
function setMarket(m){
  if(_market === m) return;
  _market = m;
  try { localStorage.setItem('fav_market', m); } catch(e){}
  document.querySelectorAll('.seg[data-mkt]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-mkt') === m));
  const sw = document.getElementById('sess-wrap');
  if(sw) sw.style.display = (m === 'NX') ? '' : 'none';
  _quotes = {};
  updateHint(); renderBody();
  refreshQuotes({force:true});
}
function setSession(s){
  _session = s;
  try { localStorage.setItem('fav_session', s); } catch(e){}
  document.querySelectorAll('.seg[data-sess]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-sess') === s));
  _quotes = {};
  updateHint(); renderBody();
  refreshQuotes({force:true});
}
function setSort(s){
  _sort = s;
  try { localStorage.setItem('fav_sort', s); } catch(e){}
  document.querySelectorAll('.seg[data-sort]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-sort') === s));
  renderBody();
}

function initControls(){
  try {
    const m = localStorage.getItem('fav_market');
    if(['UN','J','NX'].includes(m)) _market = m;
    const s = localStorage.getItem('fav_session');
    if(['auto','pre','after'].includes(s)) _session = s;
    const so = localStorage.getItem('fav_sort');
    if(['manual','chg_desc','chg_asc'].includes(so)) _sort = so;
  } catch(e){}
  document.querySelectorAll('.seg[data-mkt]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-mkt') === _market));
  document.querySelectorAll('.seg[data-sess]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-sess') === _session));
  document.querySelectorAll('.seg[data-sort]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-sort') === _sort));
  const sw = document.getElementById('sess-wrap');
  if(sw) sw.style.display = (_market === 'NX') ? '' : 'none';
  updateHint();
  setInterval(updateHint, 60000);
}

document.addEventListener('visibilitychange', () => {
  if(document.hidden) return;
  if(_editing || isTyping()) return;
  syncFromServer();
  refreshQuotes();
});

initControls();
loadData();
startAuto();
</script>
</body>
</html>
"""

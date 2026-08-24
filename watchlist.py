"""
관심종목 시황 뷰 (/watchlist)
- 섹터 → 그룹 → 종목 3단 구조
- KIS API 실시간 시세
- 편집 모드 (섹터/그룹/종목 관리)
- 자동 저장
"""
import threading

# ── 전역 Session 풀 (프로세스 살아있는 동안 재사용) ───────
# 매 요청마다 Session을 새로 만들면 TLS 핸드셰이크가 반복됨.
# 모듈 레벨에 하나 두고 계속 재사용 → 커넥션이 살아있어서 훨씬 빠름.
_session_lock = threading.Lock()
_shared_session = {"s": None, "token": ""}


def _get_session(token: str, app_key: str, app_secret: str):
    import requests as _rq
    with _session_lock:
        s = _shared_session["s"]
        if s is None:
            s = _rq.Session()
            adapter = _rq.adapters.HTTPAdapter(
                pool_connections=32, pool_maxsize=32, max_retries=0
            )
            s.mount("https://", adapter)
            _shared_session["s"] = s
        # 토큰이 바뀌었을 때만 헤더 갱신
        if _shared_session["token"] != token:
            s.headers.update({
                "authorization": f"Bearer {token}",
                "appkey": app_key,
                "appsecret": app_secret,
                "tr_id": "FHKST01010100",
                "Content-Type": "application/json",
                "Connection": "keep-alive",
            })
            _shared_session["token"] = token
        return s


def get_watchlist_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>관심종목 시황 · Yenny Dashboard</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2280%22>📊</text></svg>">
<link rel="stylesheet" href="https://webfontworld.github.io/gmarket/GmarketSans.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.0/Sortable.min.js"></script>
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

.wrap{max-width:1600px;margin:0 auto;padding:16px 24px}
.updated{font-size:11px;color:#7a8099;margin-bottom:10px}

/* 🆕 컨트롤 바 */
.controlbar{
  background:#fff;border-bottom:1px solid #e5e7eb;
  padding:10px 24px;display:flex;gap:20px;align-items:center;flex-wrap:wrap;
  position:sticky;top:57px;z-index:90;
}
.ctrl-group{display:flex;gap:4px;align-items:center}
.ctrl-label{font-size:11px;color:#7a8099;font-weight:600;margin-right:4px}
.seg{
  padding:5px 11px;border:1px solid #e5e7eb;border-radius:6px;
  background:#fff;color:#1a1d23;font-size:11.5px;font-weight:500;
  cursor:pointer;font-family:inherit;transition:all .12s;
}
.seg:hover{background:#f1f3f5;border-color:#1a1d23}
.seg.active{background:#1a1d23;color:#fff;border-color:#1a1d23}
.chk{font-size:11.5px;color:#1a1d23;display:flex;align-items:center;gap:5px;cursor:pointer}
.chk input{cursor:pointer}
.market-hint{font-size:11px;color:#7a8099;font-style:italic}

/* 🆕 드래그 핸들 */
.drag-dots,.group-drag{
  cursor:grab;font-size:12px;letter-spacing:-2px;
  color:rgba(255,255,255,0.5);user-select:none;margin-right:2px;
}
.group-drag{color:#c5ccd6;margin-right:6px}
.sector-tab:not(.active) .drag-dots{color:#c5ccd6}
.drag-dots:active,.group-drag:active{cursor:grabbing}
.sortable-ghost{opacity:0.4}
.sortable-drag{opacity:0.9}

/* 시장 배지 */
.mkt-badge{
  display:inline-block;padding:1px 5px;border-radius:4px;
  font-size:9.5px;font-weight:700;margin-left:5px;vertical-align:middle;
}
.mkt-badge.krx{background:#e3f2fd;color:#0277bd}
.mkt-badge.nxt{background:#f3e5f5;color:#7b1fa2}
.mkt-badge.un{background:#f1f3f5;color:#616161}

/* 섹터 탭바 */
.sector-tabs{
  display:flex;gap:6px;flex-wrap:wrap;padding-bottom:12px;
  border-bottom:1.5px solid #e5e7eb;margin-bottom:16px;align-items:center;
}
.sector-tab{
  display:flex;align-items:center;gap:6px;
  padding:8px 14px;border:1px solid #e5e7eb;border-radius:20px;
  background:#fff;color:#1a1d23;font-size:13px;font-weight:500;
  cursor:pointer;font-family:inherit;transition:all .12s;
  white-space:nowrap;
}
.sector-tab:hover{background:#f1f3f5;border-color:#1a1d23}
.sector-tab.active{background:#1a1d23;color:#fff;border-color:#1a1d23}
.sector-tab-name{outline:none;min-width:20px}
.sector-tab-name:focus{background:rgba(255,255,255,0.2);padding:0 4px;border-radius:3px}
.sector-add{
  width:34px;height:34px;border-radius:20px;border:1px dashed #999;
  background:transparent;color:#666;font-size:16px;font-weight:700;
  cursor:pointer;font-family:inherit;
}
.sector-add:hover{background:#fff;color:#1a1d23;border-color:#1a1d23;border-style:solid}

/* 그룹 */
.group{margin-bottom:24px}
.group-header{
  display:flex;align-items:center;gap:8px;
  padding:8px 0;margin-bottom:6px;border-bottom:1px solid #e5e7eb;
  font-size:14px;font-weight:700;color:#1a1d23;
}
.group-icon{font-size:16px}
.group-name{outline:none;min-width:20px}
.group-name:focus{background:#fff;border-radius:4px;padding:2px 6px;box-shadow:0 0 0 2px rgba(26,29,35,0.1)}
.group-actions{margin-left:auto;display:flex;gap:4px}
.group-actions .btn-mini{background:transparent;border:1px solid transparent;color:#7a8099}
.group-actions .btn-mini:hover{background:#fff;border-color:#e5e7eb;color:#1a1d23}

/* 종목 테이블 */
.stock-table{width:100%;border-collapse:collapse}
.stock-table th{
  text-align:left;padding:8px 10px;font-size:11px;color:#7a8099;
  font-weight:600;border-bottom:1px solid #e5e7eb;
}
.stock-table th.num{text-align:right}
.stock-row{border-bottom:1px solid #f1f3f5;transition:background .1s}
.stock-row:hover{background:#f8f9fa}
.stock-row td{padding:9px 10px;font-size:13px;vertical-align:middle}
.stock-row td.num{text-align:right;font-variant-numeric:tabular-nums}
.stock-name{font-weight:600;color:#1a1d23}
.stock-code{font-size:10px;color:#a8b0bd;margin-left:4px}
.up{color:#d63031}
.down{color:#0984e3}
.flat{color:#7a8099}
.hot{
  display:inline-block;padding:1px 6px;border-radius:8px;
  background:#ffe7e4;color:#d63031;font-size:10px;font-weight:700;
  margin-left:6px;vertical-align:middle;
}
.hot.volume{background:#fff59d;color:#a06d00}
.row-actions{display:none;gap:2px}
.stock-row:hover .row-actions{display:inline-flex}
.stock-row.editing .row-actions{display:inline-flex}

/* 추가 버튼 */
.add-stock{
  display:flex;gap:6px;padding:10px 0;
}
.add-stock input{
  flex:1;padding:6px 10px;border:1px solid #e5e7eb;border-radius:6px;
  font-size:12px;font-family:inherit;outline:none;
}
.add-stock input:focus{border-color:#1a1d23}
.add-stock button{padding:6px 12px;font-size:12px}

/* 🆕 자동완성 */
.ac-wrap{position:relative;flex:1}
.ac-wrap input{width:100%}
.ac-list{
  display:none;position:absolute;top:calc(100% + 2px);left:0;right:0;
  background:#fff;border:1px solid #e5e7eb;border-radius:8px;
  box-shadow:0 4px 16px rgba(0,0,0,0.1);z-index:50;
  max-height:260px;overflow-y:auto;
}
.ac-list.open{display:block}
.ac-item{
  padding:8px 12px;font-size:12.5px;cursor:pointer;
  display:flex;align-items:center;gap:8px;
  border-bottom:1px solid #f1f3f5;
}
.ac-item:last-child{border-bottom:none}
.ac-item:hover,.ac-item.sel{background:#f1f3f5}
.ac-item-name{font-weight:600;color:#1a1d23}
.ac-item-code{font-size:10.5px;color:#a8b0bd}
.ac-item-market{
  margin-left:auto;font-size:10px;padding:1px 6px;border-radius:8px;
  background:#f1f3f5;color:#7a8099;
}
.ac-loading{padding:10px 12px;font-size:12px;color:#a8b0bd;font-style:italic}
.ac-empty{padding:10px 12px;font-size:12px;color:#a8b0bd}

.add-group-btn{
  padding:8px 14px;border:1px dashed #999;border-radius:8px;
  background:transparent;color:#666;font-size:12px;cursor:pointer;
  font-family:inherit;margin-top:8px;
}
.add-group-btn:hover{background:#fff;color:#1a1d23;border-color:#1a1d23}

.content-empty{color:#b2bec3;font-style:italic;padding:40px 20px;text-align:center;display:block}
.loading{color:#7a8099;font-size:12px;padding:6px 10px;font-style:italic}

.save-indicator{
  position:fixed;bottom:24px;right:24px;background:#1a1d23;color:#fff;
  padding:10px 18px;border-radius:24px;font-size:12px;font-weight:500;
  opacity:0;transition:opacity .3s;pointer-events:none;z-index:200;
  box-shadow:0 4px 12px rgba(0,0,0,0.15);
}
.save-indicator.visible{opacity:1}

/* 편집 모드 */
body.edit-mode .row-actions{display:inline-flex !important}
body.edit-mode .add-stock,body.edit-mode .add-group-btn{display:flex}
.add-stock,.add-group-btn{display:none}
body.edit-mode .add-group-btn{display:inline-block}

@media print{
  .topbar,.sector-add,.row-actions,.add-stock,.add-group-btn,.save-indicator{display:none !important}
  body{background:#fff}
  .sector-tab:not(.active){display:none}
}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-title">📊 관심종목 시황</div>
  <div class="topbar-actions">
    <a href="/" class="btn">← 대시보드</a>
    <button class="btn" onclick="toggleEdit()" id="edit-btn">⚙️ 편집</button>
    <button class="btn btn-primary" onclick="refreshQuotes(allCodesEverywhere(), {force:true})" id="refresh-btn">🔄 시세 갱신</button>
    <button class="btn" onclick="window.print()">🖨️ 인쇄</button>
  </div>
</div>

<div class="controlbar">
  <!-- 시장 선택 -->
  <div class="ctrl-group">
    <span class="ctrl-label">시장</span>
    <button class="seg" data-mkt="UN" onclick="setMarket('UN')" title="KRX+NXT 통합 (체결 있는 쪽)">통합</button>
    <button class="seg" data-mkt="J" onclick="setMarket('J')" title="한국거래소 정규장">KRX</button>
    <button class="seg" data-mkt="NX" onclick="setMarket('NX')" title="넥스트레이드 (프리·애프터)">NXT</button>
  </div>
  <!-- 정렬 -->
  <div class="ctrl-group">
    <span class="ctrl-label">정렬</span>
    <button class="seg" data-sort="manual" onclick="setSort('manual')">기본</button>
    <button class="seg" data-sort="chg_desc" onclick="setSort('chg_desc')">등락률 ↓</button>
    <button class="seg" data-sort="chg_asc" onclick="setSort('chg_asc')">등락률 ↑</button>
    <button class="seg" data-sort="vol_desc" onclick="setSort('vol_desc')">거래량 ↓</button>
    <button class="seg gap-only" data-sort="gap_desc" onclick="setSort('gap_desc')" style="display:none;">괴리율 ↓</button>
    <button class="seg gap-only" data-sort="gap_asc" onclick="setSort('gap_asc')" style="display:none;">괴리율 ↑</button>
  </div>
  <!-- 보기 -->
  <div class="ctrl-group">
    <label class="chk"><input type="checkbox" id="flat-view" onchange="toggleFlat()"/> 그룹 무시하고 전체 정렬</label>
  </div>
  <div class="ctrl-group" style="margin-left:auto">
    <span class="market-hint" id="market-hint"></span>
  </div>
</div>

<div class="wrap">
  <div class="updated" id="updated"></div>
  <div class="sector-tabs" id="sector-tabs"></div>
  <div id="watchlist-body">
    <div class="loading" style="text-align:center;padding:80px;">불러오는 중...</div>
  </div>
</div>

<div id="save-indicator" class="save-indicator">💾 저장됨</div>

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

let _data = {sectors: [], currentSectorId: null};
let _quotes = {};
let _saveTimer = null;
let _editing = false;
let _autoRefreshTimer = null;
let _market = 'UN';           // 🆕 UN(통합) | J(KRX) | NX(NXT)
let _sort = 'manual';         // 🆕 manual | chg_desc | chg_asc | vol_desc
let _flatView = false;        // 🆕 그룹 무시하고 전체 정렬

function genId(){ return 'x' + Math.random().toString(36).slice(2, 10); }
function esc(s){ return String(s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function num(n){ return n === undefined || n === null ? '—' : Number(n).toLocaleString('ko-KR'); }

// 🆕 시장 라벨 / 힌트
const MKT_LABEL = {'UN':'통합', 'J':'KRX', 'NX':'NXT'};
const MKT_CLASS = {'UN':'un', 'J':'krx', 'NX':'nxt'};

function updateMarketHint(){
  const now = new Date();
  const h = now.getHours(), m = now.getMinutes();
  const t = h * 60 + m;
  let phase = '';
  if(t >= 8*60 && t < 9*60)          phase = '프리마켓 (NXT 유효)';
  else if(t >= 9*60 && t < 15*60+30) phase = '정규장 (KRX 유효)';
  else if(t >= 15*60+30 && t < 16*60) phase = '장 마감 정리';
  else if(t >= 16*60 && t < 20*60)   phase = '애프터마켓 (NXT 유효)';
  else                                phase = '장외 시간 (마지막 종가)';
  const el = document.getElementById('market-hint');
  if(el) el.textContent = '🕐 ' + phase + ' · 현재 ' + MKT_LABEL[_market] + ' 조회 중';
}

function setMarket(mkt){
  if(_market === mkt) return;
  _market = mkt;
  document.querySelectorAll('.seg[data-mkt]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-mkt') === mkt);
  });
  // 🆕 NXT일 때만 괴리율 정렬 버튼 노출
  const isNxt = (mkt === 'NX');
  document.querySelectorAll('.gap-only').forEach(b => {
    b.style.display = isNxt ? '' : 'none';
  });
  if(!isNxt && (_sort === 'gap_desc' || _sort === 'gap_asc')) setSort('chg_desc');
  updateMarketHint();
  _quotes = {};
  renderBody();
  refreshQuotes(allCodesEverywhere(), {force:true});
}

function setSort(s){
  _sort = s;
  document.querySelectorAll('.seg[data-sort]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-sort') === s);
  });
  renderBody();
}

function toggleFlat(){
  _flatView = document.getElementById('flat-view').checked;
  renderBody();
}

// 정렬 적용
function sortStocks(stocks){
  if(_sort === 'manual') return stocks.slice();
  const arr = stocks.slice();
  arr.sort((a, b) => {
    const qa = _quotes[a.code] || {};
    const qb = _quotes[b.code] || {};
    if(_sort === 'chg_desc') return (qb.chg_pct ?? -999) - (qa.chg_pct ?? -999);
    if(_sort === 'chg_asc')  return (qa.chg_pct ??  999) - (qb.chg_pct ??  999);
    if(_sort === 'vol_desc') return (qb.volume  ??   -1) - (qa.volume  ??   -1);
    if(_sort === 'gap_desc') return (qb.gap_pct ?? -999) - (qa.gap_pct ?? -999);
    if(_sort === 'gap_asc')  return (qa.gap_pct ??  999) - (qb.gap_pct ??  999);
    return 0;
  });
  return arr;
}

// ── 저장 / 로드 ──────────────────────────
function scheduleSave(){
  if(_saveTimer) clearTimeout(_saveTimer);
  _saveTimer = setTimeout(saveNow, 800);
}

async function saveNow(){
  try {
    const res = await fetch('/api/post/watchlist', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: JSON.stringify(_data), date: new Date().toISOString().slice(0,10)})
    });
    if(res.ok) showSaved();
  } catch(e){ console.error(e); }
}

function showSaved(msg){
  const el = document.getElementById('save-indicator');
  el.textContent = msg || ('💾 저장됨 ' + new Date().toLocaleTimeString('ko-KR', {hour:'2-digit',minute:'2-digit'}));
  el.classList.add('visible');
  setTimeout(() => el.classList.remove('visible'), 1800);
}

async function loadData(){
  try {
    const res = await fetch('/api/post/watchlist');
    if(!res.ok){ initEmpty(); return; }
    const data = await res.json();
    if(!data || !data.content){ initEmpty(); return; }
    try { _data = JSON.parse(data.content); } catch(e){ initEmpty(); return; }
    if(!_data.sectors || !_data.sectors.length){ initEmpty(); return; }
    if(!_data.currentSectorId || !_data.sectors.find(s => s.id === _data.currentSectorId)){
      _data.currentSectorId = _data.sectors[0].id;
    }
    render();
    // ⚡ 전체 섹터 시세를 한 번에 — 탭 전환이 즉시 반응함
    refreshQuotes(allCodesEverywhere());
  } catch(e){ console.error(e); initEmpty(); }
}

function initEmpty(){
  _data = {
    sectors: [
      {id: genId(), name: '⚛️ 원전', groups: [
        {id: genId(), name: '시공 및 주기기', stocks: [
          {code: '034020', name: '두산에너빌리티'},
          {code: '000720', name: '현대건설'},
        ]},
        {id: genId(), name: '운영 및 설계/정비', stocks: [
          {code: '015760', name: '한국전력'},
          {code: '051600', name: '한전KPS'},
          {code: '052690', name: '한전기술'},
        ]},
      ]},
      {id: genId(), name: '🔬 반도체', groups: [
        {id: genId(), name: '대형주', stocks: [
          {code: '005930', name: '삼성전자'},
          {code: '000660', name: 'SK하이닉스'},
        ]},
      ]},
    ],
    currentSectorId: null,
  };
  _data.currentSectorId = _data.sectors[0].id;
  scheduleSave();
  render();
  refreshQuotes();
}

// ── 렌더 ────────────────────────────────
function render(){
  renderTabs();
  renderBody();
}

let _sortableTabs = null;
let _sortableGroups = null;

function renderTabs(){
  const el = document.getElementById('sector-tabs');
  el.innerHTML = _data.sectors.map(s => {
    const active = s.id === _data.currentSectorId;
    return '<button class="sector-tab ' + (active?'active':'') + '" data-sector-id="' + s.id + '" onclick="switchSector(\'' + s.id + '\')">' +
           (_editing ? '<span class="drag-dots" title="드래그로 순서 변경">⋮⋮</span>' : '') +
           '<span class="sector-tab-name" contenteditable="' + (active && _editing ? 'true' : 'false') + '" onblur="renameSector(\'' + s.id + '\', this)" onkeydown="if(event.key===\'Enter\'){event.preventDefault();this.blur();}">' + esc(s.name) + '</span>' +
           (active && _editing ? ' <button class="btn-mini btn-danger" onclick="event.stopPropagation();deleteSector(\'' + s.id + '\')" style="background:transparent;border:0;color:#fff;padding:2px 4px;">✕</button>' : '') +
           '</button>';
  }).join('');
  if(_editing){
    el.innerHTML += '<button class="sector-add" onclick="addSector()" title="새 섹터">+</button>';
  }
  initSortableTabs();
}

// 🆕 섹터 탭 드래그 정렬
function initSortableTabs(){
  const el = document.getElementById('sector-tabs');
  if(!el || typeof Sortable === 'undefined') return;
  if(_sortableTabs){ try{ _sortableTabs.destroy(); }catch(e){} _sortableTabs = null; }
  if(!_editing) return;   // 편집 모드에서만 드래그 허용
  _sortableTabs = Sortable.create(el, {
    animation: 150,
    handle: '.drag-dots',
    filter: '.sector-add',
    draggable: '.sector-tab',
    onEnd: function(){
      const order = Array.from(el.querySelectorAll('.sector-tab'))
        .map(n => n.getAttribute('data-sector-id'))
        .filter(Boolean);
      const map = {};
      for(const s of _data.sectors) map[s.id] = s;
      _data.sectors = order.map(id => map[id]).filter(Boolean);
      scheduleSave();
      showSaved('✅ 섹터 순서 변경됨');
    }
  });
}

// 🆕 그룹 드래그 정렬
function initSortableGroups(){
  const body = document.getElementById('watchlist-body');
  if(!body || typeof Sortable === 'undefined') return;
  if(_sortableGroups){ try{ _sortableGroups.destroy(); }catch(e){} _sortableGroups = null; }
  if(!_editing || _flatView) return;
  _sortableGroups = Sortable.create(body, {
    animation: 150,
    handle: '.group-drag',
    draggable: '.group',
    onEnd: function(){
      const order = Array.from(body.querySelectorAll('.group'))
        .map(n => n.getAttribute('data-group-id'))
        .filter(Boolean);
      const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
      if(!sector) return;
      const map = {};
      for(const g of sector.groups) map[g.id] = g;
      sector.groups = order.map(id => map[id]).filter(Boolean);
      scheduleSave();
      showSaved('✅ 그룹 순서 변경됨');
    }
  });
}

function renderBody(){
  const body = document.getElementById('watchlist-body');
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector){
    body.innerHTML = '<span class="content-empty">섹터가 없음. 편집 모드에서 + 눌러 추가하세요.</span>';
    return;
  }
  // 🆕 flat view — 그룹 무시, 전체 종목 하나의 표로
  if(_flatView){
    const all = [];
    for(const g of sector.groups){
      for(const st of (g.stocks || [])){
        all.push(Object.assign({}, st, {_group: g.name, _groupId: g.id}));
      }
    }
    if(!all.length){
      body.innerHTML = '<span class="content-empty">종목 없음</span>';
      return;
    }
    const sorted = sortStocks(all);
    const isNxtF = (_market === 'NX');
    body.innerHTML =
      '<div class="group"><div class="group-header"><span class="group-icon">📊</span>' +
      '<span>' + esc(sector.name) + ' 전체 (' + all.length + '종목)</span></div>' +
      '<table class="stock-table"><thead><tr>' +
      '<th>종목명</th><th>그룹</th>' +
      (isNxtF ? '<th class="num">KRX 종가</th>' : '') +
      '<th class="num">' + (isNxtF ? 'NXT 현재가' : '현재가') + '</th>' +
      (isNxtF ? '<th class="num">괴리</th><th class="num">괴리율</th>' : '<th class="num">등락</th><th class="num">등락률</th>') +
      '<th class="num">거래량</th><th></th>' +
      '</tr></thead><tbody>' +
      sorted.map(st => renderStockRow(st._groupId, st, true)).join('') +
      '</tbody></table></div>';
    initSortableGroups();
    return;
  }

  if(!sector.groups.length){
    body.innerHTML = '<span class="content-empty">그룹이 없음. 편집 모드에서 그룹 추가.</span>' +
      (_editing ? '<div style="text-align:center"><button class="add-group-btn" onclick="addGroup()">+ 새 그룹</button></div>' : '');
    return;
  }
  let html = '';
  for(const g of sector.groups){
    html += renderGroup(sector.id, g);
  }
  if(_editing){
    html += '<div style="text-align:center"><button class="add-group-btn" onclick="addGroup()">+ 새 그룹</button></div>';
  }
  body.innerHTML = html;
  initSortableGroups();
}

function renderGroup(sectorId, group){
  let rows = '';
  const stocks = group.stocks || [];
  const isNxt = (_market === 'NX');
  if(stocks.length){
    const sorted = sortStocks(stocks);
    rows = '<table class="stock-table">' +
      '<thead><tr>' +
      '<th>종목명</th>' +
      (isNxt ? '<th class="num">KRX 종가</th>' : '') +
      '<th class="num">' + (isNxt ? 'NXT 현재가' : '현재가') + '</th>' +
      (isNxt ? '<th class="num">괴리</th><th class="num">괴리율</th>' : '<th class="num">등락</th><th class="num">등락률</th>') +
      '<th class="num">거래량</th>' +
      '<th></th>' +
      '</tr></thead><tbody>' +
      sorted.map(st => renderStockRow(group.id, st)).join('') +
      '</tbody></table>';
  } else {
    rows = '<div class="content-empty" style="padding:20px">종목 없음</div>';
  }
  // 그룹 요약 (평균)
  let summary = '';
  if(stocks.length){
    const key = isNxt ? 'gap_pct' : 'chg_pct';
    const vals = stocks.map(s => (_quotes[s.code] || {})[key]).filter(v => v !== undefined && v !== null);
    if(vals.length){
      const avg = vals.reduce((a,b)=>a+b, 0) / vals.length;
      const cls = avg > 0 ? 'up' : (avg < 0 ? 'down' : 'flat');
      summary = '<span style="margin-left:8px;font-size:11.5px;font-weight:500;" class="' + cls + '">평균 ' + (isNxt?'괴리 ':'') + (avg>0?'+':'') + avg.toFixed(2) + '%</span>';
    }
  }
  return '<div class="group" data-group-id="' + group.id + '">' +
    '<div class="group-header">' +
      (_editing ? '<span class="group-drag" title="드래그로 순서 변경">⋮⋮</span>' : '') +
      '<span class="group-icon">📌</span>' +
      '<span class="group-name" contenteditable="' + (_editing?'true':'false') + '" onblur="renameGroup(\'' + group.id + '\', this)" onkeydown="if(event.key===\'Enter\'){event.preventDefault();this.blur();}">' + esc(group.name) + '</span>' +
      summary +
      (_editing ? '<span class="group-actions"><button class="btn btn-mini btn-danger" onclick="deleteGroup(\'' + group.id + '\')" title="그룹 삭제">🗑</button></span>' : '') +
    '</div>' +
    rows +
    '<div class="add-stock">' +
      '<div class="ac-wrap">' +
        '<input type="text" placeholder="종목명 입력 (예: 두산에너빌리티)" ' +
               'id="ac-input-' + group.id + '" autocomplete="off" ' +
               'oninput="acSearch(\'' + group.id + '\', this.value)" ' +
               'onkeydown="acKeydown(event, \'' + group.id + '\')" ' +
               'onblur="setTimeout(()=>acClose(\'' + group.id + '\'), 200)"/>' +
        '<div class="ac-list" id="ac-list-' + group.id + '"></div>' +
      '</div>' +
      '<button class="btn" onclick="acManualToggle(\'' + group.id + '\')" title="종목코드로 직접 입력">🔢 코드입력</button>' +
    '</div>' +
    '<div class="add-stock manual" id="manual-' + group.id + '" style="display:none;">' +
      '<input type="text" placeholder="종목코드 6자리" id="add-code-' + group.id + '" maxlength="6"/>' +
      '<input type="text" placeholder="종목명" id="add-name-' + group.id + '"/>' +
      '<button class="btn btn-primary" onclick="addStock(\'' + group.id + '\')">+ 추가</button>' +
    '</div>' +
    '</div>';
}

function renderStockRow(groupId, st, showGroup){
  const q = _quotes[st.code] || {};
  const has = q.price !== undefined;
  const isNxt = (_market === 'NX');
  const volume = q.volume !== undefined ? num(q.volume) : '—';
  const mkt = q.market || _market;
  const mktBadge = has
    ? '<span class="mkt-badge ' + (MKT_CLASS[mkt]||'un') + '">' + (MKT_LABEL[mkt]||mkt) + '</span>'
    : '';
  const groupCol = showGroup ? '<td style="font-size:11.5px;color:#7a8099">' + esc(st._group || '') + '</td>' : '';

  let priceCols;
  let mainPct;   // 색상 기준
  if(isNxt){
    // KRX 종가 · NXT 현재가 · 괴리 · 괴리율
    const krxClose = q.krx_close ? num(q.krx_close) : '—';
    const nxtPrice = has ? num(q.price) : '—';
    const gapVal = (q.gap !== undefined && q.gap !== null) ? (q.gap > 0 ? '+' : '') + num(q.gap) : '—';
    const gapPctVal = (q.gap_pct !== undefined && q.gap_pct !== null)
      ? (q.gap_pct > 0 ? '+' : '') + q.gap_pct.toFixed(2) + '%' : '—';
    mainPct = q.gap_pct;
    const gcls = mainPct > 0 ? 'up' : (mainPct < 0 ? 'down' : 'flat');
    const noNxt = q.no_nxt ? '<span class="hot" style="background:#f1f3f5;color:#7a8099">시간외X</span>' : '';
    priceCols =
      '<td class="num" style="color:#7a8099">' + krxClose + '</td>' +
      '<td class="num">' + nxtPrice + noNxt + '</td>' +
      '<td class="num ' + gcls + '">' + gapVal + '</td>' +
      '<td class="num ' + gcls + '" style="font-weight:700">' + gapPctVal + '</td>';
  } else {
    const price = has ? num(q.price) : '—';
    const chg = q.chg !== undefined ? (q.chg > 0 ? '+' : '') + num(q.chg) : '';
    const chgPct = q.chg_pct !== undefined ? (q.chg_pct > 0 ? '+' : '') + q.chg_pct.toFixed(2) + '%' : '';
    mainPct = q.chg_pct;
    const cls = mainPct > 0 ? 'up' : (mainPct < 0 ? 'down' : 'flat');
    priceCols =
      '<td class="num">' + price + '</td>' +
      '<td class="num ' + cls + '">' + chg + '</td>' +
      '<td class="num ' + cls + '">' + chgPct + '</td>';
  }

  // 🔥 뱃지 — NXT면 괴리율 기준, 아니면 등락률 기준
  const hotBadge = (mainPct !== undefined && mainPct !== null && Math.abs(mainPct) >= (isNxt ? 3 : 5))
    ? '<span class="hot">🔥</span>' : '';

  return '<tr class="stock-row" data-code="' + st.code + '">' +
    '<td><span class="stock-name">' + esc(st.name) + '</span><span class="stock-code">' + esc(st.code) + '</span>' + mktBadge + hotBadge + '</td>' +
    groupCol +
    priceCols +
    '<td class="num">' + volume + '</td>' +
    '<td><span class="row-actions"><button class="btn btn-mini btn-danger" onclick="deleteStock(\'' + groupId + '\', \'' + st.code + '\')" title="삭제">✕</button></span></td>' +
    '</tr>';
}

// ── 섹터 관리 ─────────────────────────────
function switchSector(id){
  if(_data.currentSectorId === id) return;
  _data.currentSectorId = id;
  render();          // ⚡ 캐시된 시세로 즉시 렌더 (기다림 없음)
  scheduleSave();
  // 아직 시세 없는 종목만 추가 조회
  const sector = _data.sectors.find(s => s.id === id);
  if(sector){
    const missing = [];
    for(const g of (sector.groups || [])){
      for(const st of (g.stocks || [])){
        if(!_quotes[st.code]) missing.push(st.code);
      }
    }
    if(missing.length) refreshQuotes(missing);
  }
}

function addSector(){
  const n = _data.sectors.length + 1;
  const s = {id: genId(), name: '섹터 ' + n, groups: []};
  _data.sectors.push(s);
  _data.currentSectorId = s.id;
  render();
  scheduleSave();
}

function renameSector(id, el){
  const s = _data.sectors.find(x => x.id === id);
  const newName = (el.innerText || '').trim().slice(0, 30);
  if(s && newName && newName !== s.name){
    s.name = newName;
    scheduleSave();
  }
  el.innerText = s ? s.name : '';
}

function deleteSector(id){
  if(_data.sectors.length <= 1){ alert('마지막 섹터는 삭제 불가'); return; }
  const s = _data.sectors.find(x => x.id === id);
  if(!s) return;
  if(!confirm('"' + s.name + '" 섹터 삭제할까요?\n(하위 그룹·종목 모두 삭제됨)')) return;
  const idx = _data.sectors.findIndex(x => x.id === id);
  _data.sectors.splice(idx, 1);
  _data.currentSectorId = _data.sectors[Math.max(0, idx-1)].id;
  render();
  refreshQuotes();
  scheduleSave();
}

// ── 그룹 관리 ─────────────────────────────
function addGroup(){
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector) return;
  sector.groups.push({id: genId(), name: '새 그룹', stocks: []});
  render();
  scheduleSave();
}

function renameGroup(id, el){
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector) return;
  const g = sector.groups.find(x => x.id === id);
  const newName = (el.innerText || '').trim().slice(0, 30);
  if(g && newName && newName !== g.name){
    g.name = newName;
    scheduleSave();
  }
  el.innerText = g ? g.name : '';
}

function deleteGroup(id){
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector) return;
  const g = sector.groups.find(x => x.id === id);
  if(!g) return;
  const cnt = (g.stocks || []).length;
  if(!confirm('"' + g.name + '" 그룹 삭제할까요?' + (cnt > 0 ? '\n(종목 ' + cnt + '개 함께 삭제)' : ''))) return;
  sector.groups = sector.groups.filter(x => x.id !== id);
  render();
  scheduleSave();
}

// ── 종목 관리 ─────────────────────────────
// ── 🆕 종목명 자동완성 ────────────────────
const _acState = {};   // { groupId: {timer, items, sel, q} }

function acSearch(groupId, q){
  q = (q || '').trim();
  const st = _acState[groupId] = _acState[groupId] || {};
  if(st.timer) clearTimeout(st.timer);
  const listEl = document.getElementById('ac-list-' + groupId);
  if(!listEl) return;
  if(q.length < 1){
    acClose(groupId);
    return;
  }
  // 6자리 숫자면 코드 직접 입력으로 간주
  if(/^\d{6}$/.test(q)){
    listEl.innerHTML = '<div class="ac-item" onclick="acPickRaw(\'' + groupId + '\', \'' + q + '\')">' +
      '<span class="ac-item-name">종목코드 ' + q + '</span>' +
      '<span class="ac-item-code">직접 추가</span></div>';
    listEl.classList.add('open');
    return;
  }
  listEl.innerHTML = '<div class="ac-loading">검색 중...</div>';
  listEl.classList.add('open');
  st.timer = setTimeout(async () => {
    try {
      const res = await fetch('/api/watchlist/search?q=' + encodeURIComponent(q));
      const data = await res.json();
      const items = data.items || [];
      st.items = items;
      st.sel = -1;
      if(!items.length){
        const ms = data.master_size || 0;
        const err = data.master_error || '';
        if(ms === 0){
          listEl.innerHTML = '<div class="ac-empty">📥 종목 목록 로드 실패' +
            (err ? '<br><span style="font-size:10px;color:#d63031">' + esc(err.slice(0,120)) + '</span>' : '') +
            '<br><span style="font-size:11px"># 버튼으로 종목코드 직접 입력하세요</span></div>';
        } else {
          listEl.innerHTML = '<div class="ac-empty">검색 결과 없음 (' + ms + '종목 중) · # 버튼으로 코드 직접 입력</div>';
        }
        return;
      }
      listEl.innerHTML = items.map((it, i) =>
        '<div class="ac-item" data-idx="' + i + '" onclick="acPick(\'' + groupId + '\', ' + i + ')">' +
        '<span class="ac-item-name">' + esc(it.name) + '</span>' +
        '<span class="ac-item-code">' + esc(it.code) + '</span>' +
        (it.market ? '<span class="ac-item-market">' + esc(it.market) + '</span>' : '') +
        '</div>'
      ).join('');
    } catch(e){
      listEl.innerHTML = '<div class="ac-empty">검색 실패 · # 버튼으로 코드 직접 입력</div>';
    }
  }, 300);
}

function acKeydown(e, groupId){
  const st = _acState[groupId];
  const listEl = document.getElementById('ac-list-' + groupId);
  if(!st || !st.items || !st.items.length || !listEl || !listEl.classList.contains('open')){
    if(e.key === 'Enter'){
      // 6자리 코드면 바로 추가
      const v = (document.getElementById('ac-input-' + groupId).value || '').trim();
      if(/^\d{6}$/.test(v)) acPickRaw(groupId, v);
    }
    return;
  }
  if(e.key === 'ArrowDown'){
    e.preventDefault();
    st.sel = Math.min((st.sel === undefined ? -1 : st.sel) + 1, st.items.length - 1);
    acHighlight(groupId);
  } else if(e.key === 'ArrowUp'){
    e.preventDefault();
    st.sel = Math.max((st.sel === undefined ? 0 : st.sel) - 1, 0);
    acHighlight(groupId);
  } else if(e.key === 'Enter'){
    e.preventDefault();
    const idx = (st.sel === undefined || st.sel < 0) ? 0 : st.sel;
    acPick(groupId, idx);
  } else if(e.key === 'Escape'){
    acClose(groupId);
  }
}

function acHighlight(groupId){
  const st = _acState[groupId];
  const listEl = document.getElementById('ac-list-' + groupId);
  if(!listEl) return;
  listEl.querySelectorAll('.ac-item').forEach(el => el.classList.remove('sel'));
  const target = listEl.querySelector('[data-idx="' + st.sel + '"]');
  if(target){
    target.classList.add('sel');
    target.scrollIntoView({block:'nearest'});
  }
}

function acPick(groupId, idx){
  const st = _acState[groupId];
  if(!st || !st.items || !st.items[idx]) return;
  const it = st.items[idx];
  addStockDirect(groupId, it.code, it.name);
  const inputEl = document.getElementById('ac-input-' + groupId);
  if(inputEl) inputEl.value = '';
  acClose(groupId);
}

function acPickRaw(groupId, code){
  addStockDirect(groupId, code, code);   // 이름 = 코드 (나중에 시세 조회 후 갱신 가능)
  const inputEl = document.getElementById('ac-input-' + groupId);
  if(inputEl) inputEl.value = '';
  acClose(groupId);
}

function acClose(groupId){
  const listEl = document.getElementById('ac-list-' + groupId);
  if(listEl) listEl.classList.remove('open');
}

function acManualToggle(groupId){
  const el = document.getElementById('manual-' + groupId);
  if(!el) return;
  el.style.display = el.style.display === 'none' ? 'flex' : 'none';
}

// 공통 추가 로직
function addStockDirect(groupId, code, name){
  code = (code || '').trim();
  name = (name || '').trim();
  if(!/^\d{6}$/.test(code)){ alert('종목코드는 6자리 숫자'); return; }
  if(!name) name = code;
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector) return;
  const g = sector.groups.find(x => x.id === groupId);
  if(!g) return;
  if(g.stocks.find(s => s.code === code)){
    showSaved('⚠️ 이미 있는 종목: ' + name);
    return;
  }
  g.stocks.push({code, name});
  render();
  refreshQuotes([code]);
  scheduleSave();
  showSaved('✅ ' + name + ' 추가됨');
  // 추가 후 다시 입력창에 포커스 (연속 추가 편하게)
  setTimeout(() => {
    const inputEl = document.getElementById('ac-input-' + groupId);
    if(inputEl) inputEl.focus();
  }, 100);
}

function addStock(groupId){
  const codeEl = document.getElementById('add-code-' + groupId);
  const nameEl = document.getElementById('add-name-' + groupId);
  const code = (codeEl.value || '').trim();
  const name = (nameEl.value || '').trim();
  if(!code || !/^\d{6}$/.test(code)){
    alert('종목코드는 6자리 숫자 (예: 005930)');
    return;
  }
  if(!name){ alert('종목명을 입력해주세요'); return; }
  addStockDirect(groupId, code, name);
  codeEl.value = '';
  nameEl.value = '';
}

function deleteStock(groupId, code){
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector) return;
  const g = sector.groups.find(x => x.id === groupId);
  if(!g) return;
  const st = g.stocks.find(s => s.code === code);
  if(!confirm('"' + (st ? st.name : code) + '" 삭제할까요?')) return;
  g.stocks = g.stocks.filter(s => s.code !== code);
  render();
  scheduleSave();
}

// ── 편집 모드 ─────────────────────────────
function toggleEdit(){
  _editing = !_editing;
  document.body.classList.toggle('edit-mode', _editing);
  document.getElementById('edit-btn').textContent = _editing ? '✓ 편집 완료' : '⚙️ 편집';
  document.getElementById('edit-btn').classList.toggle('btn-primary', _editing);
  render();
}

// ── KIS 시세 조회 ──────────────────────────
let _fetching = false;

// ⚡ 전체 섹터 종목 코드 (탭 전환 시 즉시 표시용)
function allCodesEverywhere(){
  const set = new Set();
  for(const s of _data.sectors){
    for(const g of (s.groups || [])){
      for(const st of (g.stocks || [])) set.add(st.code);
    }
  }
  return Array.from(set);
}

async function refreshQuotes(codes, opts){
  opts = opts || {};
  if(_fetching && !opts.force) return;
  const btn = document.getElementById('refresh-btn');
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector){ return; }
  _fetching = true;
  if(btn){ btn.disabled = true; btn.textContent = '⏳ 조회 중...'; }
  const t0 = performance.now();
  // codes가 주어지면 그것만, 아니면 현재 섹터의 모든 종목
  let allCodes;
  if(codes && codes.length){
    allCodes = codes;
  } else {
    const set = new Set();
    for(const g of sector.groups){
      for(const s of g.stocks) set.add(s.code);
    }
    allCodes = Array.from(set);
  }
  if(!allCodes.length){
    if(btn){ btn.disabled = false; btn.textContent = '🔄 시세 갱신';}
    return;
  }
  try {
    const res = await fetch('/api/watchlist/quotes', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({codes: allCodes, market: _market, force: !!opts.force})
    });
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    Object.assign(_quotes, data.quotes || {});
    // 종목명이 코드로만 되어 있으면 API가 준 이름으로 자동 보정
    let renamed = false;
    for(const s of _data.sectors){
      for(const g of s.groups){
        for(const st of g.stocks){
          const q = _quotes[st.code];
          if(q && q.api_name && (st.name === st.code || !st.name)){
            st.name = q.api_name;
            renamed = true;
          }
        }
      }
    }
    if(renamed) scheduleSave();
    const ms = Math.round(performance.now() - t0);
    const got = Object.keys(data.quotes || {}).length;
    document.getElementById('updated').textContent =
      '📊 ' + MKT_LABEL[_market] + ' 시세 · ' + new Date().toLocaleTimeString('ko-KR') +
      ' · ' + got + '/' + allCodes.length + '종목 · ' + ms + 'ms' +
      (data.cached ? ' (캐시)' : '');
    updateMarketHint();
    renderBody();
  } catch(e){
    document.getElementById('updated').textContent = '⚠️ 시세 조회 실패: ' + e.message;
  } finally {
    _fetching = false;
    if(btn){ btn.disabled = false; btn.textContent = '🔄 시세 갱신'; }
  }
}

// 30초마다 자동 갱신 (탭 활성 시만)
function startAutoRefresh(){
  if(_autoRefreshTimer) clearInterval(_autoRefreshTimer);
  _autoRefreshTimer = setInterval(() => {
    if(document.hidden) return;
    refreshQuotes(allCodesEverywhere());
  }, 30000);
}

document.addEventListener('visibilitychange', () => {
  if(!document.hidden) refreshQuotes(allCodesEverywhere());
});

// 초기 컨트롤 상태 세팅
function initControls(){
  document.querySelectorAll('.seg[data-mkt]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-mkt') === _market);
  });
  document.querySelectorAll('.seg[data-sort]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-sort') === _sort);
  });
  updateMarketHint();
  setInterval(updateMarketHint, 60000);
}

initControls();
loadData();
startAutoRefresh();

// 종목 마스터 미리 예열 (첫 검색 빠르게)
fetch('/api/watchlist/master-status')
  .then(r => r.json())
  .then(d => {
    if(!d.loaded){
      // 백그라운드로 로드 트리거 (응답 안 기다림)
      fetch('/api/watchlist/search?q=삼성');
    }
  })
  .catch(() => {});
</script>
</body>
</html>
"""


def fetch_stock_quotes(codes: list, kis_get_fn, market: str = "UN",
                       token: str = "", app_key: str = "", app_secret: str = "") -> dict:
    """
    KIS API로 여러 종목 시세 조회 (병렬 + 커넥션 재사용)

    token/app_key/app_secret이 주어지면 requests.Session으로 직접 호출 (훨씬 빠름).
    없으면 kis_get_fn 폴백.

    market: 'J'=KRX, 'NX'=NXT, 'UN'=통합
    """
    import concurrent.futures
    import threading
    import requests as _rq

    if market not in ("J", "NX", "UN"):
        market = "UN"

    quotes = {}
    lock = threading.Lock()

    # 중복 제거 + 유효 코드만
    uniq, seen = [], set()
    for c in codes:
        c = str(c).strip()
        if c and len(c) == 6 and c not in seen:
            seen.add(c)
            uniq.append(c)
    if not uniq:
        return {}

    # ── 빠른 경로: 전역 Session 재사용 ──
    use_session = bool(token and app_key and app_secret)
    session = _get_session(token, app_key, app_secret) if use_session else None

    URL = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price"

    def parse_out(out, code):
        if not out:
            return
        def _i(k, d=0):
            try: return int(float(out.get(k, d) or d))
            except: return d
        def _f(k, d=0.0):
            try: return float(out.get(k, d) or d)
            except: return d
        chg = _i("prdy_vrss")
        chg_pct = _f("prdy_ctrt")
        sign = str(out.get("prdy_vrss_sign", "3"))
        if sign in ("4", "5"):
            chg, chg_pct = -abs(chg), -abs(chg_pct)
        elif sign in ("1", "2"):
            chg, chg_pct = abs(chg), abs(chg_pct)
        with lock:
            quotes[code] = {
                "price": _i("stck_prpr"),
                "chg": chg,
                "chg_pct": chg_pct,
                "volume": _i("acml_vol"),
                "market": market,
                "api_name": (out.get("hts_kor_isnm") or "").strip(),
                "high": _i("stck_hgpr"),
                "low": _i("stck_lwpr"),
                "open": _i("stck_oprc"),
                "prev_close": _i("stck_sdpr"),
            }

    def fetch_one(code):
        try:
            if use_session:
                r = session.get(
                    URL,
                    params={"FID_COND_MRKT_DIV_CODE": market, "FID_INPUT_ISCD": code},
                    timeout=(2, 3),   # (연결 2초, 읽기 3초) — 하나 느려도 전체 안 막힘
                )
                out = r.json().get("output", {})
            else:
                r = kis_get_fn(
                    "/uapi/domestic-stock/v1/quotations/inquire-price",
                    "FHKST01010100",
                    {"FID_COND_MRKT_DIV_CODE": market, "FID_INPUT_ISCD": code}
                )
                out = r.get("output", {}) if isinstance(r, dict) else {}
            parse_out(out, code)
        except Exception as e:
            print(f"[watchlist] {code} ({market}) 실패: {e}")

    # 워커 16개 — 전역 세션 풀(32) 안에서 최대 병렬
    workers = min(16, max(4, len(uniq)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(fetch_one, uniq))

    return quotes


_krx_close_cache = {"date": "", "prices": {}}    # {code: {price, chg_pct}}


def fetch_quotes_with_gap(codes: list, kis_get_fn, market: str = "UN",
                          token: str = "", app_key: str = "", app_secret: str = "") -> dict:
    """
    NXT 선택 시 KRX 정규장 마감가를 같이 받아 '괴리율' 계산.

    gap_pct = (NXT 현재가 - KRX 종가) / KRX 종가 * 100

    ⚡ 최적화: 장 마감(15:30) 이후엔 KRX 종가가 고정이므로 캐시.
       → 30초마다 갱신할 때 NXT만 조회 (요청 절반)
    """
    import concurrent.futures
    from datetime import datetime as _dt

    if market != "NX":
        return fetch_stock_quotes(codes, kis_get_fn, market, token, app_key, app_secret)

    now = _dt.now()
    today = now.strftime("%Y-%m-%d")
    after_close = (now.hour * 60 + now.minute) >= 15 * 60 + 40   # 15:40 이후 = 종가 확정

    # 캐시 날짜가 다르면 초기화
    if _krx_close_cache["date"] != today:
        _krx_close_cache["date"] = today
        _krx_close_cache["prices"] = {}

    need_krx = [c for c in codes if str(c).strip() not in _krx_close_cache["prices"]]
    # 장중이면 KRX도 계속 변하므로 항상 다시 받음
    if not after_close:
        need_krx = list(codes)

    if need_krx:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            f_nx = ex.submit(fetch_stock_quotes, codes, kis_get_fn, "NX",
                             token, app_key, app_secret)
            f_krx = ex.submit(fetch_stock_quotes, need_krx, kis_get_fn, "J",
                              token, app_key, app_secret)
            nx = f_nx.result()
            krx_new = f_krx.result()
        # 종가 확정 이후에만 캐시에 적재
        if after_close:
            for c, k in krx_new.items():
                _krx_close_cache["prices"][c] = {
                    "price": k.get("price", 0),
                    "chg_pct": k.get("chg_pct"),
                }
        krx = dict(_krx_close_cache["prices"])
        krx.update(krx_new)
    else:
        # KRX는 캐시로 해결 → NXT만 조회 (요청 절반!)
        nx = fetch_stock_quotes(codes, kis_get_fn, "NX", token, app_key, app_secret)
        krx = dict(_krx_close_cache["prices"])

    out = {}
    for code, q in nx.items():
        k = krx.get(code, {})
        krx_close = k.get("price", 0)
        nxt_price = q.get("price", 0)
        gap = gap_pct = None
        if krx_close and nxt_price:
            gap = nxt_price - krx_close
            gap_pct = round(gap / krx_close * 100, 2)
        q = dict(q)
        q["krx_close"] = krx_close
        q["krx_chg_pct"] = k.get("chg_pct")
        q["gap"] = gap
        q["gap_pct"] = gap_pct
        out[code] = q

    # NXT 체결 없는 종목 → KRX 값으로 채움
    for code, k in krx.items():
        if code not in out and k.get("price"):
            out[code] = {
                "price": k["price"],
                "chg": 0,
                "chg_pct": k.get("chg_pct", 0),
                "volume": 0,
                "market": "NX",
                "krx_close": k["price"],
                "krx_chg_pct": k.get("chg_pct"),
                "gap": 0,
                "gap_pct": 0.0,
                "no_nxt": True,
            }

    return out


def resolve_stock_name(code: str, kis_get_fn) -> str:
    """종목코드 → 종목명 (KIS API)"""
    try:
        r = kis_get_fn(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            "FHKST01010100",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
        )
        out = r.get("output", {}) if isinstance(r, dict) else {}
        return (out.get("hts_kor_isnm") or "").strip()
    except Exception:
        return ""

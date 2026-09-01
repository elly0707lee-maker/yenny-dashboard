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

/* 좌우 분할 */
.split{display:grid;grid-template-columns:1fr 340px;gap:20px;align-items:start}
.split-right{position:sticky;top:110px}
@media (max-width:1100px){
  .split{grid-template-columns:1fr}
  .split-right{position:static}
}

/* 🔎 전역 종목 검색 */
.gs-wrap{position:relative}
.gs-box{
  padding:5px 12px;border:1px solid #e5e7eb;border-radius:16px;
  font-size:11.5px;font-family:inherit;outline:none;width:210px;
  background:#f8f9fa;transition:all .12s;
}
.gs-box:focus{border-color:#1a1d23;background:#fff;width:280px}
.gs-list{
  display:none;position:absolute;top:calc(100% + 4px);right:0;
  min-width:280px;background:#fff;border:1px solid #e5e7eb;border-radius:9px;
  box-shadow:0 6px 20px rgba(0,0,0,0.12);z-index:120;
  max-height:300px;overflow-y:auto;
}
.gs-list.open{display:block}
.gs-item{
  padding:9px 13px;font-size:12.5px;cursor:pointer;
  display:flex;align-items:center;gap:9px;border-bottom:1px solid #f4f6f8;
}
.gs-item:last-child{border-bottom:none}
.gs-item:hover,.gs-item.sel{background:#f1f3f5}
.gs-name{font-weight:600;flex:1;min-width:0;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gs-code{font-size:10.5px;color:#a8b0bd}
.gs-tag{font-size:10px;color:#f0b429;font-weight:700}
.gs-msg{padding:11px 13px;font-size:12px;color:#a8b0bd}

/* 📊 순위 */
.rank-market{
  display:flex;gap:4px;align-items:center;margin-bottom:10px;
}
.rank-market .seg{padding:4px 11px;font-size:11px}
.rank-block{
  background:#fff;border:1px solid #e5e7eb;border-radius:11px;
  padding:12px 14px;margin-bottom:12px;
}
.rank-head{
  display:flex;align-items:center;gap:8px;
  padding-bottom:8px;margin-bottom:6px;border-bottom:1.5px solid #1a1d23;
}
.rank-title{font-size:13px;font-weight:700;white-space:nowrap}
.rank-toggle{display:flex;gap:3px;margin-left:auto}
.rank-toggle .seg{padding:3px 9px;font-size:10.5px}
.rank-row{
  display:flex;align-items:center;gap:7px;
  padding:6px 2px;border-bottom:1px solid #f4f6f8;
  font-size:12px;cursor:pointer;transition:background .1s;
}
.rank-row:last-child{border-bottom:none}
.rank-row:hover{background:#f8f9fa}
.rk-no{
  font-size:10.5px;color:#a8b0bd;min-width:15px;text-align:right;
  font-variant-numeric:tabular-nums;flex:0 0 auto;
}
.rk-star{
  background:transparent;border:0;cursor:pointer;font-size:13px;
  color:#dfe4ea;padding:0;transition:all .12s;flex:0 0 auto;
}
.rk-star:hover{color:#f0b429;transform:scale(1.2)}
.rk-star.on{color:#f0b429}
.rk-name{
  font-weight:600;flex:1;min-width:0;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.rk-name:hover{color:#0984e3}
.rk-sub{font-size:10px;color:#a8b0bd;flex:0 0 auto;font-variant-numeric:tabular-nums}
.rk-pct{
  font-weight:700;min-width:52px;text-align:right;
  font-variant-numeric:tabular-nums;flex:0 0 auto;
}
.chart-ic{
  text-decoration:none;font-size:12px;opacity:0.35;
  padding:0 3px;transition:opacity .12s;flex:0 0 auto;
}
.chart-ic:hover{opacity:1}
.stock-row:hover .chart-ic,.rank-row:hover .chart-ic,.gs-item:hover .chart-ic{opacity:0.8}
.rank-empty{font-size:11.5px;color:#a8b0bd;font-style:italic;padding:14px 2px}
.rank-more{
  width:100%;padding:6px;margin-top:6px;
  border:1px dashed #dfe4ea;border-radius:7px;
  background:transparent;color:#a8b0bd;font-size:11px;cursor:pointer;
  font-family:inherit;transition:all .12s;
}
.rank-more:hover{background:#f8f9fa;color:#1a1d23;border-color:#c5ccd6}
.split-right{max-height:calc(100vh - 130px);overflow-y:auto}

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
    <div class="gs-wrap">
      <input type="text" id="gs-input" class="gs-box" placeholder="🔎 종목 검색해서 TODAY에 담기"
             autocomplete="off" oninput="gsSearch(this.value)"
             oncompositionstart="_composing=true"
             oncompositionend="_composing=false;gsSearch(this.value)"
             onkeydown="gsKey(event)"
             onblur="setTimeout(gsClose, 200)"/>
      <div class="gs-list" id="gs-list"></div>
    </div>
  </div>
  <div class="ctrl-group">
    <span class="market-hint" id="market-hint"></span>
  </div>
</div>

<div class="wrap">
  <div class="updated" id="updated"></div>
  <div class="split">
    <div class="split-left">
      <div class="sector-tabs" id="sector-tabs"></div>
      <div id="fav-body"><div class="content-empty">불러오는 중...</div></div>
    </div>
    <div class="split-right">
      <div class="rank-market">
        <button class="seg active" data-rmkt="all" onclick="setRankMarket('all')">전체</button>
        <button class="seg" data-rmkt="kospi" onclick="setRankMarket('kospi')">코스피</button>
        <button class="seg" data-rmkt="kosdaq" onclick="setRankMarket('kosdaq')">코스닥</button>
        <button class="btn btn-mini" style="margin-left:auto" onclick="loadRanks(true)" id="rank-refresh">🔄</button>
      </div>
      <div class="rank-block">
        <div class="rank-head">
          <span class="rank-title">📊 등락률</span>
          <span class="rank-toggle">
            <button class="seg active" data-fluc="up" onclick="setFluc('up')">상승</button>
            <button class="seg" data-fluc="down" onclick="setFluc('down')">하락</button>
          </span>
        </div>
        <div id="rank-fluc"><div class="rank-empty">불러오는 중...</div></div>
        <button class="rank-more" id="more-fluc" onclick="toggleOne('fluc')">▾ 더보기</button>
      </div>
      <div class="rank-block">
        <div class="rank-head"><span class="rank-title">💰 시총 상위</span></div>
        <div id="rank-cap"><div class="rank-empty">불러오는 중...</div></div>
        <button class="rank-more" id="more-cap" onclick="toggleOne('cap')">▾ 더보기</button>
      </div>
      <div class="rank-block">
        <div class="rank-head"><span class="rank-title">💵 거래대금 상위</span></div>
        <div id="rank-amount"><div class="rank-empty">불러오는 중...</div></div>
        <button class="rank-more" id="more-amount" onclick="toggleOne('amount')">▾ 더보기</button>
      </div>
    </div>
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
    <div class="modal-foot">
      <a class="btn" id="chart-link" href="#" target="_blank">📈 네이버 차트</a>
      <a class="btn" id="naver-link" href="#" target="_blank">🔍 종목 정보</a>
      <button class="btn" onclick="closeStock()">닫기</button>
    </div>
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

function render(){
  renderTabs(); renderBody();
  // 순위 목록의 ★ 상태도 갱신
  if(_ranks[_fluc]) renderRank('rank-fluc', _ranks[_fluc]);
  if(_ranks['cap']) renderRank('rank-cap', _ranks['cap']);
  if(_ranks['amount']) renderRank('rank-amount', _ranks['amount']);
}

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
    '<td>' + chartBtn(st.code) +
      '<span class="row-actions"><button class="btn btn-mini btn-danger" ' +
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
  const cl = document.getElementById('chart-link');
  if(cl) cl.href = 'https://m.stock.naver.com/fchart/domestic/stock/' + code;
  const nl = document.getElementById('naver-link');
  if(nl) nl.href = 'https://m.stock.naver.com/domestic/stock/' + code + '/total';
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

// ── 📊 순위 (한투 API) ─────────────────────
let _fluc = 'up';
let _rankMarket = 'all';
let _ranks = {};
let _rankLoading = false;
let _expand = {fluc:false, cap:false, amount:false};   // 블록별 더보기

function setFluc(k){
  _fluc = k;
  document.querySelectorAll('.seg[data-fluc]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-fluc') === k));
  try { localStorage.setItem('fav_fluc', k); } catch(e){}
  loadRanks();
}

function setRankMarket(m){
  _rankMarket = m;
  document.querySelectorAll('.seg[data-rmkt]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-rmkt') === m));
  try { localStorage.setItem('fav_rmkt', m); } catch(e){}
  _ranks = {};
  loadRanks(true);
}

// 3개 순위를 한 번의 요청으로 (서버에서 병렬 처리)
async function loadRanks(force){
  if(_rankLoading) return;
  _rankLoading = true;
  const btn = document.getElementById('rank-refresh');
  if(btn) btn.textContent = '⏳';
  // 캐시된 게 있으면 먼저 그려두고 갱신
  if(_ranks[_fluc]) renderRank('rank-fluc', _ranks[_fluc]);
  else setRankMsg('rank-fluc', '불러오는 중...');
  if(!_ranks['cap']) setRankMsg('rank-cap', '불러오는 중...');
  if(!_ranks['amount']) setRankMsg('rank-amount', '불러오는 중...');

  try {
    const res = await fetch('/api/rankings?market=' + _rankMarket + '&fluc=' + _fluc +
                            '&limit=30');
    const d = await res.json();
    if(!d.ok){
      ['rank-fluc','rank-cap','rank-amount'].forEach(id =>
        setRankMsg(id, '⚠️ ' + (d.error || '실패')));
      return;
    }
    const map = {'rank-fluc': _fluc, 'rank-cap': 'cap', 'rank-amount': 'amount'};
    for(const id in map){
      const r = (d.data || {})[map[id]] || {};
      if(r.items && r.items.length){
        _ranks[map[id]] = r.items;
        renderRank(id, r.items);
      } else {
        setRankMsg(id, '⚠️ ' + (r.error || '데이터 없음'));
      }
    }
  } catch(e){
    ['rank-fluc','rank-cap','rank-amount'].forEach(id =>
      setRankMsg(id, '⚠️ ' + (e.message || e)));
  } finally {
    _rankLoading = false;
    if(btn) btn.textContent = '🔄';
  }
}

function toggleOne(which){
  _expand[which] = !_expand[which];
  try { localStorage.setItem('fav_exp', JSON.stringify(_expand)); } catch(e){}
  const idMap = {fluc:'rank-fluc', cap:'rank-cap', amount:'rank-amount'};
  const keyMap = {fluc:_fluc, cap:'cap', amount:'amount'};
  renderRank(idMap[which], _ranks[keyMap[which]] || []);
}

function moreLabel(which, total){
  const b = document.getElementById('more-' + which);
  if(!b) return;
  b.style.display = 'block';
  b.textContent = _expand[which] ? '▴ 접기' : ('▾ 더보기 (' + total + '위까지)');
}

function setRankMsg(id, msg){
  const el = document.getElementById(id);
  if(el) el.innerHTML = '<div class="rank-empty">' + esc(msg) + '</div>';
}

// 억·조 단위 축약
function shortAmt(n){
  if(!n) return '';
  const eok = n / 100000000;
  if(eok >= 10000) return (eok/10000).toFixed(1) + '조';
  if(eok >= 1) return Math.round(eok).toLocaleString('ko-KR') + '억';
  return Math.round(n/10000).toLocaleString('ko-KR') + '만';
}

function renderRank(elId, items){
  const el = document.getElementById(elId);
  if(!el) return;
  const whichMap = {'rank-fluc':'fluc', 'rank-cap':'cap', 'rank-amount':'amount'};
  const which = whichMap[elId];
  if(!items || !items.length){
    setRankMsg(elId, '데이터 없음');
    const b = document.getElementById('more-' + which);
    if(b) b.style.display = 'none';
    return;
  }
  const shown = _expand[which] ? items : items.slice(0, 10);
  const isCap = (elId === 'rank-cap');
  const isAmt = (elId === 'rank-amount');
  el.innerHTML = shown.map((it, i) => {
    const cls = it.chg_pct > 0 ? 'up' : (it.chg_pct < 0 ? 'down' : 'flat');
    let sub = '';
    if(isCap) sub = shortAmt((it.cap || 0) * 100000000);
    else if(isAmt) sub = shortAmt(it.amount);
    return '<div class="rank-row">' +
      '<span class="rk-no">' + (i+1) + '</span>' +
      '<button class="rk-star' + (isFavCode(it.code) ? ' on' : '') + '" ' +
        'onclick="event.stopPropagation();favStock(\'' + it.code + '\',\'' +
        esc(it.name).replace(/'/g,"\\'") + '\', this)" title="TODAY에 담기">★</button>' +
      '<span class="rk-name" onclick="openStock(\'' + it.code + '\',\'' +
        esc(it.name).replace(/'/g,"\\'") + '\')">' + esc(it.name) + '</span>' +
      (sub ? '<span class="rk-sub">' + sub + '</span>' : '') +
      '<span class="rk-pct ' + cls + '">' + (it.chg_pct>0?'+':'') +
        it.chg_pct.toFixed(2) + '%</span>' +
      chartBtn(it.code) +
      '</div>';
  }).join('');
  moreLabel(which, items.length);
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

// 순위에서 ★ → TODAY 담기/빼기
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
  render();
  refreshQuotes({force:true});
}

// 네이버 차트 링크
function chartUrl(code){ return 'https://m.stock.naver.com/fchart/domestic/stock/' + code; }
function chartBtn(code){
  return '<a class="chart-ic" href="' + chartUrl(code) + '" target="_blank" ' +
         'onclick="event.stopPropagation()" title="네이버 차트">📈</a>';
}

// ── 🔎 전역 종목 검색 → TODAY에 담기 ──────
const _gs = {timer:null, items:[], sel:-1};

function gsSearch(q){
  if(_composing) return;
  q = (q || '').trim();
  const list = document.getElementById('gs-list');
  if(!list) return;
  if(_gs.timer) clearTimeout(_gs.timer);
  if(!q){ gsClose(); return; }

  if(/^\d{6}$/.test(q)){
    _gs.items = [{code:q, name:q}];
    _gs.sel = 0;
    list.innerHTML = '<div class="gs-item sel" onclick="gsPick(0)">' +
      '<span class="gs-name">종목코드 ' + q + '</span>' +
      '<span class="gs-code">직접 추가</span></div>';
    list.classList.add('open');
    return;
  }

  list.innerHTML = '<div class="gs-msg">검색 중...</div>';
  list.classList.add('open');
  _gs.timer = setTimeout(async () => {
    try {
      const r = await fetch('/api/watchlist/search?q=' + encodeURIComponent(q));
      const d = await r.json();
      const items = d.items || [];
      _gs.items = items; _gs.sel = -1;
      if(!items.length){
        list.innerHTML = '<div class="gs-msg">검색 결과 없음 · 6자리 코드로 직접 입력 가능</div>';
        return;
      }
      list.innerHTML = items.map((it,i) =>
        '<div class="gs-item" data-i="' + i + '" onclick="gsPick(' + i + ')">' +
        '<span class="gs-name">' + esc(it.name) + '</span>' +
        '<span class="gs-code">' + esc(it.code) + '</span>' +
        (isFavCode(it.code) ? '<span class="gs-tag">★ 담김</span>' : '') +
        chartBtn(it.code) +
        '</div>').join('');
    } catch(e){
      list.innerHTML = '<div class="gs-msg">검색 실패 · 6자리 코드로 직접 입력 가능</div>';
    }
  }, 300);
}

function gsKey(e){
  if(_composing || e.isComposing || e.keyCode === 229) return;
  const list = document.getElementById('gs-list');
  if(!_gs.items.length || !list || !list.classList.contains('open')){
    if(e.key === 'Enter'){
      const v = (document.getElementById('gs-input').value || '').trim();
      if(/^\d{6}$/.test(v)){ favStock(v, v, null); document.getElementById('gs-input').value=''; }
    }
    return;
  }
  if(e.key === 'ArrowDown'){ e.preventDefault(); _gs.sel = Math.min(_gs.sel+1, _gs.items.length-1); gsHi(); }
  else if(e.key === 'ArrowUp'){ e.preventDefault(); _gs.sel = Math.max(_gs.sel-1, 0); gsHi(); }
  else if(e.key === 'Enter'){ e.preventDefault(); gsPick(_gs.sel < 0 ? 0 : _gs.sel); }
  else if(e.key === 'Escape'){ gsClose(); }
}

function gsHi(){
  const list = document.getElementById('gs-list');
  if(!list) return;
  list.querySelectorAll('.gs-item').forEach(el => el.classList.remove('sel'));
  const t = list.querySelector('[data-i="' + _gs.sel + '"]');
  if(t){ t.classList.add('sel'); t.scrollIntoView({block:'nearest'}); }
}

function gsPick(i){
  const it = _gs.items[i];
  if(!it) return;
  favStock(it.code, it.name, null);
  const inp = document.getElementById('gs-input');
  if(inp){ inp.value = ''; inp.focus(); }
  gsClose();
}

function gsClose(){
  const list = document.getElementById('gs-list');
  if(list) list.classList.remove('open');
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
    const fl = localStorage.getItem('fav_fluc');
    if(['up','down'].includes(fl)) _fluc = fl;
    const rm = localStorage.getItem('fav_rmkt');
    if(['all','kospi','kosdaq'].includes(rm)) _rankMarket = rm;
    const ex = JSON.parse(localStorage.getItem('fav_exp') || 'null');
    if(ex && typeof ex === 'object') _expand = Object.assign(_expand, ex);
  } catch(e){}
  document.querySelectorAll('.seg[data-mkt]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-mkt') === _market));
  document.querySelectorAll('.seg[data-sess]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-sess') === _session));
  document.querySelectorAll('.seg[data-sort]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-sort') === _sort));
  document.querySelectorAll('.seg[data-fluc]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-fluc') === _fluc));
  document.querySelectorAll('.seg[data-rmkt]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-rmkt') === _rankMarket));

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
loadRanks();
setInterval(() => { if(!document.hidden && !_editing) loadRanks(true); }, 180000);
</script>
</body>
</html>
"""

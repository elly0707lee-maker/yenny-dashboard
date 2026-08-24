"""
관심종목 시황 뷰 (/watchlist)
- 섹터 → 그룹 → 종목 3단 구조
- KIS API 실시간 시세
- 편집 모드 (섹터/그룹/종목 관리)
- 자동 저장
"""

def get_watchlist_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>관심종목 시황 · Yenny Dashboard</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2280%22>📊</text></svg>">
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

.wrap{max-width:1600px;margin:0 auto;padding:16px 24px}
.updated{font-size:11px;color:#7a8099;margin-bottom:10px}

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
    <button class="btn btn-primary" onclick="refreshQuotes()" id="refresh-btn">🔄 시세 갱신</button>
    <button class="btn" onclick="window.print()">🖨️ 인쇄</button>
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
let _quotes = {};         // { code: {price, chg, chg_pct, volume, ...} }
let _saveTimer = null;
let _editing = false;
let _autoRefreshTimer = null;

function genId(){ return 'x' + Math.random().toString(36).slice(2, 10); }
function esc(s){ return String(s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function num(n){ return n === undefined || n === null ? '—' : Number(n).toLocaleString('ko-KR'); }

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
    refreshQuotes();
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

function renderTabs(){
  const el = document.getElementById('sector-tabs');
  el.innerHTML = _data.sectors.map(s => {
    const active = s.id === _data.currentSectorId;
    return '<button class="sector-tab ' + (active?'active':'') + '" onclick="switchSector(\'' + s.id + '\')">' +
           '<span class="sector-tab-name" contenteditable="' + (active && _editing ? 'true' : 'false') + '" onblur="renameSector(\'' + s.id + '\', this)" onkeydown="if(event.key===\'Enter\'){event.preventDefault();this.blur();}">' + esc(s.name) + '</span>' +
           (active && _editing ? ' <button class="btn-mini btn-danger" onclick="event.stopPropagation();deleteSector(\'' + s.id + '\')" style="background:transparent;border:0;color:#fff;padding:2px 4px;">✕</button>' : '') +
           '</button>';
  }).join('');
  if(_editing){
    el.innerHTML += '<button class="sector-add" onclick="addSector()" title="새 섹터">+</button>';
  }
}

function renderBody(){
  const body = document.getElementById('watchlist-body');
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector){
    body.innerHTML = '<span class="content-empty">섹터가 없음. + 눌러서 추가하세요.</span>';
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
}

function renderGroup(sectorId, group){
  let rows = '';
  if(group.stocks && group.stocks.length){
    rows = '<table class="stock-table">' +
      '<thead><tr>' +
      '<th>종목명</th>' +
      '<th class="num">현재가</th>' +
      '<th class="num">등락</th>' +
      '<th class="num">등락률</th>' +
      '<th class="num">거래량</th>' +
      '<th></th>' +
      '</tr></thead><tbody>' +
      group.stocks.map(st => renderStockRow(group.id, st)).join('') +
      '</tbody></table>';
  } else {
    rows = '<div class="content-empty" style="padding:20px">종목 없음</div>';
  }
  return '<div class="group" data-group-id="' + group.id + '">' +
    '<div class="group-header">' +
      '<span class="group-icon">📌</span>' +
      '<span class="group-name" contenteditable="' + (_editing?'true':'false') + '" onblur="renameGroup(\'' + group.id + '\', this)" onkeydown="if(event.key===\'Enter\'){event.preventDefault();this.blur();}">' + esc(group.name) + '</span>' +
      (_editing ? '<span class="group-actions"><button class="btn btn-mini btn-danger" onclick="deleteGroup(\'' + group.id + '\')" title="그룹 삭제">🗑</button></span>' : '') +
    '</div>' +
    rows +
    '<div class="add-stock">' +
      '<input type="text" placeholder="종목코드 6자리 (예: 005930)" id="add-code-' + group.id + '" maxlength="6"/>' +
      '<input type="text" placeholder="종목명 (예: 삼성전자)" id="add-name-' + group.id + '"/>' +
      '<button class="btn btn-primary" onclick="addStock(\'' + group.id + '\')">+ 추가</button>' +
    '</div>' +
    '</div>';
}

function renderStockRow(groupId, st){
  const q = _quotes[st.code] || {};
  const price = q.price !== undefined ? num(q.price) : '—';
  const chg = q.chg !== undefined ? (q.chg > 0 ? '+' : '') + num(q.chg) : '';
  const chgPct = q.chg_pct !== undefined ? (q.chg_pct > 0 ? '+' : '') + q.chg_pct.toFixed(2) + '%' : '';
  const volume = q.volume !== undefined ? num(q.volume) : '—';
  const cls = q.chg_pct > 0 ? 'up' : (q.chg_pct < 0 ? 'down' : 'flat');
  const hotBadge = q.chg_pct !== undefined && Math.abs(q.chg_pct) >= 5
    ? '<span class="hot">🔥</span>' : '';
  return '<tr class="stock-row" data-code="' + st.code + '">' +
    '<td><span class="stock-name">' + esc(st.name) + '</span><span class="stock-code">' + esc(st.code) + '</span>' + hotBadge + '</td>' +
    '<td class="num">' + price + '</td>' +
    '<td class="num ' + cls + '">' + chg + '</td>' +
    '<td class="num ' + cls + '">' + chgPct + '</td>' +
    '<td class="num">' + volume + '</td>' +
    '<td><span class="row-actions"><button class="btn btn-mini btn-danger" onclick="deleteStock(\'' + groupId + '\', \'' + st.code + '\')" title="삭제">✕</button></span></td>' +
    '</tr>';
}

// ── 섹터 관리 ─────────────────────────────
function switchSector(id){
  if(_data.currentSectorId === id) return;
  _data.currentSectorId = id;
  render();
  refreshQuotes();
  scheduleSave();
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
function addStock(groupId){
  const codeEl = document.getElementById('add-code-' + groupId);
  const nameEl = document.getElementById('add-name-' + groupId);
  const code = (codeEl.value || '').trim();
  const name = (nameEl.value || '').trim();
  if(!code || code.length !== 6 || !/^\d{6}$/.test(code)){
    alert('종목코드는 6자리 숫자 (예: 005930)');
    return;
  }
  if(!name){
    alert('종목명을 입력해주세요');
    return;
  }
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector) return;
  const g = sector.groups.find(x => x.id === groupId);
  if(!g) return;
  if(g.stocks.find(s => s.code === code)){
    alert('이미 이 그룹에 있는 종목');
    return;
  }
  g.stocks.push({code, name});
  codeEl.value = '';
  nameEl.value = '';
  render();
  refreshQuotes([code]);
  scheduleSave();
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
async function refreshQuotes(codes){
  const btn = document.getElementById('refresh-btn');
  if(btn){ btn.disabled = true; btn.textContent = '⏳ 조회 중...'; }
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector){ if(btn){ btn.disabled = false; btn.textContent = '🔄 시세 갱신';} return; }
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
      body: JSON.stringify({codes: allCodes})
    });
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    Object.assign(_quotes, data.quotes || {});
    document.getElementById('updated').textContent = '📊 시세 갱신 ' + new Date().toLocaleTimeString('ko-KR');
    renderBody();
  } catch(e){
    document.getElementById('updated').textContent = '⚠️ 시세 조회 실패: ' + e.message;
  } finally {
    if(btn){ btn.disabled = false; btn.textContent = '🔄 시세 갱신'; }
  }
}

// 30초마다 자동 갱신 (탭 활성 시만)
function startAutoRefresh(){
  if(_autoRefreshTimer) clearInterval(_autoRefreshTimer);
  _autoRefreshTimer = setInterval(() => {
    if(document.hidden) return;
    refreshQuotes();
  }, 30000);
}

document.addEventListener('visibilitychange', () => {
  if(!document.hidden) refreshQuotes();
});

loadData();
startAutoRefresh();
</script>
</body>
</html>
"""


def fetch_stock_quotes(codes: list, kis_get_fn) -> dict:
    """KIS API로 여러 종목 시세 조회 (순차, 각각 별도 요청)"""
    quotes = {}
    for code in codes:
        if not code or len(code) != 6:
            continue
        try:
            r = kis_get_fn(
                "/uapi/domestic-stock/v1/quotations/inquire-price",
                "FHKST01010100",
                {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
            )
            out = r.get("output", {}) if isinstance(r, dict) else {}
            if not out:
                continue
            try: price = int(out.get("stck_prpr", 0) or 0)
            except: price = 0
            try: chg = int(out.get("prdy_vrss", 0) or 0)
            except: chg = 0
            try: chg_pct = float(out.get("prdy_ctrt", 0) or 0)
            except: chg_pct = 0
            try: volume = int(out.get("acml_vol", 0) or 0)
            except: volume = 0
            # 부호: 1(상한),2(상승) = +, 4(하한),5(하락) = -
            sign = out.get("prdy_vrss_sign", "3")
            if sign in ("4", "5") and chg > 0:
                chg = -chg
            if sign in ("4", "5") and chg_pct > 0:
                chg_pct = -chg_pct
            quotes[code] = {
                "price": price,
                "chg": chg,
                "chg_pct": chg_pct,
                "volume": volume,
            }
        except Exception as e:
            print(f"[watchlist] {code} 시세 조회 실패: {e}")
    return quotes

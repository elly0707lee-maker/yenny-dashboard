"""
체크포인트 풀 페이지 (/checkpoint)
- 카드 기반 UI
- 카드별 편집
- 드래그 앤 드롭 순서 변경
- 지마켓산스 폰트
- 저장: 텍스트로 재직렬화 → /api/post/checkpoint/replace (봇 호환)
"""

def get_checkpoint_page_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Checkpoint · Yenny Dashboard</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>☑</text></svg>">
<!-- 지마켓산스 (webfontworld) -->
<link rel="stylesheet" href="https://webfontworld.github.io/gmarket/GmarketSans.css">
<!-- SortableJS -->
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:'GmarketSans','GmarketSansMedium',-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans KR',sans-serif;
  background:#fbf9f4;color:#1a1d23;min-height:100vh;
  font-weight:500;letter-spacing:-0.01em;
}
.topbar{background:#1a1d23;color:#e8b84b;padding:14px 24px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}
.topbar-title{font-size:18px;font-weight:700;letter-spacing:.02em}
.topbar-actions{display:flex;gap:10px;align-items:center}
.btn{background:#fff;border:1px solid #e8e1d0;color:#1a1d23;padding:8px 14px;border-radius:8px;font-size:13px;cursor:pointer;font-weight:500;transition:all .12s;font-family:inherit}
.btn:hover{background:#f5efd9;border-color:#e8b84b}
.btn-primary{background:#1a1d23;color:#e8b84b;border-color:#1a1d23}
.btn-primary:hover{background:#2a2d33;color:#e8b84b}
.btn-danger{color:#d63031;border-color:#fab1a0}
.btn-danger:hover{background:#ffe7e4;border-color:#d63031}
.btn-mini{padding:4px 8px;font-size:11px;background:transparent;border:1px solid transparent;color:#7a8099}
.btn-mini:hover{background:#fff;border-color:#e8e1d0;color:#1a1d23}
a.btn{text-decoration:none;display:inline-flex;align-items:center;gap:6px}

.wrap{max-width:1400px;margin:0 auto;padding:24px}
.header-info{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.header-title{font-size:24px;font-weight:700;color:#1a1d23}
.header-date{font-size:14px;color:#7a8099}

.tabs{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:20px;padding-bottom:14px;border-bottom:1px solid #e8e1d0}
.tab{background:#fff;border:1px solid #e8e1d0;color:#1a1d23;padding:8px 16px;border-radius:20px;font-size:13px;cursor:pointer;font-weight:500;transition:all .12s;font-family:inherit}
.tab:hover{background:#f5efd9}
.tab.active{background:#1a1d23;color:#e8b84b;border-color:#1a1d23}

.section{margin-bottom:28px}
.section-heading{
  font-size:15px;color:#1a1d23;font-weight:700;letter-spacing:.02em;
  margin-bottom:10px;padding-bottom:8px;border-bottom:1.5px solid #e8b84b;
}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}

.card{
  background:#fff;border:1px solid #f0e9d8;border-radius:12px;padding:14px 16px;
  transition:all .15s;position:relative;
}
.card:hover{border-color:#e8b84b;box-shadow:0 2px 8px rgba(232,184,75,0.12)}
.card.editing{border-color:#e8b84b;box-shadow:0 0 0 3px rgba(232,184,75,0.15)}
.card.dragging{opacity:0.5;transform:rotate(1deg)}
.card.drag-ghost{background:#f5efd9;border-style:dashed}

.card-header{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.drag-handle{
  cursor:grab;color:#c8c1b0;font-size:14px;padding:2px 4px;user-select:none;
  transition:color .12s;
}
.card:hover .drag-handle{color:#7a8099}
.drag-handle:active{cursor:grabbing}

.card-sub{
  font-size:10px;color:#7a8099;letter-spacing:.08em;font-weight:600;
  text-transform:uppercase;flex-shrink:0;
}
.card-actions{margin-left:auto;display:flex;gap:2px;opacity:0;transition:opacity .12s}
.card:hover .card-actions{opacity:1}

.card-title{
  font-size:16px;font-weight:700;color:#1a1d23;margin-bottom:8px;
  display:flex;align-items:center;gap:6px;line-height:1.4;
}
.card-title[contenteditable]:focus{outline:none;background:#fdfbf5;border-radius:4px;padding:2px 6px;margin:-2px -6px 6px -6px}

.card-body{
  font-size:13px;color:#2d3436;line-height:1.75;white-space:pre-wrap;
}
.card-body[contenteditable]:focus{outline:none;background:#fdfbf5;border-radius:6px;padding:6px 8px;margin:-6px -8px}
.card-body a{color:#0984e3;text-decoration:none}
.card-body a:hover{text-decoration:underline}

.card-save-row{
  display:none;margin-top:10px;padding-top:10px;border-top:1px dashed #e8e1d0;
  gap:6px;
}
.card.editing .card-save-row{display:flex}
.card.editing .card-actions{opacity:0}

.content-empty{
  color:#b2bec3;font-style:italic;display:block;padding:80px 20px;text-align:center;
  font-size:14px;
}

.save-indicator{
  position:fixed;bottom:24px;right:24px;background:#1a1d23;color:#e8b84b;
  padding:10px 18px;border-radius:24px;font-size:12px;font-weight:500;
  opacity:0;transition:opacity .3s;pointer-events:none;z-index:200;
  box-shadow:0 4px 12px rgba(0,0,0,0.15);
}
.save-indicator.visible{opacity:1}

@media print{
  @page{size:A4 landscape;margin:10mm 12mm}
  body{background:#fff}
  .topbar,.tabs,.btn,.card-actions,.drag-handle,.card-save-row,.save-indicator{display:none !important}
  .wrap{max-width:none;padding:0}
  .section-heading{border-bottom:1.5px solid #000 !important}
  .grid{grid-template-columns:repeat(auto-fit,minmax(160px,1fr)) !important;gap:5mm !important}
  .card{page-break-inside:avoid;break-inside:avoid;padding:8px 10px !important;box-shadow:none !important;border:1px solid #999 !important}
  *{-webkit-print-color-adjust:exact !important;print-color-adjust:exact !important}
}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-title">☑ 체크포인트</div>
  <div class="topbar-actions">
    <a href="/" class="btn">← 대시보드</a>
    <button class="btn" onclick="loadCp()">↻ 새로고침</button>
    <button class="btn" onclick="window.print()">🖨️ 인쇄</button>
    <button class="btn btn-danger" onclick="clearAll()">🗑 초기화</button>
  </div>
</div>

<div class="wrap">
  <div class="header-info">
    <div class="header-title">오늘 체크포인트</div>
    <div class="header-date" id="cp-date"></div>
  </div>

  <div class="tabs" id="cp-tabs">
    <button class="tab active" onclick="switchTab(this,'all')">전체</button>
    <button class="tab" onclick="switchTab(this,'indicator')">📊 지표</button>
    <button class="tab" onclick="switchTab(this,'us_market')">🇺🇸 美증시</button>
    <button class="tab" onclick="switchTab(this,'signal')">📡 시그널</button>
    <button class="tab" onclick="switchTab(this,'sector')">📌 Sector</button>
    <button class="tab" onclick="switchTab(this,'kospi')">📌 코스피</button>
    <button class="tab" onclick="switchTab(this,'kosdaq')">📌 코스닥</button>
  </div>

  <div id="cp-body">
    <span class="content-empty">불러오는 중...</span>
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

let _cpDate = '';
let _cards = [];
let _currentTab = 'all';
let _saveTimer = null;

function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

function escPreserve(text){
  text = String(text || '');
  const ph = [];
  const pattern = /<(\/?(?:b|i|u|strong|em)\b|font\s+color\s*=\s*"[^"]*"|\/font|span\s+style\s*=\s*"(?:color|background-color|background)\s*:[^"]*"|\/span)>/gi;
  text = text.replace(pattern, m => { ph.push(m); return '\x00F' + (ph.length - 1) + '\x00'; });
  text = text.replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  text = text.replace(/\x00F(\d+)\x00/g, (_, i) => ph[parseInt(i)]);
  return text;
}

function linkify(text){
  let s = escPreserve(text);
  s = s.replace(/\[\[LINK:([^\]]+)\]\]/g, (_, url) =>
    ' <a href="'+url.replace(/&/g,'&amp;')+'" target="_blank">🔗</a>'
  );
  return s;
}

function genId(){ return 'c' + Math.random().toString(36).slice(2, 10); }

function parseCards(text){
  if(!text) return [];
  const lines = text.split('\n');
  const cards = [];
  let section = null;
  let current = null;

  const flush = () => {
    if(current){
      if(Array.isArray(current.body)) current.body = current.body.join('\n').trim();
      cards.push(current);
      current = null;
    }
  };

  for(const raw of lines){
    const l = raw.trim();
    if(!l){
      if(current && Array.isArray(current.body)) current.body.push('');
      continue;
    }

    if(l.startsWith('📊')){ flush(); section = 'indicator'; continue; }
    if(l.startsWith('🇺🇸')){ flush(); section = 'us_market'; continue; }
    if(l.startsWith('📡')){ flush(); section = 'signal'; continue; }
    if(l.startsWith('📌')){
      flush();
      if(l.includes('Sector') || l.includes('sector') || l.includes('섹터')) section = 'sector';
      else if(l.includes('코스피')) section = 'kospi';
      else if(l.includes('코스닥')) section = 'kosdaq';
      else section = 'other';
      continue;
    }

    if(l.includes('Check Point') || /^\d{1,2}\/\d{1,2}\s+Check/.test(l)) continue;

    if(l.startsWith('✔️')){
      flush();
      current = {id: genId(), section: section || 'sector', kind: '✔️', title: l.slice(2).trim(), body: []};
    } else if(l.startsWith('☑️')){
      flush();
      current = {id: genId(), section: section || 'signal', kind: '☑️', title: l.slice(2).trim(), body: []};
    } else if((section === 'kospi' || section === 'kosdaq') && !l.startsWith('-') && !l.startsWith('•')){
      flush();
      current = {id: genId(), section: section, kind: 'stock', title: l, body: []};
    } else if(section === 'indicator' || section === 'us_market'){
      if(!current || current.kind !== 'text'){
        flush();
        current = {id: genId(), section: section, kind: 'text', title: '', body: []};
      }
      current.body.push(raw);
    } else if(current){
      current.body.push(raw);
    } else if(section){
      current = {id: genId(), section: section, kind: 'text', title: '', body: [raw]};
    }
  }
  flush();
  return cards;
}

function serializeCards(cards, date){
  const order = ['indicator', 'us_market', 'signal', 'sector', 'kospi', 'kosdaq', 'other'];
  const headers = {
    indicator: '📊지표', us_market: '🇺🇸美증시 마감', signal: '📡시장 시그널',
    sector: '📌Sector', kospi: '📌코스피', kosdaq: '📌코스닥', other: '📌기타',
  };
  const bySection = {};
  for(const c of cards){
    const s = c.section || 'other';
    if(!bySection[s]) bySection[s] = [];
    bySection[s].push(c);
  }
  const parts = [`${date || new Date().toISOString().slice(0,10)} Check Point✨`];
  for(const s of order){
    if(!bySection[s]) continue;
    parts.push('');
    parts.push(headers[s]);
    const list = bySection[s];
    for(let i = 0; i < list.length; i++){
      const c = list[i];
      const body = typeof c.body === 'string' ? c.body : (c.body||[]).join('\n');
      if(c.kind === '✔️' || c.kind === '☑️'){
        parts.push(c.kind + (c.title || ''));
        if(body) parts.push(body);
      } else if(c.kind === 'stock'){
        parts.push(c.title || '');
        if(body) parts.push(body);
      } else {
        if(c.title) parts.push(c.title);
        if(body) parts.push(body);
      }
      if((s === 'sector' || s === 'signal' || s === 'kospi' || s === 'kosdaq') && i < list.length - 1){
        parts.push('');
      }
    }
  }
  return parts.join('\n');
}

const SEC_LABEL = {
  indicator: '📊 지표', us_market: '🇺🇸 美증시', signal: '📡 시장 시그널',
  sector: '📌 Sector', kospi: '📌 코스피', kosdaq: '📌 코스닥', other: '📌 기타',
};
const CARD_SUB = {'✔️':'섹터', '☑️':'시그널', 'stock':'종목', 'text':''};

function renderCard(c){
  const bodyText = typeof c.body === 'string' ? c.body : (c.body||[]).join('\n');
  const titleHtml = c.kind === '✔️' ? '✔️ ' + linkify(c.title || '')
                  : c.kind === '☑️' ? '☑️ ' + linkify(c.title || '')
                  : linkify(c.title || '');
  const sub = CARD_SUB[c.kind] || '';
  const hasTitle = c.title !== undefined && c.title !== '' && c.kind !== 'text';
  return `
    <div class="card" data-card-id="${c.id}" data-section="${c.section}">
      <div class="card-header">
        <span class="drag-handle" title="드래그로 이동">⋮⋮</span>
        ${sub ? '<span class="card-sub">'+sub+'</span>' : ''}
        <div class="card-actions">
          <button class="btn btn-mini" onclick="editCard('${c.id}')" title="편집">✏️</button>
          <button class="btn btn-mini" onclick="deleteCard('${c.id}')" title="삭제">🗑</button>
        </div>
      </div>
      ${hasTitle ? `<div class="card-title" data-field="title">${titleHtml}</div>` : ''}
      <div class="card-body" data-field="body">${linkify(bodyText)}</div>
      <div class="card-save-row">
        <button class="btn btn-primary" onclick="saveCardEdit('${c.id}')">💾 저장</button>
        <button class="btn" onclick="cancelCardEdit('${c.id}')">✕ 취소</button>
      </div>
    </div>
  `;
}

function renderSection(sectionKey, cards){
  if(!cards.length) return '';
  const list = cards.map(renderCard).join('');
  return `
    <div class="section">
      <div class="section-heading">${SEC_LABEL[sectionKey] || sectionKey}</div>
      <div class="grid" data-section-key="${sectionKey}">${list}</div>
    </div>
  `;
}

function render(){
  const body = document.getElementById('cp-body');
  if(!_cards.length){
    body.innerHTML = '<span class="content-empty">체크포인트가 비어있음. 봇으로 보내면 여기 표시됨.</span>';
    return;
  }
  const groups = {};
  for(const c of _cards){
    const s = c.section || 'other';
    if(!groups[s]) groups[s] = [];
    groups[s].push(c);
  }
  const order = ['indicator', 'us_market', 'signal', 'sector', 'kospi', 'kosdaq', 'other'];
  let html = '';
  for(const s of order){
    if(!groups[s]) continue;
    if(_currentTab !== 'all' && _currentTab !== s) continue;
    html += renderSection(s, groups[s]);
  }
  body.innerHTML = html || '<span class="content-empty">이 섹션은 비어있음.</span>';
  attachSortable();
}

function attachSortable(){
  document.querySelectorAll('.grid[data-section-key]').forEach(grid => {
    new Sortable(grid, {
      animation: 150,
      handle: '.drag-handle',
      ghostClass: 'drag-ghost',
      dragClass: 'dragging',
      group: 'cards',
      onEnd: () => {
        reorderFromDOM();
        scheduleSave();
      }
    });
  });
}

function reorderFromDOM(){
  const newOrder = [];
  document.querySelectorAll('.grid[data-section-key]').forEach(grid => {
    const sectionKey = grid.getAttribute('data-section-key');
    grid.querySelectorAll('.card').forEach(cardEl => {
      const id = cardEl.getAttribute('data-card-id');
      const c = _cards.find(x => x.id === id);
      if(c){
        c.section = sectionKey;
        newOrder.push(c);
      }
    });
  });
  _cards = newOrder;
}

function editCard(id){
  const card = _cards.find(c => c.id === id);
  if(!card) return;
  const el = document.querySelector('[data-card-id="'+id+'"]');
  if(!el) return;
  el.classList.add('editing');
  const titleEl = el.querySelector('[data-field="title"]');
  const bodyEl = el.querySelector('[data-field="body"]');
  if(titleEl){
    titleEl.setAttribute('contenteditable', 'true');
    titleEl.innerHTML = escPreserve(card.title || '').replace(/\n/g,'<br>');
    titleEl.focus();
  }
  if(bodyEl){
    bodyEl.setAttribute('contenteditable', 'true');
    const bodyText = typeof card.body === 'string' ? card.body : (card.body||[]).join('\n');
    bodyEl.innerHTML = escPreserve(bodyText).replace(/\n/g,'<br>');
  }
  if(!titleEl) bodyEl.focus();
}

function saveCardEdit(id){
  const card = _cards.find(c => c.id === id);
  if(!card) return;
  const el = document.querySelector('[data-card-id="'+id+'"]');
  const titleEl = el.querySelector('[data-field="title"]');
  const bodyEl = el.querySelector('[data-field="body"]');
  const stripHtml = (h) => h.replace(/<div><br><\/div>/gi,'\n').replace(/<div>/gi,'\n').replace(/<\/div>/gi,'').replace(/<br\s*\/?>/gi,'\n').replace(/&nbsp;/gi,' ');
  if(titleEl){
    card.title = stripHtml(titleEl.innerHTML).trim();
  }
  if(bodyEl){
    card.body = stripHtml(bodyEl.innerHTML).trim();
  }
  el.classList.remove('editing');
  render();
  scheduleSave();
}

function cancelCardEdit(id){
  const el = document.querySelector('[data-card-id="'+id+'"]');
  if(el) el.classList.remove('editing');
  render();
}

function deleteCard(id){
  const card = _cards.find(c => c.id === id);
  if(!card) return;
  const preview = (card.title || (typeof card.body === 'string' ? card.body : (card.body||[]).join(' '))).slice(0, 40);
  if(!confirm('이 카드를 삭제할까요?\n"' + preview + '"')) return;
  _cards = _cards.filter(c => c.id !== id);
  render();
  scheduleSave();
}

function switchTab(btn, key){
  document.querySelectorAll('#cp-tabs .tab').forEach(t=>t.classList.remove('active'));
  btn.classList.add('active');
  _currentTab = key;
  render();
}

function scheduleSave(){
  if(_saveTimer) clearTimeout(_saveTimer);
  _saveTimer = setTimeout(saveNow, 800);
}

async function saveNow(){
  const text = serializeCards(_cards, _cpDate);
  try {
    const res = await fetch('/api/post/checkpoint/replace', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: text, date: _cpDate || new Date().toISOString().slice(0,10)})
    });
    if(res.ok) showSaved();
  } catch(e){ console.error('save error', e); }
}

function showSaved(){
  const el = document.getElementById('save-indicator');
  el.textContent = '💾 저장됨 ' + new Date().toLocaleTimeString('ko-KR', {hour:'2-digit',minute:'2-digit'});
  el.classList.add('visible');
  setTimeout(() => el.classList.remove('visible'), 2000);
}

async function loadCp(){
  try {
    const res = await fetch('/api/post/checkpoint');
    if(!res.ok){
      document.getElementById('cp-body').innerHTML = '<span class="content-empty">불러오기 실패 HTTP '+res.status+'</span>';
      return;
    }
    const data = await res.json();
    const text = data.content || '';
    _cpDate = data.date || '';
    document.getElementById('cp-date').textContent = _cpDate;
    _cards = parseCards(text);
    render();
  } catch(e) {
    document.getElementById('cp-body').innerHTML = '<span class="content-empty">에러: '+esc(e.message)+'</span>';
  }
}

async function clearAll(){
  if(!confirm('체크포인트를 전부 비울까요?\n되돌릴 수 없음.')) return;
  try {
    await fetch('/api/post/checkpoint/replace', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: '', date: new Date().toISOString().slice(0,10)})
    });
    _cards = [];
    render();
  } catch(e){ alert('오류: '+e.message); }
}

loadCp();
</script>
</body>
</html>
"""

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
  background:#f8f9fa;color:#1a1d23;min-height:100vh;
  font-weight:500;letter-spacing:-0.01em;
}
/* ✏️ 필기 레이어 */
#draw-layer{
  position:absolute;top:0;left:0;width:100%;
  pointer-events:none;z-index:150;
}
#draw-canvas{display:block;width:100%;}
body.draw-on #draw-layer{pointer-events:auto}
body.draw-on{touch-action:auto}
body.draw-on #draw-canvas{cursor:crosshair}
/* 펜슬 전용 모드에서는 손가락 스크롤이 그대로 되도록 */
body.draw-on.pen-only #draw-layer{touch-action:pan-y}

#draw-toolbar{
  display:none;position:fixed;bottom:20px;left:50%;transform:translateX(-50%);
  background:#1a1d23;border-radius:14px;padding:8px 12px;
  align-items:center;gap:14px;z-index:200;
  box-shadow:0 6px 24px rgba(0,0,0,0.28);
}
body.draw-on #draw-toolbar{display:flex}
.dt-group{display:flex;align-items:center;gap:5px}
.dt-btn{
  background:rgba(255,255,255,0.1);border:0;color:#fff;
  width:34px;height:34px;border-radius:9px;cursor:pointer;
  font-size:15px;font-family:inherit;transition:all .12s;
  display:flex;align-items:center;justify-content:center;
}
.dt-btn:hover{background:rgba(255,255,255,0.22)}
.dt-btn.active{background:#fff;color:#1a1d23}
.dt-color{
  width:22px;height:22px;border-radius:50%;cursor:pointer;
  border:2px solid transparent;transition:all .12s;display:inline-block;
}
.dt-color:hover{transform:scale(1.15)}
.dt-color.active{border-color:#fff;transform:scale(1.15)}
.dt-chk{
  color:#fff;font-size:11px;display:flex;align-items:center;gap:4px;
  cursor:pointer;white-space:nowrap;
}
.dt-close{
  background:transparent;border:0;color:rgba(255,255,255,0.6);
  font-size:15px;cursor:pointer;padding:4px 6px;font-family:inherit;
}
.dt-close:hover{color:#fff}

@media print{
  #draw-toolbar{display:none !important}
  #draw-layer{position:absolute !important;pointer-events:none}
}

.topbar{background:#1a1d23;color:#fff;padding:14px 24px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}
.topbar-title{font-size:18px;font-weight:700;letter-spacing:.02em}
.topbar-actions{display:flex;gap:10px;align-items:center}
.btn{background:#fff;border:1px solid #e5e7eb;color:#1a1d23;padding:8px 14px;border-radius:8px;font-size:13px;cursor:pointer;font-weight:500;transition:all .12s;font-family:inherit}
.btn:hover{background:#f1f3f5;border-color:#1a1d23}
.btn-primary{background:#1a1d23;color:#fff;border-color:#1a1d23}
.btn-primary:hover{background:#2a2d33;color:#fff}
.btn-danger{color:#d63031;border-color:#fab1a0}
.btn-danger:hover{background:#ffe7e4;border-color:#d63031}
.btn-mini{padding:4px 8px;font-size:11px;background:transparent;border:1px solid transparent;color:#7a8099}
.btn-mini:hover{background:#fff;border-color:#e5e7eb;color:#1a1d23}
a.btn{text-decoration:none;display:inline-flex;align-items:center;gap:6px}

.wrap{max-width:1400px;margin:0 auto;padding:24px}
.header-info{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.header-title{font-size:24px;font-weight:700;color:#1a1d23}
.header-date{font-size:14px;color:#7a8099}

.tabs{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:20px;padding-bottom:14px;border-bottom:1px solid #e5e7eb}
.tab{background:#fff;border:1px solid #e5e7eb;color:#1a1d23;padding:8px 16px;border-radius:20px;font-size:13px;cursor:pointer;font-weight:500;transition:all .12s;font-family:inherit}
.tab:hover{background:#f1f3f5}
.tab.active{background:#1a1d23;color:#fff;border-color:#1a1d23}

.section{margin-bottom:28px}
.section-heading{
  font-size:15px;color:#1a1d23;font-weight:700;letter-spacing:.02em;
  margin-bottom:10px;padding-bottom:8px;border-bottom:1.5px solid #1a1d23;
}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}

.card{
  background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:14px 16px;
  transition:all .15s;position:relative;
}
.card:hover{border-color:#1a1d23;box-shadow:0 2px 8px rgba(0,0,0,0.06)}
.card.editing{border-color:#1a1d23;box-shadow:0 0 0 2px rgba(26,29,35,0.1)}
.card.dragging{opacity:0.5;transform:rotate(1deg)}
.card.drag-ghost{background:#f8f9fa;border-style:dashed}

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
.card-title[contenteditable]:focus{outline:none;background:#f8f9fa;border-radius:4px;padding:2px 6px;margin:-2px -6px 6px -6px}

.card-body{
  font-size:13px;color:#2d3436;line-height:1.75;white-space:pre-wrap;
}
.card-body[contenteditable]:focus{outline:none;background:#f8f9fa;border-radius:6px;padding:6px 8px;margin:-6px -8px}
.card-body a{color:#0984e3;text-decoration:none}
.card-body a:hover{text-decoration:underline}

.card-save-row{
  display:none;margin-top:10px;padding-top:10px;border-top:1px dashed #e5e7eb;
  gap:6px;
}
.card.editing .card-save-row{display:flex}
.card.editing .card-actions{opacity:0}

.content-empty{
  color:#b2bec3;font-style:italic;display:block;padding:80px 20px;text-align:center;
  font-size:14px;
}

.save-indicator{
  position:fixed;bottom:24px;right:24px;background:#1a1d23;color:#fff;
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
    <div style="position:relative;display:inline-block;">
      <button class="btn btn-primary" onclick="toggleAddMenu(event)">+ 새 카드 ▾</button>
      <div id="add-menu" style="display:none;position:absolute;top:calc(100% + 4px);right:0;background:#fff;border:1px solid #e5e7eb;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.1);padding:4px;min-width:180px;z-index:200;">
        <button class="btn" style="display:block;width:100%;text-align:left;border:0;background:transparent;padding:8px 12px;margin:0;font-size:12px;" onclick="addNewCard('sector')">✔️ 섹터 카드</button>
        <button class="btn" style="display:block;width:100%;text-align:left;border:0;background:transparent;padding:8px 12px;margin:0;font-size:12px;" onclick="addNewCard('signal')">☑️ 시그널 카드</button>
        <button class="btn" style="display:block;width:100%;text-align:left;border:0;background:transparent;padding:8px 12px;margin:0;font-size:12px;" onclick="addNewCard('kospi')">📌 코스피 종목</button>
        <button class="btn" style="display:block;width:100%;text-align:left;border:0;background:transparent;padding:8px 12px;margin:0;font-size:12px;" onclick="addNewCard('kosdaq')">📌 코스닥 종목</button>
        <button class="btn" style="display:block;width:100%;text-align:left;border:0;background:transparent;padding:8px 12px;margin:0;font-size:12px;" onclick="addNewCard('us_market')">🇺🇸 미증시 항목</button>
      </div>
    </div>
    <button class="btn" onclick="loadCp()">↻ 새로고침</button>
    <button class="btn btn-primary" onclick="manualSave()" id="save-btn" style="display:none;">💾 저장</button>
    <button class="btn" onclick="doPrint()">🖨️ 인쇄</button>
    <button class="btn" onclick="toggleDraw()" id="draw-btn" title="애플펜슬로 화면에 직접 필기">✏️ 필기</button>
    <button class="btn btn-danger" onclick="clearAll()">🗑 초기화</button>
  </div>
</div>

<!-- ✏️ 필기 레이어 -->
<div id="draw-layer">
  <canvas id="draw-canvas"></canvas>
</div>
<div id="draw-toolbar">
  <div class="dt-group">
    <button class="dt-btn active" data-tool="pen" onclick="setTool('pen')" title="펜">✏️</button>
    <button class="dt-btn" data-tool="hi" onclick="setTool('hi')" title="형광펜">🖍️</button>
    <button class="dt-btn" data-tool="eraser" onclick="setTool('eraser')" title="지우개">🧽</button>
  </div>
  <div class="dt-group" id="dt-colors">
    <span class="dt-color active" data-c="#e03131" style="background:#e03131" onclick="setColor('#e03131')"></span>
    <span class="dt-color" data-c="#1971c2" style="background:#1971c2" onclick="setColor('#1971c2')"></span>
    <span class="dt-color" data-c="#2f9e44" style="background:#2f9e44" onclick="setColor('#2f9e44')"></span>
    <span class="dt-color" data-c="#f08c00" style="background:#f08c00" onclick="setColor('#f08c00')"></span>
    <span class="dt-color" data-c="#1a1d23" style="background:#1a1d23" onclick="setColor('#1a1d23')"></span>
  </div>
  <div class="dt-group">
    <button class="dt-btn" data-w="2" onclick="setWidth(2)" title="가늘게">·</button>
    <button class="dt-btn active" data-w="4" onclick="setWidth(4)" title="보통">•</button>
    <button class="dt-btn" data-w="8" onclick="setWidth(8)" title="굵게">●</button>
  </div>
  <div class="dt-group">
    <button class="dt-btn" onclick="undoDraw()" title="되돌리기">↶</button>
    <button class="dt-btn" onclick="clearDraw()" title="전부 지우기">🗑</button>
  </div>
  <div class="dt-group">
    <label class="dt-chk"><input type="checkbox" id="pen-only" checked onchange="togglePenOnly()"/> 펜슬만</label>
  </div>
  <button class="dt-close" onclick="toggleDraw()" title="필기 끄기">✕</button>
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
  // 🆕 파싱 전 HTML 태그 다 제거 (붙여넣기로 들어간 오염 복구)
  //    <p>, <span>, <div>, <br>, style, class 등등 모두 제거
  text = text.replace(/<\/?p\b[^>]*>/gi, '\n');
  text = text.replace(/<\/?div\b[^>]*>/gi, '\n');
  text = text.replace(/<br\s*\/?>/gi, '\n');
  text = text.replace(/<\/?span\b[^>]*>/gi, '');
  text = text.replace(/<\/?font\b[^>]*>/gi, '');
  text = text.replace(/<\/?(strong|b|i|em|u)\b[^>]*>/gi, '');
  // 다른 태그도 그냥 다 제거 (안전)
  text = text.replace(/<[^>]+>/g, '');
  // HTML entity 복원
  text = text.replace(/&amp;/gi, '&').replace(/&lt;/gi, '<').replace(/&gt;/gi, '>').replace(/&quot;/gi, '"').replace(/&#39;/gi, "'").replace(/&nbsp;/gi, ' ');
  // 연속된 빈 줄 정리
  text = text.replace(/\n{3,}/g, '\n\n');

  const lines = text.split('\n');
  const cards = [];
  let section = null;
  let current = null;

  const flush = () => {
    if(current){
      if(Array.isArray(current.body)) current.body = current.body.join('\n').trim();
      // 병합: title 없이 body만 있는 text 카드가 앞 카드 바로 뒤 + 같은 섹션이면 → 앞 카드에 흡수
      const last = cards[cards.length - 1];
      const isOrphanText = current.kind === 'text' && !current.title && current.body;
      const canMerge = last && last.section === current.section
                       && (last.kind === '✔️' || last.kind === '☑️' || last.kind === 'stock');
      if(isOrphanText && canMerge){
        const lastBody = typeof last.body === 'string' ? last.body : (last.body||[]).join('\n');
        last.body = (lastBody ? lastBody + '\n' : '') + current.body;
      } else {
        cards.push(current);
      }
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

    // ✔️ / ☑️ 감지 (variation selector 있건 없건)
    if(l.startsWith('✔')){
      flush();
      const title = l.replace(/^✔️?\s*/, '').trim();
      current = {id: genId(), section: section || 'sector', kind: '✔️', title: title, body: []};
    } else if(l.startsWith('☑')){
      flush();
      const title = l.replace(/^☑️?\s*/, '').trim();
      current = {id: genId(), section: section || 'signal', kind: '☑️', title: title, body: []};
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
        parts.push(c.kind + (c.title ? ' ' + c.title : ''));
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
  if(_drawOn){ resizeCanvas(); redraw(); }
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
  // 🆕 paste 시 plain text만 (서식·HTML 태그 다 제거)
  const stripPaste = (e) => {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData('text/plain');
    document.execCommand('insertText', false, text);
  };
  if(titleEl){
    titleEl.setAttribute('contenteditable', 'true');
    titleEl.innerHTML = escPreserve(card.title || '').replace(/\n/g,'<br>');
    titleEl.addEventListener('paste', stripPaste);
    titleEl.focus();
  }
  if(bodyEl){
    bodyEl.setAttribute('contenteditable', 'true');
    const bodyText = typeof card.body === 'string' ? card.body : (card.body||[]).join('\n');
    bodyEl.innerHTML = escPreserve(bodyText).replace(/\n/g,'<br>');
    bodyEl.addEventListener('paste', stripPaste);
  }
  if(!titleEl) bodyEl.focus();
}

function saveCardEdit(id){
  const card = _cards.find(c => c.id === id);
  if(!card) return;
  const el = document.querySelector('[data-card-id="'+id+'"]');
  const titleEl = el.querySelector('[data-field="title"]');
  const bodyEl = el.querySelector('[data-field="body"]');
  // 🆕 innerText로 저장 (HTML 태그·인라인 스타일 무시)
  if(titleEl){
    card.title = (titleEl.innerText || '').trim();
  }
  if(bodyEl){
    card.body = (bodyEl.innerText || '').trim();
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
  // 🆕 자동 저장 X — dirty 표시만
  markDirty();
}

// 🆕 미저장 변경 표시
let _dirty = false;
function markDirty(){
  _dirty = true;
  const btn = document.getElementById('save-btn');
  if(btn){
    btn.style.display = '';
    btn.textContent = '💾 저장 (미저장)';
    btn.classList.add('btn-danger');
    btn.classList.remove('btn-primary');
  }
}
function clearDirty(){
  _dirty = false;
  const btn = document.getElementById('save-btn');
  if(btn){
    btn.style.display = 'none';
    btn.textContent = '💾 저장';
    btn.classList.remove('btn-danger');
    btn.classList.add('btn-primary');
  }
}

// 명시적 저장 (사용자 클릭)
async function manualSave(){
  const newText = serializeCards(_cards, _cpDate);
  const origLen = (_lastLoadedText || '').length;
  const newLen = newText.length;
  // 🆕 손실 감지 — 원본보다 30% 이상 줄어들면 경고
  if(origLen > 100 && newLen < origLen * 0.7){
    if(!confirm(
      '⚠️ 저장 시 내용이 크게 줄어들 것 같습니다.\n\n' +
      '원본: ' + origLen + '자\n' +
      '저장 후: ' + newLen + '자\n\n' +
      '파서가 일부 카드를 인식 못했을 가능성. 정말 저장할까요?\n' +
      '(취소하면 편집 내용은 유지되지만 서버는 안 바뀜)'
    )) return;
  }
  await saveNow(newText);
}

// 실제 서버 저장 (manualSave에서 호출)
async function saveNow(text){
  text = text || serializeCards(_cards, _cpDate);
  try {
    const res = await fetch('/api/post/checkpoint/replace', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: text, date: _cpDate || new Date().toISOString().slice(0,10)})
    });
    if(res.ok){
      _lastLoadedText = text;
      _lastSaveAt = Date.now();
      clearDirty();
      showSaved();
    } else {
      alert('저장 실패 HTTP ' + res.status);
    }
  } catch(e){
    alert('저장 오류: ' + e.message);
  }
}

function showSaved(msg){
  const el = document.getElementById('save-indicator');
  el.textContent = msg || ('💾 저장됨 ' + new Date().toLocaleTimeString('ko-KR', {hour:'2-digit',minute:'2-digit'}));
  el.classList.add('visible');
  setTimeout(() => el.classList.remove('visible'), 2000);
}

// ── ✏️ 화면 필기 (애플펜슬) ──────────────────
let _drawOn = false;
let _tool = 'pen';
let _color = '#e03131';
let _width = 4;
let _penOnly = true;
let _strokes = [];        // [{tool,color,width,pts:[{x,y,p}]}]
let _cur = null;
let _drawSaveTimer = null;
let _canvasH = 0;

function drawCanvas(){ return document.getElementById('draw-canvas'); }

function toggleDraw(){
  _drawOn = !_drawOn;
  document.body.classList.toggle('draw-on', _drawOn);
  document.body.classList.toggle('pen-only', _penOnly);
  const b = document.getElementById('draw-btn');
  if(b){
    b.textContent = _drawOn ? '✓ 필기 끄기' : '✏️ 필기';
    b.classList.toggle('btn-primary', _drawOn);
  }
  if(_drawOn){ resizeCanvas(); redraw(); }
}

function setTool(t){
  _tool = t;
  document.querySelectorAll('.dt-btn[data-tool]').forEach(b =>
    b.classList.toggle('active', b.getAttribute('data-tool') === t));
  const cw = document.getElementById('dt-colors');
  if(cw) cw.style.opacity = (t === 'eraser') ? '0.35' : '1';
}
function setColor(c){
  _color = c;
  document.querySelectorAll('.dt-color').forEach(el =>
    el.classList.toggle('active', el.getAttribute('data-c') === c));
  if(_tool === 'eraser') setTool('pen');
}
function setWidth(w){
  _width = w;
  document.querySelectorAll('.dt-btn[data-w]').forEach(b =>
    b.classList.toggle('active', +b.getAttribute('data-w') === w));
}
function togglePenOnly(){
  _penOnly = document.getElementById('pen-only').checked;
  document.body.classList.toggle('pen-only', _penOnly);
}

// 문서 전체 높이에 맞춰 캔버스 크기 조정 (스크롤해도 그림이 붙어 있게)
function resizeCanvas(){
  const cv = drawCanvas();
  if(!cv) return;
  const h = Math.max(document.body.scrollHeight, window.innerHeight);
  const w = document.documentElement.clientWidth;
  const dpr = window.devicePixelRatio || 1;
  _canvasH = h;
  cv.style.height = h + 'px';
  cv.width = Math.round(w * dpr);
  cv.height = Math.round(h * dpr);
  const ctx = cv.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
}

function redraw(){
  const cv = drawCanvas();
  if(!cv) return;
  const ctx = cv.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  ctx.clearRect(0, 0, cv.width / dpr, cv.height / dpr);
  for(const s of _strokes) drawStroke(ctx, s);
}

function drawStroke(ctx, s){
  const pts = s.pts || [];
  if(pts.length < 1) return;
  ctx.save();
  if(s.tool === 'eraser'){
    ctx.globalCompositeOperation = 'destination-out';
    ctx.strokeStyle = 'rgba(0,0,0,1)';
    ctx.lineWidth = s.width * 6;
  } else if(s.tool === 'hi'){
    ctx.globalCompositeOperation = 'multiply';
    ctx.strokeStyle = s.color;
    ctx.globalAlpha = 0.32;
    ctx.lineWidth = s.width * 4;
  } else {
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = s.color;
    ctx.lineWidth = s.width;
  }
  if(pts.length === 1){
    ctx.beginPath();
    ctx.arc(pts[0].x, pts[0].y, ctx.lineWidth / 2, 0, Math.PI * 2);
    ctx.fillStyle = ctx.strokeStyle;
    ctx.fill();
    ctx.restore();
    return;
  }
  // 필압 반영 — 구간별로 굵기를 달리해 그림
  const base = ctx.lineWidth;
  for(let i = 1; i < pts.length; i++){
    const a = pts[i-1], b = pts[i];
    if(s.tool === 'pen'){
      const p = (a.p + b.p) / 2 || 0.5;
      ctx.lineWidth = base * (0.4 + p * 1.2);
    }
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  ctx.restore();
}

function ptFrom(e){
  const cv = drawCanvas();
  const r = cv.getBoundingClientRect();
  return {
    x: e.clientX - r.left,
    y: e.clientY - r.top,
    p: (e.pressure && e.pressure > 0) ? e.pressure : 0.5,
  };
}

function initDraw(){
  const cv = drawCanvas();
  if(!cv) return;
  const ctx = cv.getContext('2d');

  cv.addEventListener('pointerdown', (e) => {
    if(!_drawOn) return;
    if(_penOnly && e.pointerType !== 'pen') return;   // 손가락은 스크롤용
    e.preventDefault();
    cv.setPointerCapture(e.pointerId);
    _cur = {tool: _tool, color: _color, width: _width, pts: [ptFrom(e)]};
    _strokes.push(_cur);
  });

  cv.addEventListener('pointermove', (e) => {
    if(!_drawOn || !_cur) return;
    if(_penOnly && e.pointerType !== 'pen') return;
    e.preventDefault();
    // 고해상도 이벤트가 있으면 다 반영 (선이 매끄러워짐)
    const evs = (e.getCoalescedEvents ? e.getCoalescedEvents() : null) || [e];
    for(const ev of evs) _cur.pts.push(ptFrom(ev));
    // 마지막 구간만 그려서 부담 줄임
    drawStroke(ctx, {tool:_cur.tool, color:_cur.color, width:_cur.width,
                     pts:_cur.pts.slice(-Math.min(evs.length + 1, _cur.pts.length))});
  });

  const endStroke = (e) => {
    if(!_cur) return;
    _cur = null;
    scheduleDrawSave();
  };
  cv.addEventListener('pointerup', endStroke);
  cv.addEventListener('pointercancel', endStroke);
  cv.addEventListener('pointerleave', endStroke);

  window.addEventListener('resize', () => {
    if(!_drawOn) return;
    resizeCanvas(); redraw();
  });
}

function undoDraw(){
  if(!_strokes.length) return;
  _strokes.pop();
  redraw();
  scheduleDrawSave();
}

function clearDraw(){
  if(!_strokes.length) return;
  if(!confirm('필기를 전부 지울까요?')) return;
  _strokes = [];
  redraw();
  scheduleDrawSave();
}

function scheduleDrawSave(){
  if(_drawSaveTimer) clearTimeout(_drawSaveTimer);
  _drawSaveTimer = setTimeout(saveDraw, 1200);
}

async function saveDraw(){
  try {
    // 좌표를 소수점 1자리로 줄여 용량 절약
    const compact = _strokes.map(s => ({
      t: s.tool, c: s.color, w: s.width,
      p: s.pts.map(p => [Math.round(p.x*10)/10, Math.round(p.y*10)/10, Math.round(p.p*100)/100]),
    }));
    const payload = {version: 1, h: _canvasH, strokes: compact};
    await fetch('/api/post/cpdraw', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: JSON.stringify(payload),
                            date: new Date().toISOString().slice(0,10)})
    });
  } catch(e){ console.error('draw save', e); }
}

async function loadDraw(){
  try {
    const res = await fetch('/api/post/cpdraw');
    if(!res.ok) return;
    const d = await res.json();
    if(!d || !d.content) return;
    const payload = JSON.parse(d.content);
    _strokes = (payload.strokes || []).map(s => ({
      tool: s.t, color: s.c, width: s.w,
      pts: (s.p || []).map(a => ({x: a[0], y: a[1], p: a[2]})),
    }));
    resizeCanvas();
    redraw();
  } catch(e){}
}

initDraw();
setTimeout(() => { resizeCanvas(); loadDraw(); }, 300);

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
    _lastLoadedText = text;
    clearDirty();
    render();
  } catch(e) {
    document.getElementById('cp-body').innerHTML = '<span class="content-empty">에러: '+esc(e.message)+'</span>';
  }
}

// 🆕 상시 리프레시 — 봇이 새 조각 보내면 자동 반영
let _lastLoadedText = '';
let _lastSaveAt = 0;

async function quietPoll(){
  // 편집 중이거나 미저장 변경이 있으면 skip
  if(document.querySelector('.card.editing')) return;
  if(_dirty) return;
  // 방금 저장 완료 후 3초 안이면 skip
  if(Date.now() - _lastSaveAt < 3000) return;
  try {
    const res = await fetch('/api/post/checkpoint');
    if(!res.ok) return;
    const data = await res.json();
    const text = data.content || '';
    if(text === _lastLoadedText) return;
    const scrollY = window.scrollY;
    _lastLoadedText = text;
    _cpDate = data.date || '';
    document.getElementById('cp-date').textContent = _cpDate;
    _cards = parseCards(text);
    render();
    window.scrollTo(0, scrollY);
    showSaved('🔄 봇 업데이트 반영');
  } catch(e){}
}
// 5초마다 폴링
setInterval(quietPoll, 5000);

// 🆕 새 카드 추가
function toggleAddMenu(e){
  if(e) e.stopPropagation();
  const menu = document.getElementById('add-menu');
  menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}
document.addEventListener('click', () => {
  const menu = document.getElementById('add-menu');
  if(menu) menu.style.display = 'none';
});

function addNewCard(sectionType){
  const menu = document.getElementById('add-menu');
  if(menu) menu.style.display = 'none';
  const kindMap = {sector:'✔️', signal:'☑️', kospi:'stock', kosdaq:'stock', us_market:'☑️'};
  const kind = kindMap[sectionType] || '✔️';
  const newCard = {
    id: genId(),
    section: sectionType,
    kind: kind,
    title: '',
    body: '',
  };
  // 그 섹션 맨 뒤에 추가
  const lastIdxOfSection = (() => {
    let idx = -1;
    for(let i = 0; i < _cards.length; i++){
      if(_cards[i].section === sectionType) idx = i;
    }
    return idx;
  })();
  if(lastIdxOfSection >= 0){
    _cards.splice(lastIdxOfSection + 1, 0, newCard);
  } else {
    _cards.push(newCard);
  }
  render();
  scheduleSave();
  // 새 카드 편집 모드로 자동 진입
  setTimeout(() => {
    editCard(newCard.id);
    // 스크롤도 그 카드로
    const el = document.querySelector('[data-card-id="'+newCard.id+'"]');
    if(el) el.scrollIntoView({behavior:'smooth', block:'center'});
  }, 100);
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

// 🆕 인쇄 — 어떤 탭 보고 있든 무조건 전체 표시로 인쇄
function doPrint(){
  const originalTab = _currentTab;
  _currentTab = 'all';
  render();
  // 렌더링 완료 후 인쇄
  setTimeout(() => {
    window.print();
    // 인쇄 다이얼로그 닫힌 후 원래 탭으로 복원
    setTimeout(() => {
      _currentTab = originalTab;
      // 활성 탭 UI 복원
      document.querySelectorAll('#cp-tabs .tab').forEach(t => {
        t.classList.remove('active');
        if(t.textContent.includes(SEC_LABEL[originalTab]) || (originalTab === 'all' && t.textContent === '전체')){
          t.classList.add('active');
        }
      });
      render();
    }, 500);
  }, 200);
}

loadCp();
</script>
</body>
</html>
"""

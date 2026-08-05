"""
질문 보드 (/postit)
- 무한 캔버스 위에 포스트잇 자유 배치
- 6가지 색상 · S/M/L 사이즈 · 제목/소제목/본문 3계층
- 드래그 이동 · 리사이즈 · 자동 저장
- 인쇄 시 배경 색깔 유지 (흑백에서도 좌측 바 패턴으로 구분)
"""

def get_postit_board_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>질문 보드 · Yenny Dashboard</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2280%22>🗂️</text></svg>">
<link rel="stylesheet" href="https://webfontworld.github.io/gmarket/GmarketSans.css">
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{overflow:hidden;height:100%}
body{
  font-family:'GmarketSans','GmarketSansMedium',-apple-system,'Segoe UI','Noto Sans KR',sans-serif;
  background:#f8f9fa;color:#1a1d23;
  font-weight:500;letter-spacing:-0.01em;
}
.topbar{background:#1a1d23;color:#fff;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;position:fixed;top:0;left:0;right:0;z-index:100;height:56px}
.topbar-title{font-size:16px;font-weight:700}
.topbar-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.btn{background:#fff;border:1px solid #e5e7eb;color:#1a1d23;padding:6px 12px;border-radius:7px;font-size:12px;cursor:pointer;font-weight:500;font-family:inherit;transition:all .12s}
.btn:hover{background:#f1f3f5;border-color:#1a1d23}
.btn-primary{background:#1a1d23;color:#fff;border-color:#1a1d23;font-weight:700}
.btn-primary:hover{background:#2a2d33}
.btn-danger{color:#d63031;border-color:#fab1a0}
.btn-danger:hover{background:#ffe7e4}
a.btn{text-decoration:none;display:inline-flex;align-items:center;gap:4px}

/* 캔버스 */
.canvas-wrap{position:absolute;top:56px;left:0;right:0;bottom:0;overflow:auto;background:#eceff1}
.canvas{position:relative;width:4000px;height:3000px;background:#ffffff;background-image:
  linear-gradient(rgba(0,0,0,0.04) 1px, transparent 1px),
  linear-gradient(90deg, rgba(0,0,0,0.04) 1px, transparent 1px);
  background-size:24px 24px;
}

/* 포스트잇 */
.postit{
  position:absolute;
  background:#fff59d;
  border:1px solid rgba(0,0,0,0.08);
  border-left:6px solid #e6c33d;
  border-radius:2px;
  box-shadow:2px 3px 8px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.03);
  padding:14px 14px 30px 14px;
  cursor:move;
  transition:box-shadow .15s;
  user-select:none;
  overflow:hidden;
}
.postit:hover{box-shadow:3px 5px 14px rgba(0,0,0,0.2)}
.postit.dragging{opacity:0.85;box-shadow:5px 8px 20px rgba(0,0,0,0.25);z-index:50}
.postit.editing{box-shadow:0 0 0 3px #1a1d23, 3px 5px 14px rgba(0,0,0,0.2);z-index:60}

.postit-title{
  font-size:18px;font-weight:700;line-height:1.35;color:#1a1d23;
  margin-bottom:6px;outline:none;min-height:1.4em;cursor:text;
}
.postit-title:empty::before{content:'제목';color:rgba(0,0,0,0.25);font-weight:500}
.postit-subtitle{
  font-size:14px;font-weight:600;line-height:1.4;color:#333;
  margin-bottom:8px;outline:none;min-height:1.3em;cursor:text;
}
.postit-subtitle:empty::before{content:'소제목';color:rgba(0,0,0,0.25);font-weight:500}
.postit-body{
  font-size:13px;font-weight:500;line-height:1.55;color:#2d3436;
  outline:none;min-height:3em;cursor:text;white-space:pre-wrap;
}
.postit-body:empty::before{content:'내용을 입력...';color:rgba(0,0,0,0.25)}

/* 컨트롤 */
.postit-controls{
  position:absolute;bottom:4px;left:4px;right:4px;
  display:flex;gap:2px;align-items:center;justify-content:space-between;
  opacity:0;transition:opacity .15s;font-size:10px;
}
.postit:hover .postit-controls,
.postit.editing .postit-controls{opacity:1}
.postit-controls .swatches{display:flex;gap:2px}
.swatch{
  width:14px;height:14px;border-radius:3px;cursor:pointer;
  border:1px solid rgba(0,0,0,0.15);transition:transform .1s;
}
.swatch:hover{transform:scale(1.2)}
.postit-controls .sizes{display:flex;gap:2px}
.size-btn{
  padding:2px 6px;font-size:9px;background:rgba(255,255,255,0.7);
  border:1px solid rgba(0,0,0,0.15);border-radius:3px;cursor:pointer;
  font-family:inherit;font-weight:700;color:#333;
}
.size-btn:hover{background:#fff}
.size-btn.active{background:#1a1d23;color:#fff;border-color:#1a1d23}
.postit-delete{
  padding:2px 6px;font-size:11px;background:rgba(255,255,255,0.7);
  border:1px solid rgba(0,0,0,0.15);border-radius:3px;cursor:pointer;color:#d63031;
}
.postit-delete:hover{background:#ffe7e4}

/* 리사이즈 핸들 */
.resize-handle{
  position:absolute;bottom:0;right:0;width:14px;height:14px;
  cursor:nwse-resize;opacity:0.3;
  background:linear-gradient(135deg, transparent 0%, transparent 40%, rgba(0,0,0,0.3) 40%, rgba(0,0,0,0.3) 55%, transparent 55%, transparent 75%, rgba(0,0,0,0.3) 75%, rgba(0,0,0,0.3) 90%, transparent 90%);
}
.postit:hover .resize-handle{opacity:0.5}

/* 삭제 X 버튼 (우상단, 항상 표시) */
.postit-x{
  position:absolute;top:5px;right:5px;
  width:22px;height:22px;
  background:rgba(255,255,255,0.75);
  border:1px solid rgba(0,0,0,0.15);
  border-radius:50%;color:#d63031;
  font-size:13px;font-weight:bold;line-height:1;
  cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  opacity:0.35;transition:all .15s;z-index:2;
}
.postit:hover .postit-x{opacity:1}
.postit-x:hover{background:#ffe7e4;border-color:#d63031;transform:scale(1.1)}

/* 색상 정의 (배경 + 좌측 바 색 + 흑백 대비용 패턴) */
.postit[data-color="yellow"]{background:#fff59d;border-left-color:#e6c33d}
.postit[data-color="pink"]{background:#f8bbd0;border-left-color:#ec7ba1}
.postit[data-color="blue"]{background:#b3e5fc;border-left-color:#4fc3f7}
.postit[data-color="green"]{background:#c8e6c9;border-left-color:#81c784}
.postit[data-color="purple"]{background:#d1c4e9;border-left-color:#9575cd}
.postit[data-color="orange"]{background:#ffccbc;border-left-color:#ff8a65}

/* 사이즈 */
.postit[data-size="s"]{width:180px;min-height:140px}
.postit[data-size="s"] .postit-title{font-size:15px}
.postit[data-size="s"] .postit-subtitle{font-size:12px}
.postit[data-size="s"] .postit-body{font-size:11px}
.postit[data-size="m"]{width:240px;min-height:200px}
.postit[data-size="l"]{width:340px;min-height:280px}
.postit[data-size="l"] .postit-title{font-size:22px}
.postit[data-size="l"] .postit-subtitle{font-size:16px}
.postit[data-size="l"] .postit-body{font-size:14px}
/* 🆕 W (Wide) — 가로형, 헤드라인 스타일 */
.postit[data-size="w"]{width:420px;min-height:150px}
.postit[data-size="w"] .postit-title{font-size:20px}
.postit[data-size="w"] .postit-subtitle{font-size:14px}
.postit[data-size="w"] .postit-body{font-size:13px}

/* 팔레트 (좌하단) */
.new-note-tray{
  position:fixed;bottom:20px;left:20px;
  background:#1a1d23;border-radius:12px;padding:10px 12px;
  display:flex;gap:8px;align-items:center;z-index:90;
  box-shadow:0 4px 16px rgba(0,0,0,0.2);
}
.new-note-tray-label{color:#fff;font-size:11px;font-weight:600;margin-right:4px}
.new-swatch{
  width:24px;height:24px;border-radius:5px;cursor:pointer;
  border:2px solid rgba(255,255,255,0.15);transition:transform .1s;
}
.new-swatch:hover{transform:scale(1.15);border-color:#fff}

/* 저장 표시 */
.save-indicator{
  position:fixed;bottom:24px;right:24px;background:#1a1d23;color:#fff;
  padding:8px 16px;border-radius:20px;font-size:11px;font-weight:500;
  opacity:0;transition:opacity .3s;pointer-events:none;z-index:200;
  box-shadow:0 4px 12px rgba(0,0,0,0.15);
}
.save-indicator.visible{opacity:1}

/* 안내 */
.empty-hint{
  position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  color:#b2bec3;font-size:14px;text-align:center;line-height:1.7;
  pointer-events:none;
}

/* 인쇄 */
@media print{
  @page{size:A4 landscape;margin:8mm}
  html,body{overflow:visible !important;height:auto !important}
  .topbar,.new-note-tray,.save-indicator,.postit-controls,.resize-handle,.empty-hint{display:none !important}
  .canvas-wrap{position:static !important;overflow:visible !important;background:#fff !important}
  .canvas{background-image:none !important;width:100% !important;height:auto !important;min-height:0 !important}
  .postit{
    box-shadow:none !important;
    border:1px solid #333 !important;
    /* 좌측 바 굵기 색깔로 구분 */
    border-left-width:8px !important;
    page-break-inside:avoid;break-inside:avoid;
  }
  /* 색깔 그대로 인쇄 */
  *{-webkit-print-color-adjust:exact !important;print-color-adjust:exact !important}
}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-title">🗂️ 질문 보드</div>
  <div class="topbar-actions">
    <a href="/" class="btn">← 대시보드</a>
    <button class="btn btn-primary" onclick="addNoteAtCenter()" title="새 포스트잇">+ 새 포스트잇</button>
    <button class="btn" onclick="window.print()">🖨️ 인쇄</button>
    <button class="btn btn-danger" onclick="clearAll()">🗑 초기화</button>
  </div>
</div>

<div class="canvas-wrap" id="canvas-wrap">
  <div class="canvas" id="canvas">
    <div class="empty-hint" id="empty-hint">
      🗂️ 비어있음<br>
      상단 '+ 새 포스트잇' 클릭하거나<br>
      좌하단 팔레트에서 색상 선택
    </div>
  </div>
</div>

<div class="new-note-tray">
  <span class="new-note-tray-label">+ 새 포스트잇:</span>
  <div class="new-swatch" style="background:#fff59d" onclick="addNoteAtCenter('yellow')" title="노랑"></div>
  <div class="new-swatch" style="background:#f8bbd0" onclick="addNoteAtCenter('pink')" title="분홍"></div>
  <div class="new-swatch" style="background:#b3e5fc" onclick="addNoteAtCenter('blue')" title="하늘"></div>
  <div class="new-swatch" style="background:#c8e6c9" onclick="addNoteAtCenter('green')" title="민트"></div>
  <div class="new-swatch" style="background:#d1c4e9" onclick="addNoteAtCenter('purple')" title="라벤더"></div>
  <div class="new-swatch" style="background:#ffccbc" onclick="addNoteAtCenter('orange')" title="살구"></div>
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

let _notes = [];
let _saveTimer = null;
let _maxZ = 100;   // 🆕 z-index 최대값 추적
const COLORS = ['yellow','pink','blue','green','purple','orange'];

function genId(){ return 'n' + Math.random().toString(36).slice(2, 10); }

function esc(s){ return String(s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

// 🆕 특정 포스트잇을 맨 앞으로 (마지막 클릭한 게 제일 위)
function bringToFront(el, n){
  _maxZ++;
  el.style.zIndex = _maxZ;
  n.z = _maxZ;
  scheduleSave();
}

function scheduleSave(){
  if(_saveTimer) clearTimeout(_saveTimer);
  _saveTimer = setTimeout(saveNow, 800);
}

async function saveNow(){
  try {
    const res = await fetch('/api/post/postit', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: JSON.stringify(_notes), date: new Date().toISOString().slice(0,10)})
    });
    if(res.ok) showSaved();
  } catch(e){ console.error(e); }
}

function showSaved(){
  const el = document.getElementById('save-indicator');
  el.textContent = '💾 저장됨 ' + new Date().toLocaleTimeString('ko-KR', {hour:'2-digit',minute:'2-digit'});
  el.classList.add('visible');
  setTimeout(() => el.classList.remove('visible'), 1800);
}

async function loadNotes(){
  try {
    const res = await fetch('/api/post/postit');
    if(!res.ok) return;
    const data = await res.json();
    if(!data || !data.content) return;
    try {
      _notes = JSON.parse(data.content) || [];
    } catch(e){ _notes = []; }
    renderAll();
  } catch(e){}
}

function renderAll(){
  const canvas = document.getElementById('canvas');
  // 기존 포스트잇 제거 (empty-hint 유지)
  canvas.querySelectorAll('.postit').forEach(el => el.remove());
  const hint = document.getElementById('empty-hint');
  if(hint) hint.style.display = _notes.length === 0 ? '' : 'none';
  for(const n of _notes){
    canvas.appendChild(makeNoteEl(n));
  }
}

function makeNoteEl(n){
  const el = document.createElement('div');
  el.className = 'postit';
  el.setAttribute('data-note-id', n.id);
  el.setAttribute('data-color', n.color || 'yellow');
  el.setAttribute('data-size', n.size || 'm');
  el.style.left = (n.x || 100) + 'px';
  el.style.top = (n.y || 100) + 'px';
  if(n.width) el.style.width = n.width + 'px';
  if(n.height) el.style.height = n.height + 'px';
  // z-index 적용
  if(n.z){ el.style.zIndex = n.z; if(n.z > _maxZ) _maxZ = n.z; }

  el.innerHTML = `
    <button class="postit-x" onclick="deleteNote('${n.id}')" title="삭제">✕</button>
    <div class="postit-title" contenteditable="true" data-field="title">${esc(n.title||'')}</div>
    <div class="postit-subtitle" contenteditable="true" data-field="subtitle">${esc(n.subtitle||'')}</div>
    <div class="postit-body" contenteditable="true" data-field="body">${esc(n.body||'')}</div>
    <div class="postit-controls">
      <div class="swatches">
        ${COLORS.map(c => `<div class="swatch" style="background:${colorHex(c)}" onclick="setColor('${n.id}','${c}')"></div>`).join('')}
      </div>
      <div class="sizes">
        <button class="size-btn ${n.size==='s'?'active':''}" onclick="setSize('${n.id}','s')">S</button>
        <button class="size-btn ${(n.size||'m')==='m'?'active':''}" onclick="setSize('${n.id}','m')">M</button>
        <button class="size-btn ${n.size==='l'?'active':''}" onclick="setSize('${n.id}','l')">L</button>
        <button class="size-btn ${n.size==='w'?'active':''}" onclick="setSize('${n.id}','w')" title="가로형">W</button>
      </div>
    </div>
    <div class="resize-handle" data-resize-for="${n.id}"></div>
  `;

  attachInteractions(el, n);
  return el;
}

function colorHex(c){
  return {yellow:'#fff59d', pink:'#f8bbd0', blue:'#b3e5fc', green:'#c8e6c9', purple:'#d1c4e9', orange:'#ffccbc'}[c];
}

function attachInteractions(el, n){
  // 편집 필드 → 저장 시 스타일링
  el.querySelectorAll('[contenteditable]').forEach(field => {
    const key = field.getAttribute('data-field');
    field.addEventListener('input', () => {
      n[key] = field.innerText;
      scheduleSave();
    });
    field.addEventListener('focus', () => {
      el.classList.add('editing');
      bringToFront(el, n);
    });
    field.addEventListener('blur', () => el.classList.remove('editing'));
    // 편집 중 드래그 방지
    field.addEventListener('mousedown', e => e.stopPropagation());
  });

  // 드래그 (헤더 부분 + 배경)
  el.addEventListener('mousedown', (e) => {
    if(e.target.closest('[contenteditable]')) return;
    if(e.target.closest('.postit-controls')) return;
    if(e.target.closest('.resize-handle')) return;
    if(e.target.closest('.postit-x')) return;
    e.preventDefault();
    // 🆕 클릭한 순간 맨 앞으로
    bringToFront(el, n);
    const startX = e.pageX;
    const startY = e.pageY;
    const origLeft = parseInt(el.style.left) || 0;
    const origTop = parseInt(el.style.top) || 0;
    el.classList.add('dragging');
    const move = (ev) => {
      const nx = Math.max(0, origLeft + (ev.pageX - startX));
      const ny = Math.max(0, origTop + (ev.pageY - startY));
      el.style.left = nx + 'px';
      el.style.top = ny + 'px';
    };
    const up = () => {
      el.classList.remove('dragging');
      n.x = parseInt(el.style.left) || 0;
      n.y = parseInt(el.style.top) || 0;
      document.removeEventListener('mousemove', move);
      document.removeEventListener('mouseup', up);
      scheduleSave();
    };
    document.addEventListener('mousemove', move);
    document.addEventListener('mouseup', up);
  });

  // 리사이즈
  const rh = el.querySelector('.resize-handle');
  if(rh){
    rh.addEventListener('mousedown', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const startX = e.pageX;
      const startY = e.pageY;
      const origW = el.offsetWidth;
      const origH = el.offsetHeight;
      const move = (ev) => {
        const nw = Math.max(140, origW + (ev.pageX - startX));
        const nh = Math.max(100, origH + (ev.pageY - startY));
        el.style.width = nw + 'px';
        el.style.height = nh + 'px';
      };
      const up = () => {
        n.width = el.offsetWidth;
        n.height = el.offsetHeight;
        document.removeEventListener('mousemove', move);
        document.removeEventListener('mouseup', up);
        scheduleSave();
      };
      document.addEventListener('mousemove', move);
      document.addEventListener('mouseup', up);
    });
  }
}

function setColor(id, color){
  const n = _notes.find(x => x.id === id);
  if(!n) return;
  n.color = color;
  const el = document.querySelector('[data-note-id="'+id+'"]');
  if(el) el.setAttribute('data-color', color);
  scheduleSave();
}

function setSize(id, size){
  const n = _notes.find(x => x.id === id);
  if(!n) return;
  n.size = size;
  // 사이즈 프리셋 사용 시 width/height 리셋 (CSS에 맡김)
  delete n.width;
  delete n.height;
  const el = document.querySelector('[data-note-id="'+id+'"]');
  if(el){
    el.setAttribute('data-size', size);
    el.style.width = '';
    el.style.height = '';
    el.querySelectorAll('.size-btn').forEach(b => b.classList.remove('active'));
    el.querySelectorAll('.size-btn').forEach(b => {
      if(b.textContent.toLowerCase() === size) b.classList.add('active');
    });
  }
  scheduleSave();
}

function deleteNote(id){
  const n = _notes.find(x => x.id === id);
  if(!n) return;
  const preview = (n.title || n.subtitle || n.body || '').slice(0, 30);
  if(!confirm('이 포스트잇 삭제할까요?' + (preview ? '\n"'+preview+'"' : ''))) return;
  _notes = _notes.filter(x => x.id !== id);
  renderAll();
  scheduleSave();
}

function addNoteAtCenter(color){
  color = color || 'yellow';
  // 캔버스의 현재 스크롤 중앙에 추가
  const wrap = document.getElementById('canvas-wrap');
  const x = wrap.scrollLeft + (wrap.clientWidth / 2) - 120 + (Math.random()*40 - 20);
  const y = wrap.scrollTop + (wrap.clientHeight / 2) - 100 + (Math.random()*40 - 20);
  const n = {
    id: genId(),
    x: Math.max(0, Math.round(x)),
    y: Math.max(0, Math.round(y)),
    color: color,
    size: 'm',
    title: '',
    subtitle: '',
    body: '',
  };
  _notes.push(n);
  document.getElementById('empty-hint').style.display = 'none';
  const el = makeNoteEl(n);
  document.getElementById('canvas').appendChild(el);
  scheduleSave();
  // 방금 만든 포스트잇의 제목 필드에 포커스
  setTimeout(() => {
    const titleEl = el.querySelector('[data-field="title"]');
    if(titleEl) titleEl.focus();
  }, 50);
}

async function clearAll(){
  if(!confirm('보드를 전부 비울까요?\n되돌릴 수 없음.')) return;
  _notes = [];
  renderAll();
  try {
    await fetch('/api/post/postit', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: '', date: new Date().toISOString().slice(0,10)})
    });
  } catch(e){}
}

loadNotes();
</script>
</body>
</html>
"""

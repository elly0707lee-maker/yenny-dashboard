"""
Yenny Dashboard - Mindmap Module (Q-CG-Comment 구조)
URL: /mindmap
저장: 'mindmap' 타입으로 PostgreSQL에 자동 저장 (1.5초 debounce)

데이터 구조:
{
  corner: {
    title: "...", subtitle: "...",
    questions: [
      {
        id, number, type, guest, title,
        cgs: [{id, image, title, subtitle, comments: [{id, text}]}],
        comments: [{id, label, text}]
      }
    ]
  },
  activeQuestionId: "..."
}
"""


def get_mindmap_html():
    return r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#1a1d23">
<title>Yenny Mindmap</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=DM+Mono:wght@400;500&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Noto Sans KR',sans-serif;background:#f0f2f5;color:#1a1d23;min-height:100vh;-webkit-font-smoothing:antialiased}
input,textarea,button{font-family:inherit;color:inherit}

.topbar{display:flex;justify-content:space-between;align-items:center;padding:12px 22px;background:#1a1d23;position:sticky;top:0;z-index:50;border-bottom:3px solid #e8b84b}
.topbar-title{font-size:15px;font-weight:700;color:#fff;letter-spacing:-.3px}
.topbar-title span{color:#e8b84b;font-weight:400;font-size:12px;margin-left:6px}
.topbar a{color:#e8b84b;text-decoration:none;font-size:12px;padding:5px 12px;border:0.5px solid #e8b84b;border-radius:6px;font-family:'DM Mono',monospace}
.topbar a:hover{background:#e8b84b;color:#1a1d23}
.save-ind{font-size:10px;color:#00b894;font-family:'DM Mono',monospace;letter-spacing:0.5px;opacity:0;transition:opacity 0.3s;padding:0 6px}
.save-ind.saving{color:#fff;opacity:1}
.save-ind.saved{color:#00b894;opacity:1}
.save-ind.error{color:#ff7878;opacity:1}

.wrap{padding:18px;max-width:1400px;margin:0 auto}

.mm{background:#fff;border:0.5px solid #D3D1C7;border-radius:12px;padding:16px 18px;min-height:640px}
.mm-corner-head{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:12px;margin-bottom:14px;border-bottom:0.5px solid #D3D1C7;gap:14px}
.mm-corner-meta{flex:1;min-width:0}
.mm-corner-label{font-size:11px;color:#5F5E5A;font-family:'DM Mono',monospace;letter-spacing:0.5px;margin-bottom:4px}
.mm-corner-title{font-size:18px;font-weight:500;line-height:1.4;border:none;background:transparent;outline:none;width:100%;padding:0;color:#1a1d23}
.mm-corner-title::placeholder{color:#B4B2A9}
.mm-corner-sub{font-size:12.5px;color:#5F5E5A;border:none;background:transparent;outline:none;width:100%;padding:3px 0 0;margin-top:2px}
.mm-corner-sub::placeholder{color:#B4B2A9}
.mm-new-q{font-size:12px;padding:6px 14px;background:#1a1d23;color:#e8b84b;border:0.5px solid #1a1d23;border-radius:6px;cursor:pointer;white-space:nowrap;display:flex;align-items:center;gap:5px;height:fit-content;align-self:center}
.mm-new-q:hover{background:#2C2C2A}

.mm-body{display:grid;grid-template-columns:180px 1fr;gap:14px;align-items:start}

.mm-q-list{display:flex;flex-direction:column;gap:6px;min-width:0}
.mm-list-head{font-size:10px;color:#888780;font-family:'DM Mono',monospace;letter-spacing:0.5px;padding:0 4px 2px}
.mm-q-card{background:#fff;border:0.5px solid #D3D1C7;border-left:3px solid #888780;border-radius:8px;padding:8px 10px;cursor:pointer;transition:all 0.12s;position:relative}
.mm-q-card:hover{border-color:#888780}
.mm-q-card.active{border:1.5px solid #185FA5;border-left-width:1.5px}
.mm-q-card.active.q2{border-color:#993C1D}
.mm-q-card.active.q3{border-color:#3B6D11}
.mm-q-card.active.q4{border-color:#3C3489}
.mm-q-card.active.q5{border-color:#854F0B}
.mm-q-card.mm-dragging{opacity:0.4;background:#FAEEDA}
.mm-q-card.q1{border-left-color:#378ADD}
.mm-q-card.q2{border-left-color:#D85A30}
.mm-q-card.q3{border-left-color:#639922}
.mm-q-card.q4{border-left-color:#7F77DD}
.mm-q-card.q5{border-left-color:#BA7517}
.mm-q-card-head{display:flex;align-items:center;gap:5px;margin-bottom:3px}
.mm-q-card-num{font-size:9px;padding:1px 5px;color:#fff;border-radius:3px;font-family:'DM Mono',monospace;font-weight:500}
.mm-q-card.q1 .mm-q-card-num{background:#378ADD}
.mm-q-card.q2 .mm-q-card-num{background:#D85A30}
.mm-q-card.q3 .mm-q-card-num{background:#639922}
.mm-q-card.q4 .mm-q-card-num{background:#7F77DD}
.mm-q-card.q5 .mm-q-card-num{background:#BA7517}
.mm-q-card-grip{font-size:10px;color:#B4B2A9;cursor:grab;letter-spacing:-2px;opacity:0;transition:opacity 0.1s;user-select:none}
.mm-q-card:hover .mm-q-card-grip{opacity:0.6}
.mm-q-card-grip:active{cursor:grabbing}
.mm-q-card-title{font-size:11.5px;line-height:1.4;color:#1a1d23;word-break:break-word}
.mm-q-card.active .mm-q-card-title{font-weight:500}
.mm-q-card-stats{display:flex;gap:7px;margin-top:4px;font-size:9.5px;color:#888780;align-items:center}
.mm-q-card-stats span{display:flex;align-items:center;gap:2px}
.mm-q-card-del{position:absolute;top:4px;right:4px;font-size:11px;color:#B4B2A9;background:none;border:none;padding:2px 5px;border-radius:3px;cursor:pointer;opacity:0;line-height:1}
.mm-q-card:hover .mm-q-card-del{opacity:0.8}
.mm-q-card-del:hover{background:#FCEBEB;color:#A32D2D;opacity:1}
.mm-q-add{border:0.5px dashed #B4B2A9;background:transparent;border-radius:8px;padding:7px;text-align:center;color:#888780;font-size:11px;cursor:pointer;transition:all 0.12s}
.mm-q-add:hover{border-color:#888780;background:#F1EFE8}

.mm-q-detail{background:#fff;border:0.5px solid #D3D1C7;border-radius:8px;padding:14px 16px;min-width:0}
.mm-q-empty{padding:60px 30px;text-align:center;color:#888780;font-size:13px;line-height:1.7}
.mm-q-empty .emo{font-size:36px;margin-bottom:10px;color:#B4B2A9}

.mm-q-head{margin-bottom:14px}
.mm-q-chips{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:8px}
.mm-q-num-chip{font-size:10px;padding:2px 8px;background:#888780;color:#fff;border-radius:4px;font-family:'DM Mono',monospace;font-weight:500;outline:none;min-width:24px;text-align:center}
.mm-q-detail.q1 .mm-q-num-chip{background:#378ADD}
.mm-q-detail.q2 .mm-q-num-chip{background:#D85A30}
.mm-q-detail.q3 .mm-q-num-chip{background:#639922}
.mm-q-detail.q4 .mm-q-num-chip{background:#7F77DD}
.mm-q-detail.q5 .mm-q-num-chip{background:#BA7517}
.mm-q-type-input{font-size:11px;padding:2px 8px;background:#E6F1FB;color:#0C447C;border:0.5px solid transparent;border-radius:4px;outline:none;width:100px}
.mm-q-type-input:focus{border-color:#378ADD;background:#fff}
.mm-q-guest-input{font-size:11px;padding:2px 8px;background:#FAEEDA;color:#633806;border:0.5px solid transparent;border-radius:4px;outline:none;font-family:'DM Mono',monospace;width:90px}
.mm-q-guest-input:focus{border-color:#BA7517;background:#fff}
.mm-q-title-input{width:100%;font-size:14px;font-weight:500;line-height:1.45;border:none;background:transparent;outline:none;resize:none;padding:2px 0;color:#1a1d23;overflow:hidden;font-family:inherit;min-height:24px}
.mm-q-title-input::placeholder{color:#B4B2A9}

.mm-cg-section{margin-bottom:14px}
.mm-section-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.mm-section-label{font-size:11px;color:#5F5E5A;font-family:'DM Mono',monospace;letter-spacing:0.4px}
.mm-section-hint{font-size:10px;color:#B4B2A9}

.mm-cg-scroll{display:flex;gap:10px;overflow-x:auto;padding:4px 2px 10px;scrollbar-width:thin;scrollbar-color:#B4B2A9 transparent}
.mm-cg-scroll::-webkit-scrollbar{height:8px}
.mm-cg-scroll::-webkit-scrollbar-thumb{background:#B4B2A9;border-radius:4px}
.mm-cg-scroll::-webkit-scrollbar-track{background:transparent}

.mm-cg-card{flex:0 0 240px;border:0.5px solid #D3D1C7;border-radius:8px;overflow:hidden;background:#fff;position:relative;transition:opacity 0.2s}
.mm-cg-card.mm-dragging{opacity:0.4}
.mm-cg-img{height:140px;background:#F1EFE8;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}
.mm-cg-img img{width:100%;height:100%;object-fit:cover;display:block;cursor:zoom-in}
.mm-cg-img-empty{color:#B4B2A9;font-size:11px;display:flex;flex-direction:column;align-items:center;gap:4px;text-align:center}
.mm-cg-img-empty .icn{font-size:24px}
.mm-cg-label{position:absolute;top:6px;right:8px;font-size:9px;color:#1a1d23;font-family:'DM Mono',monospace;background:rgba(255,255,255,0.92);padding:2px 6px;border-radius:3px;font-weight:500;cursor:grab;user-select:none}
.mm-cg-label:active{cursor:grabbing}
.mm-cg-del{position:absolute;top:6px;left:8px;font-size:11px;background:rgba(0,0,0,0.5);color:#fff;border:none;border-radius:3px;padding:2px 5px;cursor:pointer;line-height:1;opacity:0;transition:opacity 0.1s}
.mm-cg-card:hover .mm-cg-del{opacity:1}
.mm-cg-meta{padding:9px 11px}
.mm-cg-title{width:100%;border:none;background:transparent;padding:0;font-size:12.5px;font-weight:500;outline:none;color:#1a1d23}
.mm-cg-title::placeholder{color:#B4B2A9}
.mm-cg-sub{width:100%;border:none;background:transparent;padding:2px 0 0;font-size:11px;color:#5F5E5A;outline:none}
.mm-cg-sub::placeholder{color:#B4B2A9}

.mm-cg-comments{margin-top:8px;padding-top:8px;border-top:0.5px dashed #D3D1C7}
.mm-cg-comments-head{font-size:9.5px;color:#888780;font-family:'DM Mono',monospace;letter-spacing:0.3px;margin-bottom:5px}
.mm-cg-comment{display:flex;gap:6px;padding:4px 7px;font-size:11.5px;line-height:1.45;background:#FAFAF7;border-radius:4px;align-items:flex-start;margin-bottom:3px;transition:opacity 0.2s}
.mm-cg-comment.mm-dragging{opacity:0.4;background:#FAEEDA}
.mm-cg-comment .mm-grip{font-size:10px;color:#B4B2A9;opacity:0.4;padding-top:2px;cursor:grab;letter-spacing:-2px;user-select:none;flex-shrink:0;transition:opacity 0.1s}
.mm-cg-comment:hover .mm-grip{opacity:0.7}
.mm-cg-comment .mm-grip:active{cursor:grabbing}
.mm-cg-comment-text{flex:1;outline:none;word-break:break-word}
.mm-cg-comment-text:focus{background:#fff;border-radius:3px;padding:0 2px;margin:0 -2px}
.mm-cg-comment-del{background:none;border:none;color:#B4B2A9;font-size:10px;cursor:pointer;padding:0 2px;opacity:0;line-height:1;flex-shrink:0}
.mm-cg-comment:hover .mm-cg-comment-del{opacity:0.7}
.mm-cg-comment-del:hover{color:#A32D2D;opacity:1}
.mm-cg-comment-add{width:100%;border:0.5px solid #D3D1C7;padding:4px 9px;border-radius:6px;font-size:11px;outline:none;margin-top:2px;background:#fff}
.mm-cg-comment-add:focus{border-color:#888780}

.mm-cg-drop{flex:0 0 180px;border:0.5px dashed #B4B2A9;border-radius:8px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#888780;background:#F1EFE8;gap:6px;min-height:240px;cursor:pointer;transition:all 0.12s;text-align:center;padding:0 12px;font-size:11px;line-height:1.5}
.mm-cg-drop:hover, .mm-cg-drop.drag-over{border-color:#1a1d23;background:#FAEEDA;color:#412402}
.mm-cg-drop .ic{font-size:22px;margin-bottom:2px}

.mm-qc-section{border-top:0.5px solid #D3D1C7;padding-top:12px;margin-top:14px}
.mm-qc-list{display:flex;flex-direction:column;gap:3px}
.mm-qc{display:flex;gap:8px;padding:5px 8px;font-size:12px;line-height:1.5;align-items:flex-start;background:transparent;border-radius:4px;transition:opacity 0.2s}
.mm-qc.mm-dragging{opacity:0.4;background:#FAEEDA}
.mm-qc.bg-amber{background:#FDF7EC}
.mm-qc.bg-pink{background:#FCF3F7}
.mm-qc.bg-blue{background:#F0F7FE}
.mm-qc.bg-green{background:#F3F9EA}
.mm-qc.bg-purple{background:#F7F6FE}
.mm-qc .mm-grip{font-size:10px;color:#B4B2A9;opacity:0.4;padding-top:3px;cursor:grab;letter-spacing:-2px;user-select:none;flex-shrink:0;transition:opacity 0.1s}
.mm-qc:hover .mm-grip{opacity:0.7}
.mm-qc .mm-grip:active{cursor:grabbing}
.mm-qc-label{font-size:10px;flex-shrink:0;padding-top:2px;color:#5F5E5A;font-family:'DM Mono',monospace;min-width:40px;outline:none;font-weight:500}
.mm-qc-label:focus{background:#fff;border-radius:3px;padding:0 3px}
.mm-qc-label[data-placeholder]:empty::before{content:attr(data-placeholder);color:#B4B2A9;font-weight:400}
.mm-qc.bg-amber .mm-qc-label{color:#854F0B}
.mm-qc.bg-pink .mm-qc-label{color:#993556}
.mm-qc.bg-blue .mm-qc-label{color:#185FA5}
.mm-qc.bg-green .mm-qc-label{color:#3B6D11}
.mm-qc.bg-purple .mm-qc-label{color:#534AB7}
.mm-qc-text{flex:1;outline:none;color:#1a1d23;word-break:break-word}
.mm-qc.bg-amber .mm-qc-text{color:#412402}
.mm-qc.bg-pink .mm-qc-text{color:#4B1528}
.mm-qc.bg-blue .mm-qc-text{color:#042C53}
.mm-qc.bg-green .mm-qc-text{color:#173404}
.mm-qc.bg-purple .mm-qc-text{color:#26215C}
.mm-qc-text:focus{background:#fff;border-radius:3px;padding:0 3px;margin:0 -3px}
.mm-qc-del{background:none;border:none;color:#B4B2A9;font-size:11px;cursor:pointer;padding:0 4px;opacity:0;line-height:1;flex-shrink:0}
.mm-qc:hover .mm-qc-del{opacity:0.7}
.mm-qc-del:hover{color:#A32D2D;opacity:1}
.mm-qc-add{width:100%;border:0.5px solid #D3D1C7;padding:6px 10px;border-radius:6px;font-size:12px;outline:none;margin-top:6px;background:#fff}
.mm-qc-add:focus{border-color:#888780}

.mm-lightbox{position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:200;display:none;align-items:center;justify-content:center;padding:30px;cursor:zoom-out}
.mm-lightbox.show{display:flex}
.mm-lightbox img{max-width:100%;max-height:100%;object-fit:contain}
.mm-lightbox-close{position:absolute;top:18px;right:24px;background:rgba(255,255,255,0.15);color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:13px;cursor:pointer}
.mm-lightbox-close:hover{background:rgba(255,255,255,0.25)}

@media (max-width: 700px){
  .wrap{padding:10px}
  .mm{padding:12px}
  .mm-body{grid-template-columns:1fr;gap:10px}
  .mm-q-list{flex-direction:row;overflow-x:auto;padding-bottom:6px;gap:8px}
  .mm-q-card{flex:0 0 170px}
  .mm-list-head{display:none}
}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-title">🧠 YENNY <span>MINDMAP</span></div>
  <div style="display:flex;align-items:center;gap:8px">
    <span class="save-ind" id="save-ind"></span>
    <a href="/">← Dashboard</a>
  </div>
</div>

<div class="wrap">
  <div class="mm">
    <div class="mm-corner-head">
      <div class="mm-corner-meta">
        <div class="mm-corner-label">CORNER · #1</div>
        <input type="text" class="mm-corner-title" id="mm-corner-title" placeholder="코너 제목 (예: 미국 하락 코너)">
        <input type="text" class="mm-corner-sub" id="mm-corner-sub" placeholder="부제목 (선택)">
      </div>
      <button class="mm-new-q" onclick="addQuestion()"><span style="font-size:14px;line-height:1">＋</span>새 Q</button>
    </div>

    <div class="mm-body">
      <div class="mm-q-list" id="mm-q-list"></div>
      <div class="mm-q-detail" id="mm-q-detail"></div>
    </div>
  </div>
</div>

<div class="mm-lightbox" id="mm-lightbox" onclick="closeLightbox()">
  <button class="mm-lightbox-close" onclick="event.stopPropagation();closeLightbox()">✕ 닫기 (ESC)</button>
  <img id="mm-lightbox-img" src="" alt="">
</div>

<input type="file" id="mm-file-input" accept="image/*" style="display:none" multiple>

<script>
// === 데이터 모델 ===
let MD = {
  corner: { title:'', subtitle:'', questions:[] },
  activeQuestionId: null
};
let saveTimer = null;
let dirty = false;

function genId(prefix){
  return prefix + '_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2,7);
}
function getActiveQ(){
  if(!MD.activeQuestionId) return null;
  return MD.corner.questions.find(q => q.id === MD.activeQuestionId) || null;
}
function getQColorIdx(q){
  const idx = MD.corner.questions.indexOf(q);
  return (idx % 5) + 1;
}
function escapeHtml(s){
  if(s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function getQCBgClass(label){
  const l = (label || '').toLowerCase();
  if(/db|콜백/.test(l)) return 'bg-amber';
  if(/말랑|💫/.test(l)) return 'bg-pink';
  if(/상황|배경/.test(l)) return 'bg-blue';
  if(/송곳|🎯송곳/.test(l)) return 'bg-purple';
  if(/질문/.test(l)) return 'bg-green';
  return '';
}

// === 저장/로드 ===
function indSaving(){const i=document.getElementById('save-ind');if(!i)return;i.textContent='저장 중...';i.className='save-ind saving';i.style.opacity=1;}
function indSaved(){const i=document.getElementById('save-ind');if(!i)return;i.textContent='✓ 저장됨';i.className='save-ind saved';i.style.opacity=1;setTimeout(()=>{i.style.opacity=0;},1500);}
function indError(){const i=document.getElementById('save-ind');if(!i)return;i.textContent='✕ 저장 실패';i.className='save-ind error';i.style.opacity=1;}

async function saveMindmap(){
  try{
    indSaving();
    const content = JSON.stringify(MD);
    const res = await fetch('/api/post/mindmap',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({content, date: new Date().toISOString().slice(0,10)})
    });
    if(!res.ok){indError();return;}
    indSaved();
  }catch(e){indError();}
}
function scheduleSave(){
  dirty = true;
  if(saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(()=>{ saveMindmap(); dirty=false; }, 1500);
}
async function loadMindmap(){
  try{
    const d = await fetch('/api/post/mindmap').then(r => r.json());
    if(d && d.content){
      try{
        const parsed = JSON.parse(d.content);
        if(parsed && parsed.corner){
          MD = parsed;
          if(!MD.corner.questions) MD.corner.questions = [];
          MD.corner.questions.forEach(q => {
            if(!q.cgs) q.cgs = [];
            if(!q.comments) q.comments = [];
            q.cgs.forEach(cg => { if(!cg.comments) cg.comments = []; });
          });
        }
      }catch(e){console.error('parse failed', e);}
    }
  }catch(e){console.error('load failed', e);}
  render();
}

// === 렌더링 ===
function render(){
  renderHeader();
  renderQList();
  renderQDetail();
}
function renderHeader(){
  document.getElementById('mm-corner-title').value = MD.corner.title || '';
  document.getElementById('mm-corner-sub').value = MD.corner.subtitle || '';
}
function renderQList(){
  const list = document.getElementById('mm-q-list');
  const head = '<div class="mm-list-head">QUESTIONS · '+MD.corner.questions.length+'</div>';
  let html = head;
  MD.corner.questions.forEach((q, idx) => {
    const colorIdx = (idx % 5) + 1;
    const active = q.id === MD.activeQuestionId ? ' active' : '';
    const cgCount = (q.cgs || []).length;
    const commentCount = (q.comments || []).length + (q.cgs || []).reduce((s,cg)=>s+(cg.comments||[]).length,0);
    html += '<div class="mm-q-card q'+colorIdx+active+'" data-q-id="'+q.id+'" onclick="selectQuestion(\''+q.id+'\')">'+
      '<button class="mm-q-card-del" onclick="event.stopPropagation();deleteQuestion(\''+q.id+'\')" title="삭제">✕</button>'+
      '<div class="mm-q-card-head">'+
        '<span class="mm-q-card-grip" draggable="true" onclick="event.stopPropagation()">⋮⋮</span>'+
        '<span class="mm-q-card-num">'+escapeHtml(q.number || ('Q'+(idx+1)))+'</span>'+
      '</div>'+
      '<div class="mm-q-card-title">'+escapeHtml(q.title || '(제목 없음)')+'</div>'+
      '<div class="mm-q-card-stats">'+
        '<span><i class="ti ti-message-circle" style="font-size:10px"></i> '+commentCount+'</span>'+
        (cgCount ? '<span><i class="ti ti-photo" style="font-size:10px"></i> '+cgCount+'</span>' : '')+
      '</div>'+
    '</div>';
  });
  html += '<button class="mm-q-add" onclick="addQuestion()">＋ 새 질문</button>';
  list.innerHTML = html;
}
function renderQDetail(){
  const detail = document.getElementById('mm-q-detail');
  const q = getActiveQ();
  if(!q){
    detail.className = 'mm-q-detail';
    detail.innerHTML = '<div class="mm-q-empty"><div class="emo">💬</div>왼쪽에서 질문을 선택하거나<br>＋ 새 Q 버튼으로 추가하세요</div>';
    return;
  }
  const colorIdx = getQColorIdx(q);
  detail.className = 'mm-q-detail q'+colorIdx;

  let html = '';
  html += '<div class="mm-q-head">';
  html += '<div class="mm-q-chips">';
  html += '<span class="mm-q-num-chip" contenteditable="true" onblur="updateQField(\''+q.id+'\',\'number\',this.textContent.trim())">'+escapeHtml(q.number||'Q')+'</span>';
  html += '<input type="text" class="mm-q-type-input" value="'+escapeHtml(q.type||'')+'" placeholder="🅰️ 타입" onchange="updateQField(\''+q.id+'\',\'type\',this.value)">';
  html += '<input type="text" class="mm-q-guest-input" value="'+escapeHtml(q.guest||'')+'" placeholder="출연자" onchange="updateQField(\''+q.id+'\',\'guest\',this.value)">';
  html += '</div>';
  html += '<textarea class="mm-q-title-input" placeholder="질문 제목 입력..." onchange="updateQField(\''+q.id+'\',\'title\',this.value)" oninput="autoResizeTextarea(this);scheduleSave()">'+escapeHtml(q.title||'')+'</textarea>';
  html += '</div>';

  html += '<div class="mm-cg-section">';
  html += '<div class="mm-section-head">';
  html += '<div class="mm-section-label">CG · '+(q.cgs||[]).length+'장 <span style="font-family:\'Noto Sans KR\',sans-serif;color:#B4B2A9;margin-left:4px">→ 가로 스크롤</span></div>';
  html += '<div class="mm-section-hint">드래그 = 순서 · 클릭 = 풀스크린</div>';
  html += '</div>';
  html += '<div class="mm-cg-scroll" id="mm-cg-scroll-'+q.id+'">';
  (q.cgs || []).forEach((cg, idx) => {
    html += renderCGCard(q.id, cg, idx);
  });
  html += '<div class="mm-cg-drop" onclick="triggerFileInput(\''+q.id+'\')" data-q-id="'+q.id+'">'+
    '<div class="ic">⬆</div>'+
    '<div>이미지 끌어다 놓기<br>또는 클릭 · Cmd+V</div>'+
  '</div>';
  html += '</div>';
  html += '</div>';

  html += '<div class="mm-qc-section">';
  html += '<div class="mm-section-head">';
  html += '<div class="mm-section-label">Q COMMENTS · '+(q.comments||[]).length+'</div>';
  html += '</div>';
  html += '<div class="mm-qc-list">';
  (q.comments || []).forEach(qc => {
    html += renderQComment(q.id, qc);
  });
  html += '</div>';
  html += '<input type="text" class="mm-qc-add" placeholder="+ comment 추가 (자유 라벨, 예: 의도 | ▶ DB | 💫 말랑)" onkeydown="if(event.key===\'Enter\'){addQComment(\''+q.id+'\',this.value);this.value=\'\'}">';
  html += '</div>';

  detail.innerHTML = html;
  const ta = detail.querySelector('.mm-q-title-input');
  if(ta) autoResizeTextarea(ta);
}
function renderCGCard(qId, cg, idx){
  const imgHtml = cg.image
    ? '<img src="'+escapeHtml(cg.image)+'" alt="" onclick="openLightbox(this.src)">'
    : '<div class="mm-cg-img-empty"><div class="icn">📷</div>이미지 없음</div>';

  let html = '<div class="mm-cg-card" data-cg-id="'+cg.id+'" data-q-id="'+qId+'">';
  html += '<div class="mm-cg-img">'+imgHtml+
    '<span class="mm-cg-label" draggable="true">CG-'+(idx+1)+'</span>'+
    '<button class="mm-cg-del" onclick="deleteCG(\''+qId+'\',\''+cg.id+'\')" title="삭제">✕</button>'+
    '</div>';
  html += '<div class="mm-cg-meta">';
  html += '<input type="text" class="mm-cg-title" value="'+escapeHtml(cg.title||'')+'" placeholder="제목" onchange="updateCGField(\''+qId+'\',\''+cg.id+'\',\'title\',this.value)">';
  html += '<input type="text" class="mm-cg-sub" value="'+escapeHtml(cg.subtitle||'')+'" placeholder="부제목" onchange="updateCGField(\''+qId+'\',\''+cg.id+'\',\'subtitle\',this.value)">';
  html += '<div class="mm-cg-comments">';
  html += '<div class="mm-cg-comments-head">COMMENT</div>';
  (cg.comments || []).forEach(cc => {
    html += '<div class="mm-cg-comment" data-cc-id="'+cc.id+'">'+
      '<span class="mm-grip" draggable="true">⋮⋮</span>'+
      '<span class="mm-cg-comment-text" contenteditable="true" onblur="updateCGComment(\''+qId+'\',\''+cg.id+'\',\''+cc.id+'\',this.textContent)">'+escapeHtml(cc.text||'')+'</span>'+
      '<button class="mm-cg-comment-del" onclick="deleteCGComment(\''+qId+'\',\''+cg.id+'\',\''+cc.id+'\')">✕</button>'+
    '</div>';
  });
  html += '<input type="text" class="mm-cg-comment-add" placeholder="+ comment 추가" onkeydown="if(event.key===\'Enter\'){addCGComment(\''+qId+'\',\''+cg.id+'\',this.value);this.value=\'\'}">';
  html += '</div>';
  html += '</div>';
  html += '</div>';
  return html;
}
function renderQComment(qId, qc){
  const bg = getQCBgClass(qc.label);
  return '<div class="mm-qc '+bg+'" data-qc-id="'+qc.id+'">'+
    '<span class="mm-grip" draggable="true">⋮⋮</span>'+
    '<span class="mm-qc-label" contenteditable="true" data-placeholder="라벨" onblur="updateQCommentField(\''+qId+'\',\''+qc.id+'\',\'label\',this.textContent.trim())">'+escapeHtml(qc.label||'')+'</span>'+
    '<span class="mm-qc-text" contenteditable="true" onblur="updateQCommentField(\''+qId+'\',\''+qc.id+'\',\'text\',this.textContent)">'+escapeHtml(qc.text||'')+'</span>'+
    '<button class="mm-qc-del" onclick="deleteQComment(\''+qId+'\',\''+qc.id+'\')">✕</button>'+
  '</div>';
}
function escapeAttr(s){return String(s||'').replace(/'/g,"\\'").replace(/"/g,'&quot;');}
function autoResizeTextarea(el){el.style.height='auto';el.style.height=(el.scrollHeight+2)+'px';}

// === CRUD ===
function addQuestion(){
  const num = 'Q' + (MD.corner.questions.length + 1);
  const q = { id: genId('q'), number: num, type: '', guest: '', title: '', cgs: [], comments: [] };
  MD.corner.questions.push(q);
  MD.activeQuestionId = q.id;
  render();
  scheduleSave();
  setTimeout(()=>{
    const ta = document.querySelector('.mm-q-title-input');
    if(ta){ ta.focus(); }
  }, 50);
}
function selectQuestion(qId){
  MD.activeQuestionId = qId;
  render();
  scheduleSave();
}
function deleteQuestion(qId){
  const q = MD.corner.questions.find(x => x.id === qId);
  if(!q) return;
  if(!confirm('이 질문을 삭제할까요?\n\n"'+(q.title || q.number)+'"')) return;
  MD.corner.questions = MD.corner.questions.filter(x => x.id !== qId);
  if(MD.activeQuestionId === qId){
    MD.activeQuestionId = MD.corner.questions.length ? MD.corner.questions[0].id : null;
  }
  render();
  scheduleSave();
}
function updateQField(qId, field, value){
  const q = MD.corner.questions.find(x => x.id === qId);
  if(!q) return;
  q[field] = value;
  if(field === 'title' || field === 'number'){ renderQList(); }
  scheduleSave();
}
function updateCGField(qId, cgId, field, value){
  const q = MD.corner.questions.find(x => x.id === qId); if(!q) return;
  const cg = q.cgs.find(c => c.id === cgId); if(!cg) return;
  cg[field] = value;
  scheduleSave();
}
function deleteCG(qId, cgId){
  if(!confirm('이 CG를 삭제할까요?')) return;
  const q = MD.corner.questions.find(x => x.id === qId); if(!q) return;
  q.cgs = q.cgs.filter(c => c.id !== cgId);
  render();
  scheduleSave();
}
function addCG(qId, base64Image){
  const q = MD.corner.questions.find(x => x.id === qId); if(!q) return;
  const cg = { id: genId('cg'), image: base64Image, title: '', subtitle: '', comments: [] };
  q.cgs.push(cg);
  render();
  scheduleSave();
}
function addCGComment(qId, cgId, text){
  if(!text || !text.trim()) return;
  const q = MD.corner.questions.find(x => x.id === qId); if(!q) return;
  const cg = q.cgs.find(c => c.id === cgId); if(!cg) return;
  cg.comments.push({ id: genId('cc'), text: text.trim() });
  render();
  scheduleSave();
}
function updateCGComment(qId, cgId, ccId, text){
  const q = MD.corner.questions.find(x => x.id === qId); if(!q) return;
  const cg = q.cgs.find(c => c.id === cgId); if(!cg) return;
  const cc = cg.comments.find(c => c.id === ccId); if(!cc) return;
  cc.text = text;
  scheduleSave();
}
function deleteCGComment(qId, cgId, ccId){
  const q = MD.corner.questions.find(x => x.id === qId); if(!q) return;
  const cg = q.cgs.find(c => c.id === cgId); if(!cg) return;
  cg.comments = cg.comments.filter(c => c.id !== ccId);
  render();
  scheduleSave();
}
function addQComment(qId, raw){
  if(!raw || !raw.trim()) return;
  const q = MD.corner.questions.find(x => x.id === qId); if(!q) return;
  let label = '', text = raw.trim(), m;
  if((m = text.match(/^\[([^\]]+)\]\s*(.*)/))){ label = m[1]; text = m[2]; }
  else if((m = text.match(/^(\S{1,8})\s*[:：]\s*(.+)/))){ label = m[1]; text = m[2]; }
  q.comments.push({ id: genId('qc'), label: label, text: text });
  render();
  scheduleSave();
}
function updateQCommentField(qId, qcId, field, value){
  const q = MD.corner.questions.find(x => x.id === qId); if(!q) return;
  const qc = q.comments.find(c => c.id === qcId); if(!qc) return;
  qc[field] = value;
  if(field === 'label'){ renderQDetail(); }
  scheduleSave();
}
function deleteQComment(qId, qcId){
  const q = MD.corner.questions.find(x => x.id === qId); if(!q) return;
  q.comments = q.comments.filter(c => c.id !== qcId);
  render();
  scheduleSave();
}

// === 이미지 업로드 ===
let _pendingDropQId = null;
function triggerFileInput(qId){
  _pendingDropQId = qId;
  document.getElementById('mm-file-input').click();
}
document.getElementById('mm-file-input').addEventListener('change', async (e) => {
  const files = Array.from(e.target.files || []);
  const qId = _pendingDropQId;
  if(!qId || !files.length) return;
  for(const f of files){
    if(!f.type.startsWith('image/')) continue;
    const data = await resizeImage(f);
    addCG(qId, data);
  }
  e.target.value = '';
  _pendingDropQId = null;
});

function resizeImage(file, maxW=1400, maxH=900, quality=0.85){
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        let w = img.width, h = img.height;
        if(w > maxW){ h = h * maxW / w; w = maxW; }
        if(h > maxH){ w = w * maxH / h; h = maxH; }
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(w); canvas.height = Math.round(h);
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#fff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const mime = file.type === 'image/png' ? 'image/png' : 'image/jpeg';
        resolve(canvas.toDataURL(mime, quality));
      };
      img.onerror = reject;
      img.src = e.target.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// === 드롭존 드래그 & 클립보드 ===
document.addEventListener('dragover', (e) => {
  const drop = e.target.closest('.mm-cg-drop');
  if(drop){ e.preventDefault(); drop.classList.add('drag-over'); return; }
  // 정렬 드래그
  if(!_draggingEl) return;
  let targetSel = null;
  if(_draggingKind === 'q-card') targetSel = '.mm-q-card';
  else if(_draggingKind === 'cg-card') targetSel = '.mm-cg-card';
  else if(_draggingKind === 'cg-comment') targetSel = '.mm-cg-comment';
  else if(_draggingKind === 'q-comment') targetSel = '.mm-qc';
  if(!targetSel) return;
  const target = e.target.closest(targetSel);
  if(!target || target === _draggingEl) return;
  if(target.parentNode !== _draggingEl.parentNode) return;
  e.preventDefault();
  const rect = target.getBoundingClientRect();
  const horizontal = _draggingKind === 'cg-card';
  const middle = horizontal ? (rect.left + rect.width/2) : (rect.top + rect.height/2);
  const pos = horizontal ? e.clientX : e.clientY;
  if(pos < middle){ target.parentNode.insertBefore(_draggingEl, target); }
  else { target.parentNode.insertBefore(_draggingEl, target.nextSibling); }
});
document.addEventListener('dragleave', (e) => {
  const drop = e.target.closest('.mm-cg-drop');
  if(drop){ drop.classList.remove('drag-over'); }
});
document.addEventListener('drop', async (e) => {
  const drop = e.target.closest('.mm-cg-drop');
  if(!drop) return;
  e.preventDefault();
  drop.classList.remove('drag-over');
  const qId = drop.dataset.qId;
  if(!qId) return;
  const files = Array.from(e.dataTransfer.files || []);
  for(const f of files){
    if(!f.type.startsWith('image/')) continue;
    const data = await resizeImage(f);
    addCG(qId, data);
  }
});
document.addEventListener('paste', async (e) => {
  const tgt = e.target;
  // 입력란에 포커스 중이면 일반 텍스트 붙여넣기는 막지 않음
  const items = (e.clipboardData || window.clipboardData)?.items || [];
  let handled = false;
  for(const item of items){
    if(item.type && item.type.startsWith('image/')){
      const q = getActiveQ(); if(!q) continue;
      const f = item.getAsFile();
      if(f){
        e.preventDefault();
        handled = true;
        const data = await resizeImage(f);
        addCG(q.id, data);
      }
    }
  }
});

// === 드래그 정렬 ===
let _draggingEl = null;
let _draggingKind = null;

document.addEventListener('dragstart', (e) => {
  const t = e.target;
  if(!t || !t.classList) return;
  if(t.classList.contains('mm-q-card-grip')){
    _draggingEl = t.closest('.mm-q-card');
    _draggingKind = 'q-card';
  }
  else if(t.classList.contains('mm-cg-label')){
    _draggingEl = t.closest('.mm-cg-card');
    _draggingKind = 'cg-card';
  }
  else if(t.classList.contains('mm-grip')){
    const cg = t.closest('.mm-cg-comment');
    const qc = t.closest('.mm-qc');
    if(cg){ _draggingEl = cg; _draggingKind = 'cg-comment'; }
    else if(qc){ _draggingEl = qc; _draggingKind = 'q-comment'; }
  }
  if(_draggingEl){
    _draggingEl.classList.add('mm-dragging');
    try{
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain','');
    }catch(err){}
  }
});

document.addEventListener('dragend', (e) => {
  if(!_draggingEl) return;
  _draggingEl.classList.remove('mm-dragging');
  syncOrderFromDOM(_draggingKind);
  _draggingEl = null;
  _draggingKind = null;
  scheduleSave();
});

function syncOrderFromDOM(kind){
  if(kind === 'q-card'){
    const list = document.getElementById('mm-q-list');
    const ids = Array.from(list.querySelectorAll('.mm-q-card')).map(el => el.dataset.qId);
    MD.corner.questions.sort((a,b) => ids.indexOf(a.id) - ids.indexOf(b.id));
    renderQList();
  } else if(kind === 'cg-card'){
    const q = getActiveQ(); if(!q) return;
    const scroll = document.getElementById('mm-cg-scroll-'+q.id);
    if(!scroll) return;
    const ids = Array.from(scroll.querySelectorAll('.mm-cg-card')).map(el => el.dataset.cgId);
    q.cgs.sort((a,b) => ids.indexOf(a.id) - ids.indexOf(b.id));
    renderQDetail();
  } else if(kind === 'cg-comment'){
    const q = getActiveQ(); if(!q) return;
    document.querySelectorAll('.mm-cg-card').forEach(cgEl => {
      const cgId = cgEl.dataset.cgId;
      const cg = q.cgs.find(c => c.id === cgId); if(!cg) return;
      const ids = Array.from(cgEl.querySelectorAll('.mm-cg-comment')).map(el => el.dataset.ccId);
      cg.comments.sort((a,b) => ids.indexOf(a.id) - ids.indexOf(b.id));
    });
  } else if(kind === 'q-comment'){
    const q = getActiveQ(); if(!q) return;
    const list = document.querySelector('.mm-qc-list');
    if(!list) return;
    const ids = Array.from(list.querySelectorAll('.mm-qc')).map(el => el.dataset.qcId);
    q.comments.sort((a,b) => ids.indexOf(a.id) - ids.indexOf(b.id));
  }
}

// === Corner 헤더 ===
document.getElementById('mm-corner-title').addEventListener('input', (e) => {
  MD.corner.title = e.target.value;
  scheduleSave();
});
document.getElementById('mm-corner-sub').addEventListener('input', (e) => {
  MD.corner.subtitle = e.target.value;
  scheduleSave();
});

// === lightbox ===
window.openLightbox = function(src){
  const lb = document.getElementById('mm-lightbox');
  document.getElementById('mm-lightbox-img').src = src;
  lb.classList.add('show');
};
window.closeLightbox = function(){
  document.getElementById('mm-lightbox').classList.remove('show');
};
document.addEventListener('keydown', (e) => {
  if(e.key === 'Escape') closeLightbox();
});

// === Tabler icons (선택적 - CDN 차단 시 텍스트 폴백) ===
const tablerCss = document.createElement('link');
tablerCss.rel = 'stylesheet';
tablerCss.href = 'https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.47.0/tabler-icons.min.css';
document.head.appendChild(tablerCss);

// === 초기 로드 ===
loadMindmap();
</script>

</body>
</html>"""

"""
Yenny Dashboard - Corner Mindmap Module
별도 페이지로 마인드맵 도구를 제공.
URL: /mindmap
저장: 'mindmap' 타입으로 PostgreSQL에 자동 저장 (1.5초 debounce)
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
body{font-family:'Noto Sans KR',sans-serif;background:#f0f2f5;color:#1a1d23;min-height:100vh}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:12px 22px;background:#1a1d23;position:sticky;top:0;z-index:50;border-bottom:3px solid #e8b84b}
.topbar-title{font-size:15px;font-weight:700;color:#fff;letter-spacing:-.3px}
.topbar-title span{color:#e8b84b;font-weight:400;font-size:12px;margin-left:6px}
.topbar a{color:#e8b84b;text-decoration:none;font-size:12px;padding:5px 12px;border:0.5px solid #e8b84b;border-radius:6px;font-family:'DM Mono',monospace}
.topbar a:hover{background:#e8b84b;color:#1a1d23}
.wrap{padding:18px;max-width:1400px;margin:0 auto}

/* === MINDMAP === */
.mm{background:#fff;border:0.5px solid #D3D1C7;border-radius:12px;padding:14px;display:flex;gap:14px;align-items:stretch;min-height:720px;position:relative}
.links{position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;z-index:5}
.mm-main{flex:1;min-width:0;position:relative}
.canvas{position:relative;width:100%;height:720px;overflow:auto;border-radius:8px;background-image:radial-gradient(circle,#EFEDE5 0.8px,transparent 0.8px);background-size:14px 14px}
.qgroup{position:absolute;display:flex;gap:9px;align-items:flex-start;width:auto}
.qgroup.dragging{z-index:10;opacity:0.96}
.qc{flex:0 0 280px;background:#fff;border:0.5px solid #D3D1C7;border-radius:10px;padding:10px 12px;min-width:0;position:relative;box-shadow:0 1px 2px rgba(0,0,0,0.03)}
.qc::before{content:'';position:absolute;left:-6px;top:16px;width:11px;height:11px;border-radius:50%;background:#fff;box-sizing:border-box;border:2px solid;z-index:3}
.qc.q1{border-left:3px solid #378ADD}.qc.q1::before{border-color:#378ADD}
.qc.q2{border-left:3px solid #D85A30}.qc.q2::before{border-color:#D85A30}
.qc.q3{border-left:3px solid #639922}.qc.q3::before{border-color:#639922}
.qc.q4{border-left:3px solid #7F77DD}.qc.q4::before{border-color:#7F77DD}
.qc.q5{border-left:3px solid #BA7517}.qc.q5::before{border-color:#BA7517}
.qhead{display:flex;align-items:center;gap:7px;margin-bottom:7px;padding-bottom:5px;border-bottom:0.5px dashed #D3D1C7;cursor:grab;user-select:none}
.qhead:active{cursor:grabbing}
.qnum{font-size:10px;padding:2px 6px;color:#fff;border-radius:3px;font-weight:500;font-family:'DM Mono',monospace;flex-shrink:0}
.q1 .qnum{background:#378ADD}.q2 .qnum{background:#D85A30}.q3 .qnum{background:#639922}.q4 .qnum{background:#7F77DD}.q5 .qnum{background:#BA7517}
.qlbl{font-size:13px;font-weight:500;color:#1a1d23;outline:none;flex:1;min-width:0;cursor:text}
.qlbl:focus{background:#F1EFE8;border-radius:3px;padding:0 4px}
.qopt{font-size:9.5px;padding:1px 6px;background:#F1EFE8;color:#5F5E5A;border-radius:3px;flex-shrink:0}
.qc-x{cursor:pointer;background:none;border:none;font-size:11px;padding:0 3px;opacity:0;transition:opacity 0.15s,color 0.15s;font-family:inherit;flex-shrink:0;color:#888780;line-height:1;align-self:center}
.qc:hover .qc-x{opacity:0.45}
.qc-x:hover{opacity:1!important;color:#A32D2D}
.blk{display:flex;align-items:flex-start;gap:5px;padding:5px 8px;border-radius:5px;font-size:12px;line-height:1.5;margin-bottom:4px;position:relative;transition:opacity 0.2s}
.blk:last-child{margin-bottom:0}
.blk-handle{cursor:grab;color:#B4B2A9;font-size:10px;flex-shrink:0;padding:0 1px;line-height:1.2;user-select:none;align-self:center;letter-spacing:-2px;opacity:0;transition:opacity 0.15s;font-family:inherit}
.blk:hover .blk-handle{opacity:0.45}
.blk-handle:hover{opacity:1!important;color:#1a1d23}
.blk-handle:active{cursor:grabbing}
.b-q .blk-handle{color:#FAC775}
.b-q:hover .blk-handle{opacity:0.55}
.blk-dragging{opacity:0.35!important;background:rgba(232,184,75,0.2)!important;outline:1px dashed #e8b84b}
.lbl{font-size:10px;font-weight:500;flex-shrink:0;letter-spacing:0.2px;padding-top:1px;outline:none}
.lbl[contenteditable]:focus{background:rgba(255,255,255,0.65);border-radius:3px;padding:0 3px}
.lbl[data-placeholder]:empty::before{content:attr(data-placeholder);color:#B4B2A9;font-weight:400}
.blk-text{flex:1;outline:none;min-width:0}
.blk-text:focus{background:rgba(255,255,255,0.65);border-radius:3px}
.blk-x{cursor:pointer;background:none;border:none;font-size:10px;padding:0 2px;opacity:0;transition:opacity 0.15s;font-family:inherit;flex-shrink:0;color:inherit;line-height:1}
.blk:hover .blk-x{opacity:0.4}
.blk-x:hover{opacity:1!important}
.b-int{background:#F1EFE8;color:#2C2C2A}.b-int .lbl{color:#5F5E5A}
.b-cb{background:#FAEEDA;color:#633806;border-left:2px solid #BA7517;padding-left:8px;border-radius:0 5px 5px 0}.b-cb .lbl{color:#854F0B}
.b-st{background:#E6F1FB;color:#042C53}.b-st .lbl{color:#185FA5}
.b-q{background:#1a1d23;color:#fff;padding:7px 10px;font-weight:500}.b-q .lbl{color:#FAC775}
.b-mr{background:#FBEAF0;color:#7C2543}.b-mr .lbl{color:#993556}
.b-sw{background:#F4ECFB;color:#3C1B5C;border-left:2px solid #7F77DD;padding-left:8px;border-radius:0 5px 5px 0}.b-sw .lbl{color:#534AB7}
.add-blk-row{display:flex;gap:4px;flex-wrap:wrap;margin-top:6px;padding-top:6px;border-top:0.5px dashed #E5E3DA}
.add-blk{padding:3px 8px;background:transparent;border:0.5px dashed #B4B2A9;color:#888780;border-radius:4px;cursor:pointer;font-size:9.5px;font-family:'DM Mono',monospace;letter-spacing:0.3px;transition:all 0.15s}
.add-blk:hover{background:#F1EFE8;color:#1a1d23;border-color:#1a1d23}
.memo-col{flex:0 0 156px;display:flex;flex-direction:column;gap:5px;padding-top:4px;position:relative}
.memo-col::before{content:'';position:absolute;left:-9px;top:18px;width:9px;border-top:1.5px dashed #7F77DD}
.memo{display:flex;align-items:flex-start;gap:5px;padding:5px 7px;background:#EEEDFE;border-left:2px dashed #7F77DD;border-radius:0 5px 5px 0;font-size:11px;line-height:1.4;color:#26215C}
.memo-icon{font-size:9.5px;flex-shrink:0;padding-top:1px}
.memo-text{flex:1;outline:none;min-width:0}
.memo-text:focus{background:rgba(255,255,255,0.65);border-radius:3px}
.memo-x{cursor:pointer;color:#7F77DD;background:none;border:none;font-size:9.5px;padding:0 2px;opacity:0;transition:opacity 0.15s;font-family:inherit;flex-shrink:0;line-height:1}
.memo:hover .memo-x{opacity:1}
.add-memo{margin-top:auto;padding:5px 7px;background:rgba(255,255,255,0.85);border:0.5px dashed #B4B2A9;color:#888780;border-radius:5px;cursor:pointer;font-size:9.5px;font-family:'DM Mono',monospace;font-weight:500;letter-spacing:0.6px;width:100%;text-align:center;transition:all 0.15s}
.add-memo:hover{background:#EEEDFE;border-color:#7F77DD;color:#26215C}

.cg-panel{flex:0 0 180px;background:#FAFAF7;border:0.5px solid #D3D1C7;border-radius:10px;padding:11px;display:flex;flex-direction:column;gap:5px;z-index:6;position:relative}
.cg-head{display:flex;align-items:center;justify-content:space-between;padding-bottom:7px;border-bottom:0.5px dashed #D3D1C7;margin-bottom:2px}
.cg-title{font-size:11px;font-weight:500;color:#1a1d23;letter-spacing:0.4px;font-family:'DM Mono',monospace}
.cg-count{font-size:9.5px;color:#888780;font-family:'DM Mono',monospace}
.cg-list{display:flex;flex-direction:column;gap:5px;max-height:540px;overflow-y:auto}
.cg-item{display:flex;align-items:flex-start;gap:4px;padding:5px 7px;background:#fff;border:0.5px solid #E5E3DA;border-radius:5px;font-size:11px;line-height:1.4;color:#2C2C2A}
.cg-num{font-size:9px;color:#185FA5;flex-shrink:0;padding-top:2px;font-family:'DM Mono',monospace;font-weight:500;min-width:14px}
.cg-text{flex:1;outline:none;min-width:0}
.cg-text:focus{background:#F8FAFC;border-radius:3px}
.cg-link{cursor:pointer;background:#F1EFE8;border:none;font-size:8.5px;padding:2px 5px;border-radius:3px;font-family:'DM Mono',monospace;font-weight:500;color:#5F5E5A;flex-shrink:0;letter-spacing:0.3px;line-height:1;height:fit-content;align-self:center;transition:all 0.15s}
.cg-link[data-link^="g"]{}
.cg-link.l-q1{background:#E6F1FB;color:#185FA5}
.cg-link.l-q2{background:#FAECE7;color:#993C1D}
.cg-link.l-q3{background:#EAF3DE;color:#3B6D11}
.cg-link.l-q4{background:#EEEDFE;color:#3C3489}
.cg-link.l-q5{background:#FAEEDA;color:#854F0B}
.cg-link:hover{filter:brightness(0.95)}
.cg-x{cursor:pointer;color:#888780;background:none;border:none;font-size:9.5px;padding:0 2px;opacity:0;transition:opacity 0.15s;font-family:inherit;flex-shrink:0;line-height:1;align-self:center}
.cg-item:hover .cg-x{opacity:0.6}
.cg-add-row{display:flex;gap:5px;margin-top:auto}
.cg-add-row button{flex:1;padding:5px 7px;background:transparent;border:0.5px dashed #B4B2A9;color:#888780;border-radius:5px;cursor:pointer;font-size:9.5px;font-family:'DM Mono',monospace;font-weight:500;letter-spacing:0.5px;text-align:center;transition:all 0.15s}
.add-cg:hover{background:#E6F1FB;border-color:#185FA5;color:#185FA5}
.bulk-cg:hover{background:#FAEEDA;border-color:#BA7517;color:#854F0B}
.bulk-pane{display:flex;flex-direction:column;gap:5px;margin-top:6px}
.bulk-pane[hidden]{display:none}
.bulk-pane textarea{width:100%;min-height:90px;font-size:11px;padding:6px;border:0.5px solid #B4B2A9;border-radius:5px;resize:vertical;font-family:inherit;line-height:1.4;outline:none;box-sizing:border-box}
.bulk-pane textarea:focus{border-color:#185FA5}
.bulk-actions{display:flex;gap:4px;justify-content:flex-end}
.bulk-actions button{padding:4px 10px;font-size:9.5px;border:0.5px solid #B4B2A9;background:#fff;border-radius:4px;cursor:pointer;font-family:'DM Mono',monospace;font-weight:500;color:#5F5E5A}
.bulk-actions .primary{background:#1a1d23;color:#fff;border-color:#1a1d23}

/* 캔버스 툴바 */
.canvas-toolbar{position:absolute;top:8px;right:8px;display:flex;gap:6px;align-items:center;z-index:8}
.tool-btn{background:#fff;border:0.5px solid #D3D1C7;border-radius:6px;padding:5px 10px;cursor:pointer;font-size:11px;font-family:'DM Mono',monospace;color:#1a1d23;display:flex;align-items:center;gap:5px;font-weight:500;letter-spacing:0.4px;box-shadow:0 1px 2px rgba(0,0,0,0.04);transition:all 0.15s}
.tool-btn:hover{background:#FAFAF7;border-color:#A8A6A0}
.tool-btn.primary{background:#1a1d23;color:#e8b84b;border-color:#1a1d23}
.tool-btn.primary:hover{background:#2d3436}
.save-ind{font-size:10px;color:#00b894;font-family:'DM Mono',monospace;letter-spacing:0.5px;opacity:0;transition:opacity 0.3s;padding:0 6px}
.save-ind.saving{color:#888780;opacity:1}
.save-ind.saved{color:#00b894;opacity:1}

.trash-btn{background:#fff;border:0.5px solid #D3D1C7;border-radius:6px;padding:4px 8px;cursor:pointer;font-size:11px;font-family:'DM Mono',monospace;color:#5F5E5A;display:flex;align-items:center;gap:5px;box-shadow:0 1px 2px rgba(0,0,0,0.04);transition:all 0.15s}
.trash-btn[hidden]{display:none}
.trash-btn:hover{background:#FAFAF7;border-color:#A8A6A0}
.trash-count{background:#A32D2D;color:#fff;font-size:9px;padding:1px 5px;border-radius:999px;font-weight:500;font-family:'DM Mono',monospace;min-width:16px;text-align:center;line-height:1.3}
.trash-pane{position:absolute;top:42px;right:8px;background:#fff;border:0.5px solid #D3D1C7;border-radius:8px;padding:8px;width:230px;z-index:9;box-shadow:0 4px 12px rgba(0,0,0,0.06)}
.trash-pane[hidden]{display:none}
.trash-head{font-size:10px;font-weight:500;color:#1a1d23;font-family:'DM Mono',monospace;letter-spacing:0.5px;margin-bottom:6px;padding-bottom:5px;border-bottom:0.5px dashed #D3D1C7;display:flex;justify-content:space-between;align-items:center}
.trash-clear{background:none;border:none;cursor:pointer;font-size:9px;color:#888780;font-family:'DM Mono',monospace;padding:0}
.trash-clear:hover{color:#A32D2D}
.trash-list{display:flex;flex-direction:column;gap:2px;max-height:320px;overflow-y:auto}
.trash-item{display:flex;align-items:center;gap:5px;padding:5px 6px;font-size:11px;color:#444441;border-radius:4px;line-height:1.3}
.trash-item:hover{background:#F1EFE8}
.trash-type{font-size:8.5px;font-family:'DM Mono',monospace;color:#fff;padding:1px 5px;border-radius:3px;flex-shrink:0;letter-spacing:0.3px;font-weight:500}
.trash-type.t-q{background:#1a1d23}
.trash-type.t-blk{background:#854F0B}
.trash-type.t-memo{background:#7F77DD}
.trash-type.t-cg{background:#185FA5}
.trash-text{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.trash-restore{cursor:pointer;background:transparent;border:none;font-size:13px;color:#1a1d23;padding:0 3px;flex-shrink:0;font-family:inherit;line-height:1}
.trash-restore:hover{color:#185FA5}
.trash-empty{font-size:10px;color:#A8A6A0;text-align:center;padding:10px;font-family:'DM Mono',monospace}

.hint{position:absolute;bottom:8px;left:10px;font-size:10px;color:#A8A6A0;font-family:'DM Mono',monospace;letter-spacing:0.4px;pointer-events:none;z-index:1;line-height:1.5}
.hint b{color:#888780;font-weight:500}

.text-menu{position:fixed;background:#fff;border:0.5px solid #1a1d23;border-radius:8px;padding:6px;box-shadow:0 4px 16px rgba(0,0,0,0.12);z-index:100;display:flex;flex-direction:column;gap:4px}
.tm-row{display:flex;gap:3px}
.tm-btn{width:30px;height:28px;border:0.5px solid #D3D1C7;background:#fff;color:#1a1d23;border-radius:4px;cursor:pointer;font-size:13px;font-weight:600;display:inline-flex;align-items:center;justify-content:center;padding:0;font-family:inherit;transition:all 0.1s}
.tm-btn:hover{background:#1a1d23;color:#fff;border-color:#1a1d23}
.empty-state{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;color:#A8A6A0;font-size:13px;line-height:1.7;pointer-events:none}
.empty-state b{color:#888780;font-size:14px}

.import-bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:10px 14px;background:linear-gradient(135deg,#fdfbf5,#fff);border:0.5px solid #e8b84b;border-radius:10px;margin-bottom:12px}
.import-bar[hidden]{display:none}
.import-bar .label{font-size:11px;color:#888780;font-weight:500;letter-spacing:0.3px;font-family:'DM Mono',monospace;flex-shrink:0}
.import-bar .corner-name{font-size:12px;font-weight:600;color:#1a1d23}
.import-btn{padding:5px 11px;background:#fff;border:0.5px solid #e8b84b;color:#1a1d23;border-radius:5px;cursor:pointer;font-size:11px;font-weight:500;letter-spacing:0.2px;transition:all 0.15s;display:inline-flex;align-items:center;gap:4px}
.import-btn:hover{background:#e8b84b;color:#1a1d23;border-color:#1a1d23}
.import-btn .num{font-family:'DM Mono',monospace;font-size:10px;color:#888780;font-weight:500}
.import-btn:hover .num{color:#1a1d23}
.import-btn.dim{opacity:0.55}
.import-refresh{margin-left:auto;padding:4px 10px;background:transparent;border:0.5px solid #B4B2A9;color:#888780;border-radius:5px;cursor:pointer;font-size:10px;font-family:'DM Mono',monospace}
.import-refresh:hover{background:#fff;color:#1a1d23;border-color:#1a1d23}

@media(max-width:780px){
  .wrap{padding:10px}
  .mm{flex-direction:column;min-height:auto}
  .mm-main{order:1}
  .cg-panel{flex:0 0 auto;order:2;max-height:280px;overflow:hidden;display:flex;flex-direction:column}
  .cg-list{max-height:160px}
  .canvas{height:560px}
  .qc{flex:0 0 240px}
  .memo-col{flex:0 0 130px}
  .topbar{padding:10px 14px}
  .canvas-toolbar{top:6px;right:6px}
  .tool-btn{padding:4px 8px;font-size:10px}
}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-title">🗺️ 코너 마인드맵 <span>· Yenny</span></div>
  <a href="/">← 대시보드</a>
</div>

<div class="wrap">

<div class="import-bar" id="import-bar" hidden>
  <span class="label">📥 ON AIR에서:</span>
  <span id="corner-buttons"></span>
  <span style="font-size:9.5px;color:#A8A6A0;font-family:'DM Mono',monospace;letter-spacing:0.3px;margin-left:6px;">버튼 누를 때마다 그 시점 데이터 추가</span>
  <button class="import-refresh" onclick="loadOnAirCorners()" title="ON AIR 데이터 다시 불러오기">↻</button>
</div>

<div class="mm">

  <svg class="links" id="links"></svg>

  <div class="mm-main">
    <div class="canvas" id="canvas">

      <div class="empty-state" id="empty-state">
        <b>비어있어요</b><br>
        우상단 <span style="color:#1a1d23;background:#fff;padding:2px 6px;border-radius:4px;border:0.5px solid #D3D1C7;">＋ NEW Q</span> 누르면 시작
      </div>

      <div class="canvas-toolbar">
        <button class="tool-btn primary" onclick="addQuestion()">＋ NEW Q</button>
        <button class="tool-btn" onclick="clearAll()" style="color:#A32D2D;border-color:#FCC1AF;" title="전체 초기화 (캔버스 + CG + 휴지통)">🗑 비우기</button>
        <span class="save-ind" id="save-ind">저장됨</span>
        <button class="trash-btn" id="trash-btn" hidden onclick="toggleTrash()">🗑 <span class="trash-count" id="trash-count">0</span></button>
      </div>
      <div class="trash-pane" id="trash-pane" hidden>
        <div class="trash-head"><span>최근 삭제</span><button class="trash-clear" onclick="clearTrash()">비우기</button></div>
        <div class="trash-list" id="trash-list"></div>
      </div>

      <div class="hint">
        <b>드래그</b>: Q번호·헤더 잡기 · <b>CG칩</b>: 클릭=Q 순환<br>
        <b>텍스트</b>: ⌘+B/I/U · ⇧+H(노랑) ⇧+D(빨강) ⇧+B(파랑) ⇧+G(초록) ⇧+L(크게) ⇧+N(제거) · <b>우클릭</b>=메뉴
      </div>
    </div>
  </div>

  <div class="cg-panel">
    <div class="cg-head"><span class="cg-title">CG LIST</span><span class="cg-count" id="cg-count">0</span></div>
    <div class="cg-list" id="cg-list"></div>
    <div class="cg-add-row">
      <button class="add-cg" onclick="addCg()">＋ ADD</button>
      <button class="bulk-cg" onclick="openBulk()">📋 BULK</button>
    </div>
    <div class="bulk-pane" id="bulk-pane" hidden>
      <textarea id="bulk-ta" placeholder="줄바꿈으로 구분해서 한꺼번에:&#10;美 3대지수 마감 그래프&#10;코스피 7,000 돌파 차트&#10;원달러 1,360원대 추이"></textarea>
      <div class="bulk-actions">
        <button onclick="closeBulk()">취소</button>
        <button class="primary" onclick="parseBulk()">추가</button>
      </div>
    </div>
  </div>
</div>

</div>

<script>
// fetch wrapper for auth
const _origFetch = window.fetch;
window.fetch = function(url, options){
  options = options || {};
  if(typeof url === 'string' && (url.startsWith('/') || url.startsWith(location.origin))){
    options.credentials = options.credentials || 'include';
    options.headers = options.headers || {};
    if(window._API_SECRET){
      if(options.headers instanceof Headers) options.headers.set('X-API-Secret', window._API_SECRET);
      else options.headers['X-API-Secret'] = window._API_SECRET;
    }
  }
  return _origFetch(url, options);
};

const Q_CYCLE=['','g1','g2','g3','g4','g5'];
const Q_LABEL={'':'—','g1':'Q1','g2':'Q2','g3':'Q3','g4':'Q4','g5':'Q5'};
const Q_COLOR={'g1':'#378ADD','g2':'#D85A30','g3':'#639922','g4':'#7F77DD','g5':'#BA7517'};
const trash=[];
let qCounter=0;
let saveTimer=null;
let dirty=false;

function refreshAll(){
  const mm=document.querySelector('.mm');
  const svg=document.getElementById('links');
  const mmRect=mm.getBoundingClientRect();
  svg.setAttribute('viewBox',`0 0 ${mmRect.width} ${mmRect.height}`);
  while(svg.firstChild)svg.removeChild(svg.firstChild);
  document.querySelectorAll('.cg-item').forEach(cg=>{
    const linkBtn=cg.querySelector('.cg-link');
    if(!linkBtn)return;
    const target=linkBtn.dataset.link;
    if(!target)return;
    const qEl=document.querySelector('#'+target+' .qc');
    if(!qEl)return;
    const cgRect=cg.getBoundingClientRect();
    const qRect=qEl.getBoundingClientRect();
    const sx=cgRect.left-mmRect.left+4;
    const sy=cgRect.top+cgRect.height/2-mmRect.top;
    const ex=qRect.right-mmRect.left;
    const ey=qRect.top+qRect.height/2-mmRect.top;
    const midX=(sx+ex)/2;
    const path=document.createElementNS('http://www.w3.org/2000/svg','path');
    path.setAttribute('d',`M ${sx} ${sy} C ${midX} ${sy}, ${midX} ${ey}, ${ex} ${ey}`);
    path.setAttribute('stroke',Q_COLOR[target]||'#888');
    path.setAttribute('stroke-width','1.4');
    path.setAttribute('stroke-dasharray','3 3');
    path.setAttribute('fill','none');
    path.setAttribute('opacity','0.65');
    svg.appendChild(path);
  });
  // empty state
  const empty=document.getElementById('empty-state');
  if(empty) empty.style.display = document.querySelectorAll('.qgroup').length ? 'none' : 'block';
}

function makeDraggable(group){
  const handle=group.querySelector('.qhead');
  if(!handle) return;
  let sX,sY,oL,oT,dr=false;
  handle.addEventListener('pointerdown',(e)=>{
    if(e.target.closest('[contenteditable]'))return;
    if(e.target.closest('button'))return;
    e.preventDefault();dr=true;
    handle.setPointerCapture(e.pointerId);
    sX=e.clientX;sY=e.clientY;
    oL=parseInt(group.style.left)||0;oT=parseInt(group.style.top)||0;
    group.classList.add('dragging');
  });
  handle.addEventListener('pointermove',(e)=>{
    if(!dr)return;e.preventDefault();
    group.style.left=(oL+e.clientX-sX)+'px';
    group.style.top=(oT+e.clientY-sY)+'px';
    refreshAll();
  });
  const stop=(e)=>{
    if(!dr)return;dr=false;
    group.classList.remove('dragging');
    try{handle.releasePointerCapture(e.pointerId);}catch(err){}
    scheduleSave();
  };
  handle.addEventListener('pointerup',stop);
  handle.addEventListener('pointercancel',stop);
}

function renumberCg(){
  const items=document.querySelectorAll('#cg-list .cg-item');
  items.forEach((it,i)=>{const n=it.querySelector('.cg-num'); if(n) n.textContent=String(i+1).padStart(2,'0');});
  const c=document.getElementById('cg-count'); if(c) c.textContent=items.length;
}

function pushTrash(item){
  trash.unshift(item);
  if(trash.length>30)trash.pop();
  refreshTrash();
}
function refreshTrash(){
  const btn=document.getElementById('trash-btn');
  const count=document.getElementById('trash-count');
  const list=document.getElementById('trash-list');
  count.textContent=trash.length;
  btn.hidden=trash.length===0;
  if(trash.length===0)document.getElementById('trash-pane').hidden=true;
  while(list.firstChild)list.removeChild(list.firstChild);
  if(trash.length===0){
    const e=document.createElement('div');e.className='trash-empty';e.textContent='비어있음';list.appendChild(e);
    return;
  }
  trash.forEach((item,i)=>{
    const div=document.createElement('div');div.className='trash-item';
    const safePre=(item.preview||'').replace(/[<>]/g,'').slice(0,40);
    div.innerHTML='<span class="trash-type t-'+item.type+'">'+item.label+'</span><span class="trash-text">'+safePre+'</span><button class="trash-restore" onclick="restoreTrash('+i+')" title="복구">⤴</button>';
    list.appendChild(div);
  });
}
window.toggleTrash=function(){
  const p=document.getElementById('trash-pane');
  p.hidden=!p.hidden;
};
window.clearTrash=function(){trash.length=0;refreshTrash();};
window.restoreTrash=function(idx){
  const item=trash[idx];if(!item)return;
  const parent=document.querySelector(item.parentSel);if(!parent)return;
  const tmp=document.createElement('div');tmp.innerHTML=item.html;
  const el=tmp.firstElementChild;
  if(item.type==='q'){
    // canvas는 toolbar/trash-btn/hint 같은 정적 요소 보유 → 끝쪽에 단순 append
    parent.appendChild(el);
    makeDraggable(el);
  } else {
    const children=parent.children;
    if(item.index>=children.length)parent.appendChild(el);
    else parent.insertBefore(el,children[item.index]);
    if(item.type==='cg')renumberCg();
  }
  trash.splice(idx,1);
  refreshTrash();
  refreshAll();
  scheduleSave();
};

window.clearAll=function(){
  const cardCount = document.querySelectorAll('.qgroup').length;
  const cgCount = document.querySelectorAll('#cg-list .cg-item').length;
  if(cardCount===0 && cgCount===0 && trash.length===0){
    return;
  }
  if(!confirm('마인드맵 전체를 비울까요?\n\n• Q 카드 '+cardCount+'개\n• CG '+cgCount+'개\n• 휴지통 '+trash.length+'개\n\n※ 복구 불가')) return;
  document.querySelectorAll('.qgroup').forEach(g=>g.remove());
  document.getElementById('cg-list').innerHTML='';
  renumberCg();
  trash.length=0;
  refreshTrash();
  qCounter=0;
  setTimeout(refreshAll,0);
  scheduleSave();
};

window.cycleLink=function(btn){
  const cur=btn.dataset.link||'';
  const idx=Q_CYCLE.indexOf(cur);
  const next=Q_CYCLE[(idx+1)%Q_CYCLE.length];
  btn.dataset.link=next;
  btn.textContent=Q_LABEL[next];
  btn.className='cg-link';
  if(next) btn.classList.add('l-'+next.replace('g','q'));
  refreshAll();
  scheduleSave();
};

window.addMemo=function(mid){
  const memos=document.querySelector('#'+mid+' .memos');
  if(!memos)return;
  const div=document.createElement('div');div.className='memo';
  div.innerHTML='<span class="memo-icon">💭</span><span class="memo-text" contenteditable="true">하고 싶은 말</span><button class="memo-x" onclick="rmEl(this)">✕</button>';
  memos.appendChild(div);
  const t=div.querySelector('.memo-text');t.focus();
  const r=document.createRange();r.selectNodeContents(t);
  const s=window.getSelection();s.removeAllRanges();s.addRange(r);
  setTimeout(refreshAll,0);
  scheduleSave();
};

// 빈 블록 추가 — 라벨/내용 자유 편집
window.addEmptyBlk=function(btn){
  const qc=btn.closest('.qc');if(!qc)return;
  const div=document.createElement('div');
  div.className='blk b-int';
  div.innerHTML='<span class="blk-handle" draggable="true" title="드래그로 순서 변경">⋮⋮</span>'+
    '<span class="lbl" contenteditable="true" data-placeholder="라벨"></span>'+
    '<span class="blk-text" contenteditable="true">내용 입력...</span>'+
    '<button class="blk-x" onclick="rmEl(this)">✕</button>';
  // add-blk-row 앞에 삽입
  const row=qc.querySelector('.add-blk-row');
  qc.insertBefore(div, row);
  const t=div.querySelector('.blk-text');t.focus();
  const r=document.createRange();r.selectNodeContents(t);
  const s=window.getSelection();s.removeAllRanges();s.addRange(r);
  setTimeout(refreshAll,0);
  scheduleSave();
};

// === 블록 드래그 정렬 (이벤트 위임) ===
let _draggingBlk = null;
document.addEventListener('dragstart', (e)=>{
  const handle = e.target.closest('.blk-handle');
  if(!handle) return;
  const blk = handle.closest('.blk');
  if(!blk) return;
  _draggingBlk = blk;
  blk.classList.add('blk-dragging');
  try {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', '');
  } catch(err){}
});
document.addEventListener('dragover', (e)=>{
  if(!_draggingBlk) return;
  const targetBlk = e.target.closest('.blk');
  if(!targetBlk || targetBlk === _draggingBlk) return;
  // 같은 카드 안에서만 순서 변경
  if(_draggingBlk.parentNode !== targetBlk.parentNode) return;
  e.preventDefault();
  const rect = targetBlk.getBoundingClientRect();
  const middle = rect.top + rect.height/2;
  if(e.clientY < middle){
    targetBlk.parentNode.insertBefore(_draggingBlk, targetBlk);
  } else {
    targetBlk.parentNode.insertBefore(_draggingBlk, targetBlk.nextSibling);
  }
});
document.addEventListener('dragend', (e)=>{
  if(!_draggingBlk) return;
  _draggingBlk.classList.remove('blk-dragging');
  _draggingBlk = null;
  setTimeout(refreshAll, 0);
  scheduleSave();
});

window.addQuestion=function(){
  qCounter++;
  const id='g'+Date.now()+'_'+qCounter;
  const colorIdx=((qCounter-1)%5)+1;
  const colorClass='q'+colorIdx;
  const qLabel='Q'+qCounter;
  // 위치: 기존 카드들 아래 또는 우측
  const groups=document.querySelectorAll('.qgroup');
  let topY=10, leftX=8;
  if(groups.length){
    let maxBottom=0;
    groups.forEach(g=>{
      const t=parseInt(g.style.top)||0;
      const h=g.offsetHeight;
      maxBottom=Math.max(maxBottom, t+h);
    });
    topY=maxBottom+18;
    leftX=8+(groups.length%4)*20;
  }
  const html='<div class="qgroup" id="'+id+'" style="top:'+topY+'px;left:'+leftX+'px">'+
    '<div class="qc '+colorClass+'">'+
      '<div class="qhead">'+
        '<span class="qnum">'+qLabel+'</span>'+
        '<span class="qlbl" contenteditable="true">(제목 입력)</span>'+
        '<button class="qc-x" onclick="rmQ(this)" title="질문 삭제">✕</button>'+
      '</div>'+
      '<div class="blk b-q">'+
        '<span class="blk-handle" draggable="true">⋮⋮</span>'+
        '<span class="lbl" contenteditable="true" data-placeholder="라벨">[질문]</span>'+
        '<span class="blk-text" contenteditable="true">(질문 입력)</span>'+
        '<button class="blk-x" onclick="rmEl(this)">✕</button>'+
      '</div>'+
      '<div class="add-blk-row">'+
        '<button class="add-blk" onclick="addEmptyBlk(this)">＋ 추가</button>'+
      '</div>'+
    '</div>'+
    '<div class="memo-col" id="m_'+id+'">'+
      '<div class="memos"></div>'+
      '<button class="add-memo" onclick="addMemo(\'m_'+id+'\')">＋ MORE IDEAS?</button>'+
    '</div>'+
  '</div>';
  const canvas=document.getElementById('canvas');
  const tmp=document.createElement('div');tmp.innerHTML=html;
  const newGroup=tmp.firstElementChild;
  canvas.appendChild(newGroup);
  makeDraggable(newGroup);
  // 새 카드 헤더 포커스
  setTimeout(()=>{
    const lbl=newGroup.querySelector('.qlbl');
    if(lbl){
      lbl.focus();
      const r=document.createRange();r.selectNodeContents(lbl);
      const s=window.getSelection();s.removeAllRanges();s.addRange(r);
    }
    refreshAll();
  },50);
  scheduleSave();
};

function makeCgItem(text){
  const div=document.createElement('div');div.className='cg-item';
  div.innerHTML='<span class="cg-num"></span><span class="cg-text" contenteditable="true"></span><button class="cg-link" data-link="" onclick="cycleLink(this)">—</button><button class="cg-x" onclick="rmCg(this)">✕</button>';
  div.querySelector('.cg-text').textContent=text||'새 CG';
  return div;
}
window.addCg=function(){
  const list=document.getElementById('cg-list');
  const div=makeCgItem('');list.appendChild(div);
  const t=div.querySelector('.cg-text');t.focus();
  const r=document.createRange();r.selectNodeContents(t);
  const s=window.getSelection();s.removeAllRanges();s.addRange(r);
  renumberCg();setTimeout(refreshAll,0);
  scheduleSave();
};
window.rmEl=function(btn){
  const el=btn.parentElement;const parent=el.parentElement;
  const index=Array.from(parent.children).indexOf(el);
  if(el.classList.contains('memo')){
    const mc=el.closest('.memo-col');
    pushTrash({type:'memo',label:'💭',preview:el.querySelector('.memo-text').textContent.trim()||'(빈 메모)',html:el.outerHTML,parentSel:'#'+mc.id+' .memos',index});
  }else if(el.classList.contains('blk')){
    const qg=el.closest('.qgroup');
    const lblTxt=el.querySelector('.lbl').textContent.trim();
    const tag=lblTxt.replace(/[\[\]🎯▶⇒★💫☕]/g,'').trim().slice(0,4)||'블록';
    pushTrash({type:'blk',label:tag,preview:el.querySelector('.blk-text').textContent.trim()||'(빈 블록)',html:el.outerHTML,parentSel:'#'+qg.id+' .qc',index});
  }
  el.remove();setTimeout(refreshAll,0);
  scheduleSave();
};
window.rmCg=function(btn){
  const item=btn.parentElement;const parent=item.parentElement;
  const index=Array.from(parent.children).indexOf(item);
  pushTrash({type:'cg',label:'CG',preview:item.querySelector('.cg-text').textContent.trim()||'(빈 CG)',html:item.outerHTML,parentSel:'#cg-list',index});
  item.remove();renumberCg();setTimeout(refreshAll,0);
  scheduleSave();
};
window.rmQ=function(btn){
  const qg=btn.closest('.qgroup');
  const qnum=qg.querySelector('.qnum').textContent.trim();
  const qlbl=qg.querySelector('.qlbl').textContent.trim();
  pushTrash({type:'q',label:qnum,preview:qlbl||'(제목 없음)',html:qg.outerHTML,parentSel:'#canvas',index:0});
  qg.remove();setTimeout(refreshAll,0);
  scheduleSave();
};

window.openBulk=function(){
  document.querySelector('.cg-add-row').style.display='none';
  document.getElementById('bulk-pane').hidden=false;
  document.getElementById('bulk-ta').focus();
};
window.closeBulk=function(){
  document.querySelector('.cg-add-row').style.display='';
  document.getElementById('bulk-pane').hidden=true;
  document.getElementById('bulk-ta').value='';
};
window.parseBulk=function(){
  const ta=document.getElementById('bulk-ta');
  const lines=ta.value.split('\n').map(l=>l.replace(/^\s*[-•*\d.)]+\s*/,'').trim()).filter(l=>l);
  const list=document.getElementById('cg-list');
  lines.forEach(line=>list.appendChild(makeCgItem(line)));
  renumberCg();closeBulk();setTimeout(refreshAll,0);
  scheduleSave();
};

// === ON AIR 데이터 가져오기 ===
let _onAirCorners = [];

function escapeHtml(s){
  return (s==null?'':String(s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function parseOnAirText(text){
  if(!text || !text.trim()) return [];
  const lines = text.split('\n');
  const corners = [];
  let current = null;
  for(const line of lines){
    const m = line.match(/^\s*#(\d+)\s*\.?\s*(.*)/);
    if(m){
      if(current) corners.push(current);
      current = {number:m[1], title:m[2].trim()||'코너'+m[1], body:[]};
    } else if(current){
      current.body.push(line);
    }
  }
  if(current) corners.push(current);
  return corners;
}

function parseQuestionsFromBody(bodyLines){
  const qs = [];
  let current = null;
  const qHeaderRe = /^\s*Q[\d-]+\s*\.\s*/;
  for(const line of bodyLines){
    if(qHeaderRe.test(line)){
      if(current) qs.push(current);
      current = {header: line.trim(), body: []};
    } else if(current){
      current.body.push(line);
    }
  }
  if(current) qs.push(current);
  qs.forEach(q=>{
    while(q.body.length && !q.body[0].trim()) q.body.shift();
    while(q.body.length && !q.body[q.body.length-1].trim()) q.body.pop();
  });
  return qs;
}

// 한 줄 = 한 블록. 분류·합치기 안 함. 마커는 그대로 라벨에 살림.
function parseBlocksFromBody(bodyText){
  const items = [];
  if(!bodyText) return items;
  const lines = bodyText.split('\n');
  for(const raw of lines){
    const trimmed = raw.trim();
    if(!trimmed) continue;
    // ⇒ 자막은 무시
    if(/^⇒/.test(trimmed)) continue;
    
    let marker = '', text = trimmed, cls = 'b-int';
    let m;
    
    // 🎯 의도
    if((m = trimmed.match(/^🎯\s*(?:질문\s*의도\s*[:：]\s*)?(.*)/))){
      marker = '🎯 의도'; text = m[1].trim(); cls = 'b-int';
    }
    // ▶ DB / DB연결
    else if((m = trimmed.match(/^▶\s*(.*)/))){
      marker = '▶ DB'; text = m[1].trim(); cls = 'b-cb';
    }
    // → [콜백] 또는 → 콜백
    else if((m = trimmed.match(/^→\s*\[콜백\]\s*(.*)/)) || (m = trimmed.match(/^→\s*콜백\s*[:：]?\s*(.*)/))){
      marker = '→ 콜백'; text = m[1].trim(); cls = 'b-cb';
    }
    // [콜백]
    else if((m = trimmed.match(/^\[콜백\]\s*(.*)/))){
      marker = '[콜백]'; text = m[1].trim(); cls = 'b-cb';
    }
    // [💫 말랑] 또는 [말랑]
    else if((m = trimmed.match(/^\[(?:💫\s*)?말랑\]\s*(.*)/))){
      marker = '💫 말랑'; text = m[1].trim(); cls = 'b-mr';
    }
    // [송곳] 또는 [🎯송곳]
    else if((m = trimmed.match(/^\[(?:🎯\s*)?송곳\]\s*(.*)/))){
      marker = '🎯 송곳'; text = m[1].trim(); cls = 'b-sw';
    }
    // [상황] / [배경]
    else if((m = trimmed.match(/^\[(상황|배경)\]\s*(.*)/))){
      marker = '['+m[1]+']'; text = m[2].trim(); cls = 'b-st';
    }
    // [질문] 또는 ❓
    else if((m = trimmed.match(/^\[질문\]\s*(.*)/)) || (m = trimmed.match(/^❓\s*(.*)/))){
      marker = '[질문]'; text = m[1].trim(); cls = 'b-q';
    }
    // 기타 [XXX] 마커 (이름표 등)
    else if((m = trimmed.match(/^\[([^\]]+)\]\s*(.*)/))){
      marker = '['+m[1]+']'; text = m[2].trim(); cls = 'b-int';
    }
    // 마커 없는 일반 줄
    else {
      marker = ''; text = trimmed; cls = 'b-int';
    }
    
    if(!text) text = '(빈 줄)';
    items.push({marker, text, cls});
  }
  return items;
}

function createCardFromQ(q, baseTopY, leftX){
  // 헤더 파싱
  let qNum = '', qTitle = '';
  const m = q.header.match(/^(Q[\d-]+)\s*\.\s*(.+?)$/);
  if(m){
    qNum = m[1];
    qTitle = m[2].trim();
  } else {
    qNum = (q.header.match(/Q[\d-]+/)||['Q?'])[0];
    qTitle = q.header;
  }
  // [신뢰형] [🅰️ 신뢰형] [반종민] 같은 분류·이름 마커 제거
  qTitle = qTitle.replace(/\[[^\]]+\]/g, '').trim();
  
  const bodyText = q.body.join('\n').trim();
  const items = parseBlocksFromBody(bodyText);
  
  qCounter++;
  const id = 'g'+Date.now()+'_'+qCounter;
  const colorIdx = ((qCounter-1) % 5) + 1;
  const colorClass = 'q'+colorIdx;
  
  // 줄별로 별개 블록 렌더 — 분류·합치기 안 함
  let blocksHtml = '';
  items.forEach(it => {
    blocksHtml += '<div class="blk '+it.cls+'">'+
      '<span class="blk-handle" draggable="true" title="드래그로 순서 변경">⋮⋮</span>'+
      '<span class="lbl" contenteditable="true" data-placeholder="라벨">'+escapeHtml(it.marker)+'</span>'+
      '<span class="blk-text" contenteditable="true">'+escapeHtml(it.text)+'</span>'+
      '<button class="blk-x" onclick="rmEl(this)">✕</button>'+
    '</div>';
  });
  // 빈 카드 방지 — 본문 없으면 빈 [질문] 블록
  if(!blocksHtml){
    blocksHtml = '<div class="blk b-q">'+
      '<span class="blk-handle" draggable="true">⋮⋮</span>'+
      '<span class="lbl" contenteditable="true" data-placeholder="라벨">[질문]</span>'+
      '<span class="blk-text" contenteditable="true">'+escapeHtml(qTitle || '(질문 입력)')+'</span>'+
      '<button class="blk-x" onclick="rmEl(this)">✕</button>'+
    '</div>';
  }
  
  const html = '<div class="qgroup" id="'+id+'" style="top:'+baseTopY+'px;left:'+leftX+'px">'+
    '<div class="qc '+colorClass+'">'+
      '<div class="qhead">'+
        '<span class="qnum">'+escapeHtml(qNum)+'</span>'+
        '<span class="qlbl" contenteditable="true">'+escapeHtml(qTitle || '(제목)')+'</span>'+
        '<button class="qc-x" onclick="rmQ(this)" title="질문 삭제">✕</button>'+
      '</div>'+
      blocksHtml +
      '<div class="add-blk-row">'+
        '<button class="add-blk" onclick="addEmptyBlk(this)">＋ 추가</button>'+
      '</div>'+
    '</div>'+
    '<div class="memo-col" id="m_'+id+'">'+
      '<div class="memos"></div>'+
      '<button class="add-memo" onclick="addMemo(\'m_'+id+'\')">＋ MORE IDEAS?</button>'+
    '</div>'+
  '</div>';
  
  const canvas = document.getElementById('canvas');
  const tmp = document.createElement('div');
  tmp.innerHTML = html;
  const newGroup = tmp.firstElementChild;
  canvas.appendChild(newGroup);
  makeDraggable(newGroup);
  return newGroup;
}

window.importCorner = function(idx){
  const corner = _onAirCorners[idx];
  if(!corner) return;
  const qs = parseQuestionsFromBody(corner.body);
  if(!qs.length){
    alert('이 코너에 Q1, Q2 같은 질문 카드가 없어요.\n\nON AIR 텍스트에서 "Q1." 형식으로 질문을 정리해주세요.');
    return;
  }
  // 기존 카드 아래에 떨어뜨리기
  const groups = document.querySelectorAll('.qgroup');
  let topY = 10;
  if(groups.length){
    let maxBottom = 0;
    groups.forEach(g=>{
      const t = parseInt(g.style.top)||0;
      const h = g.offsetHeight;
      maxBottom = Math.max(maxBottom, t+h);
    });
    topY = maxBottom + 24;
  }
  // 코너 그룹 라벨처럼 가로로 펼치기 (각 카드 280px + 메모 156px + 간격)
  const cardWidth = 460;  // qc + memo-col + gap
  qs.forEach((q, i)=>{
    createCardFromQ(q, topY, 8 + i * cardWidth);
  });
  setTimeout(refreshAll, 50);
  scheduleSave();
  // 시각 피드백
  const btn = document.querySelectorAll('#corner-buttons .import-btn')[idx];
  if(btn){
    btn.classList.add('dim');
    btn.innerHTML = '✓ ' + btn.innerHTML;
    setTimeout(()=>{
      btn.classList.remove('dim');
      btn.innerHTML = btn.innerHTML.replace(/^✓\s*/, '');
    }, 2500);
  }
};

function renderCornerImportBar(corners){
  const bar = document.getElementById('import-bar');
  const buttonsEl = document.getElementById('corner-buttons');
  if(!bar || !buttonsEl) return;
  if(!corners.length){
    bar.hidden = true;
    return;
  }
  bar.hidden = false;
  buttonsEl.innerHTML = corners.map((c,i)=>{
    const qCount = parseQuestionsFromBody(c.body).length;
    const qLabel = qCount > 0 ? ' · Q'+qCount : '';
    return '<button class="import-btn" onclick="importCorner('+i+')" title="이 코너의 Q 카드들을 마인드맵으로 가져오기">'+
      '<span class="num">#'+escapeHtml(c.number)+'</span>'+
      '<span class="corner-name">'+escapeHtml(c.title)+'</span>'+
      '<span style="font-size:9.5px;color:#888780;font-family:DM Mono,monospace;">'+qLabel+'</span>'+
      '</button>';
  }).join(' ');
}

window.loadOnAirCorners = async function(){
  try{
    const d = await fetch('/api/post/wdaebon').then(r=>r.json());
    if(!d || !d.content){
      _onAirCorners = [];
      renderCornerImportBar([]);
      return;
    }
    let text = d.content;
    try{
      const payload = JSON.parse(d.content);
      if(payload && typeof payload === 'object' && payload.text !== undefined){
        text = payload.text;
      }
    }catch(e){}
    _onAirCorners = parseOnAirText(text);
    renderCornerImportBar(_onAirCorners);
  }catch(e){
    console.error('Load ON AIR error:', e);
  }
};


function serialize(){
  const groups=[...document.querySelectorAll('.qgroup')].map(g=>g.outerHTML);
  const cgItems=[...document.querySelectorAll('#cg-list .cg-item')].map(i=>i.outerHTML);
  return JSON.stringify({groups, cgItems, qCounter, ts:Date.now()});
}

function deserialize(text){
  try{
    const data=JSON.parse(text);
    const canvas=document.getElementById('canvas');
    canvas.querySelectorAll('.qgroup').forEach(g=>g.remove());
    (data.groups||[]).forEach(html=>{
      const tmp=document.createElement('div');tmp.innerHTML=html;
      const g=tmp.firstElementChild;
      canvas.appendChild(g);
      makeDraggable(g);
    });
    const list=document.getElementById('cg-list');
    list.innerHTML='';
    (data.cgItems||[]).forEach(html=>{
      const tmp=document.createElement('div');tmp.innerHTML=html;
      list.appendChild(tmp.firstElementChild);
    });
    qCounter=data.qCounter||document.querySelectorAll('.qgroup').length;
    renumberCg();
    setTimeout(refreshAll,50);
  }catch(e){console.error('Load error:',e);}
}

function indSaving(){
  const i=document.getElementById('save-ind');
  if(!i)return;
  i.textContent='저장 중...';i.className='save-ind saving';
}
function indSaved(){
  const i=document.getElementById('save-ind');
  if(!i)return;
  i.textContent='✓ 저장됨';i.className='save-ind saved';
  setTimeout(()=>{i.style.opacity=0.3;},1800);
}
function indError(){
  const i=document.getElementById('save-ind');
  if(!i)return;
  i.textContent='✕ 저장 실패';i.style.color='#A32D2D';i.style.opacity=1;
}

async function saveMindmap(){
  try{
    indSaving();
    const content=serialize();
    const res=await fetch('/api/post/mindmap',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({content,date:new Date().toISOString().slice(0,10)})
    });
    if(!res.ok){indError();return;}
    indSaved();
  }catch(e){indError();}
}

function scheduleSave(){
  dirty=true;
  if(saveTimer)clearTimeout(saveTimer);
  saveTimer=setTimeout(()=>{saveMindmap();dirty=false;},1500);
}

async function loadMindmap(){
  try{
    const d=await fetch('/api/post/mindmap').then(r=>r.json());
    if(d&&d.content){deserialize(d.content);}
    else{refreshAll();}
  }catch(e){refreshAll();}
}

// contenteditable 변경 감지 → 자동 저장
document.addEventListener('input',(e)=>{
  if(e.target.matches&&e.target.matches('[contenteditable]'))scheduleSave();
});
window.addEventListener('resize',refreshAll);
const ro=new ResizeObserver(refreshAll);
ro.observe(document.querySelector('.mm'));

// 페이지 떠나기 전 저장 보장
window.addEventListener('beforeunload',(e)=>{
  if(dirty){
    saveMindmap();
  }
});

// === 텍스트 효과 단축키 (Q 카드 / 메모 / CG 안에서) ===
document.addEventListener('keydown', function(e){
  const active = document.activeElement;
  if(!active || !active.isContentEditable) return;
  if(!active.closest('.qgroup, .cg-item')) return;
  const mod = e.metaKey || e.ctrlKey;
  if(!mod) return;
  // Cmd/Ctrl + B/I/U는 브라우저 기본 동작으로 처리됨 (자동)
  if(!e.shiftKey) return;
  const key = e.key.toLowerCase();
  if(key === 'h'){ e.preventDefault(); document.execCommand('backColor', false, '#fff3a0'); }
  else if(key === 'y'){ e.preventDefault(); document.execCommand('backColor', false, '#FFD6D6'); }   // 분홍 하이라이트
  else if(key === 'p'){ e.preventDefault(); document.execCommand('backColor', false, '#D6F0FF'); }   // 파랑 하이라이트
  else if(key === 'x'){ e.preventDefault(); document.execCommand('backColor', false, 'transparent'); } // 하이라이트 제거
  else if(key === 'l'){ e.preventDefault(); document.execCommand('fontSize', false, '5'); }
  else if(key === 'b'){ e.preventDefault(); document.execCommand('foreColor', false, '#0984e3'); }   // 파란 글자
  else if(key === 'g'){ e.preventDefault(); document.execCommand('foreColor', false, '#00b894'); }   // 초록 글자
  else if(key === 'd'){ e.preventDefault(); document.execCommand('foreColor', false, '#d63031'); }   // 빨간 글자
  else if(key === 'n'){ e.preventDefault(); document.execCommand('foreColor', false, ''); document.execCommand('backColor', false, 'transparent'); } // 색깔 다 제거
}, true);

// 우클릭 메뉴 — 텍스트 효과 빠르게 적용 (PWA/모바일에선 길게 누르기)
document.addEventListener('contextmenu', function(e){
  const target = e.target;
  if(!target || !target.isContentEditable) return;
  if(!target.closest('.qgroup, .cg-item')) return;
  // 텍스트 선택 있을 때만 효과
  const sel = window.getSelection();
  if(!sel.rangeCount || sel.toString().length === 0) return;
  e.preventDefault();
  showTextMenu(e.clientX, e.clientY, target);
});

function showTextMenu(x, y, target){
  const old = document.getElementById('text-menu');
  if(old) old.remove();
  const menu = document.createElement('div');
  menu.id = 'text-menu';
  menu.className = 'text-menu';
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';
  menu.innerHTML =
    '<div class="tm-row">'+
      '<button class="tm-btn" onclick="document.execCommand(\'bold\');closeTextMenu()" title="굵게"><b>B</b></button>'+
      '<button class="tm-btn" onclick="document.execCommand(\'italic\');closeTextMenu()" title="기울임"><i>I</i></button>'+
      '<button class="tm-btn" onclick="document.execCommand(\'underline\');closeTextMenu()" title="밑줄"><u>U</u></button>'+
      '<button class="tm-btn" onclick="document.execCommand(\'strikeThrough\');closeTextMenu()" title="취소선"><s>S</s></button>'+
    '</div>'+
    '<div class="tm-row">'+
      '<button class="tm-btn" style="background:#fff3a0" onclick="document.execCommand(\'backColor\',false,\'#fff3a0\');closeTextMenu()" title="노랑">H</button>'+
      '<button class="tm-btn" style="background:#FFD6D6" onclick="document.execCommand(\'backColor\',false,\'#FFD6D6\');closeTextMenu()" title="분홍">H</button>'+
      '<button class="tm-btn" style="background:#D6F0FF" onclick="document.execCommand(\'backColor\',false,\'#D6F0FF\');closeTextMenu()" title="파랑">H</button>'+
      '<button class="tm-btn" onclick="document.execCommand(\'backColor\',false,\'transparent\');closeTextMenu()" title="제거">✕</button>'+
    '</div>'+
    '<div class="tm-row">'+
      '<button class="tm-btn" style="color:#d63031" onclick="document.execCommand(\'foreColor\',false,\'#d63031\');closeTextMenu()" title="빨강"><b>A</b></button>'+
      '<button class="tm-btn" style="color:#0984e3" onclick="document.execCommand(\'foreColor\',false,\'#0984e3\');closeTextMenu()" title="파랑"><b>A</b></button>'+
      '<button class="tm-btn" style="color:#00b894" onclick="document.execCommand(\'foreColor\',false,\'#00b894\');closeTextMenu()" title="초록"><b>A</b></button>'+
      '<button class="tm-btn" onclick="document.execCommand(\'foreColor\',false,\'\');closeTextMenu()" title="기본"><b>A</b></button>'+
    '</div>';
  document.body.appendChild(menu);
  // 클릭 다른 곳 → 닫기
  setTimeout(()=>{
    document.addEventListener('click', closeTextMenu, {once:true});
  }, 50);
}
window.closeTextMenu = function(){
  const m = document.getElementById('text-menu');
  if(m) m.remove();
  scheduleSave();
};

// 초기 로드
loadMindmap();
loadOnAirCorners();

// === ON AIR 자동 동기화 ===
// 1) 다른 탭에서 돌아오면 즉시 새로고침
document.addEventListener('visibilitychange', ()=>{
  if(!document.hidden) loadOnAirCorners();
});
window.addEventListener('focus', ()=>{
  loadOnAirCorners();
});
// 2) 30초마다 백그라운드 fetch (탭이 활성일 때만)
setInterval(()=>{
  if(!document.hidden) loadOnAirCorners();
}, 30000);
</script>

</body>
</html>"""

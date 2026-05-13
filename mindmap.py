"""
Yenny Dashboard - Mindmap Module (v2: Q 섹션 데크 + 매소너리 그리드)
URL: /mindmap
저장: 'mindmap' 타입으로 PostgreSQL에 자동 저장 (1.5초 debounce)

구조:
  Q 섹션들이 세로로 데크처럼 쌓임
  각 섹션 헤더 = Q 번호/타입/출연자/제목 + 접기/순서/삭제
  각 섹션 본체 = Q comments + CG 매소너리 그리드 (columns: auto)

데이터:
{
  corner: { title, subtitle, questions: [
    {id, number, type, guest, title, collapsed,
     cgs: [{id, image, caption, comments: [{id, text}]}],
     comments: [{id, label, text}]}
  ]}
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
.save-ind{font-size:10px;color:#00b894;font-family:'DM Mono',monospace;letter-spacing:0.3px;opacity:0;transition:opacity 0.3s;padding:0 6px;white-space:nowrap;max-width:280px;overflow:hidden;text-overflow:ellipsis}
.save-ind.saving{color:#fff;opacity:1}
.save-ind.saved{color:#00b894;opacity:1}
.save-ind.error{color:#ff7878;opacity:1}

.wrap{padding:18px;max-width:1600px;margin:0 auto}

.mm{background:#fff;border:0.5px solid #D3D1C7;border-radius:12px;padding:16px 18px;min-height:640px}
.mm-corner-head{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:12px;margin-bottom:14px;border-bottom:0.5px solid #D3D1C7;gap:14px}
.mm-corner-meta{flex:1;min-width:0}
.mm-corner-label{font-size:11px;color:#5F5E5A;font-family:'DM Mono',monospace;letter-spacing:0.5px;margin-bottom:4px}
.mm-corner-title{font-size:18px;font-weight:500;line-height:1.4;border:none;background:transparent;outline:none;width:100%;padding:0;color:#1a1d23}
.mm-corner-title::placeholder{color:#B4B2A9}
.mm-corner-sub{font-size:12.5px;color:#5F5E5A;border:none;background:transparent;outline:none;width:100%;padding:3px 0 0;margin-top:2px}
.mm-corner-sub::placeholder{color:#B4B2A9}
.mm-quick-q{width:100%;border:0.5px dashed #B4B2A9;background:transparent;border-radius:6px;padding:8px 12px;font-size:13px;outline:none;margin-top:10px;color:#1a1d23;transition:all 0.12s}
.mm-quick-q:focus{border-color:#1a1d23;background:#fff;border-style:solid}
.mm-quick-q::placeholder{color:#B4B2A9}
.mm-shortcuts-hint{font-size:10px;color:#888780;font-family:'DM Mono',monospace;letter-spacing:0.2px;margin-top:6px;line-height:1.5}
.mm-shortcuts-hint kbd{font-family:inherit;background:#F1EFE8;padding:1px 5px;border-radius:3px;border:0.5px solid #D3D1C7;color:#412402;font-size:9.5px}

.mm-actions{display:flex;gap:6px;align-items:center;align-self:center}
.mm-onair-wrap{position:relative}
.mm-onair-btn{font-size:11px;padding:6px 11px;background:#FAEEDA;color:#633806;border:0.5px solid #BA7517;border-radius:6px;cursor:pointer;white-space:nowrap;display:flex;align-items:center;gap:5px;font-family:'DM Mono',monospace;letter-spacing:0.3px}
.mm-onair-btn:hover{background:#EF9F27;color:#fff;border-color:#854F0B}
.mm-onair-btn .caret{font-size:8px;opacity:0.6}
.mm-onair-menu{position:absolute;top:100%;right:0;margin-top:4px;background:#fff;border:0.5px solid #D3D1C7;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.12);min-width:300px;z-index:60;padding:6px;max-height:420px;overflow-y:auto}
.mm-onair-refresh{display:flex;align-items:center;justify-content:center;gap:5px;width:100%;padding:6px;border:0.5px dashed #D3D1C7;background:transparent;border-radius:5px;cursor:pointer;font-size:11px;color:#888780;margin-bottom:5px}
.mm-onair-refresh:hover{border-color:#888780;color:#1a1d23}
.mm-onair-item{display:block;width:100%;text-align:left;padding:8px 10px;background:transparent;border:none;cursor:pointer;border-radius:5px;line-height:1.4;border-bottom:0.5px solid #F1EFE8}
.mm-onair-item:last-child{border-bottom:none}
.mm-onair-item:hover{background:#FDF7EC}
.mm-onair-item .num{font-family:'DM Mono',monospace;color:#854F0B;font-size:10px;margin-right:7px;background:#FAEEDA;padding:1px 5px;border-radius:3px}
.mm-onair-item .title{color:#1a1d23;font-weight:500;font-size:12.5px}
.mm-onair-item .meta{display:block;color:#888780;font-size:10px;margin-top:3px;font-family:'DM Mono',monospace}
.mm-onair-empty{padding:18px 10px;text-align:center;color:#888780;font-size:11px;line-height:1.5}
.mm-onair-reset{display:flex;align-items:center;justify-content:center;gap:5px;width:100%;padding:7px;border:0.5px dashed #E68A8A;background:#FCEBEB;border-radius:5px;cursor:pointer;font-size:11px;color:#A32D2D;margin-top:6px;font-family:'Noto Sans KR',sans-serif}
.mm-onair-reset:hover{border-color:#A32D2D;background:#F5C9C9;border-style:solid}
.mm-new-q{font-size:12px;padding:6px 14px;background:#1a1d23;color:#e8b84b;border:0.5px solid #1a1d23;border-radius:6px;cursor:pointer;white-space:nowrap;display:flex;align-items:center;gap:5px;height:fit-content;align-self:center}
.mm-new-q:hover{background:#2C2C2A}

/* === Q 섹션 데크 === */
.mm-sections{display:flex;flex-direction:column;gap:12px}
.mm-section{border-radius:10px;overflow:hidden;border:0.5px solid #D3D1C7;transition:opacity 0.2s}
.mm-section.mm-dragging{opacity:0.45}
.mm-section.q1{background:#F0F7FE;border-left:3px solid #378ADD}
.mm-section.q2{background:#FCF1ED;border-left:3px solid #D85A30}
.mm-section.q3{background:#F4F9EC;border-left:3px solid #639922}
.mm-section.q4{background:#F7F6FE;border-left:3px solid #7F77DD}
.mm-section.q5{background:#FBF5EA;border-left:3px solid #BA7517}

.mm-section-head{display:flex;align-items:center;gap:8px;padding:9px 12px;background:rgba(255,255,255,0.55);flex-wrap:wrap}
.mm-section-grip{font-size:11px;color:#B4B2A9;cursor:grab;letter-spacing:-2px;user-select:none;flex-shrink:0;opacity:0.5;transition:opacity 0.1s}
.mm-section-head:hover .mm-section-grip{opacity:1}
.mm-section-grip:active{cursor:grabbing}
.mm-q-num{font-size:9.5px;padding:2px 7px;color:#fff;border-radius:4px;font-family:'DM Mono',monospace;font-weight:500;outline:none;min-width:22px;text-align:center;flex-shrink:0}
.q1 .mm-q-num{background:#378ADD}
.q2 .mm-q-num{background:#D85A30}
.q3 .mm-q-num{background:#639922}
.q4 .mm-q-num{background:#7F77DD}
.q5 .mm-q-num{background:#BA7517}
.mm-q-type{font-size:11px;padding:2px 8px;background:#fff;color:#0C447C;border:0.5px solid rgba(0,0,0,0.06);border-radius:4px;outline:none;width:100px;flex-shrink:0}
.mm-q-type:focus{border-color:#378ADD}
.mm-q-guest{font-size:11px;padding:2px 8px;background:#fff;color:#633806;border:0.5px solid rgba(0,0,0,0.06);border-radius:4px;outline:none;font-family:'DM Mono',monospace;width:80px;flex-shrink:0}
.mm-q-guest:focus{border-color:#BA7517}
.mm-q-title-input{flex:1;min-width:200px;font-size:13.5px;font-weight:500;line-height:1.45;border:none;background:transparent;outline:none;resize:none;padding:2px 0;color:#1a1d23;overflow:hidden;font-family:inherit;min-height:22px}
.mm-q-title-input::placeholder{color:#B4B2A9}
.mm-section-meta{font-size:10px;color:#888780;font-family:'DM Mono',monospace;white-space:nowrap;flex-shrink:0}
.mm-section-act{font-size:13px;padding:4px 9px;background:transparent;border:0.5px solid transparent;color:#888780;cursor:pointer;border-radius:5px;line-height:1;flex-shrink:0;font-family:'DM Mono',monospace}
.mm-section-act:hover{border-color:#D3D1C7;color:#1a1d23;background:#fff}
.mm-section-act.del:hover{border-color:#A32D2D;color:#A32D2D;background:#FCEBEB}

.mm-section-body{padding:8px 12px 12px;background:rgba(255,255,255,0.35)}
.mm-section.collapsed .mm-section-body{display:none}

/* === Q comments (섹션 상단) === */
.mm-q-comments{padding:6px 0 10px;border-bottom:0.5px dashed #D3D1C7;margin-bottom:10px}
.mm-q-comments-head{font-size:9.5px;color:#888780;font-family:'DM Mono',monospace;letter-spacing:0.4px;margin-bottom:5px}
.mm-qc-list{display:flex;flex-direction:column;gap:3px}
.mm-qc{display:flex;gap:8px;padding:4px 8px;font-size:11.5px;line-height:1.5;align-items:flex-start;background:rgba(255,255,255,0.7);border-radius:4px;transition:opacity 0.2s}
.mm-qc.mm-dragging{opacity:0.4;background:#FAEEDA}
.mm-qc.bg-amber{background:#FDF7EC}
.mm-qc.bg-pink{background:#FCF3F7}
.mm-qc.bg-blue{background:#F0F7FE}
.mm-qc.bg-green{background:#F3F9EA}
.mm-qc.bg-purple{background:#F7F6FE}
.mm-qc .mm-grip{font-size:10px;color:#B4B2A9;opacity:0.4;padding-top:3px;cursor:grab;letter-spacing:-2px;user-select:none;flex-shrink:0;transition:opacity 0.1s}
.mm-qc:hover .mm-grip{opacity:0.7}
.mm-qc .mm-grip:active{cursor:grabbing}
.mm-qc-label{font-size:10px;flex-shrink:0;padding-top:2px;color:#5F5E5A;font-family:'DM Mono',monospace;min-width:36px;outline:none;font-weight:500}
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
.mm-qc-add{width:100%;border:0.5px solid #D3D1C7;padding:5px 10px;border-radius:5px;font-size:11.5px;outline:none;margin-top:5px;background:rgba(255,255,255,0.85)}
.mm-qc-add:focus{border-color:#888780;background:#fff}

/* === CG 가로 그리드 (1→2→3, 4→5→6 순서) === */
.mm-cg-masonry{display:grid;grid-template-columns:repeat(auto-fill, minmax(220px, 1fr));gap:8px;align-items:start}

.mm-cg-card{background:#fff;border:0.5px solid #D3D1C7;border-radius:7px;overflow:hidden;position:relative;transition:opacity 0.2s;max-height:520px;display:flex;flex-direction:column}
.mm-cg-card.mm-dragging{opacity:0.4}
.mm-cg-img{background:#F1EFE8;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden;flex-shrink:0}
.mm-cg-img img{width:100%;display:block;cursor:zoom-in}
.mm-cg-img-empty{padding:30px 10px;color:#B4B2A9;font-size:11px;text-align:center}
.mm-cg-num{position:absolute;top:5px;right:6px;font-size:9px;color:#1a1d23;font-family:'DM Mono',monospace;background:rgba(255,255,255,0.92);padding:1px 5px;border-radius:3px;font-weight:500;cursor:grab;user-select:none}
.mm-cg-num:active{cursor:grabbing}
.mm-cg-del{position:absolute;top:5px;left:6px;font-size:10px;background:rgba(0,0,0,0.5);color:#fff;border:none;border-radius:3px;padding:1px 5px;cursor:pointer;line-height:1;opacity:0;transition:opacity 0.1s}
.mm-cg-card:hover .mm-cg-del{opacity:1}
.mm-cg-meta{padding:7px 9px;flex:1 1 auto;overflow-y:auto;min-height:0}
.mm-cg-caption{width:100%;border:none;background:transparent;padding:0;font-size:11.5px;line-height:1.45;outline:none;color:#1a1d23;min-height:18px;white-space:pre-wrap;word-break:break-word}
.mm-cg-caption:focus{background:#FAFAF7;border-radius:3px;padding:2px 4px;margin:-1px -4px}
.mm-cg-caption[data-placeholder]:empty::before{content:attr(data-placeholder);color:#B4B2A9;pointer-events:none}
.mm-cg-caption b, .mm-cg-caption strong{font-weight:500;color:#1a1d23}

.mm-cg-comments{margin-top:6px;padding-top:6px;border-top:0.5px dashed #E8E5DC}
.mm-cg-comments-head{font-size:9px;color:#B4B2A9;font-family:'DM Mono',monospace;letter-spacing:0.3px;margin-bottom:3px}
.mm-cg-comment{display:flex;gap:5px;padding:3px 6px;font-size:10.5px;line-height:1.4;background:#FAFAF7;border-radius:3px;align-items:flex-start;margin-bottom:2px;transition:opacity 0.2s}
.mm-cg-comment.mm-dragging{opacity:0.4;background:#FAEEDA}
.mm-cg-comment .mm-grip{font-size:9px;color:#B4B2A9;opacity:0.4;padding-top:2px;cursor:grab;letter-spacing:-2px;user-select:none;flex-shrink:0}
.mm-cg-comment:hover .mm-grip{opacity:0.7}
.mm-cg-comment-text{flex:1;outline:none;word-break:break-word}
.mm-cg-comment-text:focus{background:#fff;border-radius:2px;padding:0 2px;margin:0 -2px}
.mm-cg-comment-del{background:none;border:none;color:#B4B2A9;font-size:9px;cursor:pointer;padding:0 2px;opacity:0;line-height:1;flex-shrink:0}
.mm-cg-comment:hover .mm-cg-comment-del{opacity:0.7}
.mm-cg-comment-del:hover{color:#A32D2D;opacity:1}
.mm-cg-comment-add{width:100%;border:0.5px solid #D3D1C7;padding:3px 7px;border-radius:4px;font-size:10.5px;outline:none;margin-top:2px;background:#fff}
.mm-cg-comment-add:focus{border-color:#888780}

.mm-cg-drop{border:0.5px dashed #B4B2A9;border-radius:7px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#888780;background:rgba(255,255,255,0.6);gap:5px;min-height:120px;cursor:pointer;transition:all 0.12s;text-align:center;padding:14px 8px;font-size:10.5px;line-height:1.5;font-family:'Noto Sans KR',sans-serif}
.mm-cg-drop:hover, .mm-cg-drop.drag-over{border-color:#1a1d23;background:#FAEEDA;color:#412402}
.mm-cg-drop .ic{font-size:18px}

/* === 텍스트 카드 (이미지 없이 텍스트만) === */
.mm-text-card{background:#FAFAF7;border:0.5px solid #D3D1C7}
.mm-text-card .mm-text-card-head{display:flex;justify-content:space-between;align-items:center;padding:5px 9px;background:rgba(255,255,255,0.7);border-bottom:0.5px solid #E8E5DC;flex-shrink:0}
.mm-text-card-label{font-size:9px;color:#888780;font-family:'DM Mono',monospace;letter-spacing:0.3px;cursor:grab;user-select:none;padding:2px 6px;background:rgba(255,255,255,0.85);border-radius:3px}
.mm-text-card-label:active{cursor:grabbing}
.mm-text-card .mm-cg-del{position:static;opacity:0.6;background:transparent;color:#888780;padding:2px 5px}
.mm-text-card .mm-cg-del:hover{opacity:1;color:#A32D2D}
.mm-text-card .mm-cg-caption{font-size:13px;line-height:1.55;min-height:60px;font-weight:500;color:#1a1d23;padding:4px}
.mm-text-card .mm-cg-caption:focus{background:#fff;border-radius:4px}

.mm-cg-add-text{border:0.5px dashed #B4B2A9;border-radius:7px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#888780;background:rgba(250,238,218,0.4);gap:5px;min-height:120px;cursor:pointer;transition:all 0.12s;text-align:center;padding:14px 8px;font-size:10.5px;line-height:1.5;font-family:'Noto Sans KR',sans-serif}
.mm-cg-add-text:hover{border-color:#854F0B;background:#FAEEDA;color:#412402}
.mm-cg-add-text .ic{font-size:18px}

/* === highlight & bold === */
.hl{background:#FAC775;color:#412402;padding:0 3px;border-radius:2px;font-weight:500;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.mm-cg-caption i, .mm-cg-caption em, .mm-cg-comment-text i, .mm-cg-comment-text em, .mm-qc-text i, .mm-qc-text em{font-style:italic}
.mm-cg-caption u, .mm-cg-comment-text u, .mm-qc-text u{text-decoration:underline;text-decoration-color:#888780;text-underline-offset:2px}

/* === 새 Q 추가 버튼 === */
.mm-add-section{border:0.5px dashed #B4B2A9;background:transparent;border-radius:10px;padding:14px;text-align:center;color:#888780;font-size:12.5px;cursor:pointer;transition:all 0.12s;margin-top:6px;font-family:'Noto Sans KR',sans-serif}
.mm-add-section:hover{border-color:#888780;background:#F1EFE8;color:#1a1d23}

/* === 빈 상태 === */
.mm-empty{padding:80px 30px;text-align:center;color:#888780;font-size:13px;line-height:1.7}
.mm-empty .emo{font-size:40px;margin-bottom:12px;color:#B4B2A9}

/* === lightbox === */
.mm-lightbox{position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:200;display:none;align-items:center;justify-content:center;padding:30px;cursor:zoom-out}
.mm-lightbox.show{display:flex}
.mm-lightbox img{max-width:100%;max-height:100%;object-fit:contain}
.mm-lightbox-close{position:absolute;top:18px;right:24px;background:rgba(255,255,255,0.15);color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:13px;cursor:pointer}
.mm-lightbox-close:hover{background:rgba(255,255,255,0.25)}

/* === responsive === */
@media (max-width: 700px){
  .wrap{padding:10px}
  .mm{padding:12px}
  .mm-cg-masonry{grid-template-columns:repeat(auto-fill, minmax(160px, 1fr));gap:6px}
  .mm-cg-card{max-height:460px}
  .mm-q-type, .mm-q-guest{width:auto;min-width:70px;flex:1}
  .mm-q-title-input{min-width:100%;order:10}
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
        <input type="text" class="mm-quick-q" id="mm-quick-q" placeholder="＋ 질문 추가… (엔터로 1개 / 멀티라인 paste면 자동으로 여러 Q 생성)" onkeydown="if(event.key==='Enter'){quickAddQ(this.value);this.value=''}">
        <div class="mm-shortcuts-hint">
          텍스트 입력 중: <kbd>⌘B</kbd> 굵게 · <kbd>⌘I</kbd> 기울임 · <kbd>⌘U</kbd> 밑줄 · <kbd>⌘⇧H</kbd> 하이라이트 · <kbd>⌘⇧↑↓</kbd> 이전/다음 Q
        </div>
      </div>
      <div class="mm-actions">
        <div class="mm-onair-wrap">
          <button class="mm-onair-btn" onclick="toggleOnAirMenu(event)">⬇ ON AIR <span class="caret">▼</span></button>
          <div class="mm-onair-menu" id="mm-onair-menu" style="display:none">
            <button class="mm-onair-refresh" onclick="loadOnAirCorners()">↻ 다시 불러오기</button>
            <div id="mm-onair-list"></div>
            <button class="mm-onair-reset" onclick="resetMindmap()">🗑 마인드맵 전체 초기화</button>
          </div>
        </div>
        <button class="mm-new-q" onclick="addQuestion()"><span style="font-size:14px;line-height:1">＋</span>새 Q</button>
      </div>
    </div>

    <div class="mm-sections" id="mm-sections"></div>
  </div>
</div>

<div class="mm-lightbox" id="mm-lightbox" onclick="closeLightbox()">
  <button class="mm-lightbox-close" onclick="event.stopPropagation();closeLightbox()">✕ 닫기 (ESC)</button>
  <img id="mm-lightbox-img" src="" alt="">
</div>

<input type="file" id="mm-file-input" accept="image/*" style="display:none" multiple>

<script>
// === fetch wrapper (PWA 세션 + X-API-Secret 자동) ===
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

// === 데이터 모델 ===
let MD = {
  corner: { title:'', subtitle:'', questions:[] }
};
let saveTimer = null;

function genId(prefix){
  return prefix + '_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2,7);
}
function getQById(qId){ return MD.corner.questions.find(q => q.id === qId) || null; }
function escapeHtml(s){
  if(s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function getQCBgClass(label){
  const l = (label || '').toLowerCase();
  if(/db|콜백/.test(l)) return 'bg-amber';
  if(/말랑|💫/.test(l)) return 'bg-pink';
  if(/상황|배경/.test(l)) return 'bg-blue';
  if(/송곳/.test(l)) return 'bg-purple';
  if(/질문/.test(l)) return 'bg-green';
  return '';
}

// === 저장/로드 ===
function syncActiveContentEditable(){
  const a = document.activeElement;
  if(a && a.isContentEditable && typeof a.onblur === 'function'){
    try{ a.onblur(); }catch(e){}
  }
}
function indSaving(){const i=document.getElementById('save-ind');if(!i)return;i.textContent='저장 중...';i.className='save-ind saving';i.style.opacity=1;}
function indSaved(sizeKB){const i=document.getElementById('save-ind');if(!i)return;i.textContent='✓ 저장됨'+(sizeKB?' ('+sizeKB+'KB)':'');i.className='save-ind saved';i.style.opacity=1;setTimeout(()=>{i.style.opacity=0;},1800);}
function indError(detail){const i=document.getElementById('save-ind');if(!i)return;i.textContent='✕ '+(detail||'저장 실패');i.className='save-ind error';i.style.opacity=1;}

async function saveMindmap(){
  let sizeKB = 0;
  try{
    syncActiveContentEditable();
    indSaving();
    const content = JSON.stringify(MD);
    sizeKB = Math.round(content.length / 1024);
    if(sizeKB > 4500){
      console.error('[mindmap save] payload too large:', sizeKB+'KB');
      indError('너무 큼 '+sizeKB+'KB · 이미지 일부 삭제 필요');
      return;
    }
    const res = await fetch('/api/post/mindmap',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({content, date: new Date().toISOString().slice(0,10)})
    });
    if(!res.ok){
      let extra = '';
      try{ extra = (await res.text()).slice(0, 80); }catch(e){}
      console.error('[mindmap save] HTTP', res.status, extra, 'size:', sizeKB+'KB');
      indError('HTTP '+res.status+' · '+sizeKB+'KB');
      return;
    }
    indSaved(sizeKB);
  }catch(e){
    console.error('[mindmap save] exception', e, 'size:', sizeKB+'KB');
    indError((e.message||'network').slice(0,40)+' · '+sizeKB+'KB');
  }
}
function scheduleSave(){
  if(saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(saveMindmap, 1500);
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
            if(q.collapsed === undefined) q.collapsed = false;
            q.cgs.forEach(cg => {
              if(!cg.comments) cg.comments = [];
              if(cg.caption === undefined && (cg.title || cg.subtitle)){
                const parts = [];
                if(cg.title) parts.push(cg.title);
                if(cg.subtitle) parts.push(cg.subtitle);
                cg.caption = parts.join('\n');
                delete cg.title; delete cg.subtitle;
              }
            });
          });
        }
      }catch(e){console.error('parse failed', e);}
    }
  }catch(e){console.error('load failed', e);}
  render();
}

// === 렌더링 ===
function render(){
  syncActiveContentEditable();
  document.getElementById('mm-corner-title').value = MD.corner.title || '';
  document.getElementById('mm-corner-sub').value = MD.corner.subtitle || '';
  renderSections();
}

function renderSections(){
  const container = document.getElementById('mm-sections');
  if(!MD.corner.questions.length){
    container.innerHTML = '<div class="mm-empty"><div class="emo">📋</div>아직 질문이 없어요<br>＋ 새 Q 또는 ⬇ ON AIR 에서 가져오기로 시작하세요</div>'
      + '<button class="mm-add-section" onclick="addQuestion()">＋ 새 Q 섹션</button>';
    return;
  }
  let html = '';
  MD.corner.questions.forEach((q, idx) => {
    html += renderSection(q, idx);
  });
  html += '<button class="mm-add-section" onclick="addQuestion()">＋ 새 Q 섹션</button>';
  container.innerHTML = html;
  // textarea 자동 리사이즈
  container.querySelectorAll('.mm-q-title-input').forEach(autoResizeTextarea);
}

function renderSection(q, idx){
  const colorIdx = (idx % 5) + 1;
  const cgCount = (q.cgs || []).length;
  const cgCmtCount = (q.cgs || []).reduce((s,cg)=>s+(cg.comments||[]).length,0);
  const collapsed = q.collapsed ? ' collapsed' : '';
  const caret = q.collapsed ? '▶' : '▼';

  let html = '<div class="mm-section q'+colorIdx+collapsed+'" data-q-id="'+q.id+'">';
  html += '<div class="mm-section-head">';
  html += '<span class="mm-section-grip" draggable="true">⋮⋮</span>';
  html += '<span class="mm-q-num" contenteditable="true" onblur="updateQField(\''+q.id+'\',\'number\',this.textContent.trim())">'+escapeHtml(q.number||'Q')+'</span>';
  html += '<input type="text" class="mm-q-type" value="'+escapeHtml(q.type||'')+'" placeholder="🅰️ 타입" onchange="updateQField(\''+q.id+'\',\'type\',this.value)">';
  html += '<input type="text" class="mm-q-guest" value="'+escapeHtml(q.guest||'')+'" placeholder="출연자" onchange="updateQField(\''+q.id+'\',\'guest\',this.value)">';
  html += '<textarea class="mm-q-title-input" placeholder="질문 제목 입력..." onchange="updateQField(\''+q.id+'\',\'title\',this.value)" oninput="autoResizeTextarea(this);scheduleSave()">'+escapeHtml(q.title||'')+'</textarea>';
  html += '<span class="mm-section-meta">CG '+cgCount+(cgCmtCount?' · 💬'+cgCmtCount:'')+'</span>';
  html += '<button class="mm-section-act" title="접기/펼치기" onclick="toggleSectionCollapse(\''+q.id+'\')">'+caret+'</button>';
  html += '<button class="mm-section-act del" title="섹션 삭제" onclick="deleteQuestion(\''+q.id+'\')">✕</button>';
  html += '</div>';

  // 본체 (접혀있어도 HTML은 생성, CSS로 숨김)
  html += '<div class="mm-section-body">';

  // CG 매소너리 그리드
  html += '<div class="mm-cg-masonry" id="mm-cg-masonry-'+q.id+'">';
  (q.cgs || []).forEach((cg, cgIdx) => {
    html += renderCGCard(q.id, cg, cgIdx);
  });
  html += '<div class="mm-cg-drop" onclick="triggerFileInput(\''+q.id+'\')" data-q-id="'+q.id+'">'+
    '<div class="ic">⬆</div>'+
    '<div>이미지 끌어다 놓기<br>또는 클릭 · Cmd+V</div>'+
  '</div>';
  html += '<div class="mm-cg-add-text" onclick="addTextCard(\''+q.id+'\')">'+
    '<div class="ic">📝</div>'+
    '<div>텍스트 카드 추가<br>(이미지 없이)</div>'+
  '</div>';
  html += '</div>';

  html += '</div>'; // section-body
  html += '</div>'; // section
  return html;
}

function renderCGCard(qId, cg, idx){
  const isTextCard = !cg.image;
  let html = '<div class="mm-cg-card '+(isTextCard?'mm-text-card':'')+'" data-cg-id="'+cg.id+'" data-q-id="'+qId+'">';

  if(isTextCard){
    // 텍스트 카드 — 이미지 없이 텍스트만
    html += '<div class="mm-text-card-head">'+
      '<span class="mm-text-card-label" draggable="true">📝 NOTE-'+(idx+1)+'</span>'+
      '<button class="mm-cg-del" onclick="deleteCG(\''+qId+'\',\''+cg.id+'\')" title="삭제">✕</button>'+
    '</div>';
  } else {
    // 이미지 카드 (기존)
    const imgHtml = '<img src="'+escapeHtml(cg.image)+'" alt="" onclick="openLightbox(this.src)">';
    html += '<div class="mm-cg-img">'+imgHtml+
      '<span class="mm-cg-num" draggable="true">CG-'+(idx+1)+'</span>'+
      '<button class="mm-cg-del" onclick="deleteCG(\''+qId+'\',\''+cg.id+'\')" title="삭제">✕</button>'+
      '</div>';
  }

  html += '<div class="mm-cg-meta">';
  html += '<div class="mm-cg-caption" contenteditable="true" data-placeholder="여기에 자유 입력…" onblur="updateCGField(\''+qId+'\',\''+cg.id+'\',\'caption\',this.innerHTML)">'+(cg.caption||'')+'</div>';
  html += '<div class="mm-cg-comments">';
  html += '<div class="mm-cg-comments-head">COMMENT · '+(cg.comments||[]).length+'</div>';
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

function autoResizeTextarea(el){
  if(!el) return;
  el.style.height = 'auto';
  el.style.height = (el.scrollHeight + 2) + 'px';
}

// === CRUD ===
function addQuestion(){
  const num = 'Q' + (MD.corner.questions.length + 1);
  const q = { id: genId('q'), number: num, type: '', guest: '', title: '', cgs: [], comments: [], collapsed: false };
  MD.corner.questions.push(q);
  render();
  scheduleSave();
  // 새 섹션으로 스크롤 + 제목 포커스
  setTimeout(()=>{
    const section = document.querySelector('[data-q-id="'+q.id+'"]');
    if(section){
      section.scrollIntoView({behavior:'smooth', block:'start'});
      const title = section.querySelector('.mm-q-title-input');
      if(title) title.focus();
    }
  }, 80);
}
window.quickAddQ = function(text){
  if(!text || !text.trim()) return;
  const num = 'Q' + (MD.corner.questions.length + 1);
  const q = { id: genId('q'), number: num, type: '', guest: '', title: text.trim(), cgs: [], comments: [], collapsed: false };
  MD.corner.questions.push(q);
  render();
  scheduleSave();
  // 새 섹션으로 스크롤
  setTimeout(()=>{
    const section = document.querySelector('[data-q-id="'+q.id+'"]');
    if(section) section.scrollIntoView({behavior:'smooth', block:'start'});
    // 빠른 Q 입력 박스로 다시 포커스 (연속 입력 가능)
    const input = document.getElementById('mm-quick-q');
    if(input) input.focus();
  }, 80);
};

// 멀티라인 텍스트 → 여러 Q 섹션 자동 생성
window.importTextAsQuestions = function(text){
  if(!text || !text.trim()) return 0;
  const lines = text.split(/\r?\n/);
  // 코너 헤더 추출 (#N 제목)
  let cornerTitle = '';
  const bodyLines = [];
  for(const line of lines){
    const m = line.match(/^\s*#(\d+)\s*\.?\s*(.+)/);
    if(m && !cornerTitle){
      cornerTitle = m[2].trim();
    } else {
      bodyLines.push(line);
    }
  }
  // 코너 제목 비어있을 때만 설정 (기존 입력 보호)
  if(cornerTitle && !MD.corner.title){
    MD.corner.title = cornerTitle;
  }
  // Q 파싱
  const qs = parseQuestionsFromBody(bodyLines);
  if(!qs.length) return 0;
  let firstId = null;
  qs.forEach((q, idx) => {
    const header = parseQHeader(q.header);
    const bodyText = q.body.join('\n');
    const comments = [];
    bodyText.split('\n').forEach(line => {
      const c = parseLineToComment(line);
      if(c && c.text) comments.push({ id: genId('qc'), label: c.label || '', text: c.text });
    });
    const newId = genId('q');
    if(idx === 0) firstId = newId;
    MD.corner.questions.push({
      id: newId,
      number: header.number || ('Q' + (MD.corner.questions.length + 1)),
      type: header.type || '',
      guest: header.guest || '',
      title: header.title || '',
      collapsed: false,
      cgs: [],
      comments: comments
    });
  });
  render();
  scheduleSave();
  // 첫 새 Q로 스크롤
  setTimeout(()=>{
    if(firstId){
      const el = document.querySelector('[data-q-id="'+firstId+'"]');
      if(el) el.scrollIntoView({behavior:'smooth', block:'start'});
    }
  }, 100);
  // 알림
  const ind = document.getElementById('save-ind');
  if(ind){
    ind.textContent = '✓ '+qs.length+'개 Q 섹션 추가됨';
    ind.className = 'save-ind saved';
    ind.style.opacity = 1;
    setTimeout(()=>{ind.style.opacity = 0;}, 2800);
  }
  return qs.length;
};
function deleteQuestion(qId){
  const q = getQById(qId);
  if(!q) return;
  if(!confirm('이 질문 섹션을 삭제할까요?\n\n"'+(q.title || q.number)+'"\nCG '+(q.cgs||[]).length+'장, comment '+(q.comments||[]).length+'개도 함께 사라집니다.')) return;
  MD.corner.questions = MD.corner.questions.filter(x => x.id !== qId);
  render();
  scheduleSave();
}
function updateQField(qId, field, value){
  const q = getQById(qId); if(!q) return;
  q[field] = value;
  scheduleSave();
}
window.toggleSectionCollapse = function(qId){
  const q = getQById(qId); if(!q) return;
  q.collapsed = !q.collapsed;
  render();
  scheduleSave();
};
function updateCGField(qId, cgId, field, value){
  const q = getQById(qId); if(!q) return;
  const cg = q.cgs.find(c => c.id === cgId); if(!cg) return;
  cg[field] = value;
  scheduleSave();
}
function deleteCG(qId, cgId){
  if(!confirm('이 CG를 삭제할까요?')) return;
  const q = getQById(qId); if(!q) return;
  q.cgs = q.cgs.filter(c => c.id !== cgId);
  render();
  scheduleSave();
}
function addCG(qId, base64Image){
  const q = getQById(qId); if(!q) return;
  const cg = { id: genId('cg'), image: base64Image, caption: '', comments: [] };
  q.cgs.push(cg);
  render();
  scheduleSave();
}
window.addTextCard = function(qId){
  const q = getQById(qId); if(!q) return;
  const cg = { id: genId('cg'), image: '', caption: '', comments: [] };
  q.cgs.push(cg);
  render();
  scheduleSave();
  // 새 카드 캡션에 자동 포커스
  setTimeout(()=>{
    const cardEl = document.querySelector('[data-cg-id="'+cg.id+'"]');
    if(cardEl){
      const cap = cardEl.querySelector('.mm-cg-caption');
      if(cap) cap.focus();
    }
  }, 80);
};
function addCGComment(qId, cgId, text){
  if(!text || !text.trim()) return;
  const q = getQById(qId); if(!q) return;
  const cg = q.cgs.find(c => c.id === cgId); if(!cg) return;
  cg.comments.push({ id: genId('cc'), text: text.trim() });
  render();
  scheduleSave();
}
function updateCGComment(qId, cgId, ccId, text){
  const q = getQById(qId); if(!q) return;
  const cg = q.cgs.find(c => c.id === cgId); if(!cg) return;
  const cc = cg.comments.find(c => c.id === ccId); if(!cc) return;
  cc.text = text;
  scheduleSave();
}
function deleteCGComment(qId, cgId, ccId){
  const q = getQById(qId); if(!q) return;
  const cg = q.cgs.find(c => c.id === cgId); if(!cg) return;
  cg.comments = cg.comments.filter(c => c.id !== ccId);
  render();
  scheduleSave();
}
function addQComment(qId, raw){
  if(!raw || !raw.trim()) return;
  const q = getQById(qId); if(!q) return;
  let label = '', text = raw.trim(), m;
  if((m = text.match(/^\[([^\]]+)\]\s*(.*)/))){ label = m[1]; text = m[2]; }
  else if((m = text.match(/^(\S{1,8})\s*[:：]\s*(.+)/))){ label = m[1]; text = m[2]; }
  q.comments.push({ id: genId('qc'), label: label, text: text });
  render();
  scheduleSave();
}
function updateQCommentField(qId, qcId, field, value){
  const q = getQById(qId); if(!q) return;
  const qc = q.comments.find(c => c.id === qcId); if(!qc) return;
  qc[field] = value;
  if(field === 'label'){ render(); }
  scheduleSave();
}
function deleteQComment(qId, qcId){
  const q = getQById(qId); if(!q) return;
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

function resizeImage(file, maxW=800, maxH=540, quality=0.72){
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
        // 항상 JPEG로 변환 (PNG도 압축 적용되게 — 알파 채널은 흰 배경으로 채움)
        resolve(canvas.toDataURL('image/jpeg', quality));
      };
      img.onerror = reject;
      img.src = e.target.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// === 드롭존 + 클립보드 ===
document.addEventListener('dragover', (e) => {
  const drop = e.target.closest('.mm-cg-drop');
  if(drop){ e.preventDefault(); drop.classList.add('drag-over'); return; }
  // 정렬 드래그
  if(!_draggingEl) return;
  let targetSel = null;
  if(_draggingKind === 'q-section') targetSel = '.mm-section';
  else if(_draggingKind === 'cg-card') targetSel = '.mm-cg-card';
  else if(_draggingKind === 'cg-comment') targetSel = '.mm-cg-comment';
  else if(_draggingKind === 'q-comment') targetSel = '.mm-qc';
  if(!targetSel) return;
  const target = e.target.closest(targetSel);
  if(!target || target === _draggingEl) return;
  if(target.parentNode !== _draggingEl.parentNode) return;
  e.preventDefault();
  const rect = target.getBoundingClientRect();
  let isAfter;
  if(_draggingKind === 'cg-card'){
    // CG는 grid 가로 흐름 — 가로/세로 둘 다 고려
    const dx = e.clientX - (rect.left + rect.width/2);
    const dy = e.clientY - (rect.top + rect.height/2);
    if(Math.abs(dy) > rect.height/3){
      isAfter = dy > 0;
    } else {
      isAfter = dx > 0;
    }
  } else {
    // Q 섹션, comment 리스트 — 세로
    isAfter = e.clientY > rect.top + rect.height/2;
  }
  if(!isAfter){ target.parentNode.insertBefore(_draggingEl, target); }
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
  const items = (e.clipboardData || window.clipboardData)?.items || [];
  for(const item of items){
    if(item.type && item.type.startsWith('image/')){
      // 활성 Q 결정 — 포커스된 섹션 또는 첫 번째 펼친 섹션
      const focusSection = document.activeElement ? document.activeElement.closest('.mm-section') : null;
      let qId = focusSection ? focusSection.dataset.qId : null;
      if(!qId){
        const firstOpen = MD.corner.questions.find(q => !q.collapsed);
        if(firstOpen) qId = firstOpen.id;
      }
      if(!qId) continue;
      const f = item.getAsFile();
      if(f){
        e.preventDefault();
        const data = await resizeImage(f);
        addCG(qId, data);
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
  if(t.classList.contains('mm-section-grip')){
    _draggingEl = t.closest('.mm-section');
    _draggingKind = 'q-section';
  } else if(t.classList.contains('mm-cg-num') || t.classList.contains('mm-text-card-label')){
    _draggingEl = t.closest('.mm-cg-card');
    _draggingKind = 'cg-card';
  } else if(t.classList.contains('mm-grip')){
    const cgc = t.closest('.mm-cg-comment');
    const qc = t.closest('.mm-qc');
    if(cgc){ _draggingEl = cgc; _draggingKind = 'cg-comment'; }
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
document.addEventListener('dragend', () => {
  if(!_draggingEl) return;
  _draggingEl.classList.remove('mm-dragging');
  syncOrderFromDOM(_draggingKind);
  _draggingEl = null;
  _draggingKind = null;
  scheduleSave();
});

function syncOrderFromDOM(kind){
  if(kind === 'q-section'){
    const container = document.getElementById('mm-sections');
    const ids = Array.from(container.querySelectorAll('.mm-section')).map(el => el.dataset.qId);
    MD.corner.questions.sort((a,b) => ids.indexOf(a.id) - ids.indexOf(b.id));
    render();
  } else if(kind === 'cg-card'){
    // 어느 섹션의 CG인지 찾기
    document.querySelectorAll('.mm-section').forEach(sec => {
      const qId = sec.dataset.qId;
      const q = getQById(qId); if(!q) return;
      const grid = sec.querySelector('.mm-cg-masonry');
      if(!grid) return;
      const ids = Array.from(grid.querySelectorAll('.mm-cg-card')).map(el => el.dataset.cgId);
      q.cgs.sort((a,b) => ids.indexOf(a.id) - ids.indexOf(b.id));
    });
    // CG-N 번호 갱신을 위해 render
    render();
  } else if(kind === 'cg-comment'){
    document.querySelectorAll('.mm-cg-card').forEach(cgEl => {
      const cgId = cgEl.dataset.cgId;
      const qId = cgEl.dataset.qId;
      const q = getQById(qId); if(!q) return;
      const cg = q.cgs.find(c => c.id === cgId); if(!cg) return;
      const ids = Array.from(cgEl.querySelectorAll('.mm-cg-comment')).map(el => el.dataset.ccId);
      cg.comments.sort((a,b) => ids.indexOf(a.id) - ids.indexOf(b.id));
    });
  } else if(kind === 'q-comment'){
    document.querySelectorAll('.mm-section').forEach(sec => {
      const qId = sec.dataset.qId;
      const q = getQById(qId); if(!q) return;
      const list = sec.querySelector('.mm-qc-list');
      if(!list) return;
      const ids = Array.from(list.querySelectorAll('.mm-qc')).map(el => el.dataset.qcId);
      q.comments.sort((a,b) => ids.indexOf(a.id) - ids.indexOf(b.id));
    });
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
  document.getElementById('mm-lightbox-img').src = src;
  document.getElementById('mm-lightbox').classList.add('show');
};
window.closeLightbox = function(){
  document.getElementById('mm-lightbox').classList.remove('show');
};

// === Q 빠른 전환 (다음 Q 섹션으로 스크롤 + 펼침) ===
function commitActiveInput(){
  const a = document.activeElement;
  if(a && (a.isContentEditable || a.tagName === 'INPUT' || a.tagName === 'TEXTAREA')){
    if(typeof a.blur === 'function') a.blur();
  }
}
function scrollToSection(qId){
  const q = getQById(qId); if(!q) return;
  if(q.collapsed){ q.collapsed = false; render(); scheduleSave(); }
  setTimeout(()=>{
    const section = document.querySelector('[data-q-id="'+qId+'"]');
    if(section){
      section.scrollIntoView({behavior:'smooth', block:'start'});
      const title = section.querySelector('.mm-q-title-input');
      if(title) setTimeout(()=>title.focus(), 200);
    }
  }, q.collapsed === false ? 0 : 50);
}
window.prevQ = function(){
  if(MD.corner.questions.length < 2) return;
  commitActiveInput();
  // 현재 화면에서 가장 가까운 섹션 찾기
  const sections = Array.from(document.querySelectorAll('.mm-section'));
  let currentIdx = -1;
  const focusSection = document.activeElement ? document.activeElement.closest('.mm-section') : null;
  if(focusSection) currentIdx = sections.indexOf(focusSection);
  if(currentIdx < 0){
    // 화면 중앙에 가장 가까운 섹션
    const vh = window.innerHeight;
    let best = 0, bestDist = Infinity;
    sections.forEach((s, i) => {
      const r = s.getBoundingClientRect();
      const d = Math.abs(r.top + r.height/2 - vh/2);
      if(d < bestDist){ bestDist = d; best = i; }
    });
    currentIdx = best;
  }
  const newIdx = currentIdx > 0 ? currentIdx - 1 : MD.corner.questions.length - 1;
  scrollToSection(MD.corner.questions[newIdx].id);
};
window.nextQ = function(){
  if(MD.corner.questions.length < 2) return;
  commitActiveInput();
  const sections = Array.from(document.querySelectorAll('.mm-section'));
  let currentIdx = -1;
  const focusSection = document.activeElement ? document.activeElement.closest('.mm-section') : null;
  if(focusSection) currentIdx = sections.indexOf(focusSection);
  if(currentIdx < 0){
    const vh = window.innerHeight;
    let best = 0, bestDist = Infinity;
    sections.forEach((s, i) => {
      const r = s.getBoundingClientRect();
      const d = Math.abs(r.top + r.height/2 - vh/2);
      if(d < bestDist){ bestDist = d; best = i; }
    });
    currentIdx = best;
  }
  const newIdx = currentIdx < MD.corner.questions.length - 1 ? currentIdx + 1 : 0;
  scrollToSection(MD.corner.questions[newIdx].id);
};

// === 하이라이트 토글 ===
function toggleHighlight(){
  const sel = window.getSelection();
  if(!sel || sel.rangeCount === 0 || sel.isCollapsed) return;
  const range = sel.getRangeAt(0);
  let startNode = range.startContainer;
  if(startNode.nodeType === 3) startNode = startNode.parentNode;
  const existingHl = startNode.closest && startNode.closest('.hl');
  if(existingHl){
    const parent = existingHl.parentNode;
    if(!parent) return;
    while(existingHl.firstChild){ parent.insertBefore(existingHl.firstChild, existingHl); }
    parent.removeChild(existingHl);
    parent.normalize();
  } else {
    try{
      const span = document.createElement('span');
      span.className = 'hl';
      range.surroundContents(span);
      sel.removeAllRanges();
      const newRange = document.createRange();
      newRange.selectNodeContents(span);
      sel.addRange(newRange);
    }catch(err){
      try{
        const span = document.createElement('span');
        span.className = 'hl';
        const frag = range.extractContents();
        span.appendChild(frag);
        range.insertNode(span);
      }catch(e2){console.error('hl error', e2);}
    }
  }
}

// === 단축키 ===
document.addEventListener('keydown', (e) => {
  if(e.key === 'Escape'){ closeLightbox(); return; }
  const mod = e.metaKey || e.ctrlKey;
  if(!mod) return;
  // ⌘⇧↑/↓ — 이전/다음 Q
  if(e.shiftKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown')){
    if(MD.corner.questions.length < 2) return;
    e.preventDefault();
    if(e.key === 'ArrowUp') prevQ(); else nextQ();
    return;
  }
  if(!e.target || !e.target.isContentEditable) return;
  if(!e.shiftKey && (e.key === 'b' || e.key === 'B')){
    e.preventDefault(); document.execCommand('bold'); scheduleSave(); return;
  }
  if(!e.shiftKey && (e.key === 'i' || e.key === 'I')){
    e.preventDefault(); document.execCommand('italic'); scheduleSave(); return;
  }
  if(!e.shiftKey && (e.key === 'u' || e.key === 'U')){
    e.preventDefault(); document.execCommand('underline'); scheduleSave(); return;
  }
  if(e.shiftKey && (e.key === 'h' || e.key === 'H')){
    e.preventDefault(); toggleHighlight(); scheduleSave(); return;
  }
});

document.addEventListener('input', (e) => {
  if(e.target && e.target.isContentEditable){ scheduleSave(); }
});

// === ON AIR import ===
let _onAirCorners = [];
window.toggleOnAirMenu = function(e){
  if(e) e.stopPropagation();
  const menu = document.getElementById('mm-onair-menu');
  if(!menu) return;
  if(menu.style.display === 'none' || !menu.style.display){
    menu.style.display = 'block';
    loadOnAirCorners();
  } else { menu.style.display = 'none'; }
};
document.addEventListener('click', (e) => {
  if(!e.target.closest('.mm-onair-wrap')){
    const menu = document.getElementById('mm-onair-menu');
    if(menu) menu.style.display = 'none';
  }
});
async function loadOnAirCorners(){
  const listEl = document.getElementById('mm-onair-list');
  if(listEl) listEl.innerHTML = '<div class="mm-onair-empty">불러오는 중...</div>';
  try{
    const d = await fetch('/api/post/wdaebon').then(r => r.json());
    let text = '';
    if(d && d.content){
      try{
        const payload = JSON.parse(d.content);
        if(payload && typeof payload === 'object' && payload.text !== undefined){
          text = payload.text;
        } else { text = d.content; }
      }catch(e){ text = d.content; }
    }
    _onAirCorners = parseOnAirText(text);
    renderOnAirMenu();
  }catch(e){
    console.error('ON AIR load error:', e);
    if(listEl) listEl.innerHTML = '<div class="mm-onair-empty">ON AIR 데이터를 불러올 수 없습니다</div>';
  }
}
function renderOnAirMenu(){
  const listEl = document.getElementById('mm-onair-list');
  if(!listEl) return;
  if(!_onAirCorners.length){
    listEl.innerHTML = '<div class="mm-onair-empty">ON AIR에 코너가 없거나<br>"#1 ..." 형식이 아닙니다</div>';
    return;
  }
  let html = '';
  _onAirCorners.forEach(c => {
    const qs = parseQuestionsFromBody(c.body);
    html += '<button class="mm-onair-item" onclick="importCornerToMindmap(\''+c.number+'\')">'+
      '<span class="num">#'+c.number+'</span>'+
      '<span class="title">'+escapeHtml(c.title)+'</span>'+
      '<span class="meta">Q '+qs.length+'개</span>'+
    '</button>';
  });
  listEl.innerHTML = html;
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
    } else if(current){ current.body.push(line); }
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
    } else if(current){ current.body.push(line); }
  }
  if(current) qs.push(current);
  qs.forEach(q => {
    while(q.body.length && !q.body[0].trim()) q.body.shift();
    while(q.body.length && !q.body[q.body.length-1].trim()) q.body.pop();
  });
  return qs;
}
function parseQHeader(header){
  let number = 'Q', type = '', guest = '', title = header;
  const m = header.match(/^(Q[\d-]+)\s*\.\s*(.+)$/);
  if(!m) return {number, type, guest, title};
  number = m[1];
  let rest = m[2].trim();
  const trailing = rest.match(/\s*\[([^\]]+)\]\s*$/);
  if(trailing){
    guest = trailing[1].trim();
    rest = rest.replace(/\s*\[[^\]]+\]\s*$/, '').trim();
  }
  const leading = rest.match(/^\s*\[([^\]]+)\]\s*(.*)$/);
  if(leading){
    const inner = leading[1].trim();
    rest = leading[2].trim();
    // 이미 끝에 guest를 받았으면 시작 []는 type
    // 아니면 내용 분석: 이모지/영문 = type, 한글 이름 패턴 = guest
    if(guest){
      type = inner;
    } else {
      const hasEmojiOrLatin = /[\u{1F000}-\u{1FFFF}\u{2600}-\u{27BF}🅰🅱🅲🅴🅵🆎]/u.test(inner) || /[A-Za-z]/.test(inner);
      if(hasEmojiOrLatin){
        type = inner;
      } else {
        // 순수 한글/한자 = 출연자 이름으로 추정 (예: [황대근], [임하영→황대근])
        guest = inner;
      }
    }
  }
  title = rest;
  return {number, type, guest, title};
}
function parseLineToComment(rawLine){
  const trimmed = rawLine.trim();
  if(!trimmed) return null;
  if(/^⇒/.test(trimmed)) return null;
  let label = '', text = trimmed, m;
  if((m = trimmed.match(/^🎯\s*(?:질문\s*의도\s*[:：]\s*)?(.*)/))){ label='의도'; text=m[1].trim(); }
  else if((m = trimmed.match(/^▶\s*(.*)/))){ label='▶ DB'; text=m[1].trim(); }
  else if((m = trimmed.match(/^→\s*\[콜백\]\s*(.*)/)) || (m = trimmed.match(/^→\s*콜백\s*[:：]?\s*(.*)/))){ label='→ 콜백'; text=m[1].trim(); }
  else if((m = trimmed.match(/^\[콜백\]\s*(.*)/))){ label='콜백'; text=m[1].trim(); }
  else if((m = trimmed.match(/^\[(?:💫\s*)?말랑\]\s*(.*)/))){ label='💫 말랑'; text=m[1].trim(); }
  else if((m = trimmed.match(/^\[(?:🎯\s*)?송곳\]\s*(.*)/))){ label='🎯 송곳'; text=m[1].trim(); }
  else if((m = trimmed.match(/^\[(상황|배경)\]\s*(.*)/))){ label=m[1]; text=m[2].trim(); }
  else if((m = trimmed.match(/^\[질문\]\s*(.*)/)) || (m = trimmed.match(/^❓\s*(.*)/))){ label='질문'; text=m[1].trim(); }
  else if((m = trimmed.match(/^\[([^\]]+)\]\s*(.*)/))){ label=m[1]; text=m[2].trim(); }
  return {label, text: text || trimmed};
}

window.resetMindmap = function(){
  const qCount = MD.corner.questions.length;
  const cgCount = MD.corner.questions.reduce((s,q)=>s+(q.cgs||[]).length, 0);
  if(qCount === 0 && !MD.corner.title && !MD.corner.subtitle){
    alert('이미 비어있습니다.');
    return;
  }
  let msg = '마인드맵 전체를 초기화할까요?\n\n';
  if(MD.corner.title) msg += '코너: "'+MD.corner.title+'"\n';
  msg += 'Q '+qCount+'개';
  if(cgCount) msg += ', CG '+cgCount+'장';
  msg += ' 이 사라집니다.\n(되돌릴 수 없습니다)';
  if(!confirm(msg)) return;
  MD = { corner: { title:'', subtitle:'', questions:[] } };
  const menu = document.getElementById('mm-onair-menu');
  if(menu) menu.style.display = 'none';
  render();
  scheduleSave();
};

window.importCornerToMindmap = function(cornerNumber){
  const corner = _onAirCorners.find(c => c.number === cornerNumber);
  if(!corner) return;
  const hasWork = MD.corner.questions.length > 0 ||
                  (MD.corner.title && MD.corner.title.trim()) ||
                  MD.corner.questions.some(q => (q.cgs||[]).length > 0);
  if(hasWork){
    const cgCount = MD.corner.questions.reduce((s,q)=>s+(q.cgs||[]).length, 0);
    let msg = 'ON AIR #'+corner.number+' "'+corner.title+'" 으로 덮어쓸까요?\n\n';
    msg += '기존 마인드맵 ('+MD.corner.questions.length+'개 Q';
    if(cgCount) msg += ', CG '+cgCount+'장';
    msg += ')이 사라집니다.';
    if(!confirm(msg)) return;
  }
  MD.corner.title = corner.title;
  MD.corner.subtitle = '';
  const qs = parseQuestionsFromBody(corner.body);
  MD.corner.questions = qs.map((q, idx) => {
    const header = parseQHeader(q.header);
    const bodyText = q.body.join('\n');
    const comments = [];
    bodyText.split('\n').forEach(line => {
      const c = parseLineToComment(line);
      if(c){ comments.push({ id: genId('qc'), label: c.label || '', text: c.text }); }
    });
    return {
      id: genId('q'),
      number: header.number || ('Q' + (idx+1)),
      type: header.type || '',
      guest: header.guest || '',
      title: header.title || '',
      collapsed: false,
      cgs: [],
      comments: comments
    };
  });
  const menu = document.getElementById('mm-onair-menu');
  if(menu) menu.style.display = 'none';
  render();
  scheduleSave();
};

// === Tabler icons (선택) ===
const tablerCss = document.createElement('link');
tablerCss.rel = 'stylesheet';
tablerCss.href = 'https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.47.0/tabler-icons.min.css';
document.head.appendChild(tablerCss);

// === 빠른 Q 박스: paste 자동 파싱 ===
(function(){
  const inp = document.getElementById('mm-quick-q');
  if(!inp) return;
  inp.addEventListener('paste', (e) => {
    const text = (e.clipboardData || window.clipboardData).getData('text') || '';
    if(!text || !text.includes('\n')) return; // 한 줄이면 기본 동작
    const lines = text.split(/\r?\n/);
    const hasQPattern = lines.some(l => /^\s*Q[\d-]+\s*\./.test(l));
    if(!hasQPattern) return; // Q 패턴 없으면 기본 동작
    e.preventDefault();
    const added = importTextAsQuestions(text);
    if(added > 0) inp.value = '';
  });
})();

// === 초기 로드 ===
loadMindmap();
</script>

</body>
</html>"""

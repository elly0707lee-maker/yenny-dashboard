"""
완대본 페이지 — docx 업로드 후 코너/Q/CG로 자동 분리해서 펼침.
각 Q마다 메모 추가 가능 (인라인 + 떠다니는 스티커 토글).

1단계 (이 파일): 페이지 + docx 파싱 + 메모리 메모.
다음 단계: 메모 DB 저장 / 인라인↔스티커 토글 드래그.
"""
import re
import io
import logging

logger = logging.getLogger(__name__)


# ── 완대본 파싱 ────────────────────────────────────────────
def parse_wandaebon_docx(file_bytes: bytes) -> dict:
    """docx 파일을 받아서 코너/Q/CG/멘트 구조로 분리.

    핵심 규칙 (extract-text 결과 분석):
    - `이예은\\t\\t내용` → 화자 + 본문 시작 (탭으로 구분)
    - `\\t\\t이어진 내용` → 들여쓰기 → 이전 항목에 합침
    - `수퍼>` 시작 → CG 자막 (현재 Q에 종속)
    - `네임수퍼>` 시작 → 출연자 소개 자막
    - `#1. 오프닝` → 코너 헤더
    """
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))

    title = ""
    date_str = ""
    corners = []
    cur_corner = None
    cur_question = None
    cur_narration = None  # 직전 narration (이어 붙이기용)

    CORNER_HEADER = re.compile(r'^#(\d+)\.\s*(.+)$')
    SPEAKER_LINE = re.compile(r'^([가-힣]{2,5})\t+(.*)$')  # 화자 + 탭 + 본문
    INDENT_LINE = re.compile(r'^\t+(.*)$')  # 탭으로 시작 = 들여쓰기
    QUESTION_NUM = re.compile(r'^(Q\d+(?:-\d+)?)\.?\s*(.*)$', re.IGNORECASE)
    SUPER_LINE = re.compile(r'^수퍼\s*[>＞]\s*[:：]?\s*(.*)$')
    NAME_SUPER = re.compile(r'^네임수퍼\s*[>＞]\s*[:：]?\s*(.*)$')
    DATE_PATTERN = re.compile(r'^(20\d{2}\s*[/.\-년]\s*\d{1,2}\s*[/.\-월]\s*\d{1,2}.*)$')

    for p in doc.paragraphs:
        # 빈 줄로 끊김 → 직전 narration 종료 (이어 붙이지 않게)
        if not p.text.strip():
            cur_narration = None
            continue

        text = p.text  # strip 안 함 — 탭 보존

        # 1. 첫 줄: 제목
        if not title and ("머니플러스" in text or "한국경제" in text):
            title = text.strip().strip("*<>").strip()
            continue

        # 2. 날짜
        text_stripped = text.strip()
        m = DATE_PATTERN.match(text_stripped)
        if m and not date_str:
            date_str = m.group(1).strip()
            continue

        # 3. 코너 헤더
        m = CORNER_HEADER.match(text_stripped)
        if m:
            if cur_corner:
                corners.append(cur_corner)
            cur_corner = {
                "num": m.group(1),
                "title": m.group(2).strip(),
                "items": []
            }
            cur_question = None
            cur_narration = None
            continue

        if not cur_corner:
            continue

        # 4. 네임 수퍼
        m = NAME_SUPER.match(text_stripped)
        if m:
            name_text = m.group(1).strip()
            if name_text:
                cur_corner["items"].append({"type": "name_super", "text": name_text})
            cur_question = None
            cur_narration = None
            continue

        # 5. 수퍼 (CG)
        m = SUPER_LINE.match(text_stripped)
        if m:
            cg_text = m.group(1).strip()
            if not cg_text:
                continue
            if cur_question:
                cur_question.setdefault("cgs", []).append(cg_text)
            else:
                cur_corner["items"].append({"type": "cg", "text": cg_text})
            cur_narration = None
            continue

        # 6. 들여쓰기 (탭으로 시작) → 이전 항목에 합침
        m = INDENT_LINE.match(text)
        if m:
            body = m.group(1).strip()
            if not body:
                continue
            if cur_question:
                # 직전이 Q면 본문에 이어 붙임
                if cur_question["text"]:
                    cur_question["text"] += "\n" + body
                else:
                    cur_question["text"] = body
            elif cur_narration:
                cur_narration["text"] += "\n" + body
            elif cur_corner["items"]:
                last = cur_corner["items"][-1]
                if last.get("type") in ("narration", "question"):
                    last["text"] = (last.get("text", "") + "\n" + body).strip()
            continue

        # 7. 화자 + 본문 (탭으로 구분)
        m = SPEAKER_LINE.match(text)
        if m:
            speaker = m.group(1).strip()
            body = m.group(2).strip()
            # Q번호로 시작?
            qm = QUESTION_NUM.match(body)
            if qm:
                cur_question = {
                    "type": "question",
                    "qnum": qm.group(1).upper(),
                    "speaker": speaker,
                    "text": qm.group(2).strip(),
                    "cgs": []
                }
                cur_corner["items"].append(cur_question)
                cur_narration = None
            else:
                cur_narration = {
                    "type": "narration",
                    "speaker": speaker,
                    "text": body
                }
                cur_corner["items"].append(cur_narration)
                cur_question = None
            continue

        # 8. 그 외 — 평문 narration으로 처리 (드물어야 함)
        if cur_narration:
            cur_narration["text"] += "\n" + text_stripped
        elif cur_corner["items"]:
            last = cur_corner["items"][-1]
            if last.get("type") in ("narration", "question"):
                last["text"] = (last.get("text", "") + "\n" + text_stripped).strip()

    if cur_corner:
        corners.append(cur_corner)

    return {
        "title": title or "완대본",
        "date": date_str or "",
        "corners": corners,
    }


# ── 페이지 HTML ────────────────────────────────────────────
def get_wandaebon_html() -> str:
    """완대본 페이지의 전체 HTML.
    
    /wandaebon 경로에서 이걸 반환.
    """
    return r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ON AIR — Yenny</title>
<link rel="manifest" href="/manifest.json">
<style>
:root{
  --bg:#fdfbf5;
  --card:#fff;
  --text:#1a1d23;
  --text-dim:#5f5e5a;
  --text-faint:#888780;
  --border:#e8e1d0;
  --accent:#e8b84b;
  --blue:#185FA5;
  --blue-bg:#E6F1FB;
  --amber-bg:#FAEEDA;
  --amber-text:#854F0B;
  --amber-text-dark:#4A1B0C;
  --pink-bg:#FBEAF0;
  --pink-text:#993556;
  --pink-text-dark:#4B1528;
  --teal-bg:#E1F5EE;
  --teal-text:#0F6E56;
  --teal-text-dark:#04342C;
}
*{box-sizing:border-box}
body{
  margin:0;padding:0;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans KR',sans-serif;
  font-size:14px;line-height:1.6;
  position:relative;  /* 떠있는 메모의 absolute 기준점 */
}
.topbar{
  position:sticky;top:0;z-index:50;background:var(--card);
  border-bottom:1px solid var(--border);padding:10px 18px;
  display:flex;justify-content:space-between;align-items:center;
}
.toolbar{
  position:sticky;top:55px;z-index:49;background:#fffdf6;
  border-bottom:1px solid var(--border);padding:6px 18px;
  display:flex;align-items:center;gap:6px;flex-wrap:wrap;
}
.toolbar-label{font-size:10px;color:var(--text-faint);margin-right:4px;letter-spacing:.04em;}
.tool-btn{
  background:var(--card);border:1px solid var(--border);border-radius:5px;
  width:28px;height:28px;display:inline-flex;align-items:center;justify-content:center;
  cursor:pointer;font-size:13px;font-family:inherit;padding:0;
  transition:all .1s;
}
.tool-btn:hover{background:#f5f0e0;border-color:var(--accent);}
.tool-btn.red{color:#d63031;font-weight:700;}
.tool-btn.blue{color:#0984e3;font-weight:700;}
.tool-btn.hl{background:#fff59d;}
.tool-btn.b{font-weight:700;}
.tool-btn.i{font-style:italic;}
.tool-divider{width:1px;height:18px;background:var(--border);margin:0 4px;}
.topbar-left{display:flex;align-items:center;gap:14px;}
.brand{font-weight:700;font-size:15px;}
.brand a{color:var(--text);text-decoration:none;}
.meta-block{font-size:12px;color:var(--text-dim);}
.meta-label{font-size:10px;color:var(--text-faint);letter-spacing:.05em;}
.meta-title{font-size:14px;font-weight:600;color:var(--text);}
.btn{
  border:1px solid var(--border);background:var(--card);color:var(--text);
  padding:6px 12px;border-radius:6px;font-size:12px;cursor:pointer;
  font-family:inherit;
}
.btn:hover{background:#f5f0e0;}
.btn-primary{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600;}
.btn-primary:hover{background:#d4a73b;}
.btn-ghost{background:transparent;}
.container{max-width:1100px;margin:0 auto;padding:20px;}
.upload-zone{
  border:2px dashed var(--border);border-radius:12px;padding:40px 20px;
  text-align:center;background:var(--card);margin:20px 0;
  cursor:pointer;transition:all .15s;
}
.upload-zone:hover{border-color:var(--accent);background:#fdf8eb;}
.upload-icon{font-size:40px;display:block;margin-bottom:10px;}
.upload-hint{font-size:13px;color:var(--text-dim);margin-top:6px;}
#file-input{display:none;}
.corner-card{
  background:var(--card);border-radius:12px;padding:14px 18px;
  margin-bottom:14px;border-left:4px solid var(--blue);
}
.corner-header{
  font-size:13px;font-weight:600;color:var(--blue);
  letter-spacing:.04em;margin-bottom:10px;
}
.q-row{
  display:grid;grid-template-columns:minmax(0,1fr) 200px;gap:14px;
  padding:12px 0;border-top:1px solid var(--border);
}
.q-row:first-of-type{border-top:none;}
.q-meta{display:flex;gap:8px;align-items:center;margin-bottom:6px;flex-wrap:wrap;}
.q-tag{
  font-size:11px;padding:2px 8px;background:var(--blue-bg);color:var(--blue);
  border-radius:6px;font-weight:600;
}
.q-speaker{font-size:11px;color:var(--text-dim);}
.q-text{
  font-size:13px;line-height:1.65;margin-bottom:8px;color:var(--text);white-space:pre-wrap;
  padding:4px 6px;border-radius:4px;outline:none;min-height:1.5em;
  border:1px dashed transparent;transition:border-color .12s;
}
.q-text[contenteditable=true]:hover{border-color:var(--border);}
.q-text[contenteditable=true]:focus{border-color:var(--accent);background:#fffef8;}
.q-text[contenteditable=true]:empty:before{
  content:"질문 입력...";color:#aaa;
}
.cg-block{
  border-left:2px solid var(--border);padding:4px 0 4px 10px;margin-top:6px;
}
.cg-label{font-size:10px;color:var(--text-faint);letter-spacing:.05em;margin-bottom:3px;}
.cg-list{font-size:11.5px;color:var(--text-dim);line-height:1.6;}
.cg-list div{margin-bottom:2px;}
.cg-list div:before{content:"· ";color:var(--text-faint);}
.narration{
  font-size:12.5px;color:var(--text-dim);line-height:1.65;
  padding:6px 0;font-style:italic;white-space:pre-wrap;
}
.narration-speaker{font-weight:600;color:var(--text);font-style:normal;margin-right:8px;}
.name-super{
  font-size:11px;color:var(--text-faint);padding:4px 0;
  border-bottom:1px dashed var(--border);margin-bottom:6px;
}
.name-super:before{content:"📺 ";}
.memo-box{
  background:var(--amber-bg);border-radius:8px;padding:8px 10px;
  display:flex;flex-direction:column;
}
.memo-header{
  display:flex;justify-content:space-between;align-items:center;
  font-size:10px;color:var(--amber-text);font-weight:600;
  letter-spacing:.04em;margin-bottom:4px;
}
.memo-header-actions{display:flex;gap:4px;align-items:center;}
.memo-color-dot{
  width:12px;height:12px;border-radius:50%;cursor:pointer;
  border:1px solid transparent;
}
.memo-color-dot.active{border-color:#000;}
.memo-detach{cursor:pointer;font-size:13px;}
.memo-text{
  background:transparent;border:0;outline:none;
  font-family:inherit;font-size:11.5px;line-height:1.5;
  color:var(--amber-text-dark);min-height:50px;flex:1;width:100%;
  white-space:pre-wrap;word-break:break-word;
}
.memo-text[contenteditable=true]:empty:before{
  content:"메모 입력...";color:rgba(0,0,0,0.3);
}
.memo-box.color-pink{background:var(--pink-bg);}
.memo-box.color-pink .memo-header{color:var(--pink-text);}
.memo-box.color-pink .memo-text{color:var(--pink-text-dark);}
.memo-box.color-teal{background:var(--teal-bg);}
.memo-box.color-teal .memo-header{color:var(--teal-text);}
.memo-box.color-teal .memo-text{color:var(--teal-text-dark);}
.memo-empty{
  border:1.5px dashed var(--border);border-radius:8px;padding:12px;
  display:flex;align-items:center;justify-content:center;
  color:var(--text-faint);font-size:11px;cursor:pointer;
}
.memo-empty:hover{border-color:var(--accent);color:var(--accent);background:#fdf8eb;}
.memo-detached-placeholder{
  border:1.5px dashed var(--border);border-radius:8px;padding:10px;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  color:var(--text-faint);font-size:10px;cursor:pointer;opacity:0.7;
  line-height:1.5;text-align:center;
}
.memo-detached-placeholder:hover{border-color:var(--accent);opacity:1;}
.floating-memo{
  position:absolute;width:180px;border-radius:8px;
  padding:8px 10px;box-shadow:0 3px 12px rgba(0,0,0,0.15);
  cursor:move;z-index:100;background:var(--amber-bg);
  transform:rotate(-2deg);transition:transform .1s ease;
}
.floating-memo.color-pink{background:var(--pink-bg);}
.floating-memo.color-pink .memo-header{color:var(--pink-text);}
.floating-memo.color-pink .memo-text{color:var(--pink-text-dark);}
.floating-memo.color-teal{background:var(--teal-bg);}
.floating-memo.color-teal .memo-header{color:var(--teal-text);}
.floating-memo.color-teal .memo-text{color:var(--teal-text-dark);}
.floating-memo .memo-header{color:var(--amber-text);}
.floating-memo .memo-text{color:var(--amber-text-dark);}
.floating-memo:active{transform:rotate(0deg) scale(1.02);box-shadow:0 5px 20px rgba(0,0,0,0.2);}
.floating-memo.dragging{transform:rotate(0deg) scale(1.05);}

/* ── 인쇄용 ─────────────────────────────────────── */
@media print {
  @page { margin: 12mm 10mm; }
  body { background: white !important; font-size: 11pt; }
  /* 인터랙티브 도구 다 숨김 */
  .topbar, .toolbar { display: none !important; }
  .memo-empty,
  .memo-detached-placeholder { display: none !important; }
  .memo-color-dot,
  .memo-detach { display: none !important; }
  .floating-memo { display: none !important; }
  /* 컨테이너 풀폭 */
  .container { padding: 0; max-width: none; }
  /* 코너 카드 — 검정 테두리만, 그림자 없음 */
  .corner-card {
    border: 1px solid #999;
    border-left: 3px solid #185FA5;
    box-shadow: none;
    padding: 10px 12px;
    margin-bottom: 8px;
    page-break-inside: avoid;
    break-inside: avoid;
  }
  .corner-header { 
    page-break-after: avoid;
    break-after: avoid;
    font-size: 12pt;
  }
  /* Q-row — 한 질문 단위로 페이지 깨지지 않게 */
  .q-row {
    page-break-inside: avoid;
    break-inside: avoid;
    grid-template-columns: minmax(0,1fr) 180px;
  }
  .q-text {
    border: 0 !important;
    background: transparent !important;
    padding: 0;
    font-size: 11pt;
  }
  /* 메모 — 인쇄 시 깔끔하게 */
  .memo-box {
    border: 1px solid #aaa;
    box-shadow: none;
    padding: 6px 8px;
  }
  .memo-text {
    font-size: 9.5pt;
    min-height: auto;
  }
  /* 배경색·하이라이트 그대로 인쇄 */
  * {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
    color-adjust: exact !important;
  }
  /* 텍스트 도구로 적용한 색깔도 그대로 */
  .q-text *, .memo-text * {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
}
.empty-state{text-align:center;padding:60px 20px;color:var(--text-dim);}
.loading{text-align:center;padding:40px 20px;color:var(--text-dim);}
.err{
  background:#fdeaea;color:#993333;padding:10px 14px;border-radius:8px;
  font-size:12px;margin:10px 0;
}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-left">
    <div class="brand"><a href="/">⬅ Yenny</a></div>
    <div class="meta-block">
      <div class="meta-label">🎙️ ON AIR</div>
      <div class="meta-title" id="meta-title">완대본 업로드 대기 중</div>
    </div>
  </div>
  <div style="display:flex;gap:6px;align-items:center;">
    <input type="file" id="file-input" accept=".docx">
    <button class="btn btn-primary" onclick="document.getElementById('file-input').click()">📎 docx 업로드</button>
    <button class="btn" onclick="printPage()" title="인쇄 (Cmd+P)">🖨️ 인쇄</button>
  </div>
</div>

<div class="toolbar">
  <span class="toolbar-label">텍스트 도구</span>
  <button class="tool-btn red" onmousedown="event.preventDefault()" onclick="applyFmt('foreColor','#d63031')" title="빨강 (⌘⇧1)">A</button>
  <button class="tool-btn blue" onmousedown="event.preventDefault()" onclick="applyFmt('foreColor','#0984e3')" title="파랑 (⌘⇧2)">A</button>
  <button class="tool-btn" onmousedown="event.preventDefault()" onclick="applyFmt('foreColor','#1a1d23')" title="검정 (⌘⇧3)">A</button>
  <div class="tool-divider"></div>
  <button class="tool-btn hl" onmousedown="event.preventDefault()" onclick="applyFmt('hiliteColor','#fff59d')" title="노랑 하이라이트 (⌘⇧4)">■</button>
  <button class="tool-btn" style="background:#ffcdd2;" onmousedown="event.preventDefault()" onclick="applyFmt('hiliteColor','#ffcdd2')" title="분홍 하이라이트 (⌘⇧5)">■</button>
  <button class="tool-btn" style="background:#c8e6c9;" onmousedown="event.preventDefault()" onclick="applyFmt('hiliteColor','#c8e6c9')" title="민트 하이라이트 (⌘⇧6)">■</button>
  <div class="tool-divider"></div>
  <button class="tool-btn b" onmousedown="event.preventDefault()" onclick="applyFmt('bold')" title="굵게 (⌘B)">B</button>
  <button class="tool-btn i" onmousedown="event.preventDefault()" onclick="applyFmt('italic')" title="기울임 (⌘I)">I</button>
  <button class="tool-btn" onmousedown="event.preventDefault()" onclick="applyFmt('underline')" title="밑줄 (⌘U)"><u>U</u></button>
  <div class="tool-divider"></div>
  <button class="tool-btn" onmousedown="event.preventDefault()" onclick="applyFmt('removeFormat')" title="서식 지우기 (⌘⇧0)" style="font-size:11px;">✖</button>
  <span style="font-size:10px;color:var(--text-faint);margin-left:auto;">💡 선택 후 클릭 · 또는 ⌘⇧1~6</span>
</div>

<div class="container">
  <div id="content">
    <div class="upload-zone" onclick="document.getElementById('file-input').click()">
      <div class="upload-icon">📄</div>
      <div style="font-size:14px;font-weight:600;">완대본 docx 파일을 올려주세요</div>
      <div class="upload-hint">자동으로 코너 / Q / CG 분리해서 펼쳐드릴게요</div>
    </div>
  </div>
</div>

<script>
const fileInput = document.getElementById('file-input');
const contentEl = document.getElementById('content');
const metaTitleEl = document.getElementById('meta-title');

// 메모는 일단 메모리만 — { "1-Q0": {text, color}, ... }
let _memos = {};
// Q 텍스트 사용자 편집 — { "1-Q0": "수정된 HTML", ... }
let _qEdits = {};

// ── 텍스트 도구 ───────────────────────────────────────
function applyFmt(cmd, value){
  // 도구 버튼은 onmousedown="event.preventDefault()" 로 contenteditable 포커스 유지
  document.execCommand(cmd, false, value || null);
}

// 단축키: Cmd/Ctrl + Shift + 숫자
// B/I/U는 브라우저 기본 단축키 (Cmd+B, Cmd+I, Cmd+U)
document.addEventListener('keydown', (e) => {
  const active = document.activeElement;
  if(!active || !active.isContentEditable) return;
  const isCmd = e.metaKey || e.ctrlKey;
  if(!isCmd || !e.shiftKey) return;
  const map = {
    '1': ['foreColor', '#d63031'],     // 빨강
    '2': ['foreColor', '#0984e3'],     // 파랑
    '3': ['foreColor', '#1a1d23'],     // 검정 (원복)
    '4': ['hiliteColor', '#fff59d'],   // 노랑 하이라이트
    '5': ['hiliteColor', '#ffcdd2'],   // 분홍 하이라이트
    '6': ['hiliteColor', '#c8e6c9'],   // 민트 하이라이트
    '0': ['removeFormat', null],       // 서식 지우기
  };
  const hit = map[e.key];
  if(hit){
    e.preventDefault();
    applyFmt(hit[0], hit[1]);
  }
});

function saveQEdit(key, html){
  _qEdits[key] = html;
}

fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if(!file) return;
  contentEl.innerHTML = '<div class="loading">📖 완대본 파싱 중...</div>';
  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await fetch('/onair/upload', {method:'POST', body: fd});
    if(!res.ok){
      const t = await res.text();
      contentEl.innerHTML = `<div class="err">업로드 실패 HTTP ${res.status}: ${t.slice(0,200)}</div>`;
      return;
    }
    const data = await res.json();
    if(data.error){
      contentEl.innerHTML = `<div class="err">파싱 실패: ${data.error}</div>`;
      return;
    }
    renderWandaebon(data);
  } catch(err) {
    contentEl.innerHTML = `<div class="err">오류: ${err.message}</div>`;
  }
});

function esc(s){return (s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

function renderWandaebon(data){
  metaTitleEl.textContent = `${data.title} ${data.date ? ' · ' + data.date : ''}`;
  if(!data.corners || !data.corners.length){
    contentEl.innerHTML = '<div class="empty-state">코너를 찾지 못했어요. 파일 형식을 확인해주세요.</div>';
    return;
  }
  let html = '';
  data.corners.forEach(corner => {
    html += `<div class="corner-card">
      <div class="corner-header">#${esc(corner.num)} · ${esc(corner.title)}</div>`;
    corner.items.forEach((it, idx) => {
      const memoKey = `${corner.num}-${it.qnum || ('item'+idx)}`;
      if(it.type === 'question'){
        html += renderQuestionRow(corner, it, memoKey);
      } else if(it.type === 'narration'){
        html += `<div class="narration"><span class="narration-speaker">${esc(it.speaker)}</span>${esc(it.text)}</div>`;
      } else if(it.type === 'name_super'){
        html += `<div class="name-super">${esc(it.text)}</div>`;
      } else if(it.type === 'cg'){
        html += `<div class="cg-block"><div class="cg-label">CG · 수퍼</div><div class="cg-list"><div>${esc(it.text)}</div></div></div>`;
      }
    });
    html += '</div>';
  });
  contentEl.innerHTML = html;
}

function renderQuestionRow(corner, q, memoKey){
  const memo = _memos[memoKey];
  // 사용자 편집된 Q text 있으면 그걸로
  const qHtml = _qEdits[memoKey] !== undefined ? _qEdits[memoKey] : esc(q.text);
  const cgsHtml = (q.cgs && q.cgs.length) ? `
    <div class="cg-block">
      <div class="cg-label">CG · 수퍼</div>
      <div class="cg-list">${q.cgs.map(c=>'<div>'+esc(c)+'</div>').join('')}</div>
    </div>` : '';

  let memoHtml;
  if(memo && memo.floating){
    // 떠다님 — 자리엔 placeholder만
    memoHtml = `
      <div class="memo-detached-placeholder" onclick="reattachMemo('${memoKey}')" title="다시 인라인으로 붙이기">
        ↗ 스티커로 떠있음<br/>
        <span style="font-size:9px;">(클릭해서 다시 붙이기)</span>
      </div>`;
  } else if(memo){
    // 인라인 모드
    memoHtml = renderInlineMemo(memoKey, memo);
  } else {
    memoHtml = `<div class="memo-empty" onclick="addMemo('${memoKey}')">+ 메모 추가</div>`;
  }

  return `
    <div class="q-row" id="q-${memoKey}">
      <div>
        <div class="q-meta">
          <span class="q-tag">${esc(q.qnum)}</span>
          <span class="q-speaker">${esc(q.speaker)}${q.target ? ' → ' + esc(q.target) : ''}</span>
        </div>
        <div class="q-text" contenteditable="true" oninput="saveQEdit('${memoKey}', this.innerHTML)">${qHtml}</div>
        ${cgsHtml}
      </div>
      <div>${memoHtml}</div>
    </div>`;
}

function renderInlineMemo(key, memo){
  return `
    <div class="memo-box ${memo.color ? 'color-'+memo.color : ''}" data-key="${key}">
      <div class="memo-header">
        <span>📝 메모</span>
        <div class="memo-header-actions">
          <span class="memo-color-dot ${(!memo.color||memo.color==='amber')?'active':''}" style="background:#FAEEDA;border:1px solid #BA7517;" onclick="setMemoColor('${key}', 'amber')" title="amber"></span>
          <span class="memo-color-dot ${memo.color==='pink'?'active':''}" style="background:#FBEAF0;border:1px solid #D4537E;" onclick="setMemoColor('${key}', 'pink')" title="pink"></span>
          <span class="memo-color-dot ${memo.color==='teal'?'active':''}" style="background:#E1F5EE;border:1px solid #1D9E75;" onclick="setMemoColor('${key}', 'teal')" title="teal"></span>
          <span class="memo-detach" onclick="detachMemo('${key}')" title="떼어서 떠다니게">↗</span>
          <span class="memo-detach" onclick="deleteMemo('${key}')" title="삭제">✕</span>
        </div>
      </div>
      <div class="memo-text" contenteditable="true" oninput="updateMemo('${key}', this.innerHTML)">${memo.text||''}</div>
    </div>`;
}

function addMemo(key){
  _memos[key] = {text:'', color:'amber'};
  refreshQRow(key);
  setTimeout(()=>{
    const ta = document.querySelector(`#q-${key} .memo-text`);
    if(ta) ta.focus();
  }, 50);
}

function updateMemo(key, val){
  if(_memos[key]) _memos[key].text = val;
}

function setMemoColor(key, color){
  if(_memos[key]){
    _memos[key].color = color;
    refreshQRow(key);
  }
}

function deleteMemo(key){
  if(confirm('이 메모 삭제할까요?')){
    delete _memos[key];
    removeFloatingMemo(key);
    refreshQRow(key);
  }
}

// ── 떼기 / 다시 붙이기 / 드래그 ──────────────────
function detachMemo(key){
  if(!_memos[key]) return;
  _memos[key].floating = true;
  // 처음 떼면 현재 보고 있는 화면에 나타나게 (스크롤 위치 반영)
  if(!_memos[key].pos){
    const stackOffset = Object.values(_memos).filter(m=>m.floating).length * 30;
    _memos[key].pos = {
      x: window.scrollX + window.innerWidth - 220 - 80 - Math.random()*60,
      y: window.scrollY + 120 + stackOffset
    };
  }
  refreshQRow(key);
  renderFloatingMemo(key);
}

function reattachMemo(key){
  if(!_memos[key]) return;
  _memos[key].floating = false;
  removeFloatingMemo(key);
  refreshQRow(key);
}

function renderFloatingMemo(key){
  const memo = _memos[key];
  if(!memo) return;
  let el = document.getElementById(`float-${key}`);
  if(!el){
    el = document.createElement('div');
    el.id = `float-${key}`;
    document.body.appendChild(el);
    makeDraggable(el, key);
  }
  el.className = `floating-memo ${memo.color ? 'color-'+memo.color : ''}`;
  el.style.left = memo.pos.x + 'px';
  el.style.top = memo.pos.y + 'px';
  el.innerHTML = `
    <div class="memo-header" data-drag-handle="true">
      <span>📌 ${esc(key)}</span>
      <div class="memo-header-actions">
        <span class="memo-color-dot ${(!memo.color||memo.color==='amber')?'active':''}" style="background:#FAEEDA;border:1px solid #BA7517;" onclick="setMemoColor('${key}', 'amber')" title="amber"></span>
        <span class="memo-color-dot ${memo.color==='pink'?'active':''}" style="background:#FBEAF0;border:1px solid #D4537E;" onclick="setMemoColor('${key}', 'pink')" title="pink"></span>
        <span class="memo-color-dot ${memo.color==='teal'?'active':''}" style="background:#E1F5EE;border:1px solid #1D9E75;" onclick="setMemoColor('${key}', 'teal')" title="teal"></span>
        <span class="memo-detach" onclick="reattachMemo('${key}')" title="다시 인라인으로">↘</span>
        <span class="memo-detach" onclick="deleteMemo('${key}')" title="삭제">✕</span>
      </div>
    </div>
    <div class="memo-text" contenteditable="true" oninput="updateFloatingMemo('${key}', this.innerHTML)">${memo.text||''}</div>
  `;
}

function updateFloatingMemo(key, html){
  // 입력 시 _memos만 갱신, DOM은 그대로 (커서 위치 유지)
  if(_memos[key]) _memos[key].text = html;
}

function removeFloatingMemo(key){
  const el = document.getElementById(`float-${key}`);
  if(el) el.remove();
}

function makeDraggable(el, key){
  let dragging = false;
  let offsetX = 0, offsetY = 0;

  el.addEventListener('mousedown', (e) => {
    // 텍스트 영역, 색깔 점, 버튼 클릭이면 드래그 안 함
    const target = e.target;
    if(target.classList.contains('memo-text')) return;
    if(target.classList.contains('memo-color-dot')) return;
    if(target.classList.contains('memo-detach')) return;
    if(target.tagName === 'DIV' && target.contentEditable === 'true') return;
    
    dragging = true;
    el.classList.add('dragging');
    const rect = el.getBoundingClientRect();
    offsetX = e.clientX - rect.left;
    offsetY = e.clientY - rect.top;
    e.preventDefault();
  });

  function onMove(e){
    if(!dragging) return;
    // pageX/pageY = 페이지 좌표 (스크롤 포함) — 종이에 진짜로 붙음
    const x = Math.max(0, e.pageX - offsetX);
    const y = Math.max(0, e.pageY - offsetY);
    el.style.left = x + 'px';
    el.style.top = y + 'px';
    if(_memos[key]) _memos[key].pos = {x, y};
  }

  function onUp(){
    if(dragging){
      dragging = false;
      el.classList.remove('dragging');
    }
  }

  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
}

// ── 인쇄 ──────────────────────────────────────────
function printPage(){
  // 떠있는 메모 키 기억해뒀다가 인쇄 후 복원
  const floatingKeys = Object.keys(_memos).filter(k => _memos[k] && _memos[k].floating);
  
  // 임시로 다 인라인으로
  floatingKeys.forEach(k => {
    _memos[k].floating = false;
    removeFloatingMemo(k);
    refreshQRow(k);
  });
  
  // 인쇄 끝나면 다시 떠다니게 복원
  const restore = () => {
    floatingKeys.forEach(k => {
      if(_memos[k]){
        _memos[k].floating = true;
        renderFloatingMemo(k);
        refreshQRow(k);
      }
    });
    window.removeEventListener('afterprint', restore);
  };
  window.addEventListener('afterprint', restore);
  
  // DOM 업데이트 끝난 다음 인쇄 다이얼로그
  setTimeout(() => window.print(), 100);
}

// Cmd+P / Ctrl+P 가로채기 — 우리 printPage() 호출
document.addEventListener('keydown', (e) => {
  if((e.metaKey || e.ctrlKey) && e.key === 'p' && !e.shiftKey){
    e.preventDefault();
    printPage();
  }
});

function refreshQRow(key){
  const row = document.getElementById(`q-${key}`);
  if(!row) return;
  const memoCell = row.lastElementChild;
  const memo = _memos[key];
  if(memo && memo.floating){
    memoCell.innerHTML = `
      <div class="memo-detached-placeholder" onclick="reattachMemo('${key}')" title="다시 인라인으로 붙이기">
        ↗ 스티커로 떠있음<br/>
        <span style="font-size:9px;">(클릭해서 다시 붙이기)</span>
      </div>`;
  } else if(memo){
    memoCell.innerHTML = renderInlineMemo(key, memo);
  } else {
    memoCell.innerHTML = `<div class="memo-empty" onclick="addMemo('${key}')">+ 메모 추가</div>`;
  }
}
</script>
</body>
</html>"""

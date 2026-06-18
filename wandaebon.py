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
<title>완대본 — Yenny</title>
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
}
.topbar{
  position:sticky;top:0;z-index:50;background:var(--card);
  border-bottom:1px solid var(--border);padding:10px 18px;
  display:flex;justify-content:space-between;align-items:center;
}
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
.q-text{font-size:13px;line-height:1.65;margin-bottom:8px;color:var(--text);white-space:pre-wrap;}
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
  background:transparent;border:0;outline:none;resize:none;
  font-family:inherit;font-size:11.5px;line-height:1.5;
  color:var(--amber-text-dark);min-height:50px;flex:1;width:100%;
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
      <div class="meta-label">완대본</div>
      <div class="meta-title" id="meta-title">파일 업로드 대기 중</div>
    </div>
  </div>
  <div style="display:flex;gap:6px;align-items:center;">
    <input type="file" id="file-input" accept=".docx">
    <button class="btn btn-primary" onclick="document.getElementById('file-input').click()">📎 docx 업로드</button>
  </div>
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

fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if(!file) return;
  contentEl.innerHTML = '<div class="loading">📖 완대본 파싱 중...</div>';
  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await fetch('/wandaebon/upload', {method:'POST', body: fd});
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
  const cgsHtml = (q.cgs && q.cgs.length) ? `
    <div class="cg-block">
      <div class="cg-label">CG · 수퍼</div>
      <div class="cg-list">${q.cgs.map(c=>'<div>'+esc(c)+'</div>').join('')}</div>
    </div>` : '';

  const memoHtml = memo ? `
    <div class="memo-box ${memo.color ? 'color-'+memo.color : ''}" data-key="${memoKey}">
      <div class="memo-header">
        <span>📝 메모</span>
        <div class="memo-header-actions">
          <span class="memo-color-dot ${(!memo.color||memo.color==='amber')?'active':''}" style="background:#FAEEDA;border:1px solid #BA7517;" onclick="setMemoColor('${memoKey}', 'amber')" title="amber"></span>
          <span class="memo-color-dot ${memo.color==='pink'?'active':''}" style="background:#FBEAF0;border:1px solid #D4537E;" onclick="setMemoColor('${memoKey}', 'pink')" title="pink"></span>
          <span class="memo-color-dot ${memo.color==='teal'?'active':''}" style="background:#E1F5EE;border:1px solid #1D9E75;" onclick="setMemoColor('${memoKey}', 'teal')" title="teal"></span>
          <span class="memo-detach" onclick="deleteMemo('${memoKey}')" title="삭제">✕</span>
        </div>
      </div>
      <textarea class="memo-text" oninput="updateMemo('${memoKey}', this.value)" placeholder="메모 입력...">${esc(memo.text||'')}</textarea>
    </div>` : `
    <div class="memo-empty" onclick="addMemo('${memoKey}')">+ 메모 추가</div>`;

  return `
    <div class="q-row" id="q-${memoKey}">
      <div>
        <div class="q-meta">
          <span class="q-tag">${esc(q.qnum)}</span>
          <span class="q-speaker">${esc(q.speaker)}${q.target ? ' → ' + esc(q.target) : ''}</span>
        </div>
        <div class="q-text">${esc(q.text)}</div>
        ${cgsHtml}
      </div>
      <div>${memoHtml}</div>
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
    refreshQRow(key);
  }
}

function refreshQRow(key){
  const row = document.getElementById(`q-${key}`);
  if(!row) return;
  const memoCell = row.lastElementChild;
  const memo = _memos[key];
  if(memo){
    memoCell.innerHTML = `
      <div class="memo-box ${memo.color ? 'color-'+memo.color : ''}">
        <div class="memo-header">
          <span>📝 메모</span>
          <div class="memo-header-actions">
            <span class="memo-color-dot ${(!memo.color||memo.color==='amber')?'active':''}" style="background:#FAEEDA;border:1px solid #BA7517;" onclick="setMemoColor('${key}', 'amber')" title="amber"></span>
            <span class="memo-color-dot ${memo.color==='pink'?'active':''}" style="background:#FBEAF0;border:1px solid #D4537E;" onclick="setMemoColor('${key}', 'pink')" title="pink"></span>
            <span class="memo-color-dot ${memo.color==='teal'?'active':''}" style="background:#E1F5EE;border:1px solid #1D9E75;" onclick="setMemoColor('${key}', 'teal')" title="teal"></span>
            <span class="memo-detach" onclick="deleteMemo('${key}')" title="삭제">✕</span>
          </div>
        </div>
        <textarea class="memo-text" oninput="updateMemo('${key}', this.value)" placeholder="메모 입력...">${esc(memo.text||'')}</textarea>
      </div>`;
  } else {
    memoCell.innerHTML = `<div class="memo-empty" onclick="addMemo('${key}')">+ 메모 추가</div>`;
  }
}
</script>
</body>
</html>"""

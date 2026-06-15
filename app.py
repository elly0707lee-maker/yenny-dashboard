"""
app.py 체크포인트 편집 기능 패치 스크립트
실행: python3 patch_app.py app.py
"""
import sys, re

if len(sys.argv) < 2:
    print("사용법: python3 patch_app.py app.py")
    sys.exit(1)

path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# ── 패치 1: 체크포인트 헤더에 편집 버튼 추가 ──
old1 = '''      <div class="content-header">
        <span class="content-title">☑ 오늘 체크포인트</span>
        <span class="content-date" id="checkpoint-date"></span>
      </div>'''

new1 = '''      <div class="content-header">
        <span class="content-title">☑ 오늘 체크포인트</span>
        <div style="display:flex;gap:6px;align-items:center;">
          <span class="content-date" id="checkpoint-date"></span>
          <button class="btn" onclick="enterCpEdit()" id="cp-edit-btn" style="font-size:11px;padding:5px 10px;">✏️ 편집</button>
        </div>
      </div>'''

if old1 not in content:
    print("❌ 패치 1 실패 - 헤더를 찾을 수 없어요")
    sys.exit(1)
content = content.replace(old1, new1, 1)
print("✅ 패치 1 완료 - 편집 버튼 추가")

# ── 패치 2: JS 편집 함수 삽입 (loadAll(); 직전) ──
js_patch = r"""
// ── 체크포인트 인라인 편집 ─────────────────────────────
let _cpLinkMap = [];

function cpRawToEdit(raw) {
  _cpLinkMap = [];
  return raw.replace(/\[\[LINK:([^\]]+)\]\]/g, (_, url) => {
    _cpLinkMap.push(url);
    return '[🔗' + _cpLinkMap.length + ']';
  });
}

function cpEditToRaw(editText) {
  let result = editText;
  _cpLinkMap.forEach((url, i) => {
    result = result.split('[🔗' + (i+1) + ']').join('[[LINK:' + url + ']]');
  });
  return result;
}

function enterCpEdit() {
  const editText = cpRawToEdit(_cpRaw || '');
  const body = document.getElementById('checkpoint-body');
  const tabs = document.getElementById('cp-tabs');
  const editBtn = document.getElementById('cp-edit-btn');
  if(tabs) tabs.style.display = 'none';
  if(editBtn) editBtn.style.display = 'none';

  let legendHtml = '';
  if(_cpLinkMap.length > 0){
    legendHtml = '<div style="margin-bottom:10px;padding:10px 12px;background:#fff3a0;border-radius:8px;font-size:11px;line-height:1.7;">';
    legendHtml += '<div style="font-weight:700;margin-bottom:6px;">🔗 링크 토큰 — 지우면 링크 사라져요!</div>';
    _cpLinkMap.forEach((url, i) => {
      const short = url.length > 55 ? url.slice(0,55)+'…' : url;
      legendHtml += '<div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;">'
        + '<b style="background:#1a1d23;color:#e8b84b;padding:1px 6px;border-radius:3px;font-size:11px;white-space:nowrap;">[🔗'+(i+1)+']</b>'
        + '<a href="'+url+'" target="_blank" style="color:#0984e3;font-size:10px;word-break:break-all;">'+short+'</a>'
        + '</div>';
    });
    legendHtml += '</div>';
  }

  const ta = document.createElement('textarea');
  ta.id = 'cp-edit-textarea';
  ta.style.cssText = 'width:100%;min-height:420px;font-family:monospace;font-size:13px;padding:12px;border:1.5px solid #e8b84b;border-radius:8px;background:#fdfbf5;resize:vertical;line-height:1.65;display:block;';
  ta.value = editText;

  const btnRow = document.createElement('div');
  btnRow.style.cssText = 'margin-top:10px;display:flex;gap:8px;align-items:center;';
  btnRow.innerHTML = '<button class="btn btn-green" onclick="saveCpEdit()">💾 저장</button>'
    + '<button class="btn" onclick="cancelCpEdit()">✕ 취소</button>'
    + '<span id="cp-edit-badge" style="font-size:11px;color:#00b894;font-weight:700;display:none;">✓ 저장됨</span>';

  body.innerHTML = legendHtml;
  body.appendChild(ta);
  body.appendChild(btnRow);
  ta.focus();
}

async function saveCpEdit() {
  const ta = document.getElementById('cp-edit-textarea');
  if(!ta) return;
  const rawText = cpEditToRaw(ta.value);
  _cpRaw = rawText;
  try{
    const res = await fetch('/api/post/checkpoint', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: rawText, date: new Date().toISOString().slice(0,10)})
    });
    if(!res.ok){ alert('저장 실패 HTTP ' + res.status); return; }
    const badge = document.getElementById('cp-edit-badge');
    if(badge){ badge.style.display='inline'; }
    setTimeout(() => cancelCpEdit(), 800);
  } catch(e) {
    alert('저장 실패: ' + e.message);
  }
}

function cancelCpEdit() {
  const tabs = document.getElementById('cp-tabs');
  const editBtn = document.getElementById('cp-edit-btn');
  if(tabs) tabs.style.display = '';
  if(editBtn) editBtn.style.display = '';
  const activeBtn = document.querySelector('#cp-tabs .tab.active') || document.querySelector('#cp-tabs .tab');
  if(activeBtn){
    const m = activeBtn.getAttribute('onclick')?.match(/cpTab\(this,'(\w+)'\)/);
    if(m) cpTab(activeBtn, m[1]);
  }
}

"""

old2 = 'loadAll();\nloadFutures();'
if old2 not in content:
    print("❌ 패치 2 실패 - loadAll() 위치를 찾을 수 없어요")
    sys.exit(1)
content = content.replace(old2, js_patch + 'loadAll();\nloadFutures();', 1)
print("✅ 패치 2 완료 - JS 편집 함수 삽입")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"\n✅ {path} 저장 완료!")
print("Railway에 배포하면 바로 사용할 수 있어요.")

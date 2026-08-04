"""
체크포인트 풀 페이지 (/checkpoint)
대시보드의 체크포인트 카드를 별도 페이지로 큰 화면.
"""

def get_checkpoint_page_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Checkpoint · Yenny Dashboard</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>☑</text></svg>">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans KR',sans-serif;background:#fbf9f4;color:#1a1d23;min-height:100vh}
.topbar{background:#1a1d23;color:#e8b84b;padding:14px 24px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}
.topbar-title{font-size:18px;font-weight:700;letter-spacing:.02em}
.topbar-actions{display:flex;gap:10px;align-items:center}
.btn{background:#fff;border:1px solid #e8e1d0;color:#1a1d23;padding:8px 14px;border-radius:8px;font-size:13px;cursor:pointer;font-weight:500;transition:all .12s}
.btn:hover{background:#f5efd9;border-color:#e8b84b}
.btn-primary{background:#1a1d23;color:#e8b84b;border-color:#1a1d23}
.btn-primary:hover{background:#2a2d33;color:#e8b84b}
.btn-danger{color:#d63031;border-color:#fab1a0}
.btn-danger:hover{background:#ffe7e4;border-color:#d63031}
a.btn{text-decoration:none;display:inline-flex;align-items:center;gap:6px}
.wrap{max-width:1400px;margin:0 auto;padding:24px}
.header-info{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.header-title{font-size:22px;font-weight:700;color:#1a1d23}
.header-date{font-size:14px;color:#7a8099}
.tabs{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #e8e1d0}
.tab{background:#fff;border:1px solid #e8e1d0;color:#1a1d23;padding:8px 16px;border-radius:20px;font-size:13px;cursor:pointer;font-weight:500;transition:all .12s}
.tab:hover{background:#f5efd9}
.tab.active{background:#1a1d23;color:#e8b84b;border-color:#1a1d23}
.content-body{min-height:400px}
.content-empty{color:#b2bec3;font-style:italic;display:block;padding:60px 20px;text-align:center}
.cp-card{background:#fff;border:1px solid #f0e9d8;border-radius:10px;padding:14px 16px;margin-bottom:10px}
.cp-card-sub{font-size:11px;color:#7a8099;letter-spacing:.06em;margin-bottom:6px;font-weight:600;text-transform:uppercase}
.cp-card-title{font-size:15px;font-weight:700;color:#1a1d23;margin-bottom:8px;display:flex;align-items:center;gap:6px}
.cp-card-body{font-size:13px;color:#2d3436;line-height:1.7;white-space:pre-wrap}
.cp-card-body a{color:#0984e3;text-decoration:none}
.cp-card-body a:hover{text-decoration:underline}
.cp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
#cp-editor{width:100%;min-height:520px;font-family:monospace;font-size:14px;padding:16px;border:1.5px solid #e8b84b;border-radius:10px;background:#fdfbf5;line-height:1.7;outline:none;white-space:pre-wrap}
.toolbar{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;padding:10px 12px;background:#fffdf6;border:1px solid #e8e1d0;border-radius:8px;align-items:center}
.toolbar-label{font-size:10px;color:#888;letter-spacing:.04em;margin-right:4px}
.toolbar button{width:28px;height:28px;border:1px solid #e8e1d0;background:#fff;border-radius:5px;cursor:pointer;font-weight:700}
.toolbar .sep{width:1px;height:18px;background:#e8e1d0;margin:0 4px}
.link-legend{margin-bottom:10px;padding:10px 12px;background:#fff3a0;border-radius:8px;font-size:11px;line-height:1.7}
.notice{padding:10px 14px;background:#fff3a0;border-radius:8px;font-size:12px;margin-bottom:12px}
@media print{
  @page{size:A4 landscape;margin:10mm 12mm}
  body{background:#fff}
  .topbar,.tabs,.btn,.toolbar{display:none !important}
  .wrap{max-width:none;padding:0}
  .cp-grid{grid-template-columns:repeat(auto-fit,minmax(160px,1fr)) !important;gap:5mm !important}
  .cp-card{page-break-inside:avoid;break-inside:avoid;padding:8px 10px !important}
  *{-webkit-print-color-adjust:exact !important;print-color-adjust:exact !important}
}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-title">☑ 체크포인트</div>
  <div class="topbar-actions">
    <a href="/" class="btn">← 대시보드</a>
    <button class="btn" onclick="loadCp()" title="서버에서 최신 본문 받아오기">↻ 새로고침</button>
    <button class="btn btn-primary" onclick="enterEdit()" id="edit-btn">✏️ 편집</button>
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

  <div id="cp-body" class="content-body">
    <span class="content-empty">불러오는 중...</span>
  </div>
</div>

<script>
// fetch wrapper — API 인증 헤더 자동 삽입
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

let _cpRaw = '';
let _cpDate = '';
let _cpLinkMap = [];
let _currentTab = 'all';
let _editing = false;

const CP_SECTIONS = {
  indicator: ['📊지표','📊 지표'],
  us_market: ['🇺🇸美증시 마감','🇺🇸 美증시 마감','🇺🇸美증시','🇺🇸 美증시'],
  signal: ['📡시장 시그널','📡 시장 시그널'],
  sector: ['📌Sector','📌 Sector','📌sector','📌섹터','📌 섹터'],
  kospi: ['📌코스피','📌 코스피'],
  kosdaq: ['📌코스닥','📌 코스닥'],
};

function esc(s){
  return String(s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// 사용자 강조 태그는 보존
function escPreserve(text){
  text = String(text || '');
  const placeholders = [];
  const pattern = /<(\/?(?:b|i|u|strong|em)\b|font\s+color\s*=\s*"[^"]*"|\/font|span\s+style\s*=\s*"(?:color|background-color|background)\s*:[^"]*"|\/span)>/gi;
  text = text.replace(pattern, function(m){
    placeholders.push(m);
    return '\x00FMT' + (placeholders.length - 1) + '\x00';
  });
  text = text.replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  text = text.replace(/\x00FMT(\d+)\x00/g, function(_, i){ return placeholders[parseInt(i)]; });
  return text;
}

function linkify(text){
  let s = escPreserve(text);
  // [[LINK:url]] 마커를 🔗 링크로
  let idx = 0;
  s = s.replace(/\[\[LINK:([^\]]+)\]\]/g, function(_, url){
    idx++;
    return ' <a href="'+url.replace(/&/g,'&amp;')+'" target="_blank" title="'+esc(url)+'">🔗</a>';
  });
  return s;
}

function parseSection(text, headers){
  if(!text) return null;
  const lines = text.split('\n');
  let capturing = false, result = [];
  let headerAdded = false;
  for(let i=0;i<lines.length;i++){
    const l = lines[i];
    const isHeader = headers.some(h=>l.includes(h));
    const isOtherHeader = !isHeader && /^(📌|📊|🇺🇸|📡)/.test(l);
    if(isHeader){
      if(!headerAdded){ result.push(l); headerAdded = true; }
      capturing = true;
      continue;
    }
    if(isOtherHeader && capturing){
      capturing = false;
    }
    if(capturing && l.trim()){
      result.push(l);
    }
  }
  return result.length > 0 ? result.join('\n') : null;
}

// 섹션 텍스트 → 카드 배열 (각 ✔️ 또는 종목명 = 한 카드)
function parseCards(sectionText, kind){
  if(!sectionText) return [];
  const lines = sectionText.split('\n');
  const cards = [];
  let current = null;
  const markers = kind === 'sector' ? /^✔️/ : (kind === 'signal' ? /^☑️/ : null);
  let started = false;

  for(const l of lines){
    if(/^(📌|📊|🇺🇸|📡)/.test(l)){ started = true; continue; } // 헤더는 무시
    if(!started){ started = true; continue; }
    if(markers && markers.test(l)){
      // 새 카드 시작
      if(current) cards.push(current);
      current = {title: l, body: []};
    } else if(kind === 'stock'){
      // 코스피/코스닥 — 종목명이 카드 제목, - 로 시작 = 본문
      if(l.trim() && !l.trim().startsWith('-') && !l.trim().startsWith('•')){
        if(current) cards.push(current);
        current = {title: l.trim(), body: []};
      } else if(current){
        current.body.push(l);
      }
    } else if(current){
      current.body.push(l);
    } else {
      // 카드 없이 시작하는 텍스트 (지표 등)
      current = {title: '', body: [l]};
    }
  }
  if(current) cards.push(current);
  return cards;
}

function renderCards(cards, kind){
  if(!cards.length) return '';
  const isGrid = (kind === 'sector' || kind === 'stock' || kind === 'signal');
  const wrapClass = isGrid ? 'cp-grid' : '';
  let html = '<div class="'+wrapClass+'">';
  for(const c of cards){
    html += '<div class="cp-card">';
    if(c.title){
      const sub = kind === 'sector' ? '섹터' : (kind === 'signal' ? '시그널' : (kind === 'stock' ? '종목' : ''));
      if(sub) html += '<div class="cp-card-sub">'+sub+'</div>';
      html += '<div class="cp-card-title">'+linkify(c.title)+'</div>';
    }
    html += '<div class="cp-card-body">'+linkify(c.body.join('\n'))+'</div>';
    html += '</div>';
  }
  html += '</div>';
  return html;
}

function renderPlain(text){
  return '<div class="cp-card"><div class="cp-card-body">'+linkify(text)+'</div></div>';
}

function switchTab(btn, key){
  document.querySelectorAll('#cp-tabs .tab').forEach(t=>t.classList.remove('active'));
  btn.classList.add('active');
  _currentTab = key;
  render();
}

function render(){
  const body = document.getElementById('cp-body');
  if(!_cpRaw){
    body.innerHTML = '<span class="content-empty">체크포인트가 비어있음. 봇으로 보내면 여기 표시됨.</span>';
    return;
  }
  if(_editing) return; // 편집 모드 렌더 스킵

  if(_currentTab === 'all'){
    let html = '';
    const order = [
      {key:'indicator', label:'📊 지표'},
      {key:'us_market', label:'🇺🇸 美증시'},
      {key:'signal', label:'📡 시장 시그널'},
      {key:'sector', label:'📌 Sector'},
      {key:'kospi', label:'📌 코스피'},
      {key:'kosdaq', label:'📌 코스닥'},
    ];
    for(const o of order){
      const sec = parseSection(_cpRaw, CP_SECTIONS[o.key]);
      if(!sec) continue;
      html += '<div style="font-size:12px;color:#7a8099;font-weight:700;letter-spacing:.08em;margin:'+(html?'22px':'0')+' 0 8px;">'+o.label+'</div>';
      if(o.key === 'sector'){
        html += renderCards(parseCards(sec, 'sector'), 'sector');
      } else if(o.key === 'signal'){
        html += renderCards(parseCards(sec, 'signal'), 'signal');
      } else if(o.key === 'kospi' || o.key === 'kosdaq'){
        html += renderCards(parseCards(sec, 'stock'), 'stock');
      } else {
        // 지표·미증시는 텍스트만 (미증시는 ☑️ 있으면 카드로)
        if(o.key === 'us_market' && sec.includes('☑️')){
          html += renderCards(parseCards(sec, 'signal'), 'signal');
        } else {
          const bodyText = sec.split('\n').slice(1).join('\n').trim();
          if(bodyText) html += renderPlain(bodyText);
        }
      }
    }
    body.innerHTML = html || '<span class="content-empty">파싱된 섹션이 없음. 편집 눌러서 원문 확인.</span>';
  } else {
    const sec = parseSection(_cpRaw, CP_SECTIONS[_currentTab]);
    if(!sec){ body.innerHTML = '<span class="content-empty">이 섹션은 비어있음.</span>'; return; }
    if(_currentTab === 'sector'){
      body.innerHTML = renderCards(parseCards(sec, 'sector'), 'sector');
    } else if(_currentTab === 'signal'){
      body.innerHTML = renderCards(parseCards(sec, 'signal'), 'signal');
    } else if(_currentTab === 'kospi' || _currentTab === 'kosdaq'){
      body.innerHTML = renderCards(parseCards(sec, 'stock'), 'stock');
    } else if(_currentTab === 'us_market' && sec.includes('☑️')){
      body.innerHTML = renderCards(parseCards(sec, 'signal'), 'signal');
    } else {
      const bodyText = sec.split('\n').slice(1).join('\n').trim();
      body.innerHTML = bodyText ? renderPlain(bodyText) : '<span class="content-empty">비어있음</span>';
    }
  }
}

async function loadCp(){
  try {
    const res = await fetch('/api/post/checkpoint');
    if(!res.ok){
      document.getElementById('cp-body').innerHTML = '<span class="content-empty">불러오기 실패 HTTP '+res.status+'</span>';
      return;
    }
    const data = await res.json();
    _cpRaw = data.content || '';
    _cpDate = data.date || '';
    document.getElementById('cp-date').textContent = _cpDate;
    // 링크 마커 인덱스 만들기
    _cpLinkMap = [];
    const urls = _cpRaw.match(/\[\[LINK:([^\]]+)\]\]/g) || [];
    for(const u of urls){
      const m = u.match(/\[\[LINK:([^\]]+)\]\]/);
      if(m && !_cpLinkMap.includes(m[1])) _cpLinkMap.push(m[1]);
    }
    render();
  } catch(e) {
    document.getElementById('cp-body').innerHTML = '<span class="content-empty">에러: '+esc(e.message)+'</span>';
  }
}

function cpRawToEdit(raw){
  if(!raw) return '';
  // [[LINK:url]] → [🔗n]
  let idx = 0;
  const urlToIdx = {};
  const edited = raw.replace(/\[\[LINK:([^\]]+)\]\]/g, function(_, url){
    if(!(url in urlToIdx)){
      idx++;
      urlToIdx[url] = idx;
    }
    return ' [🔗'+urlToIdx[url]+']';
  });
  return edited;
}

function cpEditToRaw(text){
  if(!text) return '';
  return text.replace(/\s*\[🔗(\d+)\]/g, function(_, n){
    const i = parseInt(n) - 1;
    if(i >= 0 && i < _cpLinkMap.length) return ' [[LINK:'+_cpLinkMap[i]+']]';
    return '';
  });
}

function enterEdit(){
  _editing = true;
  document.getElementById('edit-btn').style.display = 'none';
  document.getElementById('cp-tabs').style.display = 'none';
  const editText = cpRawToEdit(_cpRaw || '');

  let legend = '';
  if(_cpLinkMap.length > 0){
    legend = '<div class="link-legend"><div style="font-weight:700;margin-bottom:4px;">🔗 링크 토큰 (지우면 링크 사라짐)</div>';
    _cpLinkMap.forEach((url, i) => {
      legend += '<div><b style="background:#1a1d23;color:#e8b84b;padding:1px 6px;border-radius:3px;font-size:10px;">[🔗'+(i+1)+']</b> <a href="'+url+'" target="_blank" style="color:#0984e3;font-size:10px;">'+esc(url.slice(0,80))+'</a></div>';
    });
    legend += '</div>';
  }

  const toolbar = `<div class="toolbar">
    <span class="toolbar-label">텍스트 도구</span>
    <button onmousedown="event.preventDefault()" onclick="fmt('foreColor','#d63031')" style="color:#d63031">A</button>
    <button onmousedown="event.preventDefault()" onclick="fmt('foreColor','#0984e3')" style="color:#0984e3">A</button>
    <button onmousedown="event.preventDefault()" onclick="fmt('foreColor','#1a1d23')">A</button>
    <span class="sep"></span>
    <button onmousedown="event.preventDefault()" onclick="fmt('hiliteColor','#fff59d')" style="background:#fff59d">■</button>
    <button onmousedown="event.preventDefault()" onclick="fmt('hiliteColor','#ffcdd2')" style="background:#ffcdd2">■</button>
    <button onmousedown="event.preventDefault()" onclick="fmt('hiliteColor','#c8e6c9')" style="background:#c8e6c9">■</button>
    <span class="sep"></span>
    <button onmousedown="event.preventDefault()" onclick="fmt('bold')">B</button>
    <button onmousedown="event.preventDefault()" onclick="fmt('italic')" style="font-style:italic">I</button>
    <button onmousedown="event.preventDefault()" onclick="fmt('underline')"><u>U</u></button>
    <button onmousedown="event.preventDefault()" onclick="fmt('removeFormat')" style="width:auto;padding:0 8px;">✖ 원복</button>
  </div>`;

  const safeText = escPreserve(editText).replace(/\n/g, '<br>');
  const editor = '<div id="cp-editor" contenteditable="true">'+safeText+'</div>';
  const btns = '<div style="margin-top:10px;display:flex;gap:8px;"><button class="btn btn-primary" onclick="saveEdit()">💾 저장</button><button class="btn" onclick="cancelEdit()">✕ 취소</button></div>';

  document.getElementById('cp-body').innerHTML = legend + toolbar + editor + btns;
  document.getElementById('cp-editor').focus();
}

function fmt(cmd, value){
  document.execCommand(cmd, false, value || null);
}

function cancelEdit(){
  _editing = false;
  document.getElementById('edit-btn').style.display = '';
  document.getElementById('cp-tabs').style.display = '';
  render();
}

async function saveEdit(){
  const ed = document.getElementById('cp-editor');
  if(!ed) return;
  let html = ed.innerHTML;
  html = html.replace(/<div><br><\/div>/gi, '\n');
  html = html.replace(/<div>/gi, '\n');
  html = html.replace(/<\/div>/gi, '');
  html = html.replace(/<br\s*\/?>/gi, '\n');
  html = html.replace(/&nbsp;/gi, ' ');
  const raw = cpEditToRaw(html);
  try {
    const res = await fetch('/api/post/checkpoint/replace', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: raw, date: new Date().toISOString().slice(0,10)})
    });
    if(!res.ok){ alert('저장 실패 HTTP '+res.status); return; }
    _cpRaw = raw;
    _editing = false;
    document.getElementById('edit-btn').style.display = '';
    document.getElementById('cp-tabs').style.display = '';
    await loadCp();
  } catch(e){ alert('저장 오류: '+e.message); }
}

// 단축키
document.addEventListener('keydown', (e) => {
  if(!_editing) return;
  const isCmd = e.metaKey || e.ctrlKey;
  if(!isCmd || !e.shiftKey) return;
  const map = {
    '1': ['foreColor', '#d63031'], '2': ['foreColor', '#0984e3'], '3': ['foreColor', '#1a1d23'],
    '4': ['hiliteColor', '#fff59d'], '5': ['hiliteColor', '#ffcdd2'], '6': ['hiliteColor', '#c8e6c9'],
    '0': ['removeFormat', null],
  };
  const hit = map[e.key];
  if(hit){ e.preventDefault(); fmt(hit[0], hit[1]); }
});

async function clearAll(){
  if(!confirm('체크포인트를 전부 비울까요?\n되돌릴 수 없음 (봇도 다음 메시지부터 새로 시작).')) return;
  try {
    await fetch('/api/post/checkpoint/replace', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: '', date: new Date().toISOString().slice(0,10)})
    });
    location.reload();
  } catch(e){ alert('오류: '+e.message); }
}

// 시작 시 로드
loadCp();
</script>
</body>
</html>
"""

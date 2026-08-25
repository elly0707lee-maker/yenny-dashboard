"""
관심종목 시황 뷰 (/watchlist)
- 섹터 → 그룹 → 종목 3단 구조
- KIS API 실시간 시세
- 편집 모드 (섹터/그룹/종목 관리)
- 자동 저장
"""
import threading

# ── 전역 Session 풀 (프로세스 살아있는 동안 재사용) ───────
# 매 요청마다 Session을 새로 만들면 TLS 핸드셰이크가 반복됨.
# 모듈 레벨에 하나 두고 계속 재사용 → 커넥션이 살아있어서 훨씬 빠름.
_session_lock = threading.Lock()
_shared_session = {"s": None, "token": ""}


def _get_session(token: str, app_key: str, app_secret: str):
    import requests as _rq
    with _session_lock:
        s = _shared_session["s"]
        if s is None:
            s = _rq.Session()
            adapter = _rq.adapters.HTTPAdapter(
                pool_connections=64, pool_maxsize=64, max_retries=0
            )
            s.mount("https://", adapter)
            _shared_session["s"] = s
        # 토큰이 바뀌었을 때만 헤더 갱신
        if _shared_session["token"] != token:
            s.headers.update({
                "authorization": f"Bearer {token}",
                "appkey": app_key,
                "appsecret": app_secret,
                "tr_id": "FHKST01010100",
                "Content-Type": "application/json",
                "Connection": "keep-alive",
            })
            _shared_session["token"] = token
        return s


def get_watchlist_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>관심종목 시황 · Yenny Dashboard</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2280%22>📊</text></svg>">
<link rel="stylesheet" href="https://webfontworld.github.io/gmarket/GmarketSans.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.0/Sortable.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:'GmarketSans','GmarketSansMedium',-apple-system,'Segoe UI','Noto Sans KR',sans-serif;
  background:#f8f9fa;color:#1a1d23;min-height:100vh;
  font-weight:500;letter-spacing:-0.01em;
}
.topbar{background:#1a1d23;color:#fff;padding:14px 24px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}
.topbar-title{font-size:18px;font-weight:700}
.topbar-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.btn{background:#fff;border:1px solid #e5e7eb;color:#1a1d23;padding:8px 14px;border-radius:8px;font-size:13px;cursor:pointer;font-weight:500;font-family:inherit;transition:all .12s}
.btn:hover{background:#f1f3f5;border-color:#1a1d23}
.btn-primary{background:#1a1d23;color:#fff;border-color:#1a1d23}
.btn-primary:hover{background:#2a2d33}
.btn-danger{color:#d63031;border-color:#fab1a0}
.btn-danger:hover{background:#ffe7e4}
.btn-mini{padding:4px 8px;font-size:11px}
a.btn{text-decoration:none;display:inline-flex;align-items:center;gap:4px}

.wrap{max-width:1600px;margin:0 auto;padding:16px 24px}
.updated{font-size:11px;color:#7a8099;margin-bottom:10px}

/* 🆕 그룹 다단 배치 */
#watchlist-body.cols-2,
#watchlist-body.cols-3{
  display:grid;gap:14px;align-items:start;
}
#watchlist-body.cols-2{grid-template-columns:repeat(2, minmax(0,1fr))}
#watchlist-body.cols-3{grid-template-columns:repeat(3, minmax(0,1fr))}
#watchlist-body.cols-2 .group,
#watchlist-body.cols-3 .group{
  margin-bottom:0;background:#fff;border:1px solid #e5e7eb;
  border-radius:10px;padding:12px 14px;
}
#watchlist-body.cols-2 .group-header,
#watchlist-body.cols-3 .group-header{
  border-bottom:1.5px solid #1a1d23;padding-bottom:6px;margin-bottom:4px;
}
/* 다단일 때 테이블 압축 */
#watchlist-body.cols-2 .stock-table th,
#watchlist-body.cols-3 .stock-table th{font-size:10px;padding:5px 6px}
#watchlist-body.cols-2 .stock-row td,
#watchlist-body.cols-3 .stock-row td{padding:6px;font-size:12px}
#watchlist-body.cols-3 .stock-name{font-size:12px}
#watchlist-body.cols-3 .stock-code{display:none}
#watchlist-body.cols-3 .mkt-badge{display:none}
/* 다단에선 add-stock 세로 배치 */
#watchlist-body.cols-2 .add-stock,
#watchlist-body.cols-3 .add-stock{flex-wrap:wrap;gap:4px}
#watchlist-body.cols-2 .add-stock input,
#watchlist-body.cols-3 .add-stock input{min-width:0;font-size:11px}

@media (max-width:1100px){
  #watchlist-body.cols-3{grid-template-columns:repeat(2, minmax(0,1fr))}
}
@media (max-width:760px){
  #watchlist-body.cols-2,
  #watchlist-body.cols-3{grid-template-columns:1fr}
}

/* 🆕 랭킹 뷰 폭 제한 */
.rank-wrap{max-width:920px}

/* 🆕 컨트롤 바 */
.controlbar{
  background:#fff;border-bottom:1px solid #e5e7eb;
  padding:8px 24px;display:flex;gap:14px;align-items:center;flex-wrap:wrap;
  position:sticky;top:57px;z-index:90;
}
.ctrl-group{display:flex;gap:3px;align-items:center}
.ctrl-label{font-size:10.5px;color:#7a8099;font-weight:600;margin-right:3px}
.seg{
  padding:4px 9px;border:1px solid #e5e7eb;border-radius:6px;
  background:#fff;color:#1a1d23;font-size:11px;font-weight:500;
  cursor:pointer;font-family:inherit;transition:all .12s;white-space:nowrap;
}
.seg:hover{background:#f1f3f5;border-color:#1a1d23}
.seg.active{background:#1a1d23;color:#fff;border-color:#1a1d23}
.chk{font-size:11.5px;color:#1a1d23;display:flex;align-items:center;gap:5px;cursor:pointer}
.chk input{cursor:pointer}
.market-hint{font-size:11px;color:#7a8099;font-style:italic}

/* 📈 종목 상세 */
.stock-name.clickable{cursor:pointer;border-bottom:1px dashed transparent}
.stock-name.clickable:hover{color:#0984e3;border-bottom-color:#0984e3}
.stock-quote{
  display:flex;gap:18px;flex-wrap:wrap;
  background:#f8f9fa;border-radius:8px;padding:12px 14px;margin-bottom:14px;
}
.sq-item{font-size:14px;font-weight:700;font-variant-numeric:tabular-nums}
.sq-item b{
  display:block;font-size:10px;color:#7a8099;font-weight:600;
  margin-bottom:2px;letter-spacing:.02em;
}
.stock-section{
  font-size:11.5px;color:#7a8099;font-weight:700;
  margin:14px 0 7px;padding-bottom:5px;border-bottom:1px solid #e5e7eb;
}
.stock-section:first-child{margin-top:0}
.stock-places{display:flex;flex-direction:column;gap:5px}
.stock-place{
  display:flex;align-items:center;gap:10px;
  background:#fff;border:1px solid #e5e7eb;border-radius:8px;
  padding:9px 13px;cursor:pointer;transition:all .12s;
}
.stock-place:hover{border-color:#1a1d23;background:#f8f9fa}
.sp-group{font-size:13px;font-weight:700}
.sp-sector{font-size:11.5px;color:#7a8099}
.sp-count{margin-left:auto;font-size:10.5px;color:#a8b0bd}
.db-entry{
  background:#fafbfc;border:1px solid #eceff1;border-radius:8px;
  padding:10px 13px;margin-bottom:6px;
}
.db-theme{
  display:inline-block;font-size:11px;font-weight:700;
  background:#e8f4fd;color:#0277bd;padding:2px 9px;border-radius:10px;
  margin-bottom:6px;
}
.db-desc{font-size:12.5px;line-height:1.6;color:#2d3436}
.stock-empty{font-size:12px;color:#a8b0bd;font-style:italic;padding:10px 2px}

/* 🔒 보기 전용 모드 — 편집 관련 UI 전부 숨김 */
body.readonly #edit-btn,
body.readonly #bulk-btn,
body.readonly #share-btn,
body.readonly .row-actions,
body.readonly .add-stock,
body.readonly .add-group-btn,
body.readonly .sector-add,
body.readonly .group-actions,
body.readonly .tab-icon-btn,
body.readonly .drag-dots,
body.readonly .group-drag,
body.readonly .topbar-actions a[href="/"]{display:none !important}
body.readonly .share-badge{display:inline-flex}
.share-badge{
  display:none;align-items:center;gap:5px;
  background:rgba(255,255,255,0.14);color:#fff;
  padding:5px 12px;border-radius:16px;font-size:11.5px;font-weight:600;
}

/* 📦 큰 그룹 접기 */
.big-collapsed{
  padding:14px;text-align:center;cursor:pointer;
  background:#f8f9fa;border:1px dashed #c5ccd6;border-radius:8px;
  font-size:12px;color:#636e72;font-weight:600;margin:6px 0;
  transition:all .12s;
}
.big-collapsed:hover{background:#eceff1;border-color:#1a1d23;color:#1a1d23}

/* 🔎 내 종목 찾기 */
.find-box{
  padding:5px 10px;border:1px solid #e5e7eb;border-radius:16px;
  font-size:11.5px;font-family:inherit;outline:none;width:170px;
  transition:all .12s;background:#f8f9fa;
}
.find-box:focus{border-color:#1a1d23;width:230px;background:#fff}
.find-section{
  font-size:10.5px;color:#7a8099;font-weight:700;
  padding:6px 10px 3px;border-top:1px solid #f1f3f5;margin-top:2px;
}
.find-section:first-child{border-top:none;margin-top:0}
.find-result{
  display:none;position:sticky;top:96px;z-index:88;
  background:#fff;border-bottom:1px solid #e5e7eb;
  padding:8px 24px;box-shadow:0 4px 12px rgba(0,0,0,0.06);
}
.find-result.open{display:block}
.find-item{
  display:flex;align-items:center;gap:10px;padding:7px 10px;
  border-radius:8px;cursor:pointer;font-size:12.5px;transition:background .1s;
}
.find-item:hover{background:#f1f3f5}
.find-name{font-weight:700;flex:0 0 auto}
.find-code{font-size:10.5px;color:#a8b0bd;flex:0 0 auto}
.find-path{color:#636e72;font-size:11.5px;flex:1;min-width:0;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.find-path b{color:#1a1d23;font-weight:600}
.find-pct{font-weight:700;font-variant-numeric:tabular-nums;flex:0 0 auto}
.find-none{font-size:12px;color:#a8b0bd;font-style:italic;padding:8px 10px}

/* 🚨 특이 시그널 */
#signal-box{margin-bottom:14px}
.signal-head{
  font-size:11px;color:#7a8099;font-weight:600;margin-bottom:6px;
  display:flex;align-items:center;gap:6px;
}
.signal-list{display:flex;flex-direction:column;gap:6px}
.signal-card{
  display:flex;align-items:center;gap:10px;
  background:#fff;border:1px solid #e5e7eb;border-left-width:4px;
  border-radius:9px;padding:9px 14px;cursor:pointer;transition:all .12s;
}
.signal-card:hover{box-shadow:0 2px 10px rgba(0,0,0,0.08);transform:translateX(2px)}
.signal-card.surge{border-left-color:#d63031;background:#fff6f5}
.signal-card.plunge{border-left-color:#0984e3;background:#f4f9ff}
.signal-card.solo{border-left-color:#e17055;background:#fff9f4}
.signal-card.split{border-left-color:#6c5ce7;background:#f8f7ff}
.signal-icon{font-size:17px;flex:0 0 auto}
.signal-text{flex:1;font-size:12.5px;line-height:1.45;min-width:0}
.signal-where{font-weight:700;color:#1a1d23}
.signal-detail{color:#636e72}
.signal-val{
  font-size:15px;font-weight:700;flex:0 0 auto;
  font-variant-numeric:tabular-nums;
}
.signal-empty{
  font-size:12px;color:#a8b0bd;font-style:italic;
  padding:10px 14px;background:#f8f9fa;border-radius:9px;
}

/* 📥 일괄 추가 모달 */
.modal-overlay{
  display:none;position:fixed;inset:0;background:rgba(0,0,0,0.45);
  z-index:300;align-items:center;justify-content:center;padding:20px;
}
.modal-overlay.open{display:flex}
.modal{
  background:#fff;border-radius:14px;width:100%;max-width:720px;
  max-height:88vh;display:flex;flex-direction:column;
  box-shadow:0 12px 40px rgba(0,0,0,0.25);
}
.modal-head{
  display:flex;justify-content:space-between;align-items:center;
  padding:16px 20px;border-bottom:1px solid #e5e7eb;
}
.modal-title{font-size:16px;font-weight:700}
.modal-body{padding:16px 20px;overflow-y:auto;flex:1}
.modal-foot{
  display:flex;justify-content:flex-end;gap:8px;
  padding:12px 20px;border-top:1px solid #e5e7eb;
}
.bulk-hint{
  font-size:12px;color:#636e72;line-height:1.6;
  background:#f8f9fa;border-radius:8px;padding:10px 12px;margin-bottom:12px;
}
.bulk-hint b{color:#1a1d23}
#bulk-input{
  width:100%;min-height:130px;resize:vertical;
  border:1px solid #e5e7eb;border-radius:8px;padding:10px 12px;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;
  line-height:1.5;outline:none;
}
#bulk-input:focus{border-color:#1a1d23}
.bulk-target{
  margin:14px 0 10px;display:flex;flex-direction:column;gap:8px;
  background:#f8f9fa;border-radius:8px;padding:12px;
}
.bulk-target-row{display:flex;align-items:center;gap:8px}
.bulk-target-row select{
  flex:1;padding:6px 10px;border:1px solid #e5e7eb;border-radius:6px;
  font-size:12.5px;font-family:inherit;background:#fff;outline:none;
}
.bulk-target-row select:focus{border-color:#1a1d23}
.bulk-preview-head{
  display:flex;justify-content:space-between;align-items:center;
  margin:10px 0 6px;font-size:12px;color:#7a8099;font-weight:600;
}
.bulk-preview{
  max-height:220px;overflow-y:auto;
  border:1px solid #e5e7eb;border-radius:8px;
}
.bulk-preview table{width:100%;border-collapse:collapse}
.bulk-preview th{
  position:sticky;top:0;background:#f8f9fa;font-size:10.5px;color:#7a8099;
  text-align:left;padding:6px 10px;border-bottom:1px solid #e5e7eb;
}
.bulk-preview td{padding:6px 10px;font-size:12px;border-bottom:1px solid #f1f3f5}
.bulk-preview tr.dup{background:#fff8e1;color:#a06d00}
.bulk-preview tr.missing{background:#fff5f5}
.bulk-preview tr.missing td{font-weight:600}
.bulk-mode{display:flex;gap:6px;margin:10px 0 4px}
.bulk-mode .seg{padding:6px 14px;font-size:12px}
.bulk-preview tr.dup td:last-child{font-size:10.5px}
.bulk-preview .empty{padding:24px;text-align:center;color:#b2bec3;font-size:12px;font-style:italic}

/* 🆕 섹터 등락률 랭킹 뷰 */
.rank-list{display:flex;flex-direction:column;gap:6px}
.rank-row{
  background:#fff;border:1px solid #e5e7eb;border-radius:10px;
  padding:12px 16px;cursor:pointer;transition:all .12s;
  display:flex;align-items:center;gap:12px;
}
.rank-row:hover{border-color:#1a1d23;box-shadow:0 2px 8px rgba(0,0,0,0.06)}
.rank-row.open{border-color:#1a1d23}
.rank-caret{
  font-size:11px;color:#a8b0bd;width:12px;
  transition:transform .15s;flex:0 0 auto;
}
.rank-row.open .rank-caret{transform:rotate(90deg);color:#1a1d23}
.rank-idx{
  font-size:11px;font-weight:700;color:#a8b0bd;
  min-width:20px;text-align:right;flex:0 0 auto;
  font-variant-numeric:tabular-nums;
}
.rank-name{font-size:15px;font-weight:700;flex:0 0 auto}
.rank-count{font-size:11px;color:#a8b0bd;flex:0 0 auto}
.rank-bar-wrap{
  flex:1;height:8px;background:#f1f3f5;border-radius:4px;
  position:relative;overflow:hidden;min-width:50px;
}
.rank-bar{position:absolute;top:0;bottom:0;border-radius:4px;transition:width .3s}
.rank-bar.up{background:linear-gradient(90deg,#ff7675,#d63031)}
.rank-bar.down{background:linear-gradient(90deg,#74b9ff,#0984e3)}
.rank-pct{
  font-size:16px;font-weight:700;min-width:82px;text-align:right;
  font-variant-numeric:tabular-nums;flex:0 0 auto;
}
.rank-children{
  margin:2px 0 10px 26px;display:flex;flex-direction:column;gap:5px;
  border-left:2px solid #e5e7eb;padding-left:14px;
}
.rank-sub{
  background:#fafbfc;border:1px solid #eceff1;border-radius:8px;
  padding:9px 14px;cursor:pointer;transition:all .12s;
  display:flex;align-items:center;gap:10px;
}
.rank-sub:hover{background:#f1f3f5;border-color:#c5ccd6}
.rank-sub.open{background:#f1f3f5;border-color:#1a1d23}
.rank-sub .rank-name{font-size:13px;font-weight:600}
.rank-sub .rank-pct{font-size:14px;min-width:70px}
.rank-stocks{margin:2px 0 8px 22px;padding-left:12px;border-left:2px dashed #e5e7eb}
.rank-stocks .stock-table{margin:4px 0}
.rank-stocks .stock-table th{font-size:10px;padding:5px 8px}
.rank-stocks .stock-row td{padding:6px 8px;font-size:12px}
.rank-empty{font-size:12px;color:#a8b0bd;padding:8px 14px;font-style:italic}

/* 🆕 드래그 핸들 */
.drag-dots,.group-drag{
  cursor:grab;font-size:12px;letter-spacing:-2px;
  color:rgba(255,255,255,0.5);user-select:none;margin-right:2px;
}
.group-drag{color:#c5ccd6;margin-right:6px}
.sector-tab:not(.active) .drag-dots{color:#c5ccd6}
.drag-dots:active,.group-drag:active{cursor:grabbing}
.sortable-ghost{opacity:0.4}
.sortable-drag{opacity:0.9}

/* 시장 배지 */
.mkt-badge{
  display:inline-block;padding:1px 5px;border-radius:4px;
  font-size:9.5px;font-weight:700;margin-left:5px;vertical-align:middle;
}
.mkt-badge.krx{background:#e3f2fd;color:#0277bd}
.mkt-badge.nxt{background:#f3e5f5;color:#7b1fa2}
.mkt-badge.un{background:#f1f3f5;color:#616161}

/* 섹터 탭바 */
.sector-tabs{
  display:flex;gap:6px;flex-wrap:wrap;padding-bottom:12px;
  border-bottom:1.5px solid #e5e7eb;margin-bottom:16px;align-items:center;
}
.sector-tab{
  display:flex;align-items:center;gap:6px;
  padding:8px 14px;border:1px solid #e5e7eb;border-radius:20px;
  background:#fff;color:#1a1d23;font-size:13px;font-weight:500;
  cursor:pointer;font-family:inherit;transition:all .12s;
  white-space:nowrap;
}
.sector-tab:hover{background:#f1f3f5;border-color:#1a1d23}
.sector-tab.active{background:#1a1d23;color:#fff;border-color:#1a1d23}
.sector-tab-name{min-width:20px}
.tab-icon-btn{
  background:transparent;border:0;cursor:pointer;padding:1px 3px;
  font-size:11px;line-height:1;opacity:0.75;font-family:inherit;
  border-radius:4px;
}
.tab-icon-btn:hover{opacity:1;background:rgba(255,255,255,0.2)}
.tab-icon-btn.dark{color:#7a8099;margin-left:4px}
.tab-icon-btn.dark:hover{background:#eceff1}
.sector-add{
  width:34px;height:34px;border-radius:20px;border:1px dashed #999;
  background:transparent;color:#666;font-size:16px;font-weight:700;
  cursor:pointer;font-family:inherit;
}
.sector-add:hover{background:#fff;color:#1a1d23;border-color:#1a1d23;border-style:solid}

/* 그룹 */
.group{margin-bottom:24px}
.group-header{
  display:flex;align-items:center;gap:8px;
  padding:8px 0;margin-bottom:6px;border-bottom:1px solid #e5e7eb;
  font-size:14px;font-weight:700;color:#1a1d23;
}
.group-icon{font-size:16px}
.group-name{min-width:20px}
.group-actions{margin-left:auto;display:flex;gap:4px}
.group-actions .btn-mini{background:transparent;border:1px solid transparent;color:#7a8099}
.group-actions .btn-mini:hover{background:#fff;border-color:#e5e7eb;color:#1a1d23}

/* 종목 테이블 */
.stock-table{width:100%;border-collapse:collapse}
.stock-table th{
  text-align:left;padding:8px 10px;font-size:11px;color:#7a8099;
  font-weight:600;border-bottom:1px solid #e5e7eb;
}
.stock-table th.num{text-align:right}
.stock-row{border-bottom:1px solid #f1f3f5;transition:background .1s}
.stock-row:hover{background:#f8f9fa}
.stock-row td{padding:9px 10px;font-size:13px;vertical-align:middle}
.stock-row td.num{text-align:right;font-variant-numeric:tabular-nums}
.stock-name{font-weight:600;color:#1a1d23}
.stock-code{font-size:10px;color:#a8b0bd;margin-left:4px}
.up{color:#d63031}
.down{color:#0984e3}
.flat{color:#7a8099}
.hot{
  display:inline-block;padding:1px 6px;border-radius:8px;
  background:#ffe7e4;color:#d63031;font-size:10px;font-weight:700;
  margin-left:6px;vertical-align:middle;
}
.hot.volume{background:#fff59d;color:#a06d00}
.row-actions{display:none;gap:2px}
.stock-row:hover .row-actions{display:inline-flex}
.stock-row.editing .row-actions{display:inline-flex}

/* 추가 버튼 */
.add-stock{
  display:flex;gap:6px;padding:10px 0;
}
.add-stock input{
  flex:1;padding:6px 10px;border:1px solid #e5e7eb;border-radius:6px;
  font-size:12px;font-family:inherit;outline:none;
}
.add-stock input:focus{border-color:#1a1d23}
.add-stock button{padding:6px 12px;font-size:12px}

/* 🆕 자동완성 */
.ac-wrap{position:relative;flex:1}
.ac-wrap input{width:100%}
.ac-list{
  display:none;position:absolute;top:calc(100% + 2px);left:0;right:0;
  background:#fff;border:1px solid #e5e7eb;border-radius:8px;
  box-shadow:0 4px 16px rgba(0,0,0,0.1);z-index:50;
  max-height:260px;overflow-y:auto;
}
.ac-list.open{display:block}
.ac-item{
  padding:8px 12px;font-size:12.5px;cursor:pointer;
  display:flex;align-items:center;gap:8px;
  border-bottom:1px solid #f1f3f5;
}
.ac-item:last-child{border-bottom:none}
.ac-item:hover,.ac-item.sel{background:#f1f3f5}
.ac-item-name{font-weight:600;color:#1a1d23}
.ac-item-code{font-size:10.5px;color:#a8b0bd}
.ac-item-market{
  margin-left:auto;font-size:10px;padding:1px 6px;border-radius:8px;
  background:#f1f3f5;color:#7a8099;
}
.ac-loading{padding:10px 12px;font-size:12px;color:#a8b0bd;font-style:italic}
.ac-empty{padding:10px 12px;font-size:12px;color:#a8b0bd}

.add-group-btn{
  padding:8px 14px;border:1px dashed #999;border-radius:8px;
  background:transparent;color:#666;font-size:12px;cursor:pointer;
  font-family:inherit;margin-top:8px;
}
.add-group-btn:hover{background:#fff;color:#1a1d23;border-color:#1a1d23}

.content-empty{color:#b2bec3;font-style:italic;padding:40px 20px;text-align:center;display:block}
.loading{color:#7a8099;font-size:12px;padding:6px 10px;font-style:italic}

.save-indicator{
  position:fixed;bottom:24px;right:24px;background:#1a1d23;color:#fff;
  padding:10px 18px;border-radius:24px;font-size:12px;font-weight:500;
  opacity:0;transition:opacity .3s;pointer-events:none;z-index:200;
  box-shadow:0 4px 12px rgba(0,0,0,0.15);
}
.save-indicator.visible{opacity:1}

/* 편집 모드 */
body.edit-mode .row-actions{display:inline-flex !important}
body.edit-mode .add-stock,body.edit-mode .add-group-btn{display:flex}
.add-stock,.add-group-btn{display:none}
body.edit-mode .add-group-btn{display:inline-block}

@media print{
  @page{size:A4 landscape;margin:8mm}
  .topbar,.controlbar,.sector-add,.row-actions,.add-stock,.add-group-btn,.save-indicator{display:none !important}
  body{background:#fff}
  .sector-tab:not(.active){display:none}
  .wrap{max-width:none;padding:0}
  .group{page-break-inside:avoid;break-inside:avoid}
  #watchlist-body.cols-2,#watchlist-body.cols-3{gap:8px}
  *{-webkit-print-color-adjust:exact !important;print-color-adjust:exact !important}
}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-title">📊 관심종목 시황</div>
  <div class="topbar-actions">
    <a href="/" class="btn">← 대시보드</a>
    <span class="share-badge">👀 보기 전용</span>
    <button class="btn" onclick="toggleEdit()" id="edit-btn">⚙️ 편집</button>
    <button class="btn" onclick="openBulk()" id="bulk-btn">📥 일괄 추가</button>
    <button class="btn btn-primary" onclick="refreshStaged({force:true})" id="refresh-btn">🔄 시세 갱신</button>
    <button class="btn" onclick="copyShareLink()" id="share-btn" title="보기 전용 링크 복사">🔗 공유</button>
    <button class="btn" onclick="window.print()">🖨️ 인쇄</button>
  </div>
</div>

<div class="controlbar">
  <!-- 시장 선택 -->
  <div class="ctrl-group">
    <span class="ctrl-label">시장</span>
    <button class="seg" data-mkt="UN" onclick="setMarket('UN')" title="KRX+NXT 통합 (체결 있는 쪽)">통합</button>
    <button class="seg" data-mkt="J" onclick="setMarket('J')" title="한국거래소 정규장">KRX</button>
    <button class="seg" data-mkt="NX" onclick="setMarket('NX')" title="넥스트레이드 (프리·애프터)">NXT</button>
  </div>
  <div class="ctrl-group" id="nxt-session-wrap" style="display:none">
    <span class="ctrl-label">세션</span>
    <button class="seg" data-sess="auto" onclick="setSession('auto')" title="시간대에 맞춰 자동">자동</button>
    <button class="seg" data-sess="pre" onclick="setSession('pre')" title="전일 KRX 마감가 대비">🌅 프리</button>
    <button class="seg" data-sess="after" onclick="setSession('after')" title="당일 KRX 마감가 대비">🌙 애프터</button>
  </div>
  <!-- 정렬 -->
  <div class="ctrl-group">
    <span class="ctrl-label">정렬</span>
    <button class="seg" data-sort="manual" onclick="setSort('manual')">기본</button>
    <button class="seg" data-sort="chg_desc" onclick="setSort('chg_desc')">등락률 ↓</button>
    <button class="seg" data-sort="chg_asc" onclick="setSort('chg_asc')">등락률 ↑</button>
    <button class="seg" data-sort="vol_desc" onclick="setSort('vol_desc')">거래량 ↓</button>
    <button class="seg gap-only" data-sort="gap_desc" onclick="setSort('gap_desc')" style="display:none;">괴리율 ↓</button>
    <button class="seg gap-only" data-sort="gap_asc" onclick="setSort('gap_asc')" style="display:none;">괴리율 ↑</button>
  </div>
  <!-- 보기 -->
  <div class="ctrl-group">
    <span class="ctrl-label">보기</span>
    <button class="seg" data-view="list" onclick="setView('list')">📋 리스트</button>
    <button class="seg" data-view="rank" onclick="setView('rank')">📊 등락률</button>
  </div>
  <div class="ctrl-group" id="rank-scope-wrap" style="display:none">
    <span class="ctrl-label">순위</span>
    <button class="seg" data-scope="sector" onclick="setRankScope('sector')">섹터별</button>
    <button class="seg" data-scope="group" onclick="setRankScope('group')">세부 테마별</button>
  </div>
  <div class="ctrl-group" id="cols-wrap">
    <span class="ctrl-label">단</span>
    <button class="seg" data-cols="1" onclick="setCols(1)">1단</button>
    <button class="seg" data-cols="2" onclick="setCols(2)">2단</button>
    <button class="seg" data-cols="3" onclick="setCols(3)">3단</button>
  </div>
  <div class="ctrl-group" id="flat-wrap">
    <label class="chk"><input type="checkbox" id="flat-view" onchange="toggleFlat()"/> 그룹 무시하고 전체 정렬</label>
  </div>
  <div class="ctrl-group">
    <label class="chk"><input type="checkbox" id="signal-on" checked onchange="renderSignals()"/> 🚨 시그널</label>
  </div>
  <div class="ctrl-group nxt-only-wrap" id="nxtonly-wrap" style="display:none">
    <label class="chk"><input type="checkbox" id="nxt-only" onchange="toggleNxtOnly()"/> 🌙 시간외 거래만</label>
  </div>
  <div class="ctrl-group" style="margin-left:auto">
    <input type="text" id="find-input" class="find-box" placeholder="🔎 종목 · 테마 찾기"
           autocomplete="off" oninput="findMyStock(this.value)"
           oncompositionstart="_composing=true"
           oncompositionend="_composing=false;findMyStock(this.value)"/>
  </div>
  <div class="ctrl-group">
    <span class="market-hint" id="market-hint"></span>
  </div>
</div>

<div id="find-result" class="find-result"></div>

<div class="wrap">
  <div class="updated" id="updated"></div>
  <div id="signal-box"></div>
  <div class="sector-tabs" id="sector-tabs"></div>
  <div id="watchlist-body">
    <div class="loading" style="text-align:center;padding:80px;">불러오는 중...</div>
  </div>
</div>

<div id="save-indicator" class="save-indicator">💾 저장됨</div>

<!-- 📈 종목 상세 모달 -->
<div id="stock-overlay" class="modal-overlay" onclick="if(event.target===this)closeStock()">
  <div class="modal" style="max-width:600px">
    <div class="modal-head">
      <span class="modal-title" id="stock-title">종목</span>
      <button class="btn btn-mini" onclick="closeStock()">✕</button>
    </div>
    <div class="modal-body" id="stock-body"></div>
    <div class="modal-foot">
      <button class="btn" onclick="closeStock()">닫기</button>
    </div>
  </div>
</div>

<!-- ↗ 그룹 이동 모달 -->
<div id="move-overlay" class="modal-overlay" onclick="if(event.target===this)closeMove()">
  <div class="modal" style="max-width:440px">
    <div class="modal-head">
      <span class="modal-title">↗ 그룹을 다른 섹터로 이동</span>
      <button class="btn btn-mini" onclick="closeMove()">✕</button>
    </div>
    <div class="modal-body">
      <div class="bulk-hint" id="move-desc"></div>
      <div class="bulk-target">
        <div class="bulk-target-row">
          <span class="ctrl-label">이동할 섹터</span>
          <select id="move-target"></select>
        </div>
      </div>
    </div>
    <div class="modal-foot">
      <button class="btn" onclick="closeMove()">취소</button>
      <button class="btn btn-primary" onclick="applyMove()">이동하기</button>
    </div>
  </div>
</div>

<!-- 📥 일괄 추가 모달 -->
<div id="bulk-overlay" class="modal-overlay" onclick="if(event.target===this)closeBulk()">
  <div class="modal">
    <div class="modal-head">
      <span class="modal-title">📥 엑셀에서 일괄 추가</span>
      <button class="btn btn-mini" onclick="closeBulk()">✕</button>
    </div>
    <div class="modal-body">
      <div class="bulk-hint" id="bulk-hint-text">
        엑셀에서 <b>종목명·종목코드가 포함된 범위를 그대로 복사</b>해서 아래에 붙여넣으세요.
        열 순서·개수는 상관없고, 6자리 숫자를 종목코드로 자동 인식합니다.
      </div>
      <textarea id="bulk-input" placeholder="대명에너지&#9;태양광/풍력&#9;...&#9;389260&#10;태경비케이&#9;탄소포집&#9;...&#9;014580"
        oninput="parseBulk()" onpaste="setTimeout(parseBulk, 30)"></textarea>

      <div class="bulk-mode">
        <button class="seg active" data-bmode="add" onclick="setBulkMode('add')">➕ 추가하기</button>
        <button class="seg" data-bmode="check" onclick="setBulkMode('check')">🔍 빠진 것만 확인</button>
      </div>
      <div class="bulk-target" id="bulk-target-wrap">
        <div class="bulk-target-row">
          <span class="ctrl-label">섹터</span>
          <select id="bulk-sector" onchange="onBulkSectorChange()"></select>
          <button class="btn btn-mini" onclick="bulkNewSector()">+ 새 섹터</button>
        </div>
        <div class="bulk-target-row">
          <span class="ctrl-label">그룹</span>
          <select id="bulk-group" onchange="updateBulkButton();parseBulk()"></select>
          <button class="btn btn-mini" onclick="bulkNewGroup()">+ 새 그룹</button>
        </div>
      </div>

      <div class="bulk-preview-head">
        <span id="bulk-count">인식된 종목 0개</span>
        <label class="chk"><input type="checkbox" id="bulk-skip-dup" checked/> 중복 종목 건너뛰기</label>
      </div>
      <div id="bulk-preview" class="bulk-preview"></div>
    </div>
    <div class="modal-foot">
      <button class="btn" onclick="closeBulk()">취소</button>
      <button class="btn btn-primary" onclick="applyBulk()" id="bulk-apply">추가하기</button>
    </div>
  </div>
</div>

<script>
(function(){
  const orig = window.fetch;
  const RO = !!window._READONLY;
  const TK = window._SHARE_TOKEN || '';
  window.fetch = function(url, opts){
    opts = opts || {};
    opts.headers = opts.headers || {};
    if(typeof url === 'string' && url.startsWith('/api')){
      // 공유(보기 전용) 모드 — 토큰 기반 읽기 전용 엔드포인트로 우회
      if(RO && TK){
        if(url.startsWith('/api/post/watchlist')){
          url = '/api/share/' + TK + '/watchlist';
        } else if(url.startsWith('/api/watchlist/quotes')){
          url = '/api/share/' + TK + '/quotes';
        } else if(url.startsWith('/api/watchlist/stock-info')){
          url = url.replace('/api/watchlist/stock-info', '/api/share/' + TK + '/stock-info');
        } else {
          // 그 외 API는 차단
          return Promise.resolve(new Response(
            JSON.stringify({error: 'readonly'}), {status: 403}));
        }
      } else {
        opts.headers['X-API-Secret'] = window._API_SECRET || '';
        opts.credentials = 'include';
      }
    }
    return orig(url, opts);
  };
})();

const _RO = !!window._READONLY;   // 보기 전용 모드

let _data = {sectors: [], currentSectorId: null};
let _quotes = {};
let _saveTimer = null;
let _editing = false;
let _autoRefreshTimer = null;
let _market = 'UN';           // 🆕 UN(통합) | J(KRX) | NX(NXT)
let _sort = 'manual';         // 🆕 manual | chg_desc | chg_asc | vol_desc
let _flatView = false;
let _view = 'list';            // 🆕 list | rank
let _openSectors = {};         // 🆕 랭킹 뷰에서 펼친 섹터
let _openGroups = {};          // 🆕 펼친 그룹
let _cols = 2;                 // 🆕 그룹 다단 (1/2/3)

function setCols(n){
  _cols = n;
  document.querySelectorAll('.seg[data-cols]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-cols') === String(n));
  });
  applyCols();
  try { localStorage.setItem('wl_cols', String(n)); } catch(e){}
}

function applyCols(){
  const body = document.getElementById('watchlist-body');
  if(!body) return;
  body.classList.remove('cols-2', 'cols-3');
  // 랭킹 뷰나 flat 뷰는 다단 미적용
  if(_view === 'rank' || _flatView) return;
  if(_cols === 2) body.classList.add('cols-2');
  if(_cols === 3) body.classList.add('cols-3');
}

function genId(){ return 'x' + Math.random().toString(36).slice(2, 10); }
function esc(s){ return String(s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function num(n){ return n === undefined || n === null ? '—' : Number(n).toLocaleString('ko-KR'); }

// 🆕 시장 라벨 / 힌트
const MKT_LABEL = {'UN':'통합', 'J':'KRX', 'NX':'NXT'};
const MKT_CLASS = {'UN':'un', 'J':'krx', 'NX':'nxt'};

function updateMarketHint(){
  if(_editing) return;   // 편집 중엔 안내 문구 유지
  const now = new Date();
  const h = now.getHours(), m = now.getMinutes();
  const t = h * 60 + m;
  let phase = '';
  if(t >= 8*60 && t < 9*60)          phase = '프리마켓 (NXT 유효)';
  else if(t >= 9*60 && t < 15*60+30) phase = '정규장 (KRX 유효)';
  else if(t >= 15*60+30 && t < 16*60) phase = '장 마감 정리';
  else if(t >= 16*60 && t < 20*60)   phase = '애프터마켓 (NXT 유효)';
  else                                phase = '장외 시간 (마지막 종가)';
  const el = document.getElementById('market-hint');
  if(!el) return;
  let extra = '';
  if(_market === 'NX'){
    const es = effectiveSession();
    const label = (es === 'pre') ? '🌅 프리마켓 (전일 마감가 대비)'
                                 : '🌙 애프터마켓 (당일 마감가 대비)';
    extra = ' · ' + label + (_session === 'auto' ? ' 자동' : ' 수동');
  }
  el.textContent = '🕐 ' + phase + ' · ' + MKT_LABEL[_market] + extra;
}

function updateGapButtons(){
  const show = gapMode();
  document.querySelectorAll('.gap-only').forEach(b => {
    b.style.display = show ? '' : 'none';
  });
  if(!show && (_sort === 'gap_desc' || _sort === 'gap_asc')) setSort('chg_desc');
}

function setMarket(mkt){
  if(_market === mkt) return;
  _market = mkt;
  try { localStorage.setItem('wl_market', mkt); } catch(e){}
  document.querySelectorAll('.seg[data-mkt]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-mkt') === mkt);
  });
  updateMarketHint();
  _quotes = {};
  renderBody();
  renderSignals();
  updateNxtOnlyVisible();
  updateNxtSessionVisible();
  refreshStaged({force:true});
}

function setSort(s){
  _sort = s;
  try { localStorage.setItem('wl_sort', s); } catch(e){}
  document.querySelectorAll('.seg[data-sort]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-sort') === s);
  });
  renderBody();
}

function toggleFlat(){
  _flatView = document.getElementById('flat-view').checked;
  renderBody();
  applyCols();
}

// ── 🆕 뷰 전환 ────────────────────────────
function setView(v){
  _view = v;
  try { localStorage.setItem('wl_view', v); } catch(e){}
  document.querySelectorAll('.seg[data-view]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-view') === v);
  });
  const tabs = document.getElementById('sector-tabs');
  const flatWrap = document.getElementById('flat-wrap');
  const colsWrap = document.getElementById('cols-wrap');
  const scopeWrap = document.getElementById('rank-scope-wrap');
  if(tabs) tabs.style.display = (v === 'rank') ? 'none' : '';
  if(flatWrap) flatWrap.style.display = (v === 'rank') ? 'none' : '';
  if(colsWrap) colsWrap.style.display = (v === 'rank') ? 'none' : '';
  if(scopeWrap) scopeWrap.style.display = (v === 'rank') ? '' : 'none';
  render();
  if(v === 'rank'){
    const all = allCodesEverywhere();
    const missing = all.filter(c => !_quotes[c]);
    if(!missing.length) return;
    // 창고형 대비 — 미조회 종목이 많으면 확인 후 진행
    if(missing.length > 400){
      if(!confirm('아직 시세를 안 받은 종목이 ' + missing.length + '개입니다.\n' +
                  '전부 조회하면 시간이 오래 걸릴 수 있어요. 진행할까요?\n' +
                  '(취소하면 이미 받아둔 섹터만 순위에 표시됩니다)')){
        return;
      }
    }
    refreshQuotes(missing);
  }
}

// NXT 모드이면서 실제 괴리 데이터가 있을 때만 괴리 컬럼 표시
// (정규장 중에는 괴리가 무의미해서 서버가 gap을 안 보냄)
let _session = 'auto';   // auto | pre | after

function setSession(s){
  _session = s;
  try { localStorage.setItem('wl_session', s); } catch(e){}
  document.querySelectorAll('.seg[data-sess]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-sess') === s);
  });
  updateMarketHint();
  _quotes = {};
  renderBody();
  renderSignals();
  refreshStaged({force:true});
}

// 실제 적용될 세션 (auto면 시간으로 판단)
function effectiveSession(){
  if(_session !== 'auto') return _session;
  const n = new Date();
  const t = n.getHours() * 60 + n.getMinutes();
  return (t < 9*60) ? 'pre' : 'after';
}

function updateNxtSessionVisible(){
  const w = document.getElementById('nxt-session-wrap');
  if(w) w.style.display = (_market === 'NX') ? '' : 'none';
}

// 지금이 시간외(프리/애프터) 세션인지 — 정규장 09:00~15:40만 제외
function isOffHourSession(){
  if(_session !== 'auto') return true;   // 수동 지정이면 항상 괴리 모드
  const n = new Date();
  const t = n.getHours() * 60 + n.getMinutes();
  return !(t >= 9*60 && t < 15*60+40);
}

// NXT 모드 + 정규장 아님 → 괴리 모드
function gapMode(){
  return (_market === 'NX') && isOffHourSession();
}

// 괴리 계산 — 기준은 반드시 실제 KRX 마감가(krx_close).
// prev_close(KIS 기준가)는 애프터마켓에서 전일 종가라 기준으로 쓰면 안 됨.
function gapOf(q){
  if(!q) return {gap:null, pct:null, base:0};
  const base = q.krx_close || 0;
  if(q.gap_pct !== undefined && q.gap_pct !== null){
    return {gap: q.gap, pct: q.gap_pct, base: base};
  }
  if(base && q.price){
    const g = q.price - base;
    return {gap: g, pct: Math.round(g / base * 10000) / 100, base: base};
  }
  return {gap:null, pct:null, base:base};
}

// 정렬·평균용 — 괴리 모드면 계산된 괴리율
function pctOf(code){
  const q = _quotes[code];
  if(!q) return undefined;
  if(gapMode()){
    const g = gapOf(q);
    return (g.pct === null) ? undefined : g.pct;
  }
  return q.chg_pct;
}

let _nxtOnly = false;   // 🌙 NXT 체결 있는 종목만 보기

function toggleNxtOnly(){
  _nxtOnly = document.getElementById('nxt-only').checked;
  render();
}

// 화면에 보여줄 종목만 걸러냄
function visibleStocks(stocks){
  if(!_nxtOnly || _market !== 'NX') return stocks || [];
  return (stocks || []).filter(s => {
    const q = _quotes[s.code];
    return q && !q.no_nxt && q.volume > 0;
  });
}

// NXT 모드일 때만 필터 노출
function updateNxtOnlyVisible(){
  const w = document.getElementById('nxtonly-wrap');
  if(w) w.style.display = (_market === 'NX') ? '' : 'none';
  if(_market !== 'NX' && _nxtOnly){
    _nxtOnly = false;
    const cb = document.getElementById('nxt-only');
    if(cb) cb.checked = false;
  }
}

// 지금 기준이 되는 퍼센트 키 (NXT 괴리 모드면 괴리율)
function pctKey(){ return gapMode() ? 'gap_pct' : 'chg_pct'; }

// 종목 배열의 평균 등락(또는 괴리)률
function avgPct(stocks){
  const vals = (stocks || [])
    .map(s => pctOf(s.code))
    .filter(v => v !== undefined && v !== null);
  if(!vals.length) return null;
  return vals.reduce((a,b) => a+b, 0) / vals.length;
}

// 섹터 단위 집계
function sectorStats(sector){
  const all = [];
  for(const g of (sector.groups || [])){
    for(const st of visibleStocks(g.stocks)) all.push(st);
  }
  return {avg: avgPct(all), count: all.length};
}

// ── 🆕 랭킹 뷰 렌더 ────────────────────────
let _rankScope = 'sector';   // sector | group

function setRankScope(sc){
  _rankScope = sc;
  document.querySelectorAll('.seg[data-scope]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-scope') === sc);
  });
  renderRank();
}

// 🆕 세부 테마(그룹) 전체 순위 — 섹터 구분 없이 한 줄로
function renderRankGroupsAll(){
  const body = document.getElementById('watchlist-body');
  const isNxt = gapMode();

  const rows = [];
  for(const s of _data.sectors){
    for(const g of (s.groups || [])){
      const vs = visibleStocks(g.stocks);
      if(!vs.length) continue;
      const avg = avgPct(vs);
      if(avg === null) continue;
      rows.push({
        sectorId: s.id, groupId: g.id,
        sectorName: s.name, groupName: g.name,
        count: vs.length, avg: avg,
      });
    }
  }

  if(!rows.length){
    body.className = '';
    body.innerHTML = '<span class="content-empty">시세를 받은 테마가 없음 · 섹터를 열어 시세를 먼저 받아주세요</span>';
    return;
  }

  rows.sort((a,b) => b.avg - a.avg);
  const maxAbs = Math.max(1, ...rows.map(r => Math.abs(r.avg)));

  let html = '<div class="rank-list">';
  rows.forEach((r, i) => {
    const open = !!_openGroups[r.groupId];
    const cls = r.avg > 0 ? 'up' : (r.avg < 0 ? 'down' : 'flat');
    const width = Math.min(100, Math.abs(r.avg) / maxAbs * 100);
    const pctText = (r.avg > 0 ? '+' : '') + r.avg.toFixed(2) + '%';
    html += '<div class="rank-row ' + (open?'open':'') + '" onclick="toggleGroupOpen(\'' + r.groupId + '\')">' +
      '<span class="rank-idx">' + (i+1) + '</span>' +
      '<span class="rank-caret">▶</span>' +
      '<span class="rank-name">' + esc(r.groupName) + '</span>' +
      '<span class="rank-count">' + esc(r.sectorName) + ' · ' + r.count + '종목</span>' +
      '<span class="rank-bar-wrap"><span class="rank-bar ' + cls + '" style="width:' + width + '%;' +
        (r.avg < 0 ? 'right:0' : 'left:0') + '"></span></span>' +
      '<span class="rank-pct ' + cls + '">' + pctText + '</span>' +
      '</div>';
    if(open){
      const sector = _data.sectors.find(x => x.id === r.sectorId);
      const g = sector && sector.groups.find(x => x.id === r.groupId);
      if(g) html += renderRankStocks(g);
    }
  });
  html += '</div>';

  const basis = isNxt ? 'NXT 괴리율' : '평균 등락률';
  const hint = '<div style="font-size:11px;color:#7a8099;margin-bottom:10px">' +
    '📊 세부 테마 ' + rows.length + '개 · ' + basis + ' 순 · 클릭하면 종목이 펼쳐짐</div>';
  body.className = '';
  body.innerHTML = '<div class="rank-wrap">' + hint + html + '</div>';
}

function renderRank(){
  if(_rankScope === 'group') return renderRankGroupsAll();
  const body = document.getElementById('watchlist-body');
  const isNxt = gapMode();

  const rows = _data.sectors.map(s => {
    const st = sectorStats(s);
    return {sector: s, avg: st.avg, count: st.count};
  }).filter(r => r.count > 0);

  if(!rows.length){
    body.innerHTML = '<span class="content-empty">종목이 등록된 섹터가 없음</span>';
    return;
  }

  // 등락률 큰 순 (값 없는 건 뒤로)
  rows.sort((a,b) => (b.avg ?? -999) - (a.avg ?? -999));

  // 막대 스케일 — 절대값 최대치 기준
  const maxAbs = Math.max(1, ...rows.map(r => Math.abs(r.avg ?? 0)));

  let html = '<div class="rank-list">';
  for(const r of rows){
    const s = r.sector;
    const open = !!_openSectors[s.id];
    const pct = r.avg;
    const cls = pct > 0 ? 'up' : (pct < 0 ? 'down' : 'flat');
    const width = pct === null ? 0 : Math.min(100, Math.abs(pct) / maxAbs * 100);
    const pctText = pct === null ? '—' : (pct > 0 ? '+' : '') + pct.toFixed(2) + '%';

    html += '<div class="rank-row ' + (open?'open':'') + '" onclick="toggleSectorOpen(\'' + s.id + '\')">' +
      '<span class="rank-caret">▶</span>' +
      '<span class="rank-name">' + esc(s.name) + '</span>' +
      '<span class="rank-count">' + r.count + '종목</span>' +
      '<span class="rank-bar-wrap"><span class="rank-bar ' + cls + '" style="width:' + width + '%;' +
        (pct < 0 ? 'right:0' : 'left:0') + '"></span></span>' +
      '<span class="rank-pct ' + cls + '">' + pctText + '</span>' +
      '</div>';

    if(open){
      html += renderRankGroups(s, maxAbs);
    }
  }
  html += '</div>';

  const hint = isNxt
    ? '<div style="font-size:11px;color:#7a8099;margin-bottom:10px">📊 NXT 괴리율 기준 (KRX 종가 대비) · 섹터 클릭 → 그룹 → 종목</div>'
    : '<div style="font-size:11px;color:#7a8099;margin-bottom:10px">📊 평균 등락률 기준 · 섹터 클릭 → 그룹 → 종목</div>';
  body.className = '';
  body.innerHTML = '<div class="rank-wrap">' + hint + html + '</div>';
}

function renderRankGroups(sector, maxAbs){
  const groups = (sector.groups || []).map(g => {
    const vs = visibleStocks(g.stocks);
    return {group: g, avg: avgPct(vs), count: vs.length};
  }).filter(x => x.count > 0);

  if(!groups.length){
    return '<div class="rank-children"><div class="rank-empty">등록된 종목 없음</div></div>';
  }
  groups.sort((a,b) => (b.avg ?? -999) - (a.avg ?? -999));

  let html = '<div class="rank-children">';
  for(const gr of groups){
    const g = gr.group;
    const open = !!_openGroups[g.id];
    const pct = gr.avg;
    const cls = pct > 0 ? 'up' : (pct < 0 ? 'down' : 'flat');
    const width = pct === null ? 0 : Math.min(100, Math.abs(pct) / maxAbs * 100);
    const pctText = pct === null ? '—' : (pct > 0 ? '+' : '') + pct.toFixed(2) + '%';

    html += '<div class="rank-sub ' + (open?'open':'') + '" onclick="event.stopPropagation();toggleGroupOpen(\'' + g.id + '\')">' +
      '<span class="rank-caret">▶</span>' +
      '<span class="rank-name">' + esc(g.name) + '</span>' +
      '<span class="rank-count">' + gr.count + '</span>' +
      '<span class="rank-bar-wrap"><span class="rank-bar ' + cls + '" style="width:' + width + '%;' +
        (pct < 0 ? 'right:0' : 'left:0') + '"></span></span>' +
      '<span class="rank-pct ' + cls + '">' + pctText + '</span>' +
      '</div>';

    if(open){
      html += renderRankStocks(g);
    }
  }
  html += '</div>';
  return html;
}

function renderRankStocks(group){
  const isNxt = gapMode();
  const sorted = sortStocks(visibleStocks(group.stocks)).slice();
  // 랭킹 뷰에선 항상 등락률(괴리율) 큰 순
  sorted.sort((a,b) => (pctOf(b.code) ?? -999) - (pctOf(a.code) ?? -999));

  if(!sorted.length) return '<div class="rank-empty">종목 없음</div>';

  return '<div class="rank-stocks" onclick="event.stopPropagation()">' +
    '<table class="stock-table"><thead><tr>' +
    '<th>종목명</th>' +
    (isNxt ? '<th class="num">KRX 마감가</th>' : '') +
    '<th class="num">' + (isNxt ? 'NXT 현재가' : '현재가') + '</th>' +
    (isNxt ? '<th class="num">괴리</th><th class="num">괴리율</th>' : '<th class="num">등락</th><th class="num">등락률</th>') +
    '<th class="num">거래량</th><th></th>' +
    '</tr></thead><tbody>' +
    sorted.map(st => renderStockRow(group.id, st)).join('') +
    '</tbody></table></div>';
}

function toggleSectorOpen(id){
  _openSectors[id] = !_openSectors[id];
  renderRank();
}

function toggleGroupOpen(id){
  _openGroups[id] = !_openGroups[id];
  renderRank();
}

// 정렬 적용
function sortStocks(stocks){
  if(_sort === 'manual') return stocks.slice();
  const arr = stocks.slice();
  arr.sort((a, b) => {
    const qa = _quotes[a.code] || {};
    const qb = _quotes[b.code] || {};
    const pa = pctOf(a.code), pb = pctOf(b.code);
    if(_sort === 'chg_desc' || _sort === 'gap_desc') return (pb ?? -999) - (pa ?? -999);
    if(_sort === 'chg_asc'  || _sort === 'gap_asc')  return (pa ??  999) - (pb ??  999);
    if(_sort === 'vol_desc') return (qb.volume ?? -1) - (qa.volume ?? -1);
    return 0;
  });
  return arr;
}

// ── 저장 / 로드 ──────────────────────────
function scheduleSave(){
  if(_RO) return;              // 보기 전용 — 저장 안 함
  if(_saveTimer) clearTimeout(_saveTimer);
  _saveTimer = setTimeout(saveNow, 800);
}

async function saveNow(){
  if(_RO) return;              // 보기 전용 — 저장 안 함
  try {
    const body = JSON.stringify(_data);
    const res = await fetch('/api/post/watchlist', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: body, date: new Date().toISOString().slice(0,10)})
    });
    if(res.ok){
      showSaved();
    } else {
      const txt = await res.text();
      showSaved('⚠️ 저장 실패 HTTP ' + res.status);
      console.error('save failed', res.status, txt.slice(0, 300));
      alert('저장에 실패했습니다 (HTTP ' + res.status + ')\n' +
            '데이터 크기: ' + Math.round(body.length / 1024) + 'KB\n\n' +
            txt.slice(0, 200));
    }
  } catch(e){
    showSaved('⚠️ 저장 오류');
    console.error(e);
    alert('저장 중 오류: ' + (e.message || e));
  }
}

function showSaved(msg){
  const el = document.getElementById('save-indicator');
  el.textContent = msg || ('💾 저장됨 ' + new Date().toLocaleTimeString('ko-KR', {hour:'2-digit',minute:'2-digit'}));
  el.classList.add('visible');
  setTimeout(() => el.classList.remove('visible'), 1800);
}

async function loadData(){
  try {
    const res = await fetch('/api/post/watchlist');
    if(!res.ok){
      if(_RO){
        document.getElementById('watchlist-body').innerHTML =
          '<span class="content-empty">⚠️ 데이터를 불러오지 못했습니다 (HTTP ' + res.status + ')</span>';
        return;
      }
      initEmpty(); return;
    }
    const data = await res.json();
    if(!data || !data.content){
      if(_RO){
        document.getElementById('watchlist-body').innerHTML =
          '<span class="content-empty">아직 등록된 관심종목이 없습니다</span>';
        return;
      }
      initEmpty(); return;
    }
    try { _data = JSON.parse(data.content); }
    catch(e){
      if(_RO){
        document.getElementById('watchlist-body').innerHTML =
          '<span class="content-empty">⚠️ 데이터 형식 오류</span>';
        return;
      }
      initEmpty(); return;
    }
    if(!_data.sectors || !_data.sectors.length){ initEmpty(); return; }
    if(!_data.currentSectorId || !_data.sectors.find(s => s.id === _data.currentSectorId)){
      _data.currentSectorId = _data.sectors[0].id;
    }
    render();
    updateNxtOnlyVisible();
    refreshStaged();
  } catch(e){
    console.error(e);
    if(_RO){
      document.getElementById('watchlist-body').innerHTML =
        '<span class="content-empty">⚠️ 오류: ' + esc(String(e.message || e)) + '</span>';
      return;
    }
    initEmpty();
  }
}

function initEmpty(){
  if(_RO){
    _data = {sectors: [], currentSectorId: null};
    const body = document.getElementById('watchlist-body');
    if(body) body.innerHTML = '<span class="content-empty">아직 등록된 관심종목이 없습니다</span>';
    return;
  }
  _data = {
    sectors: [
      {id: genId(), name: '⚛️ 원전', groups: [
        {id: genId(), name: '시공 및 주기기', stocks: [
          {code: '034020', name: '두산에너빌리티'},
          {code: '000720', name: '현대건설'},
        ]},
        {id: genId(), name: '운영 및 설계/정비', stocks: [
          {code: '015760', name: '한국전력'},
          {code: '051600', name: '한전KPS'},
          {code: '052690', name: '한전기술'},
        ]},
      ]},
      {id: genId(), name: '🔬 반도체', groups: [
        {id: genId(), name: '대형주', stocks: [
          {code: '005930', name: '삼성전자'},
          {code: '000660', name: 'SK하이닉스'},
        ]},
      ]},
    ],
    currentSectorId: null,
  };
  _data.currentSectorId = _data.sectors[0].id;
  scheduleSave();
  render();
  refreshQuotes();
}

// ── 렌더 ────────────────────────────────
function render(){
  renderSignals();
  if(_view === 'rank'){
    const tabs = document.getElementById('sector-tabs');
    if(tabs) tabs.style.display = 'none';
    renderRank();
    return;
  }
  const tabs = document.getElementById('sector-tabs');
  if(tabs) tabs.style.display = '';
  renderTabs();
  renderBody();
}

let _sortableTabs = null;
let _sortableGroups = null;

function renderTabs(){
  const el = document.getElementById('sector-tabs');
  el.innerHTML = _data.sectors.map(s => {
    const active = s.id === _data.currentSectorId;
    return '<button class="sector-tab ' + (active?'active':'') + '" data-sector-id="' + s.id + '" onclick="switchSector(\'' + s.id + '\')">' +
           (_editing ? '<span class="drag-dots" title="드래그로 순서 변경">⋮⋮</span>' : '') +
           '<span class="sector-tab-name">' + esc(s.name) + '</span>' +
           (active && _editing
             ? ' <button class="tab-icon-btn" onclick="event.stopPropagation();renameSectorPrompt(\'' + s.id + '\')" title="이름 변경">✏️</button>' +
               ' <button class="tab-icon-btn" onclick="event.stopPropagation();deleteSector(\'' + s.id + '\')" title="삭제">✕</button>'
             : '') +
           '</button>';
  }).join('');
  if(_editing){
    el.innerHTML += '<button class="sector-add" onclick="addSector()" title="새 섹터">+</button>';
  }
  initSortableTabs();
}

// 🆕 섹터 탭 드래그 정렬
function initSortableTabs(){
  const el = document.getElementById('sector-tabs');
  if(!el || typeof Sortable === 'undefined') return;
  if(_sortableTabs){ try{ _sortableTabs.destroy(); }catch(e){} _sortableTabs = null; }
  if(!_editing) return;   // 편집 모드에서만 드래그 허용
  _sortableTabs = Sortable.create(el, {
    animation: 150,
    handle: '.drag-dots',
    filter: '.sector-add',
    draggable: '.sector-tab',
    onEnd: function(){
      const order = Array.from(el.querySelectorAll('.sector-tab'))
        .map(n => n.getAttribute('data-sector-id'))
        .filter(Boolean);
      const map = {};
      for(const s of _data.sectors) map[s.id] = s;
      _data.sectors = order.map(id => map[id]).filter(Boolean);
      scheduleSave();
      showSaved('✅ 섹터 순서 변경됨');
    }
  });
}

// 🆕 그룹 드래그 정렬
function initSortableGroups(){
  const body = document.getElementById('watchlist-body');
  if(!body || typeof Sortable === 'undefined') return;
  if(_sortableGroups){ try{ _sortableGroups.destroy(); }catch(e){} _sortableGroups = null; }
  if(!_editing || _flatView) return;
  _sortableGroups = Sortable.create(body, {
    animation: 150,
    handle: '.group-drag',
    draggable: '.group',
    onEnd: function(){
      const order = Array.from(body.querySelectorAll('.group'))
        .map(n => n.getAttribute('data-group-id'))
        .filter(Boolean);
      const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
      if(!sector) return;
      const map = {};
      for(const g of sector.groups) map[g.id] = g;
      sector.groups = order.map(id => map[id]).filter(Boolean);
      scheduleSave();
      showSaved('✅ 그룹 순서 변경됨');
    }
  });
}

// 리렌더 전후로 포커스·입력값·스크롤 보존
function withPreservedInput(fn){
  const active = document.activeElement;
  const activeId = active && active.id ? active.id : null;
  const selStart = (active && active.selectionStart !== undefined) ? active.selectionStart : null;
  // 현재 화면의 모든 input 값 저장
  const vals = {};
  document.querySelectorAll('#watchlist-body input[id]').forEach(el => {
    if(el.value) vals[el.id] = el.value;
  });
  const scrollY = window.scrollY;

  fn();

  // 값 복원
  Object.keys(vals).forEach(id => {
    const el = document.getElementById(id);
    if(el && !el.value) el.value = vals[id];
  });
  // 포커스 복원
  if(activeId){
    const el = document.getElementById(activeId);
    if(el && typeof el.focus === 'function'){
      el.focus();
      if(selStart !== null && el.setSelectionRange){
        try { el.setSelectionRange(selStart, selStart); } catch(e){}
      }
    }
  }
  window.scrollTo(0, scrollY);
}

function renderBody(){
  if(_view === 'rank'){ renderRank(); return; }
  const body = document.getElementById('watchlist-body');
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector){
    body.innerHTML = '<span class="content-empty">섹터가 없음. 편집 모드에서 + 눌러 추가하세요.</span>';
    return;
  }
  // 🆕 flat view — 그룹 무시, 전체 종목 하나의 표로
  if(_flatView){
    const all = [];
    for(const g of sector.groups){
      for(const st of visibleStocks(g.stocks)){
        all.push(Object.assign({}, st, {_group: g.name, _groupId: g.id}));
      }
    }
    if(!all.length){
      body.innerHTML = '<span class="content-empty">종목 없음</span>';
      return;
    }
    const sorted = sortStocks(all);
    const isNxtF = gapMode();
    body.innerHTML =
      '<div class="group"><div class="group-header"><span class="group-icon">📊</span>' +
      '<span>' + esc(sector.name) + ' 전체 (' + all.length + '종목)</span></div>' +
      '<table class="stock-table"><thead><tr>' +
      '<th>종목명</th><th>그룹</th>' +
      (isNxtF ? '<th class="num">KRX 마감가</th>' : '') +
      '<th class="num">' + (isNxtF ? 'NXT 현재가' : '현재가') + '</th>' +
      (isNxtF ? '<th class="num">괴리</th><th class="num">괴리율</th>' : '<th class="num">등락</th><th class="num">등락률</th>') +
      '<th class="num">거래량</th><th></th>' +
      '</tr></thead><tbody>' +
      sorted.map(st => renderStockRow(st._groupId, st, true)).join('') +
      '</tbody></table></div>';
    applyCols();
    initSortableGroups();
    return;
  }

  if(!sector.groups.length){
    body.innerHTML = '<span class="content-empty">그룹이 없음. 편집 모드에서 그룹 추가.</span>' +
      (_editing ? '<div style="text-align:center"><button class="add-group-btn" onclick="addGroup()">+ 새 그룹</button></div>' : '');
    applyCols();
    return;
  }
  let html = '';
  for(const g of sector.groups){
    html += renderGroup(sector.id, g);
  }
  if(_editing){
    html += '<div style="text-align:center"><button class="add-group-btn" onclick="addGroup()">+ 새 그룹</button></div>';
  }
  body.innerHTML = html;
  applyCols();
  initSortableGroups();
}

const BIG_GROUP = 60;       // 이보다 크면 기본 접힘 (렌더 부하 방지)
let _expandedBig = {};      // 사용자가 펼친 큰 그룹

function toggleBigGroup(id){
  _expandedBig[id] = !_expandedBig[id];
  renderBody();
}

function renderGroup(sectorId, group){
  let rows = '';
  const stocks = visibleStocks(group.stocks);
  const isNxt = gapMode();
  const tooBig = stocks.length > BIG_GROUP && !_expandedBig[group.id];

  if(tooBig){
    rows = '<div class="big-collapsed" onclick="toggleBigGroup(\'' + group.id + '\')">' +
      '📦 ' + stocks.length + '종목 — 클릭해서 펼치기' +
      '</div>';
  } else if(stocks.length){
    const sorted = sortStocks(stocks);
    rows = '<table class="stock-table">' +
      '<thead><tr>' +
      '<th>종목명</th>' +
      (isNxt ? '<th class="num">KRX 마감가</th>' : '') +
      '<th class="num">' + (isNxt ? 'NXT 현재가' : '현재가') + '</th>' +
      (isNxt ? '<th class="num">괴리</th><th class="num">괴리율</th>' : '<th class="num">등락</th><th class="num">등락률</th>') +
      '<th class="num">거래량</th>' +
      '<th></th>' +
      '</tr></thead><tbody>' +
      sorted.map(st => renderStockRow(group.id, st)).join('') +
      '</tbody></table>' +
      (stocks.length > BIG_GROUP
        ? '<div class="big-collapsed" onclick="toggleBigGroup(\'' + group.id + '\')">▲ 접기</div>'
        : '');
  } else {
    rows = '<div class="content-empty" style="padding:20px">종목 없음</div>';
  }
  // 그룹 요약 (평균)
  let summary = '';
  if(stocks.length){
    const vals = stocks.map(s => pctOf(s.code)).filter(v => v !== undefined && v !== null);
    if(vals.length){
      const avg = vals.reduce((a,b)=>a+b, 0) / vals.length;
      const cls = avg > 0 ? 'up' : (avg < 0 ? 'down' : 'flat');
      summary = '<span style="margin-left:8px;font-size:11.5px;font-weight:500;" class="' + cls + '">평균 ' + (isNxt?'괴리 ':'') + (avg>0?'+':'') + avg.toFixed(2) + '%</span>';
    }
  }
  return '<div class="group" data-group-id="' + group.id + '">' +
    '<div class="group-header">' +
      (_editing ? '<span class="group-drag" title="드래그로 순서 변경">⋮⋮</span>' : '') +
      '<span class="group-icon">📌</span>' +
      '<span class="group-name">' + esc(group.name) + '</span>' +
      (_editing ? '<button class="tab-icon-btn dark" onclick="renameGroupPrompt(\'' + group.id + '\')" title="이름 변경">✏️</button>' : '') +
      summary +
      (_editing ? '<span class="group-actions">' +
        '<button class="btn btn-mini" onclick="moveGroupPrompt(\'' + group.id + '\')" title="다른 섹터로 이동">↗ 이동</button>' +
        '<button class="btn btn-mini btn-danger" onclick="deleteGroup(\'' + group.id + '\')" title="그룹 삭제">🗑</button>' +
        '</span>' : '') +
    '</div>' +
    rows +
    '<div class="add-stock">' +
      '<div class="ac-wrap">' +
        '<input type="text" placeholder="종목명 입력 (예: 두산에너빌리티)" ' +
               'id="ac-input-' + group.id + '" autocomplete="off" ' +
               'oninput="acSearch(\'' + group.id + '\', this.value)" ' +
               'oncompositionstart="_composing=true" ' +
               'oncompositionend="_composing=false;acSearch(\'' + group.id + '\', this.value)" ' +
               'onkeydown="acKeydown(event, \'' + group.id + '\')" ' +
               'onblur="setTimeout(()=>acClose(\'' + group.id + '\'), 200)"/>' +
        '<div class="ac-list" id="ac-list-' + group.id + '"></div>' +
      '</div>' +
      '<button class="btn" onclick="acManualToggle(\'' + group.id + '\')" title="코드 입력창 접기/펼치기">🔢</button>' +
    '</div>' +
    '<div class="add-stock manual" id="manual-' + group.id + '">' +
      '<input type="text" placeholder="종목코드 6자리" id="add-code-' + group.id + '" maxlength="6" style="max-width:160px"/>' +
      '<input type="text" placeholder="종목명" id="add-name-' + group.id + '" onkeydown="if(event.key===\'Enter\' && !event.isComposing && event.keyCode!==229)addStock(\'' + group.id + '\')"/>' +
      '<button class="btn btn-primary" onclick="addStock(\'' + group.id + '\')">+ 추가</button>' +
    '</div>' +
    '</div>';
}

function renderStockRow(groupId, st, showGroup){
  const q = _quotes[st.code] || {};
  const has = q.price !== undefined;
  const isNxt = gapMode();
  const volume = q.volume !== undefined ? num(q.volume) : '—';
  const mkt = q.market || _market;
  const mktBadge = has
    ? '<span class="mkt-badge ' + (MKT_CLASS[mkt]||'un') + '">' + (MKT_LABEL[mkt]||mkt) + '</span>'
    : '';
  const groupCol = showGroup ? '<td style="font-size:11.5px;color:#7a8099">' + esc(st._group || '') + '</td>' : '';

  let priceCols;
  let mainPct;
  if(isNxt){
    const g = gapOf(q);
    const krxClose = g.base ? num(g.base) : '—';
    const nxtPrice = has ? num(q.price) : '—';
    const gapVal = (g.gap !== null && g.gap !== undefined)
      ? (g.gap > 0 ? '+' : '') + num(g.gap) : '—';
    const gapPctVal = (g.pct !== null && g.pct !== undefined)
      ? (g.pct > 0 ? '+' : '') + g.pct.toFixed(2) + '%' : '—';
    mainPct = g.pct;
    const gcls = mainPct > 0 ? 'up' : (mainPct < 0 ? 'down' : 'flat');
    const noNxt = q.no_nxt ? '<span class="hot" style="background:#f1f3f5;color:#7a8099">시간외X</span>' : '';
    priceCols =
      '<td class="num" style="color:#7a8099">' + krxClose + '</td>' +
      '<td class="num">' + nxtPrice + noNxt + '</td>' +
      '<td class="num ' + gcls + '">' + gapVal + '</td>' +
      '<td class="num ' + gcls + '" style="font-weight:700">' + gapPctVal + '</td>';
  } else {
    const price = has ? num(q.price) : '—';
    const chg = q.chg !== undefined ? (q.chg > 0 ? '+' : '') + num(q.chg) : '';
    const chgPct = q.chg_pct !== undefined ? (q.chg_pct > 0 ? '+' : '') + q.chg_pct.toFixed(2) + '%' : '';
    mainPct = q.chg_pct;
    const cls = mainPct > 0 ? 'up' : (mainPct < 0 ? 'down' : 'flat');
    priceCols =
      '<td class="num">' + price + '</td>' +
      '<td class="num ' + cls + '">' + chg + '</td>' +
      '<td class="num ' + cls + '">' + chgPct + '</td>';
  }

  // 🔥 뱃지 — NXT면 괴리율 기준, 아니면 등락률 기준
  const hotBadge = (mainPct !== undefined && mainPct !== null && Math.abs(mainPct) >= (isNxt ? 3 : 5))
    ? '<span class="hot">🔥</span>' : '';

  return '<tr class="stock-row" data-code="' + st.code + '">' +
    '<td><span class="stock-name clickable" onclick="openStock(\'' + st.code + '\',\'' +
      esc(st.name).replace(/'/g, "\\'") + '\')">' + esc(st.name) + '</span>' +
      '<span class="stock-code">' + esc(st.code) + '</span>' + mktBadge + hotBadge + '</td>' +
    groupCol +
    priceCols +
    '<td class="num">' + volume + '</td>' +
    '<td><span class="row-actions"><button class="btn btn-mini btn-danger" onclick="deleteStock(\'' + groupId + '\', \'' + st.code + '\')" title="삭제">✕</button></span></td>' +
    '</tr>';
}

// ── 섹터 관리 ─────────────────────────────
function switchSector(id){
  if(_data.currentSectorId === id) return;
  _data.currentSectorId = id;
  render();          // ⚡ 캐시된 시세로 즉시 렌더 (기다림 없음)
  scheduleSave();
  // 아직 시세 없는 종목만 추가 조회
  const sector = _data.sectors.find(s => s.id === id);
  if(sector){
    const missing = [];
    for(const g of (sector.groups || [])){
      for(const st of (g.stocks || [])){
        if(!_quotes[st.code]) missing.push(st.code);
      }
    }
    if(missing.length) refreshQuotes(missing);
  }
}

function addSector(){
  const n = _data.sectors.length + 1;
  const s = {id: genId(), name: '섹터 ' + n, groups: []};
  _data.sectors.push(s);
  _data.currentSectorId = s.id;
  render();
  scheduleSave();
}

function renameSectorPrompt(id){
  const s = _data.sectors.find(x => x.id === id);
  if(!s) return;
  const v = prompt('섹터 이름 (이모지 포함 가능)', s.name);
  if(v === null) return;
  const name = v.trim().slice(0, 30);
  if(!name || name === s.name) return;
  s.name = name;
  render();
  scheduleSave();
  showSaved('✅ 이름 변경됨');
}

function deleteSector(id){
  if(_data.sectors.length <= 1){ alert('마지막 섹터는 삭제 불가'); return; }
  const s = _data.sectors.find(x => x.id === id);
  if(!s) return;
  if(!confirm('"' + s.name + '" 섹터 삭제할까요?\n(하위 그룹·종목 모두 삭제됨)')) return;
  const idx = _data.sectors.findIndex(x => x.id === id);
  _data.sectors.splice(idx, 1);
  _data.currentSectorId = _data.sectors[Math.max(0, idx-1)].id;
  render();
  refreshQuotes();
  scheduleSave();
}

// ── 그룹 관리 ─────────────────────────────
function addGroup(){
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector) return;
  sector.groups.push({id: genId(), name: '새 그룹', stocks: []});
  render();
  scheduleSave();
}

function renameGroupPrompt(id){
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector) return;
  const g = sector.groups.find(x => x.id === id);
  if(!g) return;
  const v = prompt('그룹 이름', g.name);
  if(v === null) return;
  const name = v.trim().slice(0, 30);
  if(!name || name === g.name) return;
  g.name = name;
  render();
  scheduleSave();
  showSaved('✅ 이름 변경됨');
}

function deleteGroup(id){
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector) return;
  const g = sector.groups.find(x => x.id === id);
  if(!g) return;
  const cnt = (g.stocks || []).length;
  if(!confirm('"' + g.name + '" 그룹 삭제할까요?' + (cnt > 0 ? '\n(종목 ' + cnt + '개 함께 삭제)' : ''))) return;
  sector.groups = sector.groups.filter(x => x.id !== id);
  render();
  scheduleSave();
}

// ── 종목 관리 ─────────────────────────────
// ── 🆕 종목명 자동완성 ────────────────────
const _acState = {};   // { groupId: {timer, items, sel, q} }
let _composing = false;   // 한글 IME 조합 중 여부

function acSearch(groupId, q){
  if(_composing) return;   // 조합 중엔 검색 안 함 (자모 단위 요청 방지)
  q = (q || '').trim();
  const st = _acState[groupId] = _acState[groupId] || {};
  if(st.timer) clearTimeout(st.timer);
  const listEl = document.getElementById('ac-list-' + groupId);
  if(!listEl) return;
  if(q.length < 1){
    acClose(groupId);
    return;
  }
  // 6자리 숫자면 코드 직접 입력으로 간주
  if(/^\d{6}$/.test(q)){
    listEl.innerHTML = '<div class="ac-item" onclick="acPickRaw(\'' + groupId + '\', \'' + q + '\')">' +
      '<span class="ac-item-name">종목코드 ' + q + '</span>' +
      '<span class="ac-item-code">직접 추가</span></div>';
    listEl.classList.add('open');
    return;
  }
  listEl.innerHTML = '<div class="ac-loading">검색 중...</div>';
  listEl.classList.add('open');
  st.timer = setTimeout(async () => {
    // 8초 넘으면 강제 중단 (무한 '검색 중' 방지)
    const ctrl = new AbortController();
    const killer = setTimeout(() => ctrl.abort(), 8000);
    try {
      const res = await fetch('/api/watchlist/search?q=' + encodeURIComponent(q),
                              {signal: ctrl.signal});
      clearTimeout(killer);
      const raw = await res.text();
      if(!res.ok){
        listEl.innerHTML = '<div class="ac-empty">⚠️ 서버 오류 HTTP ' + res.status +
          '<br><span style="font-size:10px;color:#d63031">' + esc(raw.slice(0,200)) + '</span>' +
          '<br><span style="font-size:11px">🔢 코드입력 버튼 사용</span></div>';
        return;
      }
      let data;
      try { data = JSON.parse(raw); }
      catch(pe){
        listEl.innerHTML = '<div class="ac-empty">⚠️ 응답 형식 오류' +
          '<br><span style="font-size:10px;color:#d63031">' + esc(raw.slice(0,200)) + '</span></div>';
        return;
      }
      const items = data.items || [];
      st.items = items;
      st.sel = -1;
      if(!items.length){
        const ms = data.master_size || 0;
        const loading = data.master_loading;
        const err = data.diag || data.error || '';
        listEl.innerHTML = '<div class="ac-empty">검색 결과 없음' +
          (loading ? '<br><span style="font-size:11px;color:#0984e3">📥 종목 목록 준비 중 (30초쯤 뒤 다시 시도해보세요)</span>'
                   : (ms ? '<br><span style="font-size:11px">' + ms + '종목 중 일치 없음 · 오타 확인</span>' : '')) +
          (err ? '<br><span style="font-size:10px;color:#a8b0bd">' + esc(String(err).slice(0,150)) + '</span>' : '') +
          '<br><span style="font-size:11px">🔢 코드입력 칸으로 직접 추가 가능</span></div>';
        return;
      }
      listEl.innerHTML = items.map((it, i) =>
        '<div class="ac-item" data-idx="' + i + '" onclick="acPick(\'' + groupId + '\', ' + i + ')">' +
        '<span class="ac-item-name">' + esc(it.name) + '</span>' +
        '<span class="ac-item-code">' + esc(it.code) + '</span>' +
        (it.market ? '<span class="ac-item-market">' + esc(it.market) + '</span>' : '') +
        '</div>'
      ).join('');
    } catch(e){
      clearTimeout(killer);
      const isAbort = (e.name === 'AbortError');
      listEl.innerHTML = '<div class="ac-empty">' +
        (isAbort ? '⏱️ 응답이 너무 느림 (8초 초과)' : '⚠️ 요청 실패') +
        (isAbort ? '' : '<br><span style="font-size:10px;color:#d63031">' + esc(String(e.message || e).slice(0,180)) + '</span>') +
        '<br><span style="font-size:11px">🔢 코드입력 칸에 종목코드로 추가하세요</span></div>';
    }
  }, 300);
}

function acKeydown(e, groupId){
  // IME 조합 중 Enter는 글자 확정용이므로 무시
  if(_composing || e.isComposing || e.keyCode === 229) return;
  const st = _acState[groupId];
  const listEl = document.getElementById('ac-list-' + groupId);
  if(!st || !st.items || !st.items.length || !listEl || !listEl.classList.contains('open')){
    if(e.key === 'Enter'){
      // 6자리 코드면 바로 추가
      const v = (document.getElementById('ac-input-' + groupId).value || '').trim();
      if(/^\d{6}$/.test(v)) acPickRaw(groupId, v);
    }
    return;
  }
  if(e.key === 'ArrowDown'){
    e.preventDefault();
    st.sel = Math.min((st.sel === undefined ? -1 : st.sel) + 1, st.items.length - 1);
    acHighlight(groupId);
  } else if(e.key === 'ArrowUp'){
    e.preventDefault();
    st.sel = Math.max((st.sel === undefined ? 0 : st.sel) - 1, 0);
    acHighlight(groupId);
  } else if(e.key === 'Enter'){
    e.preventDefault();
    const idx = (st.sel === undefined || st.sel < 0) ? 0 : st.sel;
    acPick(groupId, idx);
  } else if(e.key === 'Escape'){
    acClose(groupId);
  }
}

function acHighlight(groupId){
  const st = _acState[groupId];
  const listEl = document.getElementById('ac-list-' + groupId);
  if(!listEl) return;
  listEl.querySelectorAll('.ac-item').forEach(el => el.classList.remove('sel'));
  const target = listEl.querySelector('[data-idx="' + st.sel + '"]');
  if(target){
    target.classList.add('sel');
    target.scrollIntoView({block:'nearest'});
  }
}

function acPick(groupId, idx){
  const st = _acState[groupId];
  if(!st || !st.items || !st.items[idx]) return;
  const it = st.items[idx];
  addStockDirect(groupId, it.code, it.name);
  const inputEl = document.getElementById('ac-input-' + groupId);
  if(inputEl) inputEl.value = '';
  acClose(groupId);
}

function acPickRaw(groupId, code){
  addStockDirect(groupId, code, code);   // 이름 = 코드 (나중에 시세 조회 후 갱신 가능)
  const inputEl = document.getElementById('ac-input-' + groupId);
  if(inputEl) inputEl.value = '';
  acClose(groupId);
}

function acClose(groupId){
  const listEl = document.getElementById('ac-list-' + groupId);
  if(listEl) listEl.classList.remove('open');
}

function acManualToggle(groupId){
  const el = document.getElementById('manual-' + groupId);
  if(!el) return;
  const hidden = (el.style.display === 'none');
  el.style.display = hidden ? 'flex' : 'none';
}

// 공통 추가 로직
function addStockDirect(groupId, code, name){
  code = (code || '').trim();
  name = (name || '').trim();
  if(!/^\d{6}$/.test(code)){ alert('종목코드는 6자리 숫자'); return; }
  if(!name) name = code;
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector) return;
  const g = sector.groups.find(x => x.id === groupId);
  if(!g) return;
  if(g.stocks.find(s => s.code === code)){
    showSaved('⚠️ 이미 있는 종목: ' + name);
    return;
  }
  g.stocks.push({code, name});
  withPreservedInput(render);
  refreshQuotes([code]);
  scheduleSave();
  showSaved('✅ ' + name + ' 추가됨');
  // 추가 후 다시 입력창에 포커스 (연속 추가 편하게)
  setTimeout(() => {
    const inputEl = document.getElementById('ac-input-' + groupId);
    if(inputEl){ inputEl.value = ''; inputEl.focus(); }
  }, 60);
}

function addStock(groupId){
  const codeEl = document.getElementById('add-code-' + groupId);
  const nameEl = document.getElementById('add-name-' + groupId);
  const code = (codeEl.value || '').trim();
  const name = (nameEl.value || '').trim();
  if(!code || !/^\d{6}$/.test(code)){
    alert('종목코드는 6자리 숫자 (예: 005930)');
    return;
  }
  if(!name){ alert('종목명을 입력해주세요'); return; }
  addStockDirect(groupId, code, name);
  codeEl.value = '';
  nameEl.value = '';
}

function deleteStock(groupId, code){
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector) return;
  const g = sector.groups.find(x => x.id === groupId);
  if(!g) return;
  const st = g.stocks.find(s => s.code === code);
  if(!confirm('"' + (st ? st.name : code) + '" 삭제할까요?')) return;
  g.stocks = g.stocks.filter(s => s.code !== code);
  render();
  scheduleSave();
}

// ── 편집 모드 ─────────────────────────────
function toggleEdit(){
  _editing = !_editing;
  document.body.classList.toggle('edit-mode', _editing);
  const btn = document.getElementById('edit-btn');
  btn.textContent = _editing ? '✓ 편집 완료' : '⚙️ 편집';
  btn.classList.toggle('btn-primary', _editing);
  // 편집 중엔 자동 갱신 중지 안내
  const hint = document.getElementById('market-hint');
  if(hint){
    if(_editing){
      hint.dataset.prev = hint.textContent;
      hint.textContent = '⏸️ 편집 중 — 자동 갱신 멈춤 (🔄 버튼으로 수동 갱신)';
      hint.style.color = '#d63031';
    } else {
      hint.style.color = '';
      updateMarketHint();
    }
  }
  if(_editing && _view === 'rank') setView('list');
  else render();
}

// ── KIS 시세 조회 ──────────────────────────
let _fetching = false;

// ⚡ 전체 섹터 종목 코드 (탭 전환 시 즉시 표시용)
function allCodesEverywhere(){
  const set = new Set();
  for(const s of _data.sectors){
    for(const g of (s.groups || [])){
      for(const st of (g.stocks || [])) set.add(st.code);
    }
  }
  return Array.from(set);
}

async function refreshQuotes(codes, opts){
  opts = opts || {};
  if(_fetching && !opts.force) return;
  const btn = document.getElementById('refresh-btn');
  const sector = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!sector){ return; }
  _fetching = true;
  if(btn){ btn.disabled = true; btn.textContent = '⏳ 조회 중...'; }
  const t0 = performance.now();
  // codes가 주어지면 그것만, 아니면 현재 섹터의 모든 종목
  let allCodes;
  if(codes && codes.length){
    allCodes = codes;
  } else {
    const set = new Set();
    for(const g of sector.groups){
      for(const s of g.stocks) set.add(s.code);
    }
    allCodes = Array.from(set);
  }
  if(!allCodes.length){
    if(btn){ btn.disabled = false; btn.textContent = '🔄 시세 갱신';}
    return;
  }
  try {
    const res = await fetch('/api/watchlist/quotes', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({codes: allCodes, market: _market,
                            session: effectiveSession(), force: !!opts.force})
    });
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    Object.assign(_quotes, data.quotes || {});
    // 종목명이 코드로만 되어 있으면 API가 준 이름으로 자동 보정
    let renamed = false;
    for(const s of _data.sectors){
      for(const g of s.groups){
        for(const st of g.stocks){
          const q = _quotes[st.code];
          if(q && q.api_name && (st.name === st.code || !st.name)){
            st.name = q.api_name;
            renamed = true;
          }
        }
      }
    }
    if(renamed) scheduleSave();
    const ms = Math.round(performance.now() - t0);
    const got = Object.keys(data.quotes || {}).length;
    const srvMs = data.elapsed ? Math.round(data.elapsed * 1000) : null;
    const timing = srvMs !== null
      ? '서버 ' + srvMs + 'ms / 전체 ' + ms + 'ms'
      : ms + 'ms';
    document.getElementById('updated').textContent =
      '📊 ' + MKT_LABEL[_market] + ' 시세 · ' + new Date().toLocaleTimeString('ko-KR') +
      ' · ' + got + '/' + allCodes.length + '종목 · ' + timing +
      (data.cached ? ' (캐시)' : '');
    updateMarketHint();
    updateGapButtons();
    withPreservedInput(renderBody);
    renderSignals();
  } catch(e){
    document.getElementById('updated').textContent = '⚠️ 시세 조회 실패: ' + e.message;
  } finally {
    _fetching = false;
    if(btn){ btn.disabled = false; btn.textContent = '🔄 시세 갱신'; }
  }
}

// 30초마다 자동 갱신 (탭 활성 시만)
// 사용자가 입력 중인지 판단 (편집 방해 방지)
function isUserTyping(){
  const el = document.activeElement;
  if(!el) return false;
  const tag = (el.tagName || '').toLowerCase();
  if(tag === 'input' || tag === 'textarea') return true;
  if(el.isContentEditable) return true;
  // 자동완성 드롭다운이 열려 있으면 입력 중으로 간주
  if(document.querySelector('.ac-list.open')) return true;
  return false;
}

// 현재 섹터 종목 코드
function currentSectorCodes(){
  const s = _data.sectors.find(x => x.id === _data.currentSectorId);
  const out = [];
  if(s){
    for(const g of (s.groups || [])){
      for(const st of (g.stocks || [])) out.push(st.code);
    }
  }
  return out;
}

// ⚡ 창고형 운용 — 보고 있는 섹터만 조회한다.
//    등록 종목이 수천 개여도 실제 요청은 현재 섹터 크기만큼만 발생.
//    (랭킹 뷰나 시그널처럼 전체가 필요할 때만 예외적으로 전부 조회)
async function refreshStaged(opts){
  opts = opts || {};
  // 랭킹 뷰는 섹터 비교가 목적이라 전체가 필요
  if(_view === 'rank'){
    const all = allCodesEverywhere();
    if(all.length > 400 && !opts.force){
      // 너무 많으면 아직 시세 없는 것만 채움
      const missing = all.filter(c => !_quotes[c]);
      return refreshQuotes(missing.length ? missing : all, opts);
    }
    return refreshQuotes(all, opts);
  }
  const cur = currentSectorCodes();
  if(!cur.length) return;
  return refreshQuotes(cur, opts);
}

function startAutoRefresh(){
  if(_autoRefreshTimer) clearInterval(_autoRefreshTimer);
  _autoRefreshTimer = setInterval(() => {
    if(document.hidden) return;
    if(_editing) return;
    if(isUserTyping()) return;
    refreshStaged();
  }, 30000);
}

document.addEventListener('visibilitychange', () => {
  if(document.hidden) return;
  if(_editing || isUserTyping()) return;
  refreshStaged();
});

// 초기 컨트롤 상태 세팅
// ── 📈 종목 상세 (워치리스트 위치 + K-Stock DB) ────
async function openStock(code, name){
  const ov = document.getElementById('stock-overlay');
  const body = document.getElementById('stock-body');
  document.getElementById('stock-title').textContent = name + '  ' + code;
  ov.classList.add('open');

  // 1) 워치리스트에서 이 종목이 속한 테마들
  const places = [];
  for(const s of _data.sectors){
    for(const g of (s.groups || [])){
      if((g.stocks || []).some(x => x.code === code)){
        places.push({sectorId: s.id, groupId: g.id,
                     sectorName: s.name, groupName: g.name,
                     count: (g.stocks || []).length});
      }
    }
  }

  // 2) 현재 시세
  const q = _quotes[code] || {};
  const v = pctOf(code);
  const cls = v > 0 ? 'up' : (v < 0 ? 'down' : 'flat');
  const pct = (v === undefined || v === null) ? '—'
            : (v > 0 ? '+' : '') + v.toFixed(2) + '%';
  const isNxt = gapMode();

  let html = '';
  if(q.price){
    const g = gapOf(q);
    html += '<div class="stock-quote">' +
      (isNxt && g.base
        ? '<span class="sq-item"><b>KRX 마감</b>' + num(g.base) + '</span>' +
          '<span class="sq-item"><b>NXT</b>' + num(q.price) + '</span>' +
          '<span class="sq-item ' + cls + '"><b>괴리율</b>' + pct + '</span>'
        : '<span class="sq-item"><b>현재가</b>' + num(q.price) + '</span>' +
          '<span class="sq-item ' + cls + '"><b>등락률</b>' + pct + '</span>') +
      '<span class="sq-item"><b>거래량</b>' + num(q.volume || 0) + '</span>' +
      '</div>';
  }

  // 워치리스트 위치
  html += '<div class="stock-section">📁 내 워치리스트 테마 ' + places.length + '곳</div>';
  if(!places.length){
    html += '<div class="stock-empty">이 종목은 워치리스트에 없습니다</div>';
  } else {
    html += '<div class="stock-places">' + places.map(p =>
      '<div class="stock-place" onclick="closeStock();gotoSignal(\'' + p.sectorId + '\',\'' + p.groupId + '\')">' +
      '<span class="sp-group">' + esc(p.groupName) + '</span>' +
      '<span class="sp-sector">' + esc(p.sectorName) + '</span>' +
      '<span class="sp-count">' + p.count + '종목</span>' +
      '</div>').join('') + '</div>';
  }

  // K-Stock DB — 로딩 표시 후 채움
  html += '<div class="stock-section">📚 K-Stock DB</div>' +
          '<div id="stock-db"><div class="stock-empty">불러오는 중...</div></div>';
  body.innerHTML = html;

  try {
    const res = await fetch('/api/watchlist/stock-info?code=' + encodeURIComponent(code));
    const d = await res.json();
    const el = document.getElementById('stock-db');
    if(!el) return;
    const entries = d.entries || [];
    if(!entries.length){
      el.innerHTML = '<div class="stock-empty">DB에 등록된 정보가 없습니다' +
        (d.db_size ? ' (' + d.db_size + '종목 중)' : '') + '</div>';
      return;
    }
    el.innerHTML = entries.map(e =>
      '<div class="db-entry">' +
      (e.theme ? '<div class="db-theme">' + esc(e.theme) + '</div>' : '') +
      (e.desc ? '<div class="db-desc">' + esc(e.desc) + '</div>' : '') +
      '</div>').join('');
  } catch(e){
    const el = document.getElementById('stock-db');
    if(el) el.innerHTML = '<div class="stock-empty">⚠️ ' + esc(String(e.message || e)) + '</div>';
  }
}

function closeStock(){
  document.getElementById('stock-overlay').classList.remove('open');
}

// ── ↗ 그룹을 다른 섹터로 이동 ────────────────
let _moveGroupId = null;

function moveGroupPrompt(groupId){
  const cur = _data.sectors.find(s => s.id === _data.currentSectorId);
  if(!cur) return;
  const g = cur.groups.find(x => x.id === groupId);
  if(!g) return;
  const others = _data.sectors.filter(s => s.id !== cur.id);
  if(!others.length){
    alert('이동할 다른 섹터가 없어요. 먼저 섹터를 만들어주세요.');
    return;
  }
  _moveGroupId = groupId;
  document.getElementById('move-desc').innerHTML =
    '<b>' + esc(g.name) + '</b> (' + (g.stocks || []).length + '종목)을 ' +
    '<b>' + esc(cur.name) + '</b>에서 다른 섹터로 옮깁니다.';
  document.getElementById('move-target').innerHTML =
    others.map(s => '<option value="' + s.id + '">' + esc(s.name) + '</option>').join('');
  document.getElementById('move-overlay').classList.add('open');
}

function closeMove(){
  document.getElementById('move-overlay').classList.remove('open');
  _moveGroupId = null;
}

function applyMove(){
  if(!_moveGroupId) return;
  const cur = _data.sectors.find(s => s.id === _data.currentSectorId);
  const targetId = document.getElementById('move-target').value;
  const target = _data.sectors.find(s => s.id === targetId);
  if(!cur || !target){ closeMove(); return; }
  const idx = cur.groups.findIndex(x => x.id === _moveGroupId);
  if(idx < 0){ closeMove(); return; }
  const [g] = cur.groups.splice(idx, 1);
  target.groups.push(g);
  closeMove();
  render();
  scheduleSave();
  showSaved('✅ "' + g.name + '" → ' + target.name + ' 이동됨');
}

// ── 🔎 찾기 — 종목명 · 테마(그룹) · 섹터 동시 검색 ────
function findMyStock(q){
  if(_composing) return;
  const box = document.getElementById('find-result');
  if(!box) return;
  q = (q || '').trim().toLowerCase().replace(/\s/g, '');
  if(q.length < 1){ box.classList.remove('open'); box.innerHTML = ''; return; }

  const themeHits = [];   // 그룹(테마) 매칭
  const stockHits = [];   // 종목 매칭

  for(const s of _data.sectors){
    const sName = (s.name || '').toLowerCase().replace(/\s/g, '');
    for(const g of (s.groups || [])){
      const gName = (g.name || '').toLowerCase().replace(/\s/g, '');
      // 그룹명 또는 섹터명이 걸리면 테마 결과로
      if(gName.includes(q) || sName.includes(q)){
        const vs = (g.stocks || []);
        themeHits.push({
          sectorId: s.id, groupId: g.id,
          sectorName: s.name, groupName: g.name,
          count: vs.length, avg: avgPct(vs),
        });
      }
      for(const st of (g.stocks || [])){
        const nm = (st.name || '').toLowerCase().replace(/\s/g, '');
        if(nm.includes(q) || st.code.includes(q)){
          stockHits.push({
            stock: st, sectorId: s.id, groupId: g.id,
            sectorName: s.name, groupName: g.name,
          });
        }
      }
    }
  }

  if(!themeHits.length && !stockHits.length){
    box.innerHTML = '<div class="find-none">「' + esc(q) + '」 등록된 종목·테마 중에 없음</div>';
    box.classList.add('open');
    return;
  }

  let html = '';

  // ── 테마(그룹) 결과 ──
  if(themeHits.length){
    themeHits.sort((a,b) => (b.avg ?? -999) - (a.avg ?? -999));
    html += '<div class="find-section">📁 테마 ' + themeHits.length + '개</div>';
    html += themeHits.slice(0, 6).map(t => {
      const cls = t.avg > 0 ? 'up' : (t.avg < 0 ? 'down' : 'flat');
      const pct = (t.avg === null || t.avg === undefined) ? '—'
                : (t.avg > 0 ? '+' : '') + t.avg.toFixed(2) + '%';
      return '<div class="find-item" onclick="gotoSignal(\'' + t.sectorId + '\',\'' + t.groupId + '\')">' +
        '<span class="find-name">📁 ' + esc(t.groupName) + '</span>' +
        '<span class="find-code">' + t.count + '종목</span>' +
        '<span class="find-path"><b>' + esc(t.sectorName) + '</b></span>' +
        '<span class="find-pct ' + cls + '">' + pct + '</span>' +
        '</div>';
    }).join('');
  }

  // ── 종목 결과 ──
  if(stockHits.length){
    const byCode = {};
    for(const h of stockHits){
      if(!byCode[h.stock.code]) byCode[h.stock.code] = {stock: h.stock, places: []};
      byCode[h.stock.code].places.push(h);
    }
    const list = Object.values(byCode);
    html += '<div class="find-section">📈 종목 ' + list.length + '개</div>';
    html += list.slice(0, 8).map(entry => {
      const st = entry.stock;
      const v = pctOf(st.code);
      const cls = v > 0 ? 'up' : (v < 0 ? 'down' : 'flat');
      const pct = (v === undefined || v === null) ? '—'
                : (v > 0 ? '+' : '') + v.toFixed(2) + '%';
      const paths = entry.places.map(p =>
        '<b>' + esc(p.sectorName) + '</b> › ' + esc(p.groupName)).join(' &nbsp;·&nbsp; ');
      const first = entry.places[0];
      const dupNote = entry.places.length > 1
        ? ' <span style="font-size:10px;color:#e17055">' + entry.places.length + '곳 중복</span>' : '';
      return '<div class="find-item" onclick="gotoSignal(\'' + first.sectorId + '\',\'' + first.groupId + '\')">' +
        '<span class="find-name">' + esc(st.name) + '</span>' +
        '<span class="find-code">' + esc(st.code) + '</span>' +
        '<span class="find-path">' + paths + dupNote + '</span>' +
        '<span class="find-pct ' + cls + '">' + pct + '</span>' +
        '</div>';
    }).join('');
  }

  box.innerHTML = html;
  box.classList.add('open');
}

// 바깥 클릭하면 결과 닫기
document.addEventListener('click', (e) => {
  const box = document.getElementById('find-result');
  const inp = document.getElementById('find-input');
  if(!box || !inp) return;
  if(e.target === inp || box.contains(e.target)) return;
  box.classList.remove('open');
});
// 세부 그룹(테마) 단위로 이상 흐름을 잡아낸다.
const SIG = {
  GROUP_MOVE: 3.0,    // 그룹 평균 ±3% 이상 → 동반 급등/급락
  GROUP_CALM: 1.5,    // 그룹 평균 ±1.5% 이내면 '잠잠'
  SOLO_MOVE: 5.0,     // 잠잠한 그룹에서 홀로 ±5% → 개별 이슈
  SPLIT_GAP: 10.0,    // 그룹 내 최고-최저 10%p 차이 → 분열
  MIN_STOCKS: 2,      // 그룹 판정 최소 종목 수
};

function median(arr){
  if(!arr.length) return 0;
  const a = arr.slice().sort((x,y) => x-y);
  const m = Math.floor(a.length / 2);
  return a.length % 2 ? a[m] : (a[m-1] + a[m]) / 2;
}

function detectSignals(){
  const out = [];

  for(const sector of _data.sectors){
    for(const g of (sector.groups || [])){
      const stocks = (g.stocks || []).filter(s => {
        const v = pctOf(s.code);
        return v !== undefined && v !== null;
      });
      if(stocks.length < SIG.MIN_STOCKS) continue;

      const vals = stocks.map(s => pctOf(s.code));
      const avg = vals.reduce((a,b) => a+b, 0) / vals.length;
      // 중앙값 — 한 종목이 튀어서 평균을 끌어올리는 걸 걸러냄
      const med = median(vals);
      const upN = vals.filter(v => v > 0).length;
      const downN = vals.filter(v => v < 0).length;
      const half = stocks.length / 2;

      const base = {sectorId: sector.id, groupId: g.id,
                    sectorName: sector.name, groupName: g.name,
                    count: stocks.length};

      // ① 그룹 동반 급등 / 급락 — 평균과 중앙값이 둘 다 커야 '진짜 동반'
      if(avg >= SIG.GROUP_MOVE && med >= SIG.GROUP_MOVE && upN >= half){
        out.push(Object.assign({}, base, {
          type: 'surge', icon: '🔥', score: Math.abs(med) * 2,
          detail: stocks.length + '종목 중 ' + upN + '개 상승 · 테마 전체가 움직임',
          val: (avg > 0 ? '+' : '') + avg.toFixed(2) + '%',
          valCls: 'up',
        }));
      } else if(avg <= -SIG.GROUP_MOVE && med <= -SIG.GROUP_MOVE && downN >= half){
        out.push(Object.assign({}, base, {
          type: 'plunge', icon: '🧊', score: Math.abs(med) * 2,
          detail: stocks.length + '종목 중 ' + downN + '개 하락 · 테마 전반 약세',
          val: avg.toFixed(2) + '%',
          valCls: 'down',
        }));
      }

      // ② 나머지 종목은 잠잠한데 홀로 튀는 종목 (중앙값 기준)
      if(Math.abs(med) <= SIG.GROUP_CALM){
        for(const s of stocks){
          const v = pctOf(s.code);
          if(Math.abs(v) >= SIG.SOLO_MOVE){
            out.push(Object.assign({}, base, {
              type: 'solo', icon: '⚡', score: Math.abs(v),
              stockName: s.name, stockCode: s.code,
              detail: '나머지 종목은 ' + (med>0?'+':'') + med.toFixed(2) + '% 수준 · 이 종목만 단독 움직임',
              val: (v > 0 ? '+' : '') + v.toFixed(2) + '%',
              valCls: v > 0 ? 'up' : 'down',
            }));
          }
        }
      }

      // ③ 그룹 내 분열 (최고 - 최저)
      const maxV = Math.max(...vals), minV = Math.min(...vals);
      if((maxV - minV) >= SIG.SPLIT_GAP && stocks.length >= 3){
        const top = stocks.find(s => pctOf(s.code) === maxV);
        const bot = stocks.find(s => pctOf(s.code) === minV);
        out.push(Object.assign({}, base, {
          type: 'split', icon: '↔️', score: (maxV - minV) / 2,
          detail: (top ? top.name : '') + ' ' + (maxV>0?'+':'') + maxV.toFixed(1) + '% ↔ ' +
                  (bot ? bot.name : '') + ' ' + minV.toFixed(1) + '% · 같은 테마인데 온도차',
          val: (maxV - minV).toFixed(1) + '%p',
          valCls: 'flat',
        }));
      }
    }
  }

  out.sort((a,b) => b.score - a.score);
  return out.slice(0, 8);
}

function renderSignals(){
  const box = document.getElementById('signal-box');
  if(!box) return;
  if(_editing){ box.innerHTML = ''; return; }   // 편집 중엔 방해되니 숨김
  const on = document.getElementById('signal-on');
  if(on && !on.checked){ box.innerHTML = ''; return; }

  const sigs = detectSignals();
  const isNxt = gapMode();
  const basis = isNxt ? 'NXT 괴리율' : '등락률';

  if(!sigs.length){
    box.innerHTML = '<div class="signal-head">🚨 특이 시그널</div>' +
      '<div class="signal-empty">지금은 눈에 띄는 움직임 없음 (' + basis + ' 기준)</div>';
    return;
  }

  const labels = {surge:'동반 급등', plunge:'동반 급락', solo:'단독 급변',
                  split:'테마 내 분열'};

  box.innerHTML = '<div class="signal-head">🚨 특이 시그널 · ' + basis + ' 기준 · ' + sigs.length + '건</div>' +
    '<div class="signal-list">' +
    sigs.map(s => {
      const where = s.stockName
        ? esc(s.stockName) + ' <span style="font-size:10.5px;color:#a8b0bd">' + esc(s.sectorName) + ' › ' + esc(s.groupName) + '</span>'
        : esc(s.sectorName) + ' › ' + esc(s.groupName);
      return '<div class="signal-card ' + s.type + '" onclick="gotoSignal(\'' + s.sectorId + '\',\'' + s.groupId + '\')">' +
        '<span class="signal-icon">' + s.icon + '</span>' +
        '<span class="signal-text">' +
          '<span class="signal-where">' + where + '</span>' +
          ' <span style="font-size:10.5px;color:#7a8099">· ' + labels[s.type] + '</span>' +
          '<br><span class="signal-detail">' + esc(s.detail) + '</span>' +
        '</span>' +
        '<span class="signal-val ' + s.valCls + '">' + esc(s.val) + '</span>' +
        '</div>';
    }).join('') + '</div>';
}

// 시그널 클릭 → 해당 섹터/그룹으로 이동
function gotoSignal(sectorId, groupId){
  const fbox = document.getElementById('find-result');
  if(fbox) fbox.classList.remove('open');
  _expandedBig[groupId] = true;   // 접혀 있던 큰 그룹도 펼침
  if(_view === 'rank'){
    _openSectors[sectorId] = true;
    _openGroups[groupId] = true;
    renderRank();
    setTimeout(() => {
      const el = document.querySelector('[data-group-id="' + groupId + '"]');
      if(el) el.scrollIntoView({behavior:'smooth', block:'center'});
    }, 60);
    return;
  }
  _data.currentSectorId = sectorId;
  render();
  // 창고형 — 이 섹터 시세가 아직 없으면 지금 받아옴
  const missing = currentSectorCodes().filter(c => !_quotes[c]);
  if(missing.length) refreshQuotes(missing);
  setTimeout(() => {
    const el = document.querySelector('[data-group-id="' + groupId + '"]');
    if(el){
      el.scrollIntoView({behavior:'smooth', block:'center'});
      el.style.transition = 'box-shadow .3s';
      el.style.boxShadow = '0 0 0 3px rgba(26,29,35,0.25)';
      setTimeout(() => { el.style.boxShadow = ''; }, 1400);
    }
  }, 60);
}

// ── 🚨 시그널 끝 ─────────────────────────

// ── 📥 엑셀 일괄 추가 ─────────────────────
let _bulkRows = [];   // [{code, name, dup}]
let _bulkSkipped = 0; // 종목코드를 못 찾아 건너뛴 줄 수
let _bulkMode = 'add';  // add | check

function setBulkMode(m){
  _bulkMode = m;
  document.querySelectorAll('.seg[data-bmode]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-bmode') === m);
  });
  const tw = document.getElementById('bulk-target-wrap');
  if(tw) tw.style.display = (m === 'check') ? 'none' : '';
  const hint = document.getElementById('bulk-hint-text');
  if(hint){
    hint.innerHTML = (m === 'check')
      ? '엑셀 원본을 붙여넣으면 <b>대시보드에 없는 종목</b>을 찾아줍니다. 추가는 하지 않아요.'
      : '엑셀에서 <b>종목명·종목코드가 포함된 범위를 그대로 복사</b>해서 아래에 붙여넣으세요. 열 순서·개수는 상관없고, 6자리 숫자를 종목코드로 자동 인식합니다.';
  }
  parseBulk();
  updateBulkButton();
}

// 대시보드 전체에 등록된 종목코드 (어느 섹터든)
function allRegisteredCodes(){
  const set = new Set();
  for(const s of _data.sectors){
    for(const g of (s.groups || [])){
      for(const st of (g.stocks || [])) set.add(st.code);
    }
  }
  return set;
}

// 종목코드가 어느 섹터/그룹에 있는지
function whereIs(code){
  const places = [];
  for(const s of _data.sectors){
    for(const g of (s.groups || [])){
      if((g.stocks || []).some(x => x.code === code)){
        places.push(s.name + ' › ' + g.name);
      }
    }
  }
  return places;
}

function openBulk(){
  document.getElementById('bulk-overlay').classList.add('open');
  setBulkMode('add');
  fillBulkSelects();
  document.getElementById('bulk-input').value = '';
  _bulkRows = [];
  renderBulkPreview();
  setTimeout(() => document.getElementById('bulk-input').focus(), 80);
}

function closeBulk(){
  document.getElementById('bulk-overlay').classList.remove('open');
}

function fillBulkSelects(){
  const ss = document.getElementById('bulk-sector');
  ss.innerHTML = _data.sectors.map(s =>
    '<option value="' + s.id + '"' + (s.id === _data.currentSectorId ? ' selected' : '') + '>' +
    esc(s.name) + '</option>').join('');
  onBulkSectorChange();
}

function onBulkSectorChange(){
  const sid = document.getElementById('bulk-sector').value;
  const s = _data.sectors.find(x => x.id === sid);
  const gs = document.getElementById('bulk-group');
  if(!s || !s.groups.length){
    gs.innerHTML = '<option value="">(그룹 없음 — + 새 그룹)</option>';
  } else {
    gs.innerHTML = s.groups.map(g =>
      '<option value="' + g.id + '">' + esc(g.name) + '</option>').join('');
  }
  updateBulkButton();
  parseBulk();
}

function updateBulkButton(){
  const btn = document.getElementById('bulk-apply');
  if(!btn) return;
  if(_bulkMode === 'check'){
    const missN = _bulkRows.filter(r => !r.dup).length;
    btn.textContent = missN ? '빠진 ' + missN + '개 복사' : '빠진 종목 없음';
    btn.disabled = !missN;
    return;
  }
  btn.disabled = false;
  const sid = document.getElementById('bulk-sector').value;
  const gid = document.getElementById('bulk-group').value;
  const s = _data.sectors.find(x => x.id === sid);
  const g = s && s.groups.find(x => x.id === gid);
  btn.textContent = (s && g)
    ? '「' + s.name + ' › ' + g.name + '」에 추가'
    : '추가하기';
}

function bulkNewSector(){
  const v = prompt('새 섹터 이름 (이모지 포함 가능)', '새 섹터');
  if(v === null) return;
  const name = v.trim().slice(0, 30);
  if(!name) return;
  const s = {id: genId(), name: name, groups: []};
  _data.sectors.push(s);
  scheduleSave();
  fillBulkSelects();
  document.getElementById('bulk-sector').value = s.id;
  onBulkSectorChange();
}

function bulkNewGroup(){
  const sid = document.getElementById('bulk-sector').value;
  const s = _data.sectors.find(x => x.id === sid);
  if(!s){ alert('먼저 섹터를 선택하세요'); return; }
  const v = prompt('새 그룹 이름', '새 그룹');
  if(v === null) return;
  const name = v.trim().slice(0, 30);
  if(!name) return;
  const g = {id: genId(), name: name, stocks: []};
  s.groups.push(g);
  scheduleSave();
  onBulkSectorChange();
  document.getElementById('bulk-group').value = g.id;
  parseBulk();
}

// 붙여넣은 텍스트에서 (종목명, 6자리코드) 추출
// 엑셀 한 행은 반드시 종목코드를 포함하므로,
// 코드가 나올 때까지 줄을 모아 하나의 레코드로 본다.
// (셀 안 줄바꿈이나 따옴표가 꼬여도 안전)
function parseBulk(){
  const text = document.getElementById('bulk-input').value || '';
  const lines = text.split(/\r?\n/);
  const rows = [];
  const seen = new Set();

  const sid = document.getElementById('bulk-sector').value;
  const gid = document.getElementById('bulk-group').value;
  const s = _data.sectors.find(x => x.id === sid);
  const g = s && s.groups.find(x => x.id === gid);
  // 추가 모드 → 대상 그룹 기준 / 확인 모드 → 대시보드 전체 기준
  const existing = (_bulkMode === 'check')
    ? allRegisteredCodes()
    : new Set((g && g.stocks || []).map(x => x.code));

  const splitCells = (line) =>
    (line.includes('\t') ? line.split('\t')
      : (line.includes(',') ? line.split(',') : line.split(/\s{2,}/)))
    .map(c => c.replace(/^"+|"+$/g, '').trim());

  let buf = [];          // 아직 코드를 못 만난 줄들
  let skipped = 0;

  for(const raw of lines){
    if(!raw.trim() && !buf.length) continue;
    buf.push(raw);

    // 이번 줄에서 6자리 코드 찾기
    const cells = splitCells(raw);
    let code = null;
    for(const c of cells){
      const m = c.match(/^[A-Za-z]?(\d{6})$/);
      if(m){ code = m[1]; break; }
    }
    if(!code) continue;   // 아직 레코드 끝이 아님 → 계속 누적

    // 종목명 = 레코드 첫 줄의 첫 셀 (그게 코드면 두 번째 셀)
    const head = splitCells(buf[0]).filter(c => c !== '');
    let name = '';
    for(const c of head){
      if(/^[A-Za-z]?\d{6}$/.test(c)) continue;
      if(!c) continue;
      name = c.length > 25 ? c.slice(0, 25) : c;
      break;
    }
    buf = [];

    if(!name) name = code;
    if(seen.has(code)) continue;
    seen.add(code);
    rows.push({code, name, dup: existing.has(code)});
  }
  // 코드 없이 남은 줄
  if(buf.length && buf.join('').trim()) skipped = 1;

  _bulkRows = rows;
  _bulkSkipped = skipped;
  renderBulkPreview();
}

function renderBulkPreview(){
  const el = document.getElementById('bulk-preview');
  const cnt = document.getElementById('bulk-count');
  const dupN = _bulkRows.filter(r => r.dup).length;
  const missN = _bulkRows.length - dupN;

  if(_bulkMode === 'check'){
    cnt.innerHTML = '원본 ' + _bulkRows.length + '종목 중 ' +
      '<span style="color:#d63031">빠진 것 ' + missN + '개</span>' +
      ' · 등록됨 ' + dupN + '개' +
      (_bulkSkipped ? ' <span style="color:#e17055">· 인식 못한 줄 있음</span>' : '');
    if(!_bulkRows.length){
      el.innerHTML = '<div class="empty">엑셀 원본을 붙여넣으면 빠진 종목을 찾아드립니다</div>';
      return;
    }
    // 빠진 것 먼저, 그다음 등록된 것
    const sorted = _bulkRows.slice().sort((a,b) => (a.dup?1:0) - (b.dup?1:0));
    el.innerHTML = '<table><thead><tr><th>종목명</th><th>종목코드</th><th>상태</th></tr></thead><tbody>' +
      sorted.map(r =>
        '<tr class="' + (r.dup ? '' : 'missing') + '">' +
        '<td>' + esc(r.name) + '</td>' +
        '<td>' + esc(r.code) + '</td>' +
        '<td>' + (r.dup
          ? '<span style="color:#7a8099;font-size:10.5px">' + esc(whereIs(r.code).join(' · ')) + '</span>'
          : '<span style="color:#d63031;font-weight:700">없음</span>') + '</td>' +
        '</tr>').join('') +
      '</tbody></table>';
    return;
  }

  cnt.innerHTML = '인식된 종목 ' + _bulkRows.length + '개' +
    (dupN ? ' (이미 있는 종목 ' + dupN + '개)' : '') +
    (_bulkSkipped ? ' <span style="color:#e17055">· 코드 없는 줄 ' + _bulkSkipped + '개 건너뜀</span>' : '');
  if(!_bulkRows.length){
    el.innerHTML = '<div class="empty">엑셀에서 복사한 내용을 붙여넣으면 여기에 미리보기가 나옵니다</div>';
    return;
  }
  el.innerHTML = '<table><thead><tr><th>종목명</th><th>종목코드</th><th></th></tr></thead><tbody>' +
    _bulkRows.map(r =>
      '<tr class="' + (r.dup ? 'dup' : '') + '">' +
      '<td>' + esc(r.name) + '</td>' +
      '<td>' + esc(r.code) + '</td>' +
      '<td>' + (r.dup ? '이미 있음' : '') + '</td>' +
      '</tr>').join('') +
    '</tbody></table>';
}

function applyBulk(){
  // 확인 모드 — 빠진 종목 목록을 클립보드로
  if(_bulkMode === 'check'){
    const miss = _bulkRows.filter(r => !r.dup);
    if(!miss.length){ alert('빠진 종목이 없습니다 👍'); return; }
    const text = miss.map(r => r.name + '\t' + r.code).join('\n');
    try {
      navigator.clipboard.writeText(text);
      showSaved('📋 빠진 ' + miss.length + '종목 복사됨');
    } catch(e){
      prompt('아래 내용을 복사하세요 (' + miss.length + '종목)', text);
    }
    return;
  }

  if(!_bulkRows.length){ alert('추가할 종목이 없습니다'); return; }
  const sid = document.getElementById('bulk-sector').value;
  const gid = document.getElementById('bulk-group').value;
  const s = _data.sectors.find(x => x.id === sid);
  if(!s){ alert('섹터를 선택하세요'); return; }
  const g = s.groups.find(x => x.id === gid);
  if(!g){ alert('그룹을 선택하거나 + 새 그룹으로 만들어주세요'); return; }

  const existing = new Set(g.stocks.map(x => x.code));
  let added = 0, skipped = 0;
  for(const r of _bulkRows){
    if(existing.has(r.code)){ skipped++; continue; }
    g.stocks.push({code: r.code, name: r.name});
    existing.add(r.code);
    added++;
  }

  if(added === 0){
    alert('추가된 종목이 없습니다.\n' +
          '「' + s.name + ' › ' + g.name + '」에 이미 ' + skipped + '개가 모두 있습니다.');
    return;
  }

  _data.currentSectorId = s.id;
  _expandedBig[g.id] = true;      // 큰 그룹이면 펼쳐서 보이게
  closeBulk();
  render();
  scheduleSave();

  // 어디에 들어갔는지 분명히 알리고 그 위치로 이동
  showSaved('✅ 「' + s.name + ' › ' + g.name + '」에 ' + added + '종목 추가' +
            (skipped ? ' · ' + skipped + '개 중복 제외' : ''));
  setTimeout(() => {
    const el = document.querySelector('[data-group-id="' + g.id + '"]');
    if(el){
      el.scrollIntoView({behavior:'smooth', block:'center'});
      el.style.transition = 'box-shadow .3s';
      el.style.boxShadow = '0 0 0 3px rgba(26,29,35,0.25)';
      setTimeout(() => { el.style.boxShadow = ''; }, 1500);
    }
  }, 100);

  const codes = _bulkRows.map(r => r.code);
  if(codes.length) refreshQuotes(codes, {force:true});
}

// ESC로 닫기
document.addEventListener('keydown', (e) => {
  if(e.key === 'Escape'){
    const ov = document.getElementById('bulk-overlay');
    if(ov && ov.classList.contains('open')) closeBulk();
    const mv = document.getElementById('move-overlay');
    if(mv && mv.classList.contains('open')) closeMove();
    const sv = document.getElementById('stock-overlay');
    if(sv && sv.classList.contains('open')) closeStock();
    const fb = document.getElementById('find-result');
    if(fb) fb.classList.remove('open');
  }
});

// ── 📥 일괄 추가 끝 ───────────────────────

// 🔗 보기 전용 공유 링크 복사
async function copyShareLink(){
  try {
    const res = await fetch('/api/watchlist/share-link');
    const d = await res.json();
    if(!d.ok){
      alert('공유 링크가 아직 설정되지 않았습니다.\n\n' +
            'Railway 환경변수에 WATCHLIST_SHARE_TOKEN 을 추가해주세요.\n' +
            '(아무 긴 문자열이면 됩니다. 예: yenny-watch-9f3k2m)');
      return;
    }
    const url = location.origin + d.path;
    try {
      await navigator.clipboard.writeText(url);
      showSaved('🔗 공유 링크 복사됨 (보기 전용)');
    } catch(e){
      prompt('아래 링크를 복사해서 공유하세요 (보기 전용)', url);
    }
  } catch(e){
    alert('오류: ' + (e.message || e));
  }
}

function initControls(){
  if(_RO){
    document.body.classList.add('readonly');
    document.title = '관심종목 시황 (보기 전용)';
  }
  // 저장된 선택 복원 (새로고침해도 유지)
  try {
    const mk = localStorage.getItem('wl_market');
    if(['UN','J','NX'].includes(mk)) _market = mk;
    const so = localStorage.getItem('wl_sort');
    if(['manual','chg_desc','chg_asc','vol_desc','gap_desc','gap_asc'].includes(so)) _sort = so;
    const vw = localStorage.getItem('wl_view');
    if(['list','rank'].includes(vw)) _view = vw;
    const ss = localStorage.getItem('wl_session');
    if(['auto','pre','after'].includes(ss)) _session = ss;
    const saved = parseInt(localStorage.getItem('wl_cols') || '2', 10);
    if([1,2,3].includes(saved)) _cols = saved;
  } catch(e){}

  document.querySelectorAll('.seg[data-mkt]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-mkt') === _market);
  });
  document.querySelectorAll('.seg[data-sort]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-sort') === _sort);
  });
  document.querySelectorAll('.seg[data-view]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-view') === _view);
  });
  document.querySelectorAll('.seg[data-cols]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-cols') === String(_cols));
  });
  document.querySelectorAll('.seg[data-scope]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-scope') === _rankScope);
  });
  document.querySelectorAll('.seg[data-sess]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-sess') === _session);
  });
  updateNxtOnlyVisible();
  updateNxtSessionVisible();
  // 복원된 뷰에 맞춰 컨트롤 표시
  const tabs = document.getElementById('sector-tabs');
  const flatWrap = document.getElementById('flat-wrap');
  const colsWrap = document.getElementById('cols-wrap');
  const scopeWrap = document.getElementById('rank-scope-wrap');
  const isRank = (_view === 'rank');
  if(tabs) tabs.style.display = isRank ? 'none' : '';
  if(flatWrap) flatWrap.style.display = isRank ? 'none' : '';
  if(colsWrap) colsWrap.style.display = isRank ? 'none' : '';
  if(scopeWrap) scopeWrap.style.display = isRank ? '' : 'none';
  updateMarketHint();
  setInterval(updateMarketHint, 60000);
}

initControls();
loadData();
startAutoRefresh();

// 종목 마스터 백그라운드 예열 (보기 전용에선 불필요)
if(!_RO){
  fetch('/api/watchlist/master-warmup', {method:'POST'}).catch(() => {});
}
</script>
</body>
</html>
"""


def fetch_quotes_naver_bulk(codes: list) -> dict:
    """
    네이버 실시간 API로 여러 종목을 한 번에 조회.
    KIS는 종목당 1요청(초당 20건 제한)이라 종목이 많으면 수십 초 걸리지만,
    이건 한 요청에 수십 종목을 담아서 훨씬 빠름.
    """
    import requests as _rq
    import concurrent.futures

    uniq, seen = [], set()
    for c in codes:
        c = str(c).strip()
        if c and len(c) == 6 and c not in seen:
            seen.add(c)
            uniq.append(c)
    if not uniq:
        return {}

    quotes = {}
    headers = {
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        "Referer": "https://m.stock.naver.com/",
        "Accept": "application/json",
    }

    def _num(v, d=0):
        try:
            return float(str(v).replace(",", "").strip() or d)
        except Exception:
            return d

    def fetch_chunk(chunk):
        joined = ",".join(chunk)
        urls = [
            f"https://polling.finance.naver.com/api/realtime/domestic/stock/{joined}",
            f"https://m.stock.naver.com/api/realtime/domestic/stock/{joined}",
        ]
        for url in urls:
            try:
                r = _rq.get(url, headers=headers, timeout=(3, 6))
                if r.status_code != 200:
                    continue
                data = r.json()
                found = 0

                def walk(node, depth=0):
                    nonlocal found
                    if depth > 6:
                        return
                    if isinstance(node, dict):
                        code = None
                        for ck in ("itemCode", "cd", "code", "stockCode"):
                            v = node.get(ck)
                            if isinstance(v, str) and re.fullmatch(r"[A-Z]?\d{6}", v.strip()):
                                code = v.strip()[-6:]
                                break
                        if code:
                            price = _num(node.get("closePrice") or node.get("nv")
                                         or node.get("currentPrice") or 0)
                            chg = _num(node.get("compareToPreviousClosePrice")
                                       or node.get("cv") or 0)
                            pct = _num(node.get("fluctuationsRatio") or node.get("cr") or 0)
                            vol = _num(node.get("accumulatedTradingVolume")
                                       or node.get("aq") or 0)
                            # 하락 부호 보정
                            sign = str(node.get("compareToPreviousPrice", {}).get("code", "")
                                       if isinstance(node.get("compareToPreviousPrice"), dict)
                                       else node.get("rf", ""))
                            if sign in ("4", "5"):
                                chg = -abs(chg)
                                pct = -abs(pct)
                            if price > 0:
                                quotes[code] = {
                                    "price": int(price),
                                    "chg": int(chg),
                                    "chg_pct": round(pct, 2),
                                    "volume": int(vol),
                                    "market": "J",
                                    "api_name": (node.get("stockName") or node.get("nm") or "").strip(),
                                }
                                found += 1
                            return
                        for v in node.values():
                            walk(v, depth + 1)
                    elif isinstance(node, list):
                        for v in node:
                            walk(v, depth + 1)

                walk(data)
                if found:
                    return
            except Exception as e:
                print(f"[naver bulk] {url[:60]}: {e}")

    # 40종목씩 나눠서 병렬
    chunks = [uniq[i:i+40] for i in range(0, len(uniq), 40)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(chunks))) as ex:
        list(ex.map(fetch_chunk, chunks))

    return quotes


def fetch_stock_quotes(codes: list, kis_get_fn, market: str = "UN",
                       token: str = "", app_key: str = "", app_secret: str = "") -> dict:
    """
    KIS API로 여러 종목 시세 조회 (병렬 + 커넥션 재사용)

    token/app_key/app_secret이 주어지면 requests.Session으로 직접 호출 (훨씬 빠름).
    없으면 kis_get_fn 폴백.

    market: 'J'=KRX, 'NX'=NXT, 'UN'=통합
    """
    import concurrent.futures
    import threading
    import requests as _rq

    if market not in ("J", "NX", "UN"):
        market = "UN"

    quotes = {}
    lock = threading.Lock()

    # 중복 제거 + 유효 코드만
    uniq, seen = [], set()
    for c in codes:
        c = str(c).strip()
        if c and len(c) == 6 and c not in seen:
            seen.add(c)
            uniq.append(c)
    if not uniq:
        return {}

    # ── 빠른 경로: 전역 Session 재사용 ──
    use_session = bool(token and app_key and app_secret)
    session = _get_session(token, app_key, app_secret) if use_session else None

    URL = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price"

    def parse_out(out, code):
        if not out:
            return
        def _i(k, d=0):
            try: return int(float(out.get(k, d) or d))
            except: return d
        def _f(k, d=0.0):
            try: return float(out.get(k, d) or d)
            except: return d
        chg = _i("prdy_vrss")
        chg_pct = _f("prdy_ctrt")
        sign = str(out.get("prdy_vrss_sign", "3"))
        if sign in ("4", "5"):
            chg, chg_pct = -abs(chg), -abs(chg_pct)
        elif sign in ("1", "2"):
            chg, chg_pct = abs(chg), abs(chg_pct)
        with lock:
            quotes[code] = {
                "price": _i("stck_prpr"),
                "chg": chg,
                "chg_pct": chg_pct,
                "volume": _i("acml_vol"),
                "market": market,
                "api_name": (out.get("hts_kor_isnm") or "").strip(),
                "high": _i("stck_hgpr"),
                "low": _i("stck_lwpr"),
                "open": _i("stck_oprc"),
                "prev_close": _i("stck_sdpr"),
            }

    def fetch_one(code):
        import time as _tt
        t0 = _tt.time()
        try:
            if use_session:
                r = session.get(
                    URL,
                    params={"FID_COND_MRKT_DIV_CODE": market, "FID_INPUT_ISCD": code},
                    timeout=(2, 3),
                )
                out = r.json().get("output", {})
            else:
                r = kis_get_fn(
                    "/uapi/domestic-stock/v1/quotations/inquire-price",
                    "FHKST01010100",
                    {"FID_COND_MRKT_DIV_CODE": market, "FID_INPUT_ISCD": code}
                )
                out = r.get("output", {}) if isinstance(r, dict) else {}
            parse_out(out, code)
            el = _tt.time() - t0
            if el > 1.5:
                print(f"[watchlist] ⚠️ {code} 느림 {el:.1f}초")
        except Exception as e:
            print(f"[watchlist] {code} ({market}) 실패 {(_tt.time()-t0):.1f}초: {e}")

    # 워커 — 종목 수에 맞춰 확장 (KIS 초당 20건 제한 고려해 최대 32)
    workers = min(32, max(8, len(uniq)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(fetch_one, uniq))

    return quotes


_krx_close_cache = {"date": "", "prices": {}}    # {code: {price, chg_pct}}
_no_nxt_cache = {"date": "", "codes": set()}     # 오늘 NXT 체결이 없던 종목


def fetch_quotes_with_gap(codes: list, kis_get_fn, market: str = "UN",
                          token: str = "", app_key: str = "", app_secret: str = "",
                          nxt_only: bool = False, session: str = "") -> dict:
    """
    시장별 최적 경로로 시세 조회.

    session: 'pre'  → 전일 KRX 마감가를 괴리 기준으로
             'after'→ 당일 KRX 마감가를 괴리 기준으로
             ''     → 시간으로 자동 판단
    """
    import concurrent.futures
    from datetime import datetime as _dt

    # ⚡ KRX·통합은 네이버 일괄 조회
    if market != "NX":
        q = fetch_quotes_naver_bulk(codes)
        if q:
            for v in q.values():
                v["market"] = market
            missing = [c for c in codes if str(c).strip() not in q]
            if missing and len(missing) <= 30:
                q.update(fetch_stock_quotes(missing, kis_get_fn, market,
                                            token, app_key, app_secret))
            return q
        return fetch_stock_quotes(codes, kis_get_fn, market, token, app_key, app_secret)

    now = _dt.now()
    mins = now.hour * 60 + now.minute
    # 세션 — 명시 지정 우선, 없으면 시간으로 판단
    if session in ("pre", "after"):
        sess = session
        intraday = False          # 수동 지정이면 항상 괴리 계산
    else:
        sess = "pre" if mins < 9 * 60 else "after"
        intraday = (9 * 60) <= mins < (15 * 60 + 40)
    today = now.strftime("%Y-%m-%d") + "-" + sess

    if _krx_close_cache["date"] != today:
        _krx_close_cache["date"] = today
        _krx_close_cache["prices"] = {}
    if _no_nxt_cache["date"] != now.strftime("%Y-%m-%d"):
        _no_nxt_cache["date"] = now.strftime("%Y-%m-%d")
        _no_nxt_cache["codes"] = set()

    codes = [str(c).strip() for c in codes if str(c).strip()]
    # 오늘 NXT 체결이 없던 종목은 KIS 조회에서 제외
    ask_nxt = [c for c in codes if c not in _no_nxt_cache["codes"]]
    skipped = len(codes) - len(ask_nxt)
    if skipped:
        print(f"[watchlist] NXT 미거래 {skipped}종목 스킵")

    # 정규장 중에는 괴리율이 무의미 → NXT만
    if intraday:
        nx = fetch_stock_quotes(ask_nxt, kis_get_fn, "NX", token, app_key, app_secret) if ask_nxt else {}
        for c in ask_nxt:
            if not nx.get(c, {}).get("price"):
                _no_nxt_cache["codes"].add(c)
        out = {}
        for code, q in nx.items():
            q = dict(q)
            q["krx_close"] = 0
            q["gap"] = None
            q["gap_pct"] = None
            q["intraday"] = True
            out[code] = q
        return out

    # ⚡ 괴리율 기준은 '직전 KRX 정규장 마감가'.
    #    프리마켓(장 시작 전) → 전일 종가
    #    애프터마켓(장 마감 후) → 당일 종가
    #    KIS 기준가(stck_sdpr)는 두 세션 모두 '전일 종가'라서 애프터에선 틀림.
    #    → 네이버 일괄 조회로 실제 KRX 종가를 받아 기준으로 삼는다.
    need_krx = [c for c in codes if c not in _krx_close_cache["prices"]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        f_nx = ex.submit(fetch_stock_quotes, ask_nxt, kis_get_fn, "NX",
                         token, app_key, app_secret) if ask_nxt else None
        f_krx = ex.submit(fetch_quotes_naver_bulk, need_krx) if need_krx else None
        nx = f_nx.result() if f_nx else {}
        krx_new = f_krx.result() if f_krx else {}

    # ⚠️ 네이버가 못 준 종목은 KIS 정규장(J)으로 보충.
    #    KIS 기준가(prev_close)는 애프터마켓에서도 '전일 종가'라 괴리 기준으로 쓰면 안 됨.
    miss_krx = [c for c in need_krx if c not in krx_new]
    if miss_krx:
        print(f"[watchlist] 네이버 KRX 미수신 {len(miss_krx)}종목 → KIS(J) 보충")
        krx_kis = fetch_stock_quotes(miss_krx, kis_get_fn, "J",
                                     token, app_key, app_secret)
        for c, k in krx_kis.items():
            if k.get("price"):
                krx_new[c] = k

    for c in ask_nxt:
        if not nx.get(c, {}).get("price"):
            _no_nxt_cache["codes"].add(c)

    # 장중이 아니면 KRX 종가는 더 안 변하므로 캐시해도 안전
    for c, k in krx_new.items():
        if k.get("price"):
            _krx_close_cache["prices"][c] = {
                "price": k["price"], "chg_pct": k.get("chg_pct"),
                "api_name": k.get("api_name", ""),
            }
    krx = dict(_krx_close_cache["prices"])
    krx.update(krx_new)

    out = {}
    # NXT 체결이 있는 종목 — 실제 KRX 마감가 대비 괴리 계산
    for code, q in nx.items():
        if not q.get("price"):
            continue
        q = dict(q)
        k = krx.get(code, {})
        # ⚠️ 반드시 실제 KRX 종가만 기준으로 사용.
        #    KIS 기준가(prev_close)는 애프터마켓에서 전일 종가라 폴백으로 쓰면 안 됨.
        krx_close = k.get("price") or 0
        q["market"] = "NX"
        q["krx_close"] = krx_close
        q["krx_chg_pct"] = k.get("chg_pct")
        q["session"] = sess
        if krx_close:
            gap = q["price"] - krx_close
            q["gap"] = gap
            q["gap_pct"] = round(gap / krx_close * 100, 2)
        else:
            q["gap"] = None
            q["gap_pct"] = None
        out[code] = q

    # NXT 체결이 없는 종목 — KRX 종가 그대로, 괴리 0
    for code, k in krx.items():
        if code in out or not k.get("price"):
            continue
        if code not in codes:
            continue
        out[code] = {
            "price": k["price"],
            "chg": 0,
            "chg_pct": k.get("chg_pct", 0),
            "volume": 0,
            "market": "NX",
            "api_name": k.get("api_name", ""),
            "krx_close": k["price"],
            "gap": 0,
            "gap_pct": 0.0,
            "no_nxt": True,
        }

    return out


def resolve_stock_name(code: str, kis_get_fn) -> str:
    """종목코드 → 종목명 (KIS API)"""
    try:
        r = kis_get_fn(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            "FHKST01010100",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
        )
        out = r.get("output", {}) if isinstance(r, dict) else {}
        return (out.get("hts_kor_isnm") or "").strip()
    except Exception:
        return ""

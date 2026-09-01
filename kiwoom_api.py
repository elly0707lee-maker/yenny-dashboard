"""
키움 REST API 연동
- 토큰 발급/캐시
- 관심종목 그룹 조회 (ka01300 / ka01301)
- 테마 조회 (ka90001 / ka90002)
"""
import os
import time
import requests

KIWOOM_APP_KEY = os.environ.get("KIWOOM_APP_KEY", "")
KIWOOM_APP_SECRET = os.environ.get("KIWOOM_APP_SECRET", "")

# 실전 / 모의
BASE = os.environ.get("KIWOOM_BASE", "https://api.kiwoom.com")

_token_cache = {"token": "", "expires": 0.0}


def has_keys() -> bool:
    return bool(KIWOOM_APP_KEY and KIWOOM_APP_SECRET)


def get_token(force: bool = False) -> str:
    """접근토큰 발급 (24시간 유효, 여유 두고 20시간 캐시)"""
    if not has_keys():
        raise RuntimeError("KIWOOM_APP_KEY / KIWOOM_APP_SECRET 미설정")
    if not force and _token_cache["token"] and time.time() < _token_cache["expires"]:
        return _token_cache["token"]

    url = f"{BASE}/oauth2/token"
    r = requests.post(url, json={
        "grant_type": "client_credentials",
        "appkey": KIWOOM_APP_KEY,
        "secretkey": KIWOOM_APP_SECRET,
    }, headers={"Content-Type": "application/json;charset=UTF-8"}, timeout=10)

    data = {}
    try:
        data = r.json()
    except Exception:
        pass

    token = data.get("token") or data.get("access_token") or ""
    if not token:
        raise RuntimeError(f"토큰 발급 실패 HTTP {r.status_code}: {str(data)[:200] or r.text[:200]}")

    _token_cache["token"] = token
    _token_cache["expires"] = time.time() + 3600 * 20
    return token


def call(api_id: str, body: dict = None, cont_yn: str = "N", next_key: str = "",
         path: str = "/api/dostk/stkinfo") -> dict:
    """
    키움 REST API 공통 호출.
    api_id: TR 코드 (예: ka01300)
    path:   기능군별 엔드포인트 경로
    """
    token = get_token()
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": api_id,
        "cont-yn": cont_yn,
        "next-key": next_key,
    }
    r = requests.post(f"{BASE}{path}", json=(body or {}),
                      headers=headers, timeout=12)
    out = {}
    try:
        out = r.json()
    except Exception:
        out = {"_raw": r.text[:400]}
    out["_status"] = r.status_code
    out["_cont_yn"] = r.headers.get("cont-yn", "")
    out["_next_key"] = r.headers.get("next-key", "")
    return out


THEME_PATH = "/api/dostk/thme"

_theme_cache = {"key": "", "at": 0.0, "items": []}


def get_themes(date_tp: str = "1", sort: str = "0", force: bool = False) -> list:
    """
    인포스탁 테마 목록 + 등락률 (ka90001)

    date_tp: 기간 (1~99일)
    sort: 0=전체, 1=상위등락률, 2=하위등락률, 3=상위기간수익률, 4=하위기간수익률
    """
    key = f"{date_tp}|{sort}"
    if not force and _theme_cache["key"] == key and (time.time() - _theme_cache["at"]) < 120:
        return _theme_cache["items"]

    items, cont, nkey = [], "N", ""
    for _ in range(6):          # 페이지 최대 6회
        r = call("ka90001", {
            "qry_tp": sort,
            "date_tp": str(date_tp),
            "flu_pl_amt_tp": "1",
            "stex_tp": "1",
        }, cont_yn=cont, next_key=nkey, path=THEME_PATH)
        if r.get("return_code") not in (0, "0"):
            break
        for t in (r.get("thema_grp") or []):
            items.append({
                "code": (t.get("thema_grp_cd") or "").strip(),
                "name": (t.get("thema_nm") or "").strip(),
                "count": _to_int(t.get("stk_num")),
                "chg_pct": _to_float(t.get("flu_rt")),
                "up": _to_int(t.get("rising_stk_num")),
                "down": _to_int(t.get("fall_stk_num")),
                "period_pct": _to_float(t.get("dt_prft_rt")),
                "main": (t.get("main_stk") or "").strip(),
            })
        if r.get("_cont_yn") != "Y" or not r.get("_next_key"):
            break
        cont, nkey = "Y", r.get("_next_key")

    if items:
        _theme_cache["key"] = key
        _theme_cache["at"] = time.time()
        _theme_cache["items"] = items
    return items


def get_theme_stocks(theme_code: str, date_tp: str = "1") -> list:
    """테마 구성 종목 (ka90002)"""
    out, cont, nkey = [], "N", ""
    for _ in range(4):
        r = call("ka90002", {
            "date_tp": str(date_tp),
            "thema_grp_cd": str(theme_code),
            "stex_tp": "1",
        }, cont_yn=cont, next_key=nkey, path=THEME_PATH)
        if r.get("return_code") not in (0, "0"):
            out.append({"_error": r.get("return_msg"), "_keys": list(r.keys())})
            break
        # 응답 배열 키 이름이 버전마다 다를 수 있어 리스트를 찾아서 사용
        arr = None
        for k, v in r.items():
            if k.startswith("_"):
                continue
            if isinstance(v, list) and v and isinstance(v[0], dict):
                arr = v
                break
        for s in (arr or []):
            code = ""
            for ck in ("stk_cd", "stk_code", "code"):
                v = s.get(ck)
                if isinstance(v, str) and v.strip():
                    code = v.strip()[-6:]
                    break
            name = ""
            for nk in ("stk_nm", "stk_name", "name"):
                v = s.get(nk)
                if isinstance(v, str) and v.strip():
                    name = v.strip()
                    break
            if not code:
                continue
            out.append({
                "code": code,
                "name": name or code,
                "price": _to_int(s.get("cur_prc")),
                "chg_pct": _to_float(s.get("flu_rt")),
                "volume": _to_int(s.get("acc_trde_qty") or s.get("trde_qty")),
            })
        if r.get("_cont_yn") != "Y" or not r.get("_next_key"):
            break
        cont, nkey = "Y", r.get("_next_key")
    return out


def _to_int(v, d=0):
    try:
        return int(float(str(v).replace(",", "").replace("+", "").strip() or d))
    except Exception:
        return d


def _to_float(v, d=0.0):
    try:
        return float(str(v).replace(",", "").replace("+", "").strip() or d)
    except Exception:
        return d


def diagnose() -> dict:
    """연결 진단 — 어디까지 되는지 단계별 확인"""
    out = {"keys_set": has_keys(), "base": BASE}
    if not has_keys():
        out["error"] = "KIWOOM_APP_KEY / KIWOOM_APP_SECRET 환경변수가 없습니다"
        return out
    # 1) 토큰
    try:
        t = get_token(force=True)
        out["token"] = "발급 성공 (" + t[:12] + "...)"
    except Exception as e:
        out["token"] = f"실패: {str(e)[:300]}"
        return out
    # 2) 관심종목 그룹 목록
    for label, api_id, path, body in [
        ("관심종목 그룹", "ka01300", "/api/dostk/stkinfo", {"qry_tp": "1"}),
        ("테마 그룹", "ka90001", "/api/dostk/thme",
         {"qry_tp": "0", "date_tp": "1", "flu_pl_amt_tp": "1", "stex_tp": "1"}),
    ]:
        try:
            r = call(api_id, body, path=path)
            keys = [k for k in r.keys() if not k.startswith("_")]
            out[label] = {
                "status": r.get("_status"),
                "return_code": r.get("return_code"),
                "return_msg": r.get("return_msg"),
                "keys": keys[:12],
                "sample": str({k: r[k] for k in keys[:3]})[:400],
            }
        except Exception as e:
            out[label] = f"실패: {str(e)[:200]}"
    return out

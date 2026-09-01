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

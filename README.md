# Yenny Dashboard

머니플러스 앵커 이예은의 방송 준비 대시보드.

## 기능
- 국내외 실시간 시장 지수 (코스피, 코스닥, 나스닥, 다우, WTI, 원달러, VIX)
- 미증시 브리핑 자동 생성 (Claude AI)
- 텔레그램 봇 연동 체크포인트 표시
- 텔레그램 봇 연동 마감일지 표시

## Railway 환경변수 설정

| 변수명 | 설명 |
|--------|------|
| `KIS_APP_KEY` | 한국투자증권 오픈API 앱키 |
| `KIS_APP_SECRET` | 한국투자증권 오픈API 앱시크릿 |
| `ANTHROPIC_API_KEY` | Anthropic API 키 |
| `DASHBOARD_PASSWORD` | 대시보드 접속 비밀번호 (기본: yenny2026) |
| `API_SECRET` | 봇에서 데이터 올릴 때 사용하는 시크릿 (기본: moneyplus) |

## 텔레그램 봇 연동

봇에서 아래 엔드포인트로 POST 요청을 보내면 대시보드에 표시됩니다.

```
POST https://[대시보드URL]/api/post/checkpoint
POST https://[대시보드URL]/api/post/closing

Headers:
  X-API-Secret: [API_SECRET 값]

Body:
  {
    "content": "내용",
    "date": "2026-04-08"
  }
```

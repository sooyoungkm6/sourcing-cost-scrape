---
name: domestic-sourcing-scrape
description: 수집 방식 ① 국내 도구 — 도매꾹·도매매(오픈API) 저장 도구를 실행해 스키마① 원가 CSV를 만든다. This skill should be used when the user asks to "도매꾹 가격 뽑아줘", "도매매 알아봐", "국내 도매가", "국내 소싱처".
argument-hint: "[검색어] [--detail-top N]"
---

# domestic-sourcing-scrape — 국내 도매처 수집 (수집 방식 ①)

> 실행 = **저장된 파이썬 도구**가 끝까지 돈다. 사람 개입 없음(계정은 `.env`). 산출 = `output/{D}-{소싱처}-{T}.csv`
> (스키마①, `pattern`=①). 수집하는 소싱처와 접속 방법은 `.claude/references/sourcing-channels.md` 에 있다.
> 열 정의는 `research-output-schema.md` 스키마①.
> ⛔ API 키는 `.env`에만 둔다. 키 값을 화면에 출력하거나 채팅으로 주고받지 않는다.
> `.env`가 없으면 `.env.example`을 복사해 `.env`를 만들고, 그 파일에 도매꾹 API 키를 직접 넣어 달라고 안내한다.

## 도매꾹 · 도매매 (오픈API)

```
python3 tools/tool-domeggook-sourcing.py --keyword {검색어} --with-detail --sort rd --sz 30 --pages 1 --detail-top 30            # 도매꾹
python3 tools/tool-domeggook-sourcing.py --keyword {검색어} --with-detail --sort rd --sz 30 --pages 1 --detail-top 30 --market supply   # 도매매 (같은 API·같은 .env DOMEGGOOK_API_KEY, market 값만 다름)
  → getItemView selectOpt로 옵션(규격)별 행 분리 자동. MOQ·배송비 포함.
  ⭐ 수집 기준 = **랭킹순(`--sort rd`) 상위 상품 30 + 그 30개 전부 상세**.
    이유: 옵션은 상세에서만 보인다 — 상세 밖 상품은 규격이 비어 상품명으로 짐작하게 된다. 그리고 «어디서 자르나»가 중앙값을 바꾼다 — 소싱처끼리 비교하려면 같은 자리에서 자른다.
    ⚠️ 도구 기본값(`--sort aa` 낮은가격순 · `--detail-top 20`)과 다르니 실행 명령에 위 값을 준다.
⛔ 도매꾹과 도매매는 source·파일명이 갈린다 — 한 CSV에 섞지 않는다(도매매는 배송대행 B2B라 판매단위가 1이고, 같은 상품도 단가가 같거나 더 높다).
```

## 산출 확인

- 각 CSV의 행수·최저·최고·중앙값은 **파일에서 읽어** 보고한다(API 응답 건수 ≠ CSV 행수 — 중복·무단가 제거).

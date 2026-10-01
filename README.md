# sourcing-cost-scrape

**품목명 하나로 국내·해외·거래처 세 경로에서 원가를 모으는, Claude Code에 설치해 쓰는 스킬 3개입니다.**

- **국내 도구** (`domestic-sourcing-scrape`) — 도매꾹·도매매 오픈API에서 상품별·옵션별 단가를 수집합니다.
- **해외 명세** (`intl-sourcing-scrape`) — alibaba·1688 상세페이지를 Claude가 직접 읽어 원가를 수집합니다.
- **거래처 단가표** (`pricebook-update`) — 거래처가 메일로 보낸 단가표 PDF를 받아 정리합니다.

세 스킬 모두 **원가를 모으는 것까지**입니다. 경쟁사 판매가 조사·마진 계산은 이 팩에 없습니다.

- **실행 주체** — Claude Code가 스킬 문서를 읽고 도구를 실행한 뒤 결과를 보고합니다. 국내 도구는 터미널에서 스크립트를 직접 실행해도 됩니다.
- **공통 산출 형식** — 세 스킬 모두 같은 16열 CSV(`output/{YYYYMMDD}-{소싱처}-{품목명}.csv`, `pattern` 열로 ①②③ 구분)를 씁니다. 열 정의는 `research-output-schema.md`가 정본입니다.

## 무엇이 들어 있나

| | 국내 도구 | 해외 명세 | 거래처 단가표 |
|---|---|---|---|
| 스킬 | `domestic-sourcing-scrape` | `intl-sourcing-scrape` | `pricebook-update` |
| 소싱처 | 도매꾹·도매매 | alibaba·1688 | 거래처 메일 |
| 실행 방식 | 저장된 파이썬 도구가 오픈API 호출 | **저장된 코드 없음** — Claude가 playwright-mcp로 페이지를 직접 읽는다(SKILL.md 자체가 실행 명세) | 저장된 도구 3개(받기→판정→정규화)를 순서대로 |
| 준비물 | 도매꾹 오픈API 키 | playwright-mcp + 1688 로그인 시 본인 SMS 인증 | 네이버 메일 앱 비밀번호 + 거래처 표 채우기 |
| 사람 개입 | 없음 | 배대지 요금 기준(kg/CBM) 확인 질문 1회 | 새 거래처 첫 확인 1회, 그 뒤 자동 |

- **스킬 3개** — `.claude/skills/domestic-sourcing-scrape/`·`intl-sourcing-scrape/`·`pricebook-update/` (각 `SKILL.md`)
- **코드 5개** — `tool-domeggook-sourcing.py`·`schema_loader.py`(국내) · `tool-naver-mail-fetch.py`·`tool-pricebook-intake.py`·`tool-pricebook-parse.py`(거래처 단가표) · `vendor_registry.py`(거래처 문서 읽기, 단가표 스킬이 씀) · `ocr-vision.js`(단가표 표지 OCR, macOS 전용)
- **참조 문서 2개** — `sourcing-channels.md`(소싱처 레지스트리) · `research-output-schema.md`(출력 스키마 정의)
- **견본 4개** — `examples/`에 도매꾹·도매매 CSV 각 1개 + 거래처 단가표용 읽기 설정·품명 대응표 견본 각 1개

## 설치 (최초 1회, 공통)

### 필요한 것

| 필요 | 확인 | 비고 |
|---|---|---|
| Claude Code | — | 스킬 호출용. 국내 도구를 터미널 직접 실행만 할 경우 불필요 |
| Python 3 | `python3 --version` | 국내 도구·메일 받기는 표준 라이브러리만. **거래처 단가표를 쓰면** `python3 -m pip install -r requirements.txt`(pdfplumber 하나) 필요. 3.14.4에서 실행 확인 |
| 도매꾹 오픈API 키 | — | 국내 도구를 쓸 때만. openapi.domeggook.com → 도매꾹 아이디로 로그인 → API 키 발급·관리 |
| 네이버 메일 앱 비밀번호 | — | 거래처 단가표를 쓸 때만. 네이버 메일 환경설정 → POP3/IMAP 사용 ON → 앱 비밀번호 발급 |
| 1688 계정 | — | 해외 명세에서 1688을 쓸 때만(alibaba는 로그인 불필요). 검색 시점에 본인이 직접 SMS 인증 |

세 스킬 다 안 쓸 계획이면 해당 항목은 건너뛰어도 됩니다 — 준비물이 없는 스킬만 그 자리에서 안내 메시지를 내고 멈춥니다.

### 절차

1. 빈 폴더를 하나 만들고 Claude Code로 그 폴더를 엽니다.
2. 이 저장소 링크(`https://github.com/sooyoungkm6/sourcing-cost-scrape.git`)를 주고 **"이 저장소를 현재 폴더에 클론하고 쓸 수 있게 세팅해 줘"**라고 요청합니다.
3. 세팅이 끝나면 `.env`를 열어 쓸 스킬의 값만 채웁니다 — `DOMEGGOOK_API_KEY`(국내 도구) · `NAVER_LOGIN_ID`·`NAVER_MAIL_APP_PW`(거래처 단가표).
4. 거래처 단가표를 쓸 계획이면 `python3 -m pip install -r requirements.txt`로 pdfplumber를 설치하고, `sourcing-channels.md`의 소싱처 레지스트리 ③ 줄에 거래처 정식 상호·메일 주소를 먼저 적습니다(아래 "거래처 단가표" 절 참조).
5. 스킬이 목록에 보이지 않으면 Claude Code를 다시 시작합니다.

```
(내가 만든 폴더)/
├─ .claude/
│   ├─ skills/domestic-sourcing-scrape/SKILL.md
│   │        intl-sourcing-scrape/SKILL.md
│   │        pricebook-update/SKILL.md
│   └─ references/
│       ├─ sourcing-channels.md      ← 거래처 단가표를 쓰려면 ③ 줄을 채운다
│       └─ research-output-schema.md
├─ tools/
│   ├─ tool-domeggook-sourcing.py · schema_loader.py             ← 국내 도구
│   ├─ tool-naver-mail-fetch.py · tool-pricebook-intake.py
│   │   tool-pricebook-parse.py · vendor_registry.py · ocr-vision.js   ← 거래처 단가표
├─ examples/            ← 견본 4개(그대로 저장소에 들어 있음)
├─ .env.example
├─ .env                 ← 세팅 때 만들어지는 파일(.env.example 을 복사해 만든 것)
├─ requirements.txt     ← 거래처 단가표를 쓸 때만 설치(pdfplumber)
└─ output/              ← 실행하면 생기는 폴더. 수집 결과 CSV
```

### 에이전트용 셋업 안내

> 이 절은 위 요청("클론하고 세팅해 줘")을 받은 에이전트에게 하는 말입니다. 사용자는 이 저장소 링크와 요청 한 줄만 주면 됩니다.

- 저장소를 **현재 폴더 바로 아래에** 받는다 — 하위 폴더를 새로 만들지 않는다. `.claude/`가 이 폴더 바로 아래에 있어야 스킬로 인식된다.
- `.env.example`을 복사해 `.env`를 만든다. 값은 전부 비워 둔다. **키·비밀번호 값은 사용자가 직접 입력한다 — 채팅으로 받거나 화면에 출력하지 않는다.**
- 사용자가 거래처 단가표를 쓸 계획이면 `python3 -m pip install -r requirements.txt`를 실행한다(국내 도구·메일 받기만 쓸 계획이면 건너뛴다).
- 검증: `python3 tools/tool-domeggook-sourcing.py --help` · `tools/tool-naver-mail-fetch.py --help` · `tools/tool-pricebook-intake.py --help` 종료 코드 0.
- 스킬이 목록에 보이지 않으면 Claude Code를 다시 시작해 달라고 안내한다.
- 보고: 클론 결과, `.env` 처리 결과(값은 출력하지 않는다), 검증 명령의 결과.

## 사용법

### 국내 도구 — 도매꾹·도매매

```
/domestic-sourcing-scrape [품목명]
```

1. 도매꾹 — 검색 결과 상위 30개 상품 조회(`getItemList`) → 그 30개 전부 상세 조회(`getItemView`) → 옵션별로 행 분리.
2. 도매매 — 같은 스크립트에 `--market supply`를 붙여 같은 절차로 한 번 더.
3. `output/{YYYYMMDD}-도매꾹-{품목명}.csv` · `output/{YYYYMMDD}-도매매-{품목명}.csv`로 저장하고, 다시 읽어 저장 행수·상품 수·단가 최저·중앙값·최고를 보고합니다.

도매꾹이 공식 제공하는 오픈API만 호출합니다 — 웹 스크래핑·로그인·브라우저 자동화는 없습니다.

터미널 직접 실행:

```bash
python3 tools/tool-domeggook-sourcing.py --keyword "[품목명]" --with-detail --sort rd --sz 30 --pages 1 --detail-top 30                   # 도매꾹
python3 tools/tool-domeggook-sourcing.py --keyword "[품목명]" --with-detail --sort rd --sz 30 --pages 1 --detail-top 30 --market supply   # 도매매
```

옵션·출력 CSV 16열 정의는 `.claude/skills/domestic-sourcing-scrape/SKILL.md`와 `research-output-schema.md`를 참조하세요.

### 해외 명세 — alibaba·1688

```
/intl-sourcing-scrape [품명 또는 영문/중문 키워드]
```

이 스킬은 저장된 코드가 없습니다 — Claude가 playwright-mcp로 alibaba·1688 페이지를 직접 열어 `SKILL.md`에 적힌 규칙대로 읽습니다.

1. 시작 전 질문 하나 — 배대지(국제배송 대행) 요금이 kg 기준인지 CBM(부피) 기준인지 물어서, 상세페이지 재방문 없이 필요한 값만 한 번에 뽑습니다.
2. alibaba 먼저(로그인 불필요), 그다음 1688(원칙상 본인 SMS 인증 필요 — 브라우저에 기존 로그인이 남아 있으면 생략될 수 있습니다). 검색 상위 30상품 + 그 30개 전부 상세.
3. 가격이 수량구간별로 달라지는 **사다리형**과 규격별로 달라지는 **규격형**을 판별해 행을 쪼갭니다 — 한 행에 범위를 우겨넣지 않습니다.
4. `output/{YYYYMMDD}-alibaba-{품명}.csv` · `output/{YYYYMMDD}-1688-{품명}.csv`로 저장.

가격 모델 판별 로직·규격 단위(mm) 정규화 규칙은 `.claude/skills/intl-sourcing-scrape/SKILL.md`에 자세히 적혀 있습니다.

### 거래처 단가표

```
/pricebook-update [거래처명]
```

거래처가 메일로 보낸 단가표 PDF를 받아 정리합니다. **먼저 할 일** — `sourcing-channels.md`의 소싱처 레지스트리 ③ 줄에 거래처 정식 상호와 단가표를 보내는 메일 주소를 적습니다. 도구는 이 문서에 적힌 거래처만 찾습니다.

1. `tool-naver-mail-fetch.py` — 네이버 메일함(IMAP)에서 문서에 적힌 거래처가 보낸 메일만 찾아 첨부를 받습니다. 제목 키워드로 찾지 않습니다(고객 견적 문의 등이 섞여 들어오는 것을 막기 위해서입니다).
2. `tool-pricebook-intake.py` — 받은 파일마다 자동 판정합니다: ✅ 확실한 단가표는 자동 이동, 🗄 오래된 판은 보관만, ⏭ 같은 시행일의 중복본은 건너뜀, ❓ 애매한 건만 사용자 확인, ⛔ 단가표가 아닌 파일은 그대로 둡니다. **새 거래처는 첫 확인 한 번**(표본 10행 + 자체 검사, 질문 하나)만 거치면 그 뒤로 자동입니다.
3. `tool-pricebook-parse.py` — 거래처별 정규화 CSV를 갱신합니다. 표 양식이 기본 방식으로 안 읽히는 거래처만 `examples/견본-거래처-읽기-설정.json`·`견본-거래처-품명-대응표.csv`를 참고해 설정 파일을 만들면 됩니다.
4. 교차 대조 — `tool-pricebook-parse.py --lookup {품명}`으로 이미 확보한 거래처 단가 중 최저가를 바로 조회할 수 있습니다.

스캔본·손글씨 단가표는 읽지 못합니다 — PDF(글자가 선택되는 것)나 엑셀로 받아야 합니다. 엑셀 단가표 읽기는 아직 구현돼 있지 않습니다.

## 저장소 구성

```
.claude/skills/
  domestic-sourcing-scrape/SKILL.md   국내 도구 — 실행 명령·수집 기준·산출 확인 절차
  intl-sourcing-scrape/SKILL.md       해외 명세 — 실행 명세(저장된 코드 없음, 이 문서 자체가 실행 절차)
  pricebook-update/SKILL.md           거래처 단가표 — 절차 3단계·읽기 설정 설명
.claude/references/
  sourcing-channels.md                소싱처 레지스트리 — ①②③ 수집 방식 표 + 거래처 ③ 줄(받는 분이 채운다)
  research-output-schema.md           출력 스키마 정의 — 16열(스키마①)의 이름·의미·예시
tools/
  tool-domeggook-sourcing.py          국내 도구 — 도매꾹·도매매 오픈API 호출, 옵션별 행 분리
  schema_loader.py                    국내 도구가 import — 스키마 문서에서 CSV 머리글을 읽는다
  tool-naver-mail-fetch.py            거래처 단가표 1단계 — 메일 받기
  tool-pricebook-intake.py            거래처 단가표 2단계 — 판정·이동
  tool-pricebook-parse.py             거래처 단가표 3단계 — 정규화 + 교차 대조(--lookup)
  vendor_registry.py                  거래처 문서(sourcing-channels.md ③ 줄) 읽기 — 위 세 도구가 import
  ocr-vision.js                       단가표 표지가 이미지일 때 macOS 내장 OCR로 읽는다
examples/                             견본 4개 — 도구를 돌리면 나오는 것과 같은 모양
.env.example                          환경 변수 템플릿
output/                               수집 결과 — 실행하면 생기는 폴더(git 제외)
```

**참조 문서와 도구의 관계**

- `sourcing-channels.md`의 소싱처 표는 **국내·해외 두 방식은 기록용**입니다 — 행을 추가·수정해도 그 스킬의 수집 대상은 바뀌지 않습니다(수집 대상은 각 도구의 인자로만 정해집니다). **거래처 단가표(③)는 다릅니다** — 이 문서의 ③ 줄이 실제 설정값입니다. 도구가 이 표에서 거래처 이름·메일 주소를 읽습니다.
- `research-output-schema.md`는 CSV 머리글의 정본입니다. 국내 도구는 `schema_loader.py`가 실행 시 이 문서에서 열 이름을 읽어 씁니다.

### 출력 CSV — 16열 (스키마①, 공통)

세 스킬 모두 같은 16열을 씁니다. `pattern` 열로 어느 방식에서 나왔는지 구분합니다(① 국내 · ② 해외 · ③ 거래처).

| 열 | 내용 |
|---|---|
| `source` | 소싱처(`도매꾹`·`도매매`·`alibaba.com`·`1688`·거래처 정식 상호) |
| `pattern` | 수집 방식 번호(①②③) |
| `item` | 상품명 |
| `origin` | 원산지(국내 도구만 채움) |
| `material` | 재질 |
| `spec` | 규격 |
| `manufacturer` | 제조사/브랜드 |
| `unit_price_krw` | 판매단위당 단가(원) |
| `moq` | 최소 주문 수량 |
| `currency_orig` / `price_orig` | 원통화 / 원통화 가격(해외는 USD·CNY, 국내는 공란) |
| `effective_cost_note` | 원가 관련 부가 정보(배송비·프로모션가·실패 사유 등) |
| `source_ref` | 출처 URL 또는 파일 경로 |
| `collected_at` | 수집일 |
| `weight_g` / `volume_cm3` | 개당 중량·부피(해외 명세만 채움 — 국제 운임 계산용) |

전체 열 정의·예시는 `research-output-schema.md`가 정본입니다.

## .gitignore 정책

| 패턴 | 이유 |
|---|---|
| `.env` · `.env.*`(`.env.example` 제외) | API 키·비밀번호는 올리지 않고 템플릿만 올린다 |
| `output/` | 수집 결과는 제3자(판매자·거래처)의 상품·가격 정보라 올리지 않는다. 폴더 자체가 팩에 없고 실행하면 생긴다 |
| `.claude/references/sourcing-prices/` | 거래처 단가표 원본·정규화 CSV — 거래처 실거래가라 올리지 않는다 |
| `__pycache__/` · `*.pyc` | 파이썬 컴파일 캐시 |

## 안전 규칙

API 키·메일 비밀번호는 `.env`에만 넣습니다 — 코드나 커밋에 직접 적지 않습니다. 거래처 단가표 도구는 화면에 계정 아이디를 표시할 때 앞 두 글자만 보여주고, 비밀번호는 "있음/없음"만 표시합니다.

## 알려진 한계

- 거래처 단가표: 엑셀 단가표 읽기 미구현. 표 머리글이 규격이 아닌 형태(목록형 표)는 일부 거래처에서 아직 지원하지 않습니다. 스캔본·손글씨는 읽지 못합니다.
- 해외 명세: 페이지 구조가 바뀌면(alibaba·1688이 자체 개편) `SKILL.md`의 데이터 읽기 경로도 함께 갱신이 필요할 수 있습니다.

## 라이선스

MIT.

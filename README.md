# domestic-sourcing-scrape

**품목명을 입력하면 도매꾹·도매매 오픈API에서 상품별·옵션별 도매 단가를 수집해 CSV 파일로 저장하는, Claude Code에 설치해 쓰는 스킬입니다.**

- **역할** — 국내 도매몰(도매꾹·도매매)의 원가 수집. 검색 결과 상위 30개 상품과 그 30개 상품의 상세 정보를 조회해, 옵션(규격)마다 상품명·원산지·제조사·판매단위당 단가·최소주문수량·배송비를 한 행으로 기록합니다.
- **구성** — `SKILL.md`(스킬 문서) · `tool-domeggook-sourcing.py`(수집 스크립트) · `schema_loader.py`(스키마 로더 모듈) · `sourcing-channels.md`·`research-output-schema.md`(참조 문서).
- **실행 주체** — Claude Code가 스킬 문서를 읽고 스크립트를 실행한 뒤 결과를 보고합니다. 터미널에서 스크립트를 직접 실행해도 됩니다.

## 시작하기 전에

도매꾹이 공식 제공하는 오픈API(`getItemList`·`getItemView`)만 호출합니다. 웹 페이지 스크래핑·로그인·브라우저 자동화는 없습니다. 1회 실행의 호출 수는 목록 조회 1회 + 상세 조회 최대 30회입니다. 수집 결과는 재배포하지 않고 자체 원가 검토에만 씁니다.

## 무엇이 들어 있나

- **스킬 1** — `SKILL.md`
- **코드 2** — `tool-domeggook-sourcing.py`(수집 스크립트) · `schema_loader.py`(스키마 로더 모듈)
- **참조 문서 2** — `sourcing-channels.md`(소싱처 레지스트리) · `research-output-schema.md`(출력 스키마 정의)
- **견본 2** — `examples/`의 CSV 2개(도매꾹·도매매 각 1개)

경쟁가 조사·마진 계산은 이 팩에 없습니다. 도매꾹·도매매에서 원가를 수집하는 것까지입니다.

## 사용법 (설치 후)

```
/domestic-sourcing-scrape [품목명]
```

Claude Code가 수행하는 순서:

1. `SKILL.md`와 참조 문서 2개(`sourcing-channels.md`·`research-output-schema.md`)를 읽습니다.
2. 도매꾹 — 검색 결과를 랭킹순으로 상위 30개 상품 조회(`getItemList`) → 그 30개 상품 전부의 상세 조회(`getItemView`) → 옵션별로 행 분리.
3. 도매매 — 같은 스크립트에 `--market supply`를 붙여 같은 절차로 한 번 더 실행.
4. 결과를 아래 두 파일로 저장하고, 저장한 파일을 다시 읽어 **저장 행수 · 상품 수 · 판매단위당 단가 최저·중앙값·최고**를 보고합니다.

```
output/{YYYYMMDD}-도매꾹-{품목명}.csv
output/{YYYYMMDD}-도매매-{품목명}.csv
```

`output/` 폴더가 없으면 스크립트가 만듭니다. 도매꾹과 도매매는 `source` 값과 파일이 분리됩니다(도매매는 배송대행 B2B라 판매단위가 1이고, 같은 상품도 단가가 같거나 더 높습니다).

## 설치 (최초 1회)

### 필요한 것

| 필요 | 확인 | 비고 |
|---|---|---|
| Claude Code | — | 스킬 호출용. 터미널 직접 실행만 할 경우 불필요 |
| Python 3 | `python3 --version` | 표준 라이브러리만 사용(`pip install` 없음). 3.14.4에서 실행 확인 |
| 도매꾹 오픈API 키 | — | openapi.domeggook.com → 도매꾹 아이디로 로그인 → API 키 발급·관리. 도매매도 같은 키 |

### 절차

1. 빈 폴더를 하나 만들고 Claude Code로 그 폴더를 엽니다.
2. 이 저장소 링크(`https://github.com/sooyoungkm6/domestic-sourcing-scrape.git`)를 주고 **"이 저장소를 현재 폴더에 클론하고 쓸 수 있게 세팅해 줘"**라고 요청합니다.
3. 세팅이 끝나면 발급받은 도매꾹 API 키를 `.env`의 `DOMEGGOOK_API_KEY=` 뒤에 입력합니다.
4. 스킬이 목록에 보이지 않으면 Claude Code를 다시 시작합니다.

```
(내가 만든 폴더)/
├─ .claude/
│   ├─ skills/domestic-sourcing-scrape/SKILL.md
│   └─ references/
│       ├─ sourcing-channels.md
│       └─ research-output-schema.md
├─ tools/
│   ├─ tool-domeggook-sourcing.py
│   └─ schema_loader.py
├─ examples/            ← 견본 CSV 2개(그대로 저장소에 들어 있음)
├─ .env.example
├─ .env                 ← 세팅 때 만들어지는 파일(.env.example 을 복사해 만든 것 — DOMEGGOOK_API_KEY)
└─ output/              ← 실행하면 생기는 폴더. 수집 결과 CSV
```

### 에이전트용 셋업 안내

> 이 절은 위 요청("클론하고 세팅해 줘")을 받은 에이전트에게 하는 말입니다. 사용자는 이 저장소 링크와 요청 한 줄만 주면 됩니다.

- 저장소를 **현재 폴더 바로 아래에** 받는다 — 하위 폴더를 새로 만들지 않는다. `.claude/`가 이 폴더 바로 아래에 있어야 스킬로 인식된다.
- `.env.example`을 복사해 `.env`를 만든다. `DOMEGGOOK_API_KEY=` 뒤 값은 비워 둔다. **키 값은 사용자가 직접 입력한다 — 채팅으로 받거나 화면에 출력하지 않는다.**
- 검증: `python3 tools/tool-domeggook-sourcing.py --help` 종료 코드 0.
- 사용자가 키를 입력한 뒤에는 `--keyword "[품목명]" --sz 5 --pages 1`로 1회 실행해 `output/`에 CSV가 생기는지 확인한다.
- 스킬이 목록에 보이지 않으면 Claude Code를 다시 시작해 달라고 안내한다.
- 보고: 클론 결과, `.env` 처리 결과(값은 출력하지 않는다), 검증 명령의 결과.

## 저장소 구성

```
.claude/skills/domestic-sourcing-scrape/SKILL.md   스킬 문서 — 실행 명령·수집 기준·산출 확인 절차
.claude/references/
  sourcing-channels.md                             소싱처 레지스트리 — 도매꾹·도매매 소싱처 표
  research-output-schema.md                        출력 스키마 정의 — 스키마①(소싱 원가) 16열의 이름·의미·예시
tools/
  tool-domeggook-sourcing.py                       수집 스크립트 — 도매꾹 오픈API 호출, 옵션별 행 분리, CSV 저장
  schema_loader.py                                 파이썬 모듈 — 수집 스크립트가 import 해 스키마 문서에서 CSV 머리글을 읽는다
examples/                                          견본 CSV 2개 — 도구를 돌리면 나오는 것과 같은 모양
.env.example                                       환경 변수 템플릿 (DOMEGGOOK_API_KEY)
output/                                            수집 결과 — 실행하면 생기는 폴더(git 제외)
```

**참조 문서와 스크립트의 관계**

- `sourcing-channels.md`의 소싱처 표에는 도매꾹·도매매 2행이 기재돼 있습니다. **이 표는 기록용 문서입니다 — 행을 추가·수정해도 이 스킬의 수집 대상은 바뀌지 않습니다.** 수집 대상은 스크립트의 `--market` 값(`dome`·`supply`)으로만 정해집니다.
- `research-output-schema.md`는 CSV 머리글의 정본입니다. `schema_loader.py`가 실행 시 이 문서의 스키마① 표에서 열 이름을 읽어 머리글로 씁니다. 문서를 찾지 못하면 경고를 출력하고 모듈에 내장된 같은 16열을 씁니다. ⚠️ **열의 개수와 순서는 바꾸지 않습니다** — 스크립트가 값을 열 순서대로 기록합니다.

### 출력 CSV — 16열 (스키마①)

옵션이 있는 상품은 옵션 1개 = 1행, 옵션이 없는 상품은 상품 1개 = 1행입니다.

| 열 | 내용 | 이 스킬에서의 값 |
|---|---|---|
| `source` | 소싱처 | `도매꾹` 또는 `도매매`(`--market`으로 지정) |
| `pattern` | 수집 방식 번호 | `①` 국내 도구 고정 |
| `item` | 상품명 | 목록 조회(`getItemList`)의 `title`(상품명 원문) |
| `origin` | 원산지 | 상세 조회(`getItemView`)의 `detail.country`를 `국내산` / `{국가}(수입)` 형태로 변환한 값 |
| `material` | 재질 | 공란(API가 제공하지 않음) |
| `spec` | 규격 | 옵션이 있으면 옵션명(`selectOpt`) + `(옵션)`(예: `315pcs(옵션)`). 옵션이 없으면 상세 조회의 `detail.size` 값 — `0`·`해당없음`처럼 의미 없는 값이면 공란(추정해 채우지 않음) |
| `manufacturer` | 제조사/브랜드 | 상세 조회의 `detail.manufacturer`(값이 없거나 `해당없음`이면 공란) |
| `unit_price_krw` | 판매단위당 단가(원) | 목록 조회의 `price`. 옵션이 있으면 옵션 추가금(`selectOpt`의 `domPrice`)을 더한 값 |
| `moq` | 최소 주문 수량 | 목록 조회의 `unitQty` |
| `currency_orig` | 원통화 | `KRW` 고정 |
| `price_orig` | 원통화 가격 | 공란(국내는`unit_price_krw`와 중복이라 비움) |
| `effective_cost_note` | 원가 관련 부가 정보 | 배송비(목록 조회 `deli.fee`), 옵션 추가금 내역, 상세 조회 실패·미조회 여부 |
| `source_ref` | 출처 | 목록 조회의 `url`을 https로 정규화한 값. 도매꾹은 `https://domeggook.com/{상품번호}`, 도매매는 `https://domeme.domeggook.com/s/{상품번호}` |
| `collected_at` | 수집일 | `--date` 값(기본: 실행일), `YYYYMMDD` |
| `weight_g` · `volume_cm3` | 개당 중량·부피 | 공란(이 도구가 채우지 않는 열 — 국제 운임 계산용) |

`material`·`price_orig`·`weight_g`·`volume_cm3` 4열은 도매꾹·도매매에서는 **항상 빈 칸**입니다 — 열마다 이유가 다릅니다: `material`은 API가 원산지 외의 재질 정보를 제공하지 않고, `price_orig`는 국내 거래라 `unit_price_krw`와 같은 값이 되어 비워 두며, `weight_g`·`volume_cm3`는 국제 운임 계산용 칸이라 국내 수집에서는 채우지 않습니다.

### 터미널에서 직접 실행할 때

```bash
python3 tools/tool-domeggook-sourcing.py --keyword "[품목명]" --with-detail --sort rd --sz 30 --pages 1 --detail-top 30                   # 도매꾹
python3 tools/tool-domeggook-sourcing.py --keyword "[품목명]" --with-detail --sort rd --sz 30 --pages 1 --detail-top 30 --market supply   # 도매매
```

| 옵션 | 의미 | 기본값 |
|---|---|---|
| `--keyword` | 검색어 | — |
| `--market` | `dome`=도매꾹 · `supply`=도매매 | `dome` |
| `--sort` | `rd`=랭킹 · `aa`=낮은 가격 · `ha`=인기 · `qd`=많은 판매단위 | `aa` |
| `--sz` / `--pages` | 페이지당 상품 수(최대 200) / 페이지 수 | 100 / 2 |
| `--with-detail` | 상품별 상세 조회(원산지·제조사·옵션별 행 분리). 없으면 목록 값만 저장 | 꺼짐 |
| `--detail-top` | 상세 조회할 상품 수 상한 | 20 |
| `--date` | `collected_at`과 파일명에 쓸 날짜 | 오늘 |

스킬 문서의 실행 명령은 스크립트 기본값과 다릅니다(`--sort rd --sz 30 --pages 1 --detail-top 30`). 옵션 규격은 상세 조회에서만 나오므로, 목록에 올린 상품 수와 상세 조회 상품 수를 30으로 맞춰 둔 것입니다.

## 견본

`examples/` 폴더의 견본 CSV 2개(도매꾹·도매매 각 1개)는 이 도구를 돌리면 나오는 것과 같은 모양의 파일입니다. 실제로 수집된 줄이고, 상품 주소의 번호와 제조사 상호 일부만 가렸습니다.

## .gitignore 정책

| 패턴 | 이유 |
|---|---|
| `.env` · `.env.*` (`.env.example` 제외) | API 키는 올리지 않고 템플릿만 올린다 |
| `output/` | 수집 결과는 제3자(도매몰 판매자)의 상품 정보라 올리지 않는다. 폴더 자체가 팩에 없고 실행하면 생긴다 |
| `__pycache__/` · `*.pyc` | 파이썬 컴파일 캐시 |

확인:

```bash
git check-ignore -v .env
git check-ignore -v output/{생성된 CSV 파일명}
```

## 안전 규칙

API 키는 `.env`에만 넣습니다 — 코드나 커밋에 직접 적지 않습니다.

## 문제 해결

| 증상 | 원인 | 조치 |
|---|---|---|
| `❌ .env DOMEGGOOK_API_KEY 없음` | `.env`가 없거나, 있어도 키 값이 비어 있음 | `.env.example`을 복사해 `.env`를 만들고 `DOMEGGOOK_API_KEY=` 뒤에 키를 입력 |
| `❌ API 오류: …` | 키가 틀렸거나 도매꾹 API 응답 오류 | `.env`의 키 확인 |
| `/domestic-sourcing-scrape`가 목록에 없음 | Claude Code 실행 중에 파일을 받음 | Claude Code 재시작 |
| 저장 0건 | 도매꾹에 검색 결과가 없는 품목명 | 도매꾹 사이트에서 같은 검색어의 결과 유무 확인 |
| `spec` 열이 공란인 행 | 옵션이 없고, 상세 조회의 `detail.size`도 없거나 의미 없는 값(`0`·`해당없음` 등)인 상품. 상품명에서 추정해 채우지 않음 | 조치 불필요. 규격은`item`·`source_ref`에서 확인 |
| `effective_cost_note`에 `실패`·`미조회` 표시 | 그 상품의 상세 조회가 실패했거나`--detail-top` 범위 밖 | 재실행 또는`--detail-top` 상향 |

## 라이선스

MIT.

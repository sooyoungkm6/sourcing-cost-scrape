#!/usr/bin/env python3
"""
tool-pricebook-intake.py
메일에서 받은 단가표 PDF → 시행일·거래처 감지 → «YYYY-MM-DD_단가표.pdf» (통일 규칙) 이름으로 거래처 폴더에 이동.
pricebook-update/SKILL.md §절차 2번(분류·이름·이동)의 자동화. 파싱은 그 다음 tool-pricebook-parse.py.

⭐ 3단계 판정:
   · auto ✅ 자동 이동: «단가표» 문구 + 거래처 1곳 + 시행일 1개 + tool-pricebook-parse.py 의 표 파서(A/B/C)로 읽힘
                     + 파싱 행수 ≥ 기존 정규화 CSV 행수 × AUTO_MIN_RATIO (= 그 거래처의 아는 양식·전체본)
   · ask  ❓ 사람 확인: 그 사이 전부 — 견적서·발췌본 의심(행수 부족), 시행일 2종류(거래처A 6/26·6/30), 거래처 미감지,
                     파서 미지원 양식, 비교할 CSV 없는 새 거래처(처음 한 번은 사람이 확인한다)
   · ⭐ 이전 판은 묻지 않고 보관만: 문구·거래처·시행일이 확인됐는데 표만 못 읽은(파싱 0건) 파일이
     그 거래처의 **최신 판보다 이전 시행일**이면 auto(보관) — 가격은 최신 판에서만 읽는다.
     계기: 거래처A가 2026-06-26 부터 양식을 바꿔 이전 판 9개가 전부 «확인 요청»이 됐다.
     최신 판 = 거래처 폴더에 이미 있는 단가표 + 이번에 auto 로 판정된 파일 중 가장 늦은 시행일.
     ⛔ 최신 판보다 **새** 파일을 못 읽으면 그대로 ask — 가격을 못 얻은 것이다.
     조금만 읽힌 이전 판(거래처B 2026-02판: 34쪽 옛 양식, 12행만 읽힘)도 보관.
     ⛔ 최신 판과 같은 날짜거나 더 새 파일이 조금만 읽혔으면(발췌본·견적서 의심) 그대로 ask.
   · ⭐ 같은 거래처·같은 시행일 단가표가 여럿이면 **가장 늦게 받은 전체본 하나**만 옮긴다:
     앞선 발송본·같은 날짜의 발췌본(행수 부족)은 ⏭ 옮기지 않는다. 받은 날짜 = 파일의 수정한 날짜(mail-fetch 가 메일 날짜로 맞춘다).
     근거: 거래처A 6/26자 3통·거래처B 7/6자 2통 모두 마지막 메일이 확정본이었다(앞선 발송본은 11·32·6행이 다름).
     폴더에 같은 시행일 파일이 이미 있으면: 그보다 먼저 받은 파일은 ⏭ 건너뜀, 더 늦게 받은 파일(정정 재발송)은 ❓ 확인.
   · skip ⛔ 자동 제외: «단가표» 문구도 없고 파싱도 0건 — 청구서·공문·성적서
   기본 실행 = dry-run(판정만 표시). --apply = auto 는 옮기고 ask 는 목록(tty 면 물어봄), skip 은 안 건드림.
   --apply --file … --vendor … [--date] = 사람이 확정한 값으로 파일 하나 이동(ask 처리용). «단가표» 문구 없는 건 --force.

⭐ 거래처 이름의 기준 = 거래처 문서 `sourcing-channels.md` §소싱처 레지스트리.
  폴더 이름에서 배우지 않는다 — 처음 쓰는 사람은 폴더가 없다. 문서에 있는 거래처면 옮길 때 폴더를 만든다.
  문서엔 정식 상호를 적고, 표지·파일명과 대조할 때는 회사 표시(주식회사·(주)·㈜)를 떼고 본다.

⭐ 시행일 = PDF 표지·라벨·내지에 기재된 «… 시행» 날짜. 메일 수신일·첨부명 날짜가 아니다.
  감지 패턴·전 쪽 스캔·OCR 은 tool-pricebook-parse.py pdf_written_dates() 가 정본(파싱 단계에서 같은 기준으로 대조한다).
  실측 (4개 거래처 17개 PDF):
  · 거래처A: 표지엔 날짜 없음, 3쪽부터 라벨 «2026.06.26 시행» / 옛 양식 «시행일자 : 2024년 5월 30일»
  · 거래처B: 표지 «[ 2026년 7월 6일 시행 ]»  · 거래처C: 표지 «2026年 05月 01日»
  · 거래처D: 표지 «(2022년 6월 1일 시행)» — 글꼴에 유니코드 매핑이 없어 텍스트 추출은 (cid:…) → 맥 내장 Vision OCR 로 읽는다
  ⚠️ 첨부명 날짜는 참고로만 보여준다 — «2026.07.06_변동적용_전체단가표.pdf» 의 본문은 «2026.06.26 시행»(3~17쪽)·
     «2026.06.30 시행»(18쪽)이고 7/6 은 PDF 어디에도 없다. 쪽마다 시행일이 다르면 2종류로 감지되어 --date 로 사람이 확정한다.

사용법:
  python3 tools/tool-pricebook-intake.py                                   # dry-run: 판정 목록
  python3 tools/tool-pricebook-intake.py --apply                           # auto 자동 이동, ask 는 목록(tty 면 질문)
  python3 tools/tool-pricebook-intake.py --apply --file INBOX_단가표.pdf \\
      --vendor "거래처A" --date 2026-07-06                     # 명시 이동 (Claude 세션용 · 줄임말 «거래처A»도 된다)
  이동 후: python3 tools/tool-pricebook-parse.py --vendor {거래처}          # 최신 단가표 자동 선택·파싱
"""
import argparse
import csv
import datetime
import importlib.util
import re
import shutil
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRICES = ROOT / ".claude" / "references" / "sourcing-prices"
CHANNELS = ROOT / ".claude" / "references" / "sourcing-channels.md"   # 거래처 이름의 기준
INBOX = ROOT / "output" / "sourcing"   # tool-naver-mail-fetch.py OUT_DIR
FILE_DATE = re.compile(r"(\d{4})[.\-_](\d{2})[.\-_](\d{2})")  # 첨부 원본명 날짜 — 참고용(시행일 아님)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vendor_registry  # noqa: E402

_spec = importlib.util.spec_from_file_location("tool_pricebook_parse", Path(__file__).with_name("tool-pricebook-parse.py"))
pb = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(pb)


def _nfc(s):
    return unicodedata.normalize("NFC", str(s or ""))


def _squash(s):
    return re.sub(r"\s+", "", _nfc(s))


def extract_text(pdf):
    """전 쪽 텍스트(거래처·«단가표» 문구 감지용). 표지가 (cid:…) 뿐이면(글꼴 매핑 없음 — 거래처D) 표지는 OCR 로 보탠다."""
    import pdfplumber
    parts = []
    with pdfplumber.open(pdf) as d:
        for i, p in enumerate(d.pages):
            t = p.extract_text() or ""
            if i == 0 and "(cid:" in t:
                t += "\n" + pb.ocr_page_text(p)
            parts.append(t)
    return "\n".join(parts)


def detect_dates(text):
    """텍스트에 기재된 «… 시행» 날짜만 — 첨부명 날짜는 후보가 아니다."""
    return pb.written_dates(text)


def filename_date(filename):
    """첨부명 날짜(참고). 메일 수신·발송일일 수 있어 시행일 후보로 쓰지 않는다."""
    m = FILE_DATE.search(_nfc(filename))
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def detect_vendors(text, filename, vendors, recipes=None):
    """거래처 이름이 본문(공백 제거 — «㈜ 오 메 가 화 스 너» 대응)이나 파일명에 들어 있으면 후보.
    문서의 정식 상호(«거래처A»)와 표지 표기(«거래처A»)가 달라도 걸리게 회사 표시를 떼고 본다.
    recipes = {거래처: 읽기 설정} — 표지에 상호가 다른 글자로 적힌 거래처(거래처D «BRAND-NAME»)는 설정의 «표지 이름» 으로 찾는다."""
    hay = (_squash(text) + "|" + _squash(filename)).upper()
    out = []
    for v in vendors:
        names = [vendor_registry.core_name(v), *((recipes or {}).get(v) or {}).get("표지 이름", [])]
        if any(_squash(n) and _squash(n).upper() in hay for n in names):
            out.append(v)
    return out


def pricebook_kind(text, filename):
    """'단가표' / '' (이름·본문 어디에도 «단가표»가 없음 → 청구서·공문·성적서 의심).
    «특별단가표»도 전체 단가표라 구분하지 않는다 — 파일명은 항상 YYYY-MM-DD_단가표.pdf."""
    hay = _squash(text) + "|" + _squash(filename)
    return "단가표" if "단가표" in hay else ""


def known_vendors(channels=None):
    """거래처 문서에 적힌 단가표 거래처(방식 ③) 이름. 폴더가 있든 없든 문서가 기준이다."""
    return sorted(_nfc(v.name) for v in vendor_registry.load_vendors(channels or CHANNELS))


AUTO_MIN_RATIO = 0.5   # 파싱 행수가 기존 정규화 CSV 행수의 이 비율 이상이어야 «전체본»으로 자동 확정


def vendor_csv_rows(vendor, prices=None):
    """거래처 정규화 CSV 의 데이터 행수(없으면 0) — 전체본 여부 비교 기준."""
    if not vendor:
        return 0
    p = Path(prices or PRICES) / vendor / f"{vendor}-단가-정규화.csv"
    if not p.exists():
        return 0
    with open(p, encoding="utf-8-sig", newline="") as f:
        return max(0, sum(1 for _ in csv.reader(f)) - 1)


def vendor_recipes(vendors, prices=None):
    """{거래처: 읽기 설정} — 거래처 폴더에 설정 파일이 없으면 기본값. 거래처 문서 비고 칸의 «표지 이름: …» 도 «표지 이름» 에 보탠다
    (폴더가 아직 없는 새 거래처도 표지의 다른 이름으로 알아본다 — 거래처B «거래처B»).
    설정 파일이 깨진 거래처는 {"오류": 이유} — 그 거래처 파일만 사람 확인으로 돌리고 다른 거래처 판정은 계속한다."""
    doc_aliases = {_nfc(v.name): list(v.aliases) for v in vendor_registry.load_vendors(CHANNELS)}
    out = {}
    for v in vendors:
        try:
            out[v] = pb.load_recipe(Path(prices or PRICES) / v)
            out[v]["표지 이름"] = list(dict.fromkeys([*out[v]["표지 이름"], *doc_aliases.get(_nfc(v), [])]))
        except ValueError as e:                 # 모르는 항목·잘못된 값·JSON 문법 오류(JSONDecodeError 도 ValueError)
            out[v] = {"오류": f"{v} 읽기 설정을 못 읽음 — {e}"}
    return out


def parsed_rows(pdf, recipe=None):
    """tool-pricebook-parse.py 의 표 파서(A/B/C)가 읽어낸 행수 — 아는 단가표 양식이면 수백 행, 아니면 0.
    recipe = 그 거래처의 읽기 설정(거래처가 한 곳으로 정해졌을 때만)."""
    try:
        rows, _ = pb.parse_pdf(pdf, recipe)
    except Exception:
        return 0
    return len(rows)


FIRST_CHECK_ROWS = 10


def first_check(pdf, recipe=None):
    """새 거래처 첫 확인 — 읽은 결과의 표본 10행(파일 앞·중간·뒤에서 고르게)과 자체 검사. 아무것도 옮기거나 쓰지 않는다.
    자체 검사는 «잘못 읽었을 때만 나오는 모양»만 본다 — 잘 읽힌 거래처C·거래처A·거래처B에서는 0건이다."""
    recipe = recipe or {}
    rows, skipped = pb.parse_pdf(pdf, recipe)
    step = max(1, len(rows) // FIRST_CHECK_ROWS)
    warnings = []
    if "(cid:" in extract_text(pdf) and not recipe.get("글자표"):
        warnings.append("글자가 (cid:번호) 로 나온다(글꼴에 글자 정보 없음) — 읽기 설정 «글자표» 가 필요하다")
    elif not rows:
        warnings.append(f"읽은 행 0행 (못 읽은 표 {skipped}개) — 아는 표 모양이 아니다")
    nameless = sum(1 for r in rows if not re.sub(r"[\W\d_]", "", str(r[0])))
    if nameless:
        warnings.append(f"표 이름이 기호뿐인 행 {nameless}개 — 표 제목이 갈라져 읽혔다(읽기 설정 «제목 읽기»)")
    glued = [r[3] for r in rows if not re.fullmatch(r"\d+(\.\d{1,2})?", str(r[3]))]
    if glued:
        warnings.append(f"단가 모양이 이상한 행 {len(glued)}개 (예: {glued[0]}) — 옆 칸 숫자가 붙었다(읽기 설정 «칸 나누기»)")
    return {"rows": len(rows), "skipped": skipped, "names": len({r[0] for r in rows}),
            "sample": rows[::step][:FIRST_CHECK_ROWS], "warnings": warnings}


def classify(card, csv_rows):
    """3단계 판정 → (verdict, reason). auto=자동 이동 / ask=사람 확인 / skip=자동 제외 (머리말 참조)."""
    if card.get("recipe_error"):
        return "ask", f"읽기 설정 오류 — {card['recipe_error']}"
    if not card["kind"] and card["rows"] == 0:
        return "skip", "«단가표» 문구 없음 + 표 파싱 0건 (청구서·공문·성적서)"
    why = []
    if not card["kind"]:
        why.append("«단가표» 문구 없음")
    if len(card["vendors"]) != 1:
        why.append("거래처 감지 " + ("없음" if not card["vendors"] else f"{len(card['vendors'])}곳"))
    if not card["dates"]:
        why.append("시행일 없음")
    elif len(card["dates"]) > 1 and not majority_date(card.get("date_pages") or {}):
        why.append(f"시행일 {len(card['dates'])}종류가 같은 쪽수 {card['dates']}")
    if card["rows"] == 0:
        why.append("아는 표 양식 아님(파싱 0건)")
    elif csv_rows == 0:
        why.append("비교할 기존 CSV 없음")
    elif card["rows"] < csv_rows * AUTO_MIN_RATIO:
        why.append(f"행수 {card['rows']} < 기존 CSV {csv_rows}×{AUTO_MIN_RATIO} (발췌본·견적서 의심)")
    if why:
        return "ask", " · ".join(why)
    return "auto", f"문구·거래처·시행일 확정, {card['rows']}행 파싱(기존 CSV {csv_rows}행)"


def plan(inbox=None, prices=None):
    """inbox 의 *.pdf 마다 감지 + 3단계 판정 카드. 아무것도 옮기지 않는다."""
    inbox = Path(inbox or INBOX)
    vendors = known_vendors()
    recipes = vendor_recipes(vendors, prices)
    cards = []
    for pdf in sorted(inbox.glob("*.pdf")):
        text = extract_text(pdf)
        found = detect_vendors(text, pdf.name, vendors, recipes)
        recipe = recipes[found[0]] if len(found) == 1 else None
        broken = (recipe or {}).get("오류", "")
        card = {
            "file": pdf,
            "vendors": found,
            "date_pages": pb.pdf_written_dates(pdf),      # {날짜: [쪽…]} — 전 쪽 + (cid) 쪽 OCR, 파싱 단계와 같은 기준
            "file_date": filename_date(pdf.name),
            "kind": pricebook_kind(text, pdf.name),
            "rows": 0 if broken else parsed_rows(pdf, recipe),
            "recipe_error": broken,
        }
        card["dates"] = sorted(card["date_pages"])
        v = card["vendors"][0] if len(card["vendors"]) == 1 else ""
        card["csv_rows"] = vendor_csv_rows(v, prices)
        card["verdict"], card["reason"] = classify(card, card["csv_rows"])
        card["archive_only"] = False
        card["superseded"] = False
        cards.append(card)
    return already_in_folder(supersede_same_edition(archive_older(cards, prices)), prices)


def latest_edition(vendor, cards, prices=None):
    """그 거래처의 최신 판 시행일 — 폴더에 이미 있는 단가표 + 이번에 auto 로 판정된 파일 중 가장 늦은 날짜. 없으면 ''."""
    vdir = Path(prices or PRICES) / vendor
    dates = [pb.file_date(p.name) for p in vdir.glob("*.pdf") if "단가표" in _nfc(p.name)] if vdir.is_dir() else []
    for c in cards:
        if c["verdict"] == "auto" and not c["archive_only"] and c["vendors"] == [vendor]:
            try:
                dates.append(resolve_date(c))
            except ValueError:
                pass
    return max((d for d in dates if d), default="")


def _short_read(c):
    """표를 못 읽었거나(0행) 조금만 읽힌(행수 < 기존 CSV × AUTO_MIN_RATIO) 파일인가."""
    return c["rows"] == 0 or (c["csv_rows"] > 0 and c["rows"] < c["csv_rows"] * AUTO_MIN_RATIO)


def archive_older(cards, prices=None):
    """못 읽었거나 조금만 읽힌 파일이 그 거래처의 최신 판보다 이전 시행일이면 auto(보관)로 바꾼다 (머리말 ⭐)."""
    for c in cards:
        if c["verdict"] != "ask" or not _short_read(c) or not c["kind"] or len(c["vendors"]) != 1:
            continue
        try:
            date = resolve_date(c)
        except ValueError:
            continue
        latest = latest_edition(c["vendors"][0], cards, prices)
        if latest and date < latest:
            c["verdict"], c["archive_only"] = "auto", True
            read = f"조금만 읽힘 {c['rows']}행 · " if c["rows"] else ""
            c["reason"] = f"이전 판(시행 {date} < 최신 {latest}) — {read}보관만, 가격은 최신 판에서 읽는다"
    return cards


def already_in_folder(cards, prices=None):
    """폴더에 같은 시행일 단가표가 이미 있으면: 그보다 먼저 받은 파일은 ⏭ 건너뜀, 더 늦게 받은 파일(정정 재발송)은 ❓ 확인.
    조용히 덮어쓰지도(apply_move 가 거부한다), 조용히 버리지도 않는다. 받은 날짜 = 파일의 수정한 날짜."""
    for c in cards:
        if c["verdict"] not in ("auto", "ask") or c.get("archive_only") or c["rows"] == 0 or len(c["vendors"]) != 1:
            continue
        try:
            date = resolve_date(c)
        except ValueError:
            continue
        have = Path(prices or PRICES) / c["vendors"][0] / f"{date}_단가표.pdf"
        if not have.exists():
            continue
        got, kept = c["file"].stat().st_mtime, have.stat().st_mtime
        if got <= kept:
            c["verdict"], c["superseded"] = "skip", True
            c["reason"] = f"같은 시행일({date}) 단가표가 폴더에 이미 있고 이 파일은 그보다 먼저 받은 것 — 옮기지 않는다"
        else:
            c["verdict"] = "ask"
            c["reason"] = (f"같은 시행일({date}) 단가표가 폴더에 이미 있는데 이 파일을 더 늦게 받았다(새 발송본?) — "
                           f"사람이 보고 바꾸려면 폴더의 파일을 치운 뒤 --apply --file")
    return cards


def supersede_same_edition(cards):
    """같은 거래처·같은 시행일 파일이 여럿이면 가장 늦게 받은 전체본 하나만 남기고 나머지는 ⏭ 옮기지 않는다 (머리말 ⭐)."""
    groups = {}
    for c in cards:
        if c["verdict"] not in ("auto", "ask") or c.get("archive_only") or c["rows"] == 0 or len(c["vendors"]) != 1:
            continue
        try:
            groups.setdefault((c["vendors"][0], resolve_date(c)), []).append(c)
        except ValueError:
            continue
    for (vendor, date), group in groups.items():
        if len(group) < 2:
            continue
        biggest = max(c["rows"] for c in group)
        full = [c for c in group if c["rows"] >= biggest * AUTO_MIN_RATIO]
        winner = max(full, key=lambda c: c["file"].stat().st_mtime)
        when = datetime.date.fromtimestamp(winner["file"].stat().st_mtime)
        for c in group:
            if c is winner:
                continue
            kind = "앞선 발송본" if c in full else "발췌본"
            c["verdict"], c["superseded"] = "skip", True
            c["reason"] = f"같은 시행일({date}) {kind} — 가장 늦게 받은 전체본 {winner['file'].name}({when} 수신)만 옮긴다"
    return cards


def majority_date(date_pages):
    """쪽마다 시행일이 다르면 파일 시행일 = 가장 많은 쪽에 적힌 날짜.
    거래처A 2026-06-26본: 6/26 ×18쪽, 6/30 ×1쪽 → 6/26. 동수면 '' (사람이 --date)."""
    if not date_pages:
        return ""
    ranked = sorted(date_pages.items(), key=lambda kv: -len(kv[1]))
    if len(ranked) > 1 and len(ranked[0][1]) == len(ranked[1][1]):
        return ""
    return ranked[0][0]


def resolve_date(card, date_arg=""):
    """확정 시행일. --date 가 이긴다. 없으면 PDF 기재 날짜(복수면 다수 쪽 날짜). 없거나 동수면 ValueError."""
    if date_arg:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_arg):
            raise ValueError(f"--date 는 YYYY-MM-DD 형식: «{date_arg}»")
        return date_arg
    if not card["dates"]:
        raise ValueError("PDF 에서 시행일을 못 읽음 — 표지를 눈으로 보고 --date YYYY-MM-DD 를 준다 (추정 금지)")
    d = majority_date(card.get("date_pages") or {x: [1] for x in card["dates"]})
    if not d:
        raise ValueError(f"PDF 에 시행일이 {len(card['dates'])}종류 기재됐고 쪽수가 같다 {card['dates']} — --date 로 하나를 확정한다")
    return d


def apply_move(card, vendor, date, force=False, prices=None):
    """inbox 파일 → {prices}/{vendor}/{date}_단가표.pdf 로 이동. 이동한 경로를 돌려준다."""
    prices = Path(prices or PRICES)
    vendor = _nfc(vendor)
    known = known_vendors()
    hit = vendor_registry.find([vendor_registry.Vendor(n, ()) for n in known], vendor)
    if hit is None:
        raise ValueError(f"거래처 문서에 없는 거래처: {vendor} — sourcing-channels.md 거래처 표에 먼저 적는다 (지금 적힌 곳: {known})")
    vendor = hit.name                           # 폴더 이름 = 문서에 적힌 이름 그대로
    vdir = prices / vendor
    if not card["kind"] and not force:
        raise ValueError("이름에도 본문에도 «단가표»가 없다(청구서·공문·성적서 의심) — 단가표가 맞으면 --force")
    dest = vdir / f"{date}_단가표.pdf"          # 파일명 통일: YYYY-MM-DD_단가표.pdf
    if dest.exists():
        raise ValueError(f"이미 있음: {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest} — 덮어쓰지 않는다")
    vdir.mkdir(parents=True, exist_ok=True)     # 처음 받는 거래처 — 폴더가 없으면 만든다
    shutil.move(str(card["file"]), str(dest))
    return dest


ICON = {"auto": "✅ 자동", "ask": "❓ 확인", "skip": "⛔ 제외"}
ICON_ARCHIVE = "🗄 보관"          # auto 중 이전 판 — 옮기기만 하고 읽지 않는다
ICON_SUPERSEDED = "⏭ 건너뜀"      # 같은 시행일의 앞선 발송본·발췌본 — 옮기지 않는다


def _print_card(i, c):
    v = ", ".join(c["vendors"]) or "(감지 없음)"
    dp = c.get("date_pages") or {}
    d = ", ".join(f"{x}({len(dp[x])}쪽)" if len(dp.get(x, [])) and len(dp) > 1 else x for x in c["dates"]) or "(PDF 기재 없음)"
    k = c["kind"] or "«단가표» 문구 없음"
    fd = c.get("file_date")
    note = f" · 첨부명 날짜 {fd}(참고 — 시행일 아님)" if fd and fd not in c["dates"] else ""
    icon = ICON_ARCHIVE if c.get("archive_only") else ICON_SUPERSEDED if c.get("superseded") else ICON[c["verdict"]]
    print(f"  [{i}] {icon}  {c['file'].name}\n"
          f"      거래처 {v} · PDF 기재 시행일 {d} · {k} · 파싱 {c['rows']}행{note}\n"
          f"      → {c['reason']}")


def _rel(p):
    return p.relative_to(ROOT) if p.is_relative_to(ROOT) else p


def _print_first_check(card, r):
    v = ", ".join(card["vendors"]) or "(감지 없음)"
    print(f"🔎 첫 확인 — {card['file'].name}\n"
          f"   거래처 {v} · PDF 기재 시행일 {', '.join(card['dates']) or '(기재 없음)'}\n"
          f"   읽은 행 {r['rows']:,} · 표 이름 {r['names']}종 · 못 읽은 표 {r['skipped']}개")
    print("   자체 검사: " + ("이상 없음" if not r["warnings"] else ""))
    for w in r["warnings"]:
        print(f"     ⚠️ {w}")
    if r["sample"]:
        print(f"   표본 {len(r['sample'])}행 (파일 앞·중간·뒤에서 고르게) — 표 이름 | 규격 | 포장 | 개당단가")
        for n, s, p, pr, _ in r["sample"]:
            print(f"     {n} | {s} | {p or '-'} | {pr}")
    print("   ❓ 질문은 하나: 위 표본이 단가표 PDF 의 같은 칸과 같습니까?\n"
          "      같으면 → --apply --file … --vendor … 로 옮긴다 (그 뒤로 이 거래처는 자동)\n"
          "      다르면 → 거래처 폴더의 읽기 설정을 고친 뒤 다시 본다")


def _ask_one(c, force):
    """tty 대화형: ask 카드 하나를 사람이 확정. 옮겼으면 True."""
    ans = input("      이 파일이 단가표입니까? [y/N] ").strip().lower()
    if ans != "y":
        return False
    default_v = c["vendors"][0] if c["vendors"] else ""
    vendor = input(f"      거래처 [{default_v}]: ").strip() or default_v
    date = input(f"      시행일 YYYY-MM-DD [{majority_date(c.get('date_pages') or {})}]: ").strip()
    try:
        dest = apply_move(c, vendor, resolve_date(c, date), force)
        print(f"      ✅ → {_rel(dest)}")
        return True
    except ValueError as e:
        print(f"      ⛔ {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="메일 단가표 PDF 3단계 판정(auto/ask/skip) → 이름·이동")
    ap.add_argument("--inbox", default=str(INBOX), help="스캔 폴더 (기본: tool-naver-mail-fetch.py 저장 폴더)")
    ap.add_argument("--apply", action="store_true", help="auto 는 자동 이동, ask 는 목록(tty 면 질문). --file 과 함께면 그 파일만")
    ap.add_argument("--file", default="", help="옮길 파일명 (inbox 안) — ask 판정을 사람이 확정할 때")
    ap.add_argument("--vendor", default="", help="거래처 이름 — 거래처 문서의 정식 상호 (줄임말도 그 글자가 든 거래처가 한 곳이면 된다)")
    ap.add_argument("--date", default="", help="시행일 YYYY-MM-DD (PDF 에 기재된 날짜) — 감지 0건·복수면 필수, 주면 감지값을 덮어쓴다")
    ap.add_argument("--force", action="store_true", help="«단가표» 문구가 없는 파일도 옮긴다 (--file 과 함께)")
    ap.add_argument("--first-check", action="store_true",
                    help="새 거래처 첫 확인: --file 의 표본 10행과 자체 검사를 보여 준다 (아무것도 옮기지 않음)")
    a = ap.parse_args()

    inbox = Path(a.inbox)
    if not inbox.is_dir():
        print(f"❌ 폴더 없음: {inbox} — 먼저 tool-naver-mail-fetch.py 로 받는다"); return 1
    cards = plan(inbox)
    if not cards:
        print(f"ℹ️ {_rel(inbox)} 에 PDF 없음"); return 0

    n = {k: sum(1 for c in cards if c["verdict"] == k and not c.get("archive_only") and not c.get("superseded")) for k in ICON}
    extra = {"🗄 보관": sum(1 for c in cards if c.get("archive_only")), "⏭ 건너뜀": sum(1 for c in cards if c.get("superseded"))}
    summary = f"✅ 자동 {n['auto']} · ❓ 확인 {n['ask']} · ⛔ 제외 {n['skip']}" + "".join(f" · {k} {v}" for k, v in extra.items() if v)

    if a.file:
        card = next((c for c in cards if _nfc(c["file"].name) == _nfc(a.file)), None)
        if card is None:
            print(f"❌ inbox 에 없음: {a.file}"); return 1
        if a.first_check:
            vendor = pb.resolve_vendor(_nfc(a.vendor)) if a.vendor else (card["vendors"][0] if len(card["vendors"]) == 1 else "")
            recipe = vendor_recipes([vendor])[vendor] if vendor else None
            if (recipe or {}).get("오류"):
                print(f"⛔ {recipe['오류']}"); return 1
            _print_first_check(card, first_check(card["file"], recipe))
            return 0
        if not a.apply:
            _print_card(1, card); return 0
        if not a.vendor:
            print("❌ --apply --file 에는 --vendor 필수 (거래처는 사람이 확정한다)"); return 1
        try:
            dest = apply_move(card, a.vendor, resolve_date(card, a.date), a.force)
        except ValueError as e:
            print(f"⛔ {e}"); return 1
        print(f"✅ {card['file'].name} → {_rel(dest)}\n   다음: python3 tools/tool-pricebook-parse.py --vendor {a.vendor}")
        return 0

    print(f"📥 후보 {len(cards)}건 — {summary}" + ("" if a.apply else "  (dry-run: 아무것도 옮기지 않음)"))
    moved, vendors_done = 0, []
    for i, c in enumerate(cards, 1):
        _print_card(i, c)
        if not a.apply:
            continue
        if c["verdict"] == "auto":
            try:
                dest = apply_move(c, c["vendors"][0], resolve_date(c))
                moved += 1
                if c["archive_only"]:
                    print(f"      🗄 보관 → {_rel(dest)}")
                else:
                    print(f"      ✅ 이동 → {_rel(dest)}"); vendors_done.append(c["vendors"][0])
            except ValueError as e:
                print(f"      ⛔ {e}")
        elif c["verdict"] == "ask":
            if sys.stdin.isatty():
                if _ask_one(c, False):
                    moved += 1; vendors_done.append(_nfc(c["vendors"][0]) if c["vendors"] else "?")
            else:
                print(f"      ↪ 사람 확정: --apply --file \"{c['file'].name}\" --vendor <거래처> [--date YYYY-MM-DD]")
    if not a.apply:
        print("\n   --apply 로 ✅ 자동 건을 옮기고, ❓ 확인 건은 --apply --file … --vendor … [--date] 로 하나씩 확정한다")
    elif moved:
        nxt = " ; ".join(f'python3 tools/tool-pricebook-parse.py --vendor "{v}"' for v in dict.fromkeys(vendors_done))
        print(f"\n✅ 이동 {moved}건" + (f" → 다음: {nxt}" if nxt else " (전부 이전 판 보관 — 다시 읽을 단가표 없음)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

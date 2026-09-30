#!/usr/bin/env python3
"""
tool-pricebook-parse.py
거래처 단가표 PDF → 정규화 CSV. sourcing-channels.md 수집 방식 ③(거래처 단가표)의 파싱 배선 — pattern 값 ③ (2026-09-17 재매김, 구 ④).

입력:  .claude/references/sourcing-prices/{거래처}/{YYYY-MM-DD}_단가표.pdf
산출:  .claude/references/sourcing-prices/{거래처}/{거래처}-단가-정규화.csv
       열: 거래처,품번,품명,규격,단위,개당단가_krw,시행일,원본파일
       (거래처A 단가표는 품번이 없어 품번 공란. 단위 = 포장 수량.
        단가는 표기값 그대로 = 개당단가 가정 — 박스가로 확인되면 보정 필요)

표 유형:
  A. 가로형 — 첫 열이 '규격'인 행 + '단가' 행 (+ '포장'/'소포장' 행)
  B. 매트릭스형(라벨행) — col0=규격(M12·5/8 등, 병합), col1=단 가/포 장, col2=재질(철/201/304),
     헤더행=길이. 규격 = "{col0}x{길이}" + 재질 병기
  C. 순수 매트릭스형(거래처B) — row0=길이 헤더(첫 칸 공란), col0=규격(M4 등), 셀=개당단가(소수 허용)
품명 = 표 위 라벨 텍스트 (좌우 2단 배치 → x 좌표로 매칭, '■' 접두어 유무 무관),
없으면 페이지 헤더 카테고리. 행 시행일 = 그 쪽에 기재된 «… 시행» 날짜(없으면 파일명 날짜 —  2026-09-16).

xls 단가표는 현재 실물 0건(회원 도매처 청구서는 보관 제외 규정) — 확보 시 python_calamine로 추가.

⭐ 거래처별 읽기 설정 — 틀은 코드에, 거래처마다 다른 것은 거래처 폴더의 설정 파일에 둔다:
  · {거래처}-읽기-설정.json   «글자표»: 글꼴에 글자 정보가 없어 (cid:N) 만 나오는 PDF 를 표준 글자표로 푼다(예: "Adobe-Korea1")
                             «표지 이름»: 단가표에 적힌 이름이 거래처 문서의 이름과 다를 때(예: ["BRAND-NAME"])
                             «칸 나누기»: "기본"(표 찾기가 묶어 준 칸) / "선 위치"(표 안의 세로선·가로선 위치를 직접 읽는다)
                               표 찾기가 칸을 잘못 묶어 옆 칸 글자가 섞이거나(«45 50»), 표 영역을 좁게 잡아 마지막 칸이
                               잘리거나(«100» → «10»), 빈 칸이 있는 줄의 값이 밀리는 단가표는 "선 위치"로 읽는다
                             «포장 줄»: "바로 위"(기본 — 포장 줄은 바로 위 값 줄의 포장) / "위 전부"(직전 포장 줄 이후의 값 줄 전부)
                               거래처C는 "바로 위"여야 한다(100EA 가격 줄에 아래 «수량 1000» 이 붙으면 안 된다).
                               거래처D은 값 줄 둘 아래 포장 줄 하나가 두 줄 모두의 포장이라 "위 전부"
                             «제목 읽기»: "기본" / "줄 단위" — 표 제목이 갈라지거나(«…SEMS» + «)») 옆 그림 설명과 붙어 읽히면 "줄 단위".
                               거래처C·거래처A는 "기본"으로 읽은 품명에 매핑 규칙이 걸려 있다 — 기본값을 바꾸지 않는다
  · {거래처}-품명-대응표.csv   품명을 사람이 다듬어 쓰는 경우에만. 열 = 표 이름, 줄 이름, 품명, 규격 앞
      표 이름 = PDF 표 위에 적힌 이름 / 줄 이름 = 표의 첫 칸(비우면 표 전체) / 품명 = 확정 품명(여러 줄이면 여러 품명으로 나뉜다)
      규격 앞 = 줄 이름이 굵기가 아닐 때 규격의 앞부분을 바꾼다(비우면 줄 이름 그대로)
    대응표에 없는 표는 PDF 에 적힌 이름을 그대로 쓴다.
  설정 파일이 없으면 종전과 같이 읽는다 — 거래처A·거래처B·거래처C는 설정 없이 읽힌다.
  실측(거래처D 2022-06-01본): 본문 글꼴의 번호가 한글 표준 글자표(Adobe-Korea1) 순서와 같아 OCR 없이 풀린다.

⭐ 최신 단가표 = 기준:
  · --file 을 생략하면 거래처 폴더에서 **파일명 날짜가 가장 최신인 `*단가표*.pdf`** 를 자동 선택한다.
    파일명은 `YYYY-MM-DD_단가표.pdf` 로 통일한다 — 한 시행일에 파일 하나. «특별단가표»도 같은 규칙.
  · 정규화 CSV 는 통째로 덮어쓴다 — 그래서 **이미 기록된 시행일보다 오래된 파일은 거부**한다(--force 로만 허용).
    종전엔 마지막에 돌린 파일이 무조건 이겼다 — 옛 단가표를 나중에 돌리면 인상 전 가격으로 조용히 되돌아갔다.
  · --emit-sourcing-cost 는 append 가 아니라 **그 거래처의 기존 ③행을 지우고 교체**한다.
  · 시행일 = **PDF 표지·라벨·내지에 기재된 «… 시행» 날짜**. 메일 수신일·첨부명 날짜가 아니다.
    코드는 파일명 날짜를 시행일로 쓰되, 파싱 전에 PDF 기재 날짜와 대조해 **파일명 날짜가 PDF 에 없으면 멈춘다**(--force 로만 통과).
    실측: 거래처A가 7/6 메일로 보낸 변동적용본은 본문 라벨이 «2026.06.26 시행»(3~17쪽)·«2026.06.30 시행»(18쪽)이고
    7/6 은 PDF 어디에도 없다 → 2026-06-26_단가표.pdf 로 개명.
    거래처D PDF 는 표지에 «(2022년 6월 1일 시행)» 이 있지만 글꼴에 유니코드 매핑이 없어
    extract_text 가 (cid:…) 만 뱉는다 → 그런 쪽은 맥 내장 Vision OCR(tools/ocr-vision.js)로 다시 읽는다.
    맥이 아닌 환경에선 OCR 을 건너뛰어 «못 읽음» 경고 후 파일명 날짜를 쓴다.
    메일에서 받은 PDF 의 감지·이름·이동은 tool-pricebook-intake.py (dry-run 기본, «단가표인가»·시행일 확정은 사람).

사용법:
  python3 tools/tool-pricebook-parse.py --vendor "거래처A"            # 최신 단가표 자동 선택 (줄임말 «거래처A»도 된다)
  python3 tools/tool-pricebook-parse.py --vendor "거래처A" --file 2026-06-26_단가표.pdf   # 명시 (오래되면 거부)
  python3 tools/tool-pricebook-parse.py --vendor "거래처A" \
      --emit-sourcing-cost --date 20260802 --topic 내품목   # 스키마① ③행 교체
  python3 tools/tool-pricebook-parse.py --lookup 육각볼트      # 전 거래처 실거래가 교차 대조
  python3 tools/tool-pricebook-parse.py --lookup 육각볼트 \
      --emit-sourcing-cost --date 20260810 --topic 육각볼트   # 매칭 전부 ③행 주입
"""
import argparse, csv, re, sys, unicodedata
from pathlib import Path
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from schema_loader import schema_cols

ROOT = Path(__file__).parent.parent
PRICES = ROOT / ".claude" / "references" / "sourcing-prices"
RESEARCH = ROOT / "output"
import vendor_registry                 # 거래처 이름의 기준 = 거래처 문서

NORM_HDR = ["거래처", "품번", "품명", "규격", "단위", "개당단가_krw", "시행일", "원본파일"]
NAME_MAP_HDR = ["표 이름", "줄 이름", "품명", "규격 앞"]
RECIPE_KEYS = {"글자표": "", "표지 이름": [], "칸 나누기": "기본", "포장 줄": "바로 위", "제목 읽기": "기본"}   # 읽기 설정 항목과 기본값
COLUMN_MODES = ("기본", "선 위치")
PACK_SCOPES = ("바로 위", "위 전부")
TITLE_MODES = ("기본", "줄 단위")
PACK_ROWS = ("수량", "포장", "소포장", "포장단위")    # 매트릭스 표에서 포장 수량이 적힌 줄의 첫 칸
CID = re.compile(r"\(cid:(\d+)\)")
SCHEMA1_HDR = schema_cols(1)  # ⛔ 하드코딩 금지 — research-output-schema.md 가 정본


def _num(s):
    s = re.sub(r"[^\d]", "", str(s or ""))
    return int(s) if s else None


def _squash(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", str(s or "")))


def resolve_vendor(name):
    """--vendor 로 받은 이름 → 거래처 문서의 정식 상호. 문서가 없거나 문서에 없는 이름이면 받은 그대로."""
    try:
        hit = vendor_registry.find(vendor_registry.load_vendors(), name)
    except (FileNotFoundError, ValueError):
        return name
    return hit.name if hit else name


def load_recipe(vendor_dir):
    """거래처 폴더의 읽기 설정 + 품명 대응표. 파일이 없으면 기본값 — 설정 없이 읽히는 거래처가 대부분이다."""
    d = Path(vendor_dir)
    name = unicodedata.normalize("NFC", d.name)
    recipe = {k: (list(v) if isinstance(v, list) else v) for k, v in RECIPE_KEYS.items()}
    f = d / f"{name}-읽기-설정.json"
    if f.exists():
        import json
        data = json.loads(f.read_text(encoding="utf-8"))
        unknown = sorted(set(data) - set(RECIPE_KEYS))
        if unknown:
            raise ValueError(f"{f.name} 에 모르는 항목 {unknown} — 쓸 수 있는 항목: {sorted(RECIPE_KEYS)}")
        recipe.update(data)
    if recipe["칸 나누기"] not in COLUMN_MODES:
        raise ValueError(f"읽기 설정 «칸 나누기» 는 {COLUMN_MODES} 중 하나여야 합니다: «{recipe['칸 나누기']}»")
    if recipe["포장 줄"] not in PACK_SCOPES:
        raise ValueError(f"읽기 설정 «포장 줄» 은 {PACK_SCOPES} 중 하나여야 합니다: «{recipe['포장 줄']}»")
    if recipe["제목 읽기"] not in TITLE_MODES:
        raise ValueError(f"읽기 설정 «제목 읽기» 는 {TITLE_MODES} 중 하나여야 합니다: «{recipe['제목 읽기']}»")
    m = d / f"{name}-품명-대응표.csv"
    recipe["품명 대응표"] = []
    if m.exists():
        with open(m, encoding="utf-8-sig", newline="") as fh:
            recipe["품명 대응표"] = [{k: (r.get(k) or "").strip() for k in NAME_MAP_HDR} for r in csv.DictReader(fh)]
    return recipe


_UNICODE_MAPS = {}


def decode_cid(text, table):
    """(cid:N) 을 표준 글자표로 푼다. table 이 비면 그대로 돌려준다. 글자표에 없는 번호(글머리 기호 등)는 뺀다."""
    if not table or "(cid:" not in (text or ""):
        return text
    if table not in _UNICODE_MAPS:
        from pdfminer.cmapdb import CMapDB
        try:
            _UNICODE_MAPS[table] = CMapDB.get_unicode_map(table)
        except Exception as e:
            raise ValueError(f"글자표 «{table}» 를 찾지 못했습니다 — 읽기 설정의 «글자표» 값을 확인하세요 ({type(e).__name__})")
    um = _UNICODE_MAPS[table]

    def one(m):
        try:
            return um.get_unichr(int(m.group(1)))
        except Exception:
            return ""
    return CID.sub(one, text)


def decode_page(page, table):
    """쪽의 글자를 그 자리에서 푼다 — 이후 표·글 추출이 풀린 글자로 나온다."""
    if table:
        for ch in page.chars:
            if "(cid:" in ch["text"]:
                ch["text"] = decode_cid(ch["text"], table)


def _covered(spans):
    """겹치는 구간은 한 번만 센 길이."""
    total, end = 0, None
    for a, b in sorted(spans):
        if end is None or a > end:
            total, end = total + (b - a), b
        elif b > end:
            total, end = total + (b - end), b
    return total


def _ruled(edges, pos, a, b, lo, hi, span, tol=1.5, cover=0.5):
    """같은 위치(±tol)에 놓인 선분이 표 길이(span)의 cover 이상을 덮는 위치만 — 그림·장식의 짧은 선은 빠진다.
    칸 테두리는 같은 자리에 선이 두세 겹 그려지므로 겹친 부분은 한 번만 센다.
    cover 0.5 = 실측(거래처D): 합쳐진 칸 때문에 5줄 중 3줄에만 있는 칸 선 58% · 머리글 줄에만 걸친 그림 선 32%."""
    groups = []
    for e in sorted(edges, key=lambda e: e[pos]):
        seg = (max(e[a], lo), min(e[b], hi))
        if seg[1] <= seg[0]:
            continue
        if groups and abs(groups[-1][0] - e[pos]) <= tol:
            groups[-1][1].append(seg)
        else:
            groups.append([e[pos], [seg]])
    return [p for p, spans in groups if _covered(spans) >= span * cover]


def _with_border(positions, first, last, tol=2.0):
    out = []
    for v in sorted([*positions, first, last]):
        if not out or v - out[-1] > tol:
            out.append(v)
    return out


def grid_from_rules(chars, v_edges, h_edges, bbox):
    """표 안의 선 위치로 칸을 나눈 표. chars·edges = pdfplumber 의 글자·선(dict: x0,x1,top,bottom[,text]).
    bbox = 표 찾기가 준 영역 — 오른쪽 끝은 믿지 않고 **가로선이 끝나는 곳**을 테두리로 본다."""
    x0, top, x1, bottom = bbox
    hs = [e for e in h_edges if top - 2 <= e["top"] <= bottom + 2 and e["x1"] > x0 and e["x0"] <= x0 + 5]
    right = max([e["x1"] for e in hs], default=x1)
    vs = [e for e in v_edges if x0 - 2 <= e["x0"] <= right + 2]
    xs = _with_border(_ruled(vs, "x0", "top", "bottom", top, bottom, bottom - top), x0, right)
    ys = _with_border(_ruled(hs, "top", "x0", "x1", x0, right, right - x0), top, bottom)
    if len(xs) < 3 or len(ys) < 3:
        return []

    def mid(c, a, b):
        return (c[a] + c[b]) / 2

    def ruled_here(x, ya, yb, tol=1.5, cover=0.6):
        """그 줄(ya~yb)에 x 위치의 세로선이 있는가 — 없으면 양옆 칸은 합쳐진 한 칸이다."""
        spans = [(max(e["top"], ya), min(e["bottom"], yb)) for e in vs if abs(e["x0"] - x) <= tol]
        return _covered([s for s in spans if s[1] > s[0]]) >= (yb - ya) * cover

    grid = []
    for ya, yb in zip(ys, ys[1:]):
        band = [c for c in chars if ya <= mid(c, "top", "bottom") < yb]
        row, start = [], 0
        for i in range(1, len(xs)):
            if i < len(xs) - 1 and not ruled_here(xs[i], ya, yb):
                continue
            cell = sorted((c for c in band if xs[start] <= mid(c, "x0", "x1") < xs[i]),
                          key=lambda c: (round(c["top"]), c["x0"]))
            row.extend(["".join(c["text"] for c in cell).strip(), *[None] * (i - start - 1)])   # 합쳐진 칸 = 값 + None
            start = i
        grid.append(row)
    return grid


def table_grid(page, table, mode):
    """표 한 개 → 칸 배열. mode = 읽기 설정 «칸 나누기»."""
    if mode != "선 위치":
        return table.extract()
    edges = page.edges
    return grid_from_rules(page.chars, [e for e in edges if e["orientation"] == "v"],
                           [e for e in edges if e["orientation"] == "h"], table.bbox)


def apply_name_map(rows, name_map):
    """품명 대응표 적용. rows=[(표 이름, 규격, 포장, 단가, 쪽시행일)] → 같은 모양.
    표 이름(공백 무시)과 줄 이름(규격의 «x» 앞부분)이 맞는 줄마다 확정 품명 하나씩 — 여러 줄이면 여러 품명으로 나뉜다."""
    if not name_map:
        return list(rows)
    index = {}
    for m in name_map:
        index.setdefault(_squash(m["표 이름"]), []).append(m)
    out = []
    for name, spec, pack, price, date in rows:
        head, sep, tail = str(spec).rpartition("x")
        key = _squash(head if sep else "")
        hits = [m for m in index.get(_squash(name), []) if not m["줄 이름"] or _squash(m["줄 이름"]) == key]
        if not hits:
            out.append((name, spec, pack, price, date))
            continue
        for m in hits:
            new_spec = f"{m['규격 앞']}x{tail}" if (m["규격 앞"] and sep) else spec
            out.append((m["품명"], new_spec, pack, price, date))
    return out


def _by_line(words):
    """단어를 줄로 묶어(단어 가운데가 그 줄 첫 단어의 위·아래 사이) 줄마다 왼쪽부터 → [(단어, 줄의 첫 단어인가)]."""
    lines = []
    for w in sorted(words, key=lambda w: w["top"]):
        if lines and lines[-1][0]["top"] <= (w["top"] + w["bottom"]) / 2 <= lines[-1][0]["bottom"]:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [(w, i == 0) for line in lines for i, w in enumerate(sorted(line, key=lambda w: w["x0"]))]


def _labels(page, table_bboxes, by_line=False):
    """표 밖 라벨 텍스트 목록 → [(top, x0, text)].
    세그먼트 분리: '■' 시작 단어 / 줄바뀜(top 차 4↑) / 가로 간격 40px↑ (좌우 2단 라벨 대응).
    by_line = 읽기 설정 «제목 읽기: 줄 단위» — 제목에 큰 글자·작은 글자가 섞여 top 이 어긋나는 단가표(거래처D)."""
    words = page.extract_words()
    outside = [w for w in words
               if not any(bb[1] - 2 <= w["top"] <= bb[3] + 2 for bb in table_bboxes)]
    if by_line:
        ordered = _by_line(outside)
    else:
        outside.sort(key=lambda w: (round(w["top"]), w["x0"]))
        ordered = [(w, None) for w in outside]
    labels, cur, prev = [], None, None
    for w, first_in_line in ordered:
        new_line = first_in_line if by_line else (cur is not None and abs(w["top"] - cur[0]) >= 4)
        new_seg = (cur is None or w["text"].startswith("■")
                   or new_line
                   or (prev is not None and w["x0"] - prev["x1"] > 40))
        if new_seg:
            if cur:
                labels.append(cur)
            cur = [w["top"], w["x0"], w["text"].lstrip("■").strip()]
        else:
            cur[2] = (cur[2] + " " + w["text"].lstrip("■")).strip()
        prev = w
    if cur:
        labels.append(cur)
    # 날짜·'시행' 표기 줄은 품명 라벨에서 제외 (예: '2022년 7월 18일', '2026.06.26 시행')
    return [(t, x, s) for t, x, s in labels
            if s and not re.fullmatch(r"[\d\s년월일.\-]+(시행)?", s)]


def _label_for(table, labels, fallback):
    """표 위쪽에서 가장 가까운, x 구간이 겹치는 라벨"""
    x0, top, x1, _ = table.bbox
    cands = [(t, x, s) for t, x, s in labels if t < top + 5 and x0 - 30 <= x <= x1]
    if not cands:
        cands = [(t, x, s) for t, x, s in labels if t < top + 5]
    return max(cands, key=lambda c: c[0])[2] if cands else fallback


def _parse_type_a(grid, name):
    """가로형: '규격' 행 + '단가' 행 (+ 포장). 반환 [(품명, 규격, 단위, 단가)]"""
    def row_key(r):
        return re.sub(r"\s", "", str(r[0] or ""))
    spec_row = next((r for r in grid if row_key(r) == "규격"), None)
    price_row = next((r for r in grid if row_key(r) == "단가"), None)
    if not (spec_row and price_row):
        return None
    pack_row = next((r for r in grid if row_key(r) in ("포장", "소포장")), None)
    out = []
    for i in range(1, len(spec_row)):
        spec = (spec_row[i] or "").strip()
        price = _num(price_row[i] if i < len(price_row) else "")
        if spec and price:
            pack = (pack_row[i] or "").strip() if pack_row and i < len(pack_row) else ""
            out.append((name, spec, pack, price))
    return out


def _parse_type_b(grid, name):
    """매트릭스형: col1에 '단 가'/'포 장', col2=재질, 헤더행=길이"""
    def cell(r, i):
        return re.sub(r"\s", "", str(r[i] or "")) if i < len(r) else ""
    if not any(cell(r, 1) in ("단가", "포장") for r in grid):
        return None
    header = grid[0]
    out, spec0 = [], ""
    packs = {}  # 열 index → 포장
    for r in grid[1:]:
        if cell(r, 0):
            spec0 = cell(r, 0)
        kind = cell(r, 1)
        if kind == "포장":
            for i in range(3, len(r)):
                if _num(r[i]):
                    packs[i] = str(r[i]).strip()
            continue
        mat = cell(r, 2)
        # 단가 그룹: kind=='단가' 첫 행 또는 재질만 있는 후속 행
        if kind == "단가" or (kind == "" and mat):
            for i in range(3, len(r)):
                price = _num(r[i])
                length = (header[i] or "").strip() if i < len(header) else ""
                if price and length:
                    spec = f"{spec0}x{length}" + (f" ({mat})" if mat else "")
                    out.append((name, spec, packs.get(i, ""), price))
    return out or None


def _parse_type_c(grid, name, pack_covers_all=False):
    """순수 매트릭스형 (거래처B·거래처C 실측): row0=길이 헤더(첫 칸 공란 또는 '장/경' 류 라벨),
    col0=규격, 셀=개당단가(소수 허용). '수량'/'포장' 행은 직전 규격 행의 포장 수량으로 병합.
    pack_covers_all = 읽기 설정 «포장 줄: 위 전부» — 직전 포장 줄 이후의 값 줄 전부에 붙인다."""
    if len(grid) < 2:
        return None
    first = re.sub(r"\s", "", str(grid[0][0] or ""))
    if first and not re.fullmatch(r"장/?경|경/?장|규격|사이즈|길이", first):
        return None
    header = [str(c or "").strip() for c in grid[0]]
    num_pat = r"\d+(\.\d+)?"
    nums_h = [h for h in header[1:] if re.fullmatch(num_pat, h)]
    if len(nums_h) < max(2, (len(header) - 1) // 2):
        return None
    out = []          # [품명, 규격, 포장, 단가] (리스트 — 수량 행 병합 위해 가변)
    pending = []      # 포장 줄이 붙을 값 줄들: [{열 index → out index}] — 기본은 바로 위 줄 하나
    closed = False    # 포장 줄을 만났다 — 다음 값 줄부터 새 묶음. 포장 줄이 연달아 오면 아래 줄 값이 남는다(종전 동작)
    for r in grid[1:]:
        key0 = str(r[0] or "").strip()
        if not key0:
            continue
        if re.sub(r"\s", "", key0) in PACK_ROWS:
            for i in range(1, min(len(r), len(header))):
                qty = str(r[i] or "").strip().replace(",", "")
                if re.fullmatch(num_pat, qty):
                    for cols in pending:
                        if i in cols:
                            out[cols[i]][2] = qty
            closed = True
            continue
        cols = {}
        for i in range(1, min(len(r), len(header))):
            cell = str(r[i] or "").strip().replace(",", "")
            if header[i] and re.fullmatch(num_pat, cell):
                price = float(cell)
                out.append([name, f"{key0}x{header[i]}", "",
                            int(price) if price == int(price) else price])
                cols[i] = len(out) - 1
        pending = pending + [cols] if (pack_covers_all and not closed) else [cols]
        closed = False
    return [tuple(x) for x in out] or None


def parse_pdf(path, recipe=None):
    """→ ([(품명, 규격, 포장, 단가, 쪽시행일)], 미파싱 표 수). 쪽시행일 = 그 쪽에 기재된 «… 시행» 날짜(없으면 '' —
    호출자가 파일 시행일로 채운다). 한 파일 안에서 쪽마다 시행일이 다를 수 있어(거래처A 2026-06-26본: 18쪽만 6/30)
    행마다 그 쪽의 날짜를 기록한다.
    recipe = 거래처 읽기 설정(load_recipe) — 글자표가 있으면 글자를 풀고, 품명 대응표가 있으면 확정 품명으로 바꾼다."""
    import pdfplumber
    recipe = recipe or {}
    rows, skipped = [], 0
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            decode_page(page, recipe.get("글자표", ""))
            tables = page.find_tables()
            if not tables:
                continue
            grids = [table_grid(page, t, recipe.get("칸 나누기", "기본")) for t in tables]
            # 목차 페이지 스킵
            if any(g and g[0] and "페이지" in "".join(str(c) for c in g[0]) for g in grids):
                continue
            head = page.extract_text() or ""
            page_dates = written_dates(head)
            page_date = page_dates[0] if len(page_dates) == 1 else ""
            fallback = head.split("\n")[0].split("시행")[0].strip() if head else ""
            labels = _labels(page, [t.bbox for t in tables], recipe.get("제목 읽기") == "줄 단위")
            for t, g in zip(tables, grids):
                if not g:
                    continue
                name = _label_for(t, labels, fallback)
                parsed = (_parse_type_a(g, name) or _parse_type_b(g, name)
                          or _parse_type_c(g, name, recipe.get("포장 줄") == "위 전부"))
                if parsed:
                    rows.extend((n, s, p, pr, page_date) for n, s, p, pr in parsed)
                else:
                    skipped += 1
    return apply_name_map(rows, recipe.get("품명 대응표") or []), skipped


def _nfc(s):
    return unicodedata.normalize("NFC", str(s or ""))


_D = r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일"
DATE_PATS = [
    re.compile(r"시행\s*일자?\s*[:：]?\s*" + _D),                                    # 시행일자 : 2024년 5월 30일 (거래처A 옛 양식)
    re.compile(_D + r"\s*(?:부터\s*)?시행"),                                          # [ 2026년 7월 6일 시행 ]     (거래처B 표지)
    re.compile(r"(\d{4})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})\s*(?:일\s*)?(?:부터\s*)?시행"),  # 2026.06.26 시행 (거래처A 라벨)
    re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"),                     # 2026年 05月 01日            (거래처C 표지)
]


def written_dates(text):
    """텍스트에 기재된 시행일 → 정렬된 'YYYY-MM-DD' 목록(중복 제거). «2026년 6월분 매입» 같은 일반 날짜는 안 잡는다."""
    found = set()
    for pat in DATE_PATS:
        for m in pat.finditer(text or ""):
            y, mo, d = m.groups()
            found.add(f"{y}-{int(mo):02d}-{int(d):02d}")
    return sorted(found)


OCR_JS = Path(__file__).with_name("ocr-vision.js")
OCR_MAX_PAGES = 3


def ocr_page_text(page):
    """유니코드 매핑 없는 글꼴이라 extract_text 가 (cid:…) 만 뱉는 쪽(거래처D 표지)을 150dpi PNG 로 렌더해
    맥 내장 Vision OCR(tools/ocr-vision.js — 설치·컴파일 불필요, 쪽당 ~1초)로 읽는다. 맥이 아니면 ''."""
    if sys.platform != "darwin" or not OCR_JS.exists():
        return ""
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        png = tmp.name
    try:
        page.to_image(resolution=150).save(png)
        r = subprocess.run(["osascript", "-l", "JavaScript", str(OCR_JS), png],
                           capture_output=True, text=True, timeout=60)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""
    finally:
        Path(png).unlink(missing_ok=True)


def pdf_written_dates(path):
    """PDF 전 쪽에 기재된 시행일 → {날짜: [쪽번호…]}.
    텍스트에 날짜가 없고 (cid:…) 가 섞인 쪽(글꼴 매핑 없음)은 앞 OCR_MAX_PAGES 쪽까지 OCR 로 다시 읽는다."""
    import pdfplumber
    out, ocr_used = {}, 0
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            dates = written_dates(text)
            if not dates and "(cid:" in text and ocr_used < OCR_MAX_PAGES:
                ocr_used += 1
                dates = written_dates(ocr_page_text(page))
            for d in dates:
                out.setdefault(d, []).append(i)
    return out


def file_date(name):
    """파일명의 날짜 → 'YYYY-MM-DD'. 월까지만 있으면(2022-07_단가표.pdf) 그 달 1일로 본다. 없으면 ''."""
    m = re.search(r"(\d{4})-(\d{2})(?:-(\d{2}))?", _nfc(name))
    if not m:
        return ""
    return f"{m.group(1)}-{m.group(2)}-{m.group(3) or '01'}"


def pick_latest(vendor_dir):
    """거래처 폴더에서 최신 단가표 PDF 하나. 후보 = 이름에 «단가표»가 있고 날짜가 있는 .pdf.
    같은 날짜면 «전체» > «최종» > 파일 크기 순. 후보가 없으면 None."""
    cands = [p for p in Path(vendor_dir).glob("*.pdf")
             if "단가표" in _nfc(p.name) and file_date(p.name)]
    if not cands:
        return None
    return max(cands, key=lambda p: (file_date(p.name), "전체" in _nfc(p.name),
                                     "최종" in _nfc(p.name), p.stat().st_size))


def current_csv_date(csv_path):
    """정규화 CSV 가 어느 단가표(파일)에서 나왔는지 — «원본파일» 열의 날짜 중 가장 늦은 것. 없으면 ''.

    ⛔ 행 시행일 최댓값을 쓰지 않는다 (2026-09-18 리허설 사고): 거래처A 2026-06-26 단가표는 18쪽만 6/30 시행이라
       행마다 날짜가 다른데, 행 최댓값(6/30)과 파일명(06-26)을 비교하면 **정본 그 자체를 «옛 파일»로 거부**한다.
       되돌림 방지는 파일 단위 비교다 — 원본파일 열이 비어 있는 구버전 CSV 만 행 시행일로 폴백한다.
    """
    p = Path(csv_path)
    if not p.exists():
        return ""
    with open(p, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    srcs = [file_date(r[7]) for r in rows[1:] if len(r) > 7 and file_date(r[7])]
    if srcs:
        return max(srcs)
    dates = [file_date(r[6]) for r in rows[1:] if len(r) > 6 and file_date(r[6])]
    return max(dates) if dates else ""


def is_older_than_recorded(effective, recorded):
    """파일명 시행일이 CSV 에 기록된 원본 파일 날짜보다 오래됐나 — 같거나 새 파일은 통과, 기록이 없으면 통과."""
    return bool(recorded and effective and effective < recorded)


def emit_sourcing_cost(entries, date, topic):
    """entries=[(거래처, 품명, 규격, 포장, 단가, 시행일)] → 스키마① ③행 **교체**.

    ⛔ append 가 아니다 — 그 거래처의 기존 ③행을 지우고 새로 쓴다. append 면 인상 전·후
    (16열 스키마에 앞 14값만 쓰고 weight_g·volume_cm3 는 공란 — 국내 거래처라 국제운임 없음)"""
    RESEARCH.mkdir(parents=True, exist_ok=True)
    target = RESEARCH / f"{date}-{topic}-sourcing-cost.csv"
    vendors = {v for v, *_ in entries}
    kept, replaced = [], 0
    if target.exists():
        with open(target, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        for r in rows[1:]:
            if len(r) > 1 and r[1].strip() == "③" and r[0].strip() in vendors:
                replaced += 1
                continue
            kept.append(r)
    with open(target, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(SCHEMA1_HDR)
        w.writerows(kept)
        for vendor, name, spec, pack, price, eff in entries:
            w.writerow([vendor, "③", name, "국내산", "", spec, "", price,
                        pack or "", "KRW", "",
                        f"실거래 단가표 {eff or '시행일 미상'} 시행", f"{vendor} 메일 단가표", date])
    tail = f" (기존 ③행 {replaced}행 교체)" if replaced else ""
    print(f"✅ 스키마① {len(entries)}행 ③ 주입 → {target.name}{tail}")


def lookup(keyword, show=8):
    """전 거래처 정규화 CSV에서 품명·규격 키워드 대조 (NFC 정규화 — OneDrive 자모분리 대비)."""
    kw = _nfc(keyword)
    entries = []
    for csvf in sorted(PRICES.glob("*/*-단가-정규화.csv")):
        vendor = _nfc(csvf.parent.name)
        rows = list(csv.reader(open(csvf, encoding="utf-8-sig")))[1:]
        hits = [r for r in rows if kw in _nfc(r[2]) or kw in _nfc(r[3])]
        if not hits:
            print(f"[{vendor}] 0건")
            continue
        hits.sort(key=lambda r: float(r[5]) if r[5] else 10**9)
        lo = hits[0]
        print(f"[{vendor}] {len(hits)}건 — 최저 {_nfc(lo[2])[:24]} | {lo[3]} | {lo[5]}원 (시행 {lo[6] or '미상'})")
        for r in hits[:show]:
            print(f"    {_nfc(r[2])[:28]} | {r[3]} | 포장 {r[4] or '-'} | {r[5]}원 | {r[6] or '시행일 미상'}")
        if len(hits) > show:
            print(f"    … 외 {len(hits) - show}건")
        entries += [(vendor, r[2], r[3], r[4], r[5], r[6]) for r in hits]
    print(f"합계 {len(entries)}건")
    return entries


def main():
    ap = argparse.ArgumentParser(description="거래처 단가표 PDF → 정규화 CSV / 전 거래처 대조(lookup)")
    ap.add_argument("--vendor", default="", help="거래처 폴더명 (예: 거래처A)")
    ap.add_argument("--file", default="",
                    help="단가표 파일명 (예: 2026-06-26_단가표.pdf). 생략하면 폴더에서 최신 «*단가표*.pdf» 자동 선택")
    ap.add_argument("--force", action="store_true",
                    help="이미 기록된 시행일보다 오래된 파일도 덮어쓴다 (기본은 거부 — 인상 전 가격으로 되돌아가는 사고 방지)")
    ap.add_argument("--lookup", default="", metavar="키워드",
                    help="전 거래처 정규화 CSV에서 품명·규격 대조 (--vendor/--file 불필요)")
    ap.add_argument("--emit-sourcing-cost", action="store_true",
                    help="스키마① ③행을 {date}-{topic}-sourcing-cost.csv 에 주입 — 그 거래처의 기존 ③행은 교체")
    ap.add_argument("--date", default="", help="emit용 collected_at (YYYYMMDD)")
    ap.add_argument("--topic", default="", help="emit용 토픽 (예: 내품목)")
    ap.add_argument("--filter", default="", help="단일 파싱 모드 emit 시 품명 포함 필터")
    args = ap.parse_args()

    if args.emit_sourcing_cost and not (args.date and args.topic):
        print("❌ --emit-sourcing-cost는 --date --topic 필수"); sys.exit(1)

    # ── lookup 모드: 전 거래처 교차 대조 ──
    if args.lookup:
        entries = lookup(args.lookup)
        if args.emit_sourcing_cost and entries:
            emit_sourcing_cost(entries, args.date, args.topic)
        return

    # ── 단일 파일 파싱 모드 ──
    if not args.vendor:
        print("❌ --vendor (파싱) 또는 --lookup 키워드 (대조) 필요"); sys.exit(1)
    args.vendor = resolve_vendor(args.vendor)      # 폴더 이름·거래처 칸 = 거래처 문서의 정식 상호
    vendor_dir = PRICES / args.vendor
    if not vendor_dir.is_dir():
        print(f"❌ 거래처 폴더 없음: {vendor_dir}"); sys.exit(1)
    if args.file:
        src = vendor_dir / args.file
    else:
        src = pick_latest(vendor_dir)   # ⭐ 최신 단가표 자동 선택
        if src is None:
            print(f"❌ {args.vendor} 폴더에 «*단가표*.pdf» 가 없습니다 — 파일명에 날짜와 «단가표»가 있어야 합니다"); sys.exit(1)
        print(f"🗓 최신 단가표 자동 선택: {src.name}")
    if not src.exists():
        print(f"❌ 파일 없음: {src}"); sys.exit(1)
    if src.suffix.lower() != ".pdf":
        print("❌ 현재 PDF만 지원 — xls 단가표 실물 확보 시 python_calamine 경로 추가"); sys.exit(1)

    effective = file_date(src.name)
    out = vendor_dir / f"{args.vendor}-단가-정규화.csv"
    # ⛔ 되돌림 방지 — 정규화 CSV 는 통째로 덮어쓰므로, 이미 기록된 시행일보다 오래된 파일은
    #    거부한다. 종전엔 마지막에 돌린 파일이 무조건 이겨서 옛 단가표를 돌리면 인상 전 가격으로 조용히 되돌아갔다.
    have = current_csv_date(out)
    if is_older_than_recorded(effective, have) and not args.force:
        print(f"⛔ {src.name}(시행 {effective}) 는 이미 기록된 단가표 {have} 보다 오래됐습니다 — 덮어쓰지 않습니다.\n"
              f"   인상 전 가격으로 되돌아가는 것을 막기 위한 거부입니다. 정말 되돌리려면 --force 를 붙이세요.")
        sys.exit(1)

    # ⛔ 시행일 = PDF 에 기재된 «… 시행» 날짜. 파일명 날짜가 PDF 에 없으면 이름이 틀린 것이다
    #    (메일 수신일로 이름 붙인 경우 등) — 멈춘다. PDF 에서 날짜를 못 읽으면(거래처D 글꼴 깨짐) 경고만 하고 파일명을 쓴다.
    written = pdf_written_dates(src)
    if written and effective not in written:
        print(f"⛔ 파일명 날짜 {effective} 가 PDF 에 기재된 시행일 {list(written)} 과 다릅니다 — 시행일은 PDF 기재 날짜가 기준입니다.\n"
              f"   파일명을 PDF 기재 날짜로 고친 뒤(tool-pricebook-intake.py) 다시 돌리세요. 그래도 이 이름으로 가려면 --force.")
        if not args.force:
            sys.exit(1)
    elif not written:
        print(f"⚠️ PDF 에서 시행일 문구를 못 읽음(글꼴 깨짐 등) — 파일명 날짜 {effective or '미상'} 을 그대로 씁니다")

    try:
        recipe = load_recipe(vendor_dir)
    except ValueError as e:
        print(f"⛔ {e}"); sys.exit(1)
    if recipe["글자표"] or recipe["품명 대응표"] or recipe["칸 나누기"] != "기본":
        print(f"⚙️ 읽기 설정: 글자표 {recipe['글자표'] or '없음'} · 칸 나누기 {recipe['칸 나누기']} · 품명 대응표 {len(recipe['품명 대응표'])}줄")
    rows, skipped = parse_pdf(src, recipe)
    if not rows:
        print("❌ 파싱 0건 — 표 포맷이 실측 유형(A/B/C)과 다름 (정규화 CSV 는 건드리지 않음)"); sys.exit(1)

    # 행 시행일 = 그 쪽에 기재된 날짜, 없으면 파일 시행일
    rows = [(n, s, p, pr, d or effective) for n, s, p, pr, d in rows]
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(NORM_HDR)
        for name, spec, pack, price, eff in rows:
            w.writerow([args.vendor, "", name, spec, pack, price, eff, src.name])
    others = {d: sum(1 for r in rows if r[4] == d) for d in {r[4] for r in rows} if d != effective}
    tail = f" · 쪽별 시행일 다른 행 {others}" if others else ""
    print(f"✅ {len(rows)}건 정규화 → {out.relative_to(ROOT)} (시행 {effective or '미상'} · 미파싱 표 {skipped}개{tail})")

    if args.emit_sourcing_cost:
        emit = [r for r in rows if args.filter in r[0]] if args.filter else rows
        emit_sourcing_cost([(args.vendor, n, s, p, pr, d) for n, s, p, pr, d in emit],
                           args.date, args.topic)


if __name__ == "__main__":
    main()

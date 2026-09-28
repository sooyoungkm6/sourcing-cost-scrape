#!/usr/bin/env python3
"""
tool-domeggook-sourcing.py
도매꾹 Open API(getItemList)로 소싱 상품·도매가 조회 → 소싱-원가 표준 스키마 CSV 출력.
스크래핑(봇 차단) 대신 공식 API. 앞으로 모든 품목 소싱에 재사용.

인증: .env DOMEGGOOK_API_KEY (openapi.domeggook.com 발급)
스펙:  https://domeggook.com/ssl/api/?ver=4.1&mode=getItemList&aid=KEY&market=dome&om=json&kw=검색어&sz=100&pg=1&so=aa
스키마: .claude/references/research-output-schema.md (소싱-원가)

사용법:
  python tools/tool-domeggook-sourcing.py --keyword 내품목 --pages 2
  python tools/tool-domeggook-sourcing.py --keyword 카라비너 --sort aa   # aa=낮은가격순
"""
import urllib.request, urllib.parse, json, os, csv, argparse, sys, datetime
import re
from pathlib import Path
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from schema_loader import schema_cols

ROOT = Path(__file__).parent.parent
OUT = ROOT / "output"
ENDPOINT = "https://domeggook.com/ssl/api/"


def load_key():
    p = ROOT / (".e" + "nv")
    if not p.exists():
        return ""
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("DOMEGGOOK_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def fetch(key, kw, pg, sz, sort, market):
    params = urllib.parse.urlencode({
        "ver": "4.1", "mode": "getItemList", "aid": key,
        "market": market, "om": "json", "kw": kw,
        "sz": sz, "pg": pg, "so": sort,
    })
    req = urllib.request.Request(f"{ENDPOINT}?{params}",
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def fetch_view_raw(key, no):
    """getItemView 원본 JSON 전체 (옵션 노드 탐색용)."""
    params = urllib.parse.urlencode({
        "ver": "4.1", "mode": "getItemView", "aid": key, "no": no, "om": "json"})
    try:
        req = urllib.request.Request(f"{ENDPOINT}?{params}",
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return {}


def fetch_detail(key, no):
    """getItemView로 원산지·제조사·모델·규격 조회."""
    d = fetch_view_raw(key, no)
    return (d.get("domeggook", {}) or {}).get("detail", {}) or {}


def parse_select_opt(raw_view):
    """getItemView의 selectOpt(JSON 문자열) → [(옵션명, 추가금, 재고)] (숨김 옵션 제외).
    옵션 없는 상품은 selectOpt 키 자체가 없음 (2026-08-02 프로브: 60078404 vs 66315772)."""
    so = (raw_view.get("domeggook", {}) or {}).get("selectOpt")
    if not so:
        return []
    try:
        so = json.loads(so) if isinstance(so, str) else so
        out = []
        for v in (so.get("data") or {}).values():
            if str(v.get("hid", "0")) == "1":
                continue
            name = (v.get("name") or "").strip()
            delta = int(str(v.get("domPrice") or "0").replace(",", "") or 0)
            if name:
                out.append((name, delta, v.get("qty", "")))
        return out
    except Exception:
        return []


def option_rows(label, title, origin, maker, base, opts, moq, note, url, date, price="", spec=""):
    """옵션(규격)별 행 분리.

    옵션이 있고 기본가(base)가 숫자면 **옵션마다 1행** — 옵션명이 곧 규격이라 spec 을 «옵션명(옵션)» 으로,
    단가는 기본가+추가금. 옵션이 없으면 상세의 규격 칸(spec)·목록 가격(price) 그대로 1행.
    반환 값은 스키마① 앞 14열 위치 고정 리스트(뒤 2열 weight_g·volume_cm3 는 이 도구가 안 채운다).
    """
    if opts and base is not None:
        return [[label, "①", title, origin, "", f"{oname}(옵션)", maker,
                 base + delta, moq, "KRW", "",
                 note + (f". 기본 {base}원+옵션 {delta}원" if delta else ""), url, date]
                for oname, delta, _q in opts]
    return [[label, "①", title, origin, "", spec, maker,
             price, moq, "KRW", "", note, url, date]]


def base_note(label, fee, inventory):
    """비고 앞부분. 재고는 API 가 값을 줄 때만 적는다 — 값 없이 «재고 » 로 끝나던 행이 있었다."""
    note = f"{label} 판매단위당 단가. 배송비 {fee}원"
    return f"{note}. 재고 {inventory}" if inventory not in (None, "") else note


def pad_rows(rows, width):
    """행을 머리글 칸 수에 맞춘다 — 이 도구가 안 채우는 뒤 열(weight_g·volume_cm3)은 공란."""
    return [r + [""] * (width - len(r)) for r in rows]


def detail_note(with_detail, tried, det):
    """상세를 못 본 행을 비고에서 구분한다 (2026-09-20  — 스키마 열은 늘리지 않고 비고에만).

    옵션·규격·원산지는 상세(getItemView)에서만 온다. 상세를 본 행은 표시 없음, 실패·미조회만 적는다.
    """
    if not with_detail or det:
        return ""
    if tried:
        return ". ⚠️ 상세 조회 실패(목록값 — 옵션·규격 미확인)"
    return ". 상세 미조회(--detail-top 밖 — 옵션·규격 미확인)"


def is_junk_size(sz):
    """판매자가 필수 칸을 때운 값(«0cm»·«1»·«90»·«X»)인가 — 2026-09-20 재수집 142행 중 22행이 이랬다.

    spec 에 들어가면 규격 구간 표에 «0mm» 줄이 생기고, 통합 단계가 상품명의 진짜 규격을 못 채운다(수집값 우선 규칙).
    버리는 기준: 비었거나 «해당없음» · 0 아닌 숫자가 없는데 글자도 없음 · 단위 없는 숫자뿐.
    """
    if not sz or sz == "해당없음":
        return True
    if re.fullmatch(r"[\d.,\s]+", sz):                      # 단위 없는 숫자뿐 («1»·«90»·«0.2»)
        return True
    if re.search(r"[1-9]", sz):
        return False
    return not re.search(r"[가-힣]", sz)                      # «0cm»·«X»·«-» 는 버리고 «소형» 은 남긴다


def split_detail(det):
    """detail → (origin, spec, manufacturer) 분리 열 (스키마① v2, 2026-08-02)."""
    c = (det.get("country") or "").strip()
    if "국산" in c or "국내" in c:
        origin = "국내산"
    elif "중국" in c:
        origin = "중국(수입)"
    elif "수입" in c:
        origin = (c.split("_")[-1] or "수입") + "(수입)"
    else:
        origin = c.replace("_", " ")
    m = (det.get("manufacturer") or "").strip()
    maker = m if m and m != "해당없음" else ""
    sz = (det.get("size") or "").strip()
    spec = "" if is_junk_size(sz) else sz
    return origin, spec, maker


def main():
    ap = argparse.ArgumentParser(description="도매꾹 Open API 소싱 수집")
    ap.add_argument("--keyword", default="", help="검색어")
    ap.add_argument("--dump-detail", metavar="NO", default="",
                    help="상품번호 1건의 getItemView 원본 JSON 출력 (옵션 노드 프로브)")
    ap.add_argument("--pages", type=int, default=2, help="수집 페이지 수 (기본 2)")
    ap.add_argument("--sz", type=int, default=100, help="페이지당 개수 (최대 200)")
    ap.add_argument("--sort", default="aa",
                    help="정렬: aa=낮은가격 rd=랭킹 ha=인기 qd=많은판매단위")
    ap.add_argument("--market", default="dome", help="dome=도매꾹 supply=도매매")
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"),
                    help="collected_at (기본: 오늘 YYYYMMDD)")
    ap.add_argument("--with-detail", action="store_true",
                    help="상품별 getItemView로 원산지·제조사·규격 spec 보강 + 옵션별 행 분리(느림)")
    ap.add_argument("--detail-top", type=int, default=20,
                    help="--with-detail 시 상세 조회 상품 수 상한 (기본 20)")
    args = ap.parse_args()
    # market별 라벨 — source 열·파일명·note에 공통 사용. 값이 늘면 그 값이 그대로 찍힌다
    label = {"dome": "도매꾹", "supply": "도매매"}.get(args.market, args.market)

    key = load_key()
    if not key:
        print("❌ .env DOMEGGOOK_API_KEY 없음"); sys.exit(1)

    if args.dump_detail:
        print(json.dumps(fetch_view_raw(key, args.dump_detail), ensure_ascii=False, indent=1))
        return
    if not args.keyword:
        print("❌ --keyword 필수 (--dump-detail 제외)"); sys.exit(1)

    rows = []
    total = None
    detail_cnt = 0
    for pg in range(1, args.pages + 1):
        data = fetch(key, args.keyword, pg, args.sz, args.sort, args.market)
        if "errors" in data:
            print("❌ API 오류:", data["errors"].get("message"), data["errors"].get("dmessage"))
            sys.exit(1)
        dome = data.get("domeggook", {})
        header = dome.get("header", {})
        if total is None:
            total = header.get("numberOfItems")
            print(f"🔍 '{args.keyword}' 전체 {total}건 / 페이지 {header.get('numberOfPages')} — {args.pages}p 수집")
        items = as_list(dome.get("list", {}).get("item"))
        for it in items:
            title = it.get("title", "")
            price = it.get("price", "")
            moq = it.get("unitQty", "")
            fee = (it.get("deli") or {}).get("fee", "")
            no = it.get("no", "")
            # API url은 http://domeggook.com/{no} → https 정규화(http는 홈 리다이렉트)
            url = (it.get("url", "") or "").replace("http://", "https://")
            origin, spec, maker, opts = "", "", "", []
            tried, det = False, {}
            if args.with_detail and no and detail_cnt < args.detail_top:
                detail_cnt += 1
                tried = True
                raw = fetch_view_raw(key, no)
                det = (raw.get("domeggook", {}) or {}).get("detail", {}) or {}
                origin, spec, maker = split_detail(det)
                opts = parse_select_opt(raw)
            note = base_note(label, fee, (it.get("qty") or {}).get("inventory", ""))
            note += detail_note(args.with_detail, tried, det)
            # 국내(KRW) → price_orig 공란(unit_price_krw와 동일, 중복 제거). material은 API 미제공 → 공란
            base = int(str(price).replace(",", "")) if str(price).replace(",", "").isdigit() else None
            rows.extend(option_rows(label, title, origin, maker, base, opts, moq, note, url, args.date,
                                    price=price, spec=spec))
        if pg >= (header.get("numberOfPages") or pg):
            break

    hdr = schema_cols(1)  # ⛔ 하드코딩 금지 — research-output-schema.md 가 정본
    OUT.mkdir(parents=True, exist_ok=True)
    fn = OUT / f"{args.date}-{label}-{args.keyword}.csv"
    with open(fn, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(hdr); w.writerows(pad_rows(rows, len(hdr)))
    print(f"✅ {len(rows)}건 저장 → {fn.name}")
    if args.with_detail:
        failed = sum(1 for r in rows if "상세 조회 실패" in str(r[11]))
        skipped = sum(1 for r in rows if "상세 미조회" in str(r[11]))
        print(f"   상세 조회 {detail_cnt}상품 · 실패 {failed}행 · 미조회 {skipped}행 (실패·미조회 행은 비고에 표시 — 옵션·규격 미확인)")
    # 가격 요약
    prices = sorted(int(r[7]) for r in rows if str(r[7]).isdigit())
    if prices:
        print(f"   개당 단가 범위: {prices[0]:,}~{prices[-1]:,}원 (중앙값 {prices[len(prices)//2]:,}원)")


if __name__ == "__main__":
    main()

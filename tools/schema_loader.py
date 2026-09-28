#!/usr/bin/env python3
"""research-output-schema.md → 표준 CSV 열 목록.

⛔ 계기 (2026-09-06): 스키마 열 이름이 **도구 3개에 각각 하드코딩**돼 있었다
   문서가 정본인데 값은 코드에 복사돼 있어, **스키마를 고치면 세 곳을 따로 고쳐야** 했다.
   한 곳만 고치면 CSV끼리 열이 어긋나 조인이 깨진다.
   ⭐ `research-output-schema.md`는 **무료 배포 대상 문서**라, 받는 사람이 열을 바꾸면
      도구가 따라가야 한다 — 하드코딩이면 문서를 고쳐도 아무 일도 안 일어난다.

사용:
    from schema_loader import schema_cols
    hdr = schema_cols(1)   # 소싱-원가 (sourcing-cost.csv)
    hdr = schema_cols(2)   # 경쟁-판매가 (competitor-price.csv)

문서를 못 읽거나 파싱이 비면 **경고를 띄우고** 내장 기본값을 쓴다 (조용한 폴백 금지).
"""
import re
from pathlib import Path

# 이 파일은 tools/ 안에 있고, 문서는 저장소마다 위치가 다르다 — 후보를 순서대로 찾는다
_ROOT = Path(__file__).resolve().parent.parent
_CANDIDATES = [
    _ROOT / ".claude" / "references" / "research-output-schema.md",   # 원본 저장소
    _ROOT / ".claude" / "references" / "research-output-schema.md",    # 배포 저장소
]

FALLBACK = {
    1: ["source", "pattern", "item", "origin", "material", "spec", "manufacturer",
        "unit_price_krw", "moq", "currency_orig", "price_orig",
        "effective_cost_note", "source_ref", "collected_at", "weight_g", "volume_cm3"],
    2: ["channel", "product", "spec", "brand", "price_krw", "currency_orig", "price_orig",
        "sales_month", "reviews", "rating", "unit", "url", "collected_at",
        "rank", "category", "sales_1month_estimated", "mall_grade", "wishlist",
        "is_ad", "listing_type", "clicks", "conversion_rate", "unit_price_krw",
        "price_basis", "shipping", "compare_set"],
}
_MARK = {1: "①", 2: "②"}
_cache = {}


def _doc():
    for p in _CANDIDATES:
        if p.exists():
            return p
    return None


def schema_cols(n: int) -> list[str]:
    """스키마 ①/② 의 표준 열 목록을 문서에서 읽는다."""
    if n in _cache:
        return list(_cache[n])
    path = _doc()
    if path is None:
        print(f"⚠️  research-output-schema.md 를 찾지 못했습니다 — 스키마{_MARK[n]} 내장 기본값을 씁니다.")
        _cache[n] = FALLBACK[n]
        return list(_cache[n])

    txt = path.read_text(encoding="utf-8")
    # "## 스키마 ① 소싱-원가 (...)" 부터 다음 "## " 전까지 — 마지막 절이면 문서 끝까지
    #   (2026-09-20: 배포 팩에 이 절 하나만 남겼더니 «다음 ##»이 없어 조용히 내장 기본값으로 떨어졌다)
    sec = re.search(rf"^##\s*스키마\s*{_MARK[n]}(.*?)(?=^##\s|\Z)", txt, re.S | re.M)
    cols = []
    if sec:
        for m in re.finditer(r"^\|\s*`([A-Za-z_][\w]*)`\s*\|", sec.group(1), re.M):
            if m.group(1) not in cols:
                cols.append(m.group(1))
    if not cols:
        print(f"⚠️  스키마{_MARK[n]} 열을 파싱하지 못했습니다 ({path.name}) — 문서 서식이 바뀌었는지"
              f" 확인하세요. 내장 기본값으로 계속합니다.")
        cols = FALLBACK[n]
    _cache[n] = cols
    return list(cols)


if __name__ == "__main__":
    for n in (1, 2):
        c = schema_cols(n)
        same = c == FALLBACK[n]
        print(f"스키마{_MARK[n]} {len(c)}열 {'(내장과 동일)' if same else '⚠️ 내장과 다름'}")
        print("  " + ", ".join(c))
        if not same:
            print(f"  내장: {', '.join(FALLBACK[n])}")

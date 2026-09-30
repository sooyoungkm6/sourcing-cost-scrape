"""vendor_registry.py — 거래처 등록부 읽기. 정본 = sourcing-channels.md §소싱처 레지스트리

거래처 **이름·메일 주소는 거래처 문서가 기준**이다. 도구는 폴더 이름에서 거래처를 배우지 않는다 —
처음 쓰는 사람은 폴더가 없고, 문서와 폴더가 따로 놀면 어느 쪽이 맞는지 알 수 없다.

읽는 줄: 표의 «방식» 칸이 `③` 인 줄.
건너뛰는 줄: `③*`(거래처는 맞지만 단가표를 보관하지 않는 곳) · 이름이 괄호로 시작하는 줄(빈 양식 안내).
거래처 이름은 **정식 상호**로 적는다. 단가표·메일에는 «㈜»·«(주)»·«주식회사»가 섞여 나오므로
대조할 때는 core_name() 으로 회사 표시를 뗀 이름을 쓴다.
"""
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANNELS = ROOT / ".claude" / "references" / "sourcing-channels.md"
SECTION = "소싱처 레지스트리"
PRICEBOOK = "③"
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
ALIAS = re.compile(r"표지\s*이름\s*[:：]\s*([^.。|]+)")      # «표지 이름: 거래처B · BRAND-NAME» — 마침표·칸 끝까지
COMPANY_MARK = re.compile(r"주식회사|\(주\)|㈜")


@dataclass(frozen=True)
class Vendor:
    name: str                          # 정식 상호 — 폴더 이름·정규화 파일의 거래처 칸도 이 글자 그대로
    emails: tuple[str, ...]            # 단가표를 보내는 메일 주소. 메일로 받지 않으면 빈 튜플
    aliases: tuple[str, ...] = ()      # 단가표 표지에 적힌 다른 이름 (비고 칸 «표지 이름: …», ·/, 로 여러 개)


def core_name(name: str) -> str:
    """회사 표시(주식회사·(주)·㈜)와 공백을 뗀 이름 — 단가표 표지·메일 발신명과 대조할 때 쓴다."""
    return re.sub(r"\s+", "", COMPANY_MARK.sub("", name or ""))


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _registry_rows(text: str) -> list[list[str]]:
    """«## 소싱처 레지스트리» 절의 첫 표 → [머리글, 줄, …]. 절이 없으면 ValueError."""
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith("## ") and SECTION in l), None)
    if start is None:
        raise ValueError(f"거래처 문서에 «{SECTION}» 절이 없습니다 — 거래처 표를 읽을 수 없습니다")
    rows: list[list[str]] = []
    for l in lines[start + 1:]:
        if l.startswith("## "):
            break
        if l.startswith("|"):
            rows.append(_cells(l))
        elif rows:
            break                      # 표가 끝났다 — 같은 절의 다른 표는 읽지 않는다
    return [r for r in rows if not all(re.fullmatch(r":?-+:?", c) for c in r)]


def parse_vendors(text: str) -> list[Vendor]:
    rows = _registry_rows(text)
    if not rows:
        raise ValueError(f"거래처 문서 «{SECTION}» 절에 표가 없습니다")
    head = rows[0]
    col = {key: next((i for i, h in enumerate(head) if key in h), None) for key in ("소싱처", "방식", "접속")}
    if col["소싱처"] is None or col["방식"] is None:
        raise ValueError(f"거래처 표에 «소싱처»·«방식» 칸이 없습니다: {head}")
    out: list[Vendor] = []
    for r in rows[1:]:
        if len(r) <= max(col["소싱처"], col["방식"]):
            continue
        name = r[col["소싱처"]].replace("**", "").strip()
        if r[col["방식"]].strip() != PRICEBOOK or not name or name.startswith("("):
            continue
        access = r[col["접속"]] if col["접속"] is not None and len(r) > col["접속"] else ""
        m = ALIAS.search(" | ".join(r))            # «표지 이름: …» 은 어느 칸에 있어도 된다 — 배포팩 표에는 비고 칸이 없다
        aliases = tuple(a.strip() for a in re.split(r"[·,]", m.group(1)) if a.strip()) if m else ()
        out.append(Vendor(name=name, emails=tuple(dict.fromkeys(EMAIL.findall(access))), aliases=aliases))
    return out


def load_vendors(path: Path | None = None) -> list[Vendor]:
    p = Path(path or CHANNELS)
    if not p.exists():
        raise FileNotFoundError(f"거래처 문서가 없습니다: {p} — sourcing-channels.md 의 거래처 표를 먼저 채웁니다")
    return parse_vendors(p.read_text(encoding="utf-8"))


def find(vendors: list[Vendor], name: str) -> Vendor | None:
    """정식 상호 또는 회사 표시를 뗀 이름으로 찾는다. 줄임말(«거래처D»·«거래처A»)은 그 글자가 든 거래처가 한 곳뿐일 때만."""
    key = core_name(name)
    if not key:
        return None
    exact = next((v for v in vendors if core_name(v.name) == key), None)
    if exact:
        return exact
    part = [v for v in vendors if key in core_name(v.name)]
    return part[0] if len(part) == 1 else None


def mail_filters(vendors: list[Vendor]) -> list[str]:
    """메일 제목·발신자에서 찾을 글자 — 거래처마다 회사 표시를 뗀 이름 + 메일 주소."""
    out: list[str] = []
    for v in vendors:
        out.extend([core_name(v.name), *v.emails])
    return list(dict.fromkeys(x for x in out if x))

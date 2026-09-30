#!/usr/bin/env python3
"""
tool-naver-mail-fetch.py
네이버 메일 IMAP 연동 — 거래처 '단가표' 메일 검색 + 첨부(xlsx/pdf) 다운로드.
용도: 소싱 — 거래처가 메일로 보낸 단가표 수집. 받는 쪽 메일함이 네이버여야 한다(보내는 쪽 메일은 무엇이든 된다).

⭐ 발신자는 거래처 문서에서 읽는다 — `sourcing-channels.md` §소싱처 레지스트리의 방식 ③ 줄.
   종전엔 우리 거래처 이름이 기본값으로 코드에 박혀 있어 다른 사람은 그대로 쓸 수 없었다.
   거래처 표가 비어 있으면 멈추고 안내한다 — 거래처 이름과 메일 주소를 먼저 적는다.

인증:
  - imap.naver.com:993 SSL. 네이버 메일 환경설정 → POP3/IMAP 사용 ON 필요.
  - 계정 = NAVER_LOGIN_ID(스마트스토어 계정과 동일). **앱 비번(NAVER_MAIL_APP_PW) 먼저**,
    실패하거나 비어 있으면 NAVER_LOGIN_PW. (2단계 인증 계정은 로그인 PW 로 IMAP 에 못 들어간다 — _connect() 의 순서가 정본)

사용법:
  python tools/tool-naver-mail-fetch.py                          # 거래처 문서의 전 거래처가 보낸 메일만
  python tools/tool-naver-mail-fetch.py --vendor "거래처명"        # 그 거래처가 보낸 메일만 (쉼표로 여러 곳)
  python tools/tool-naver-mail-fetch.py --keywords "단가표,가격표"  # 제목 글자로도 찾는다 (문서에 없는 발신자까지 — 넓게 받힌다)
  python tools/tool-naver-mail-fetch.py --senders "이름,메일주소"   # 문서에 없는 발신자를 직접 줄 때

출력:
  output/sourcing/ 에 첨부 다운로드 + 매칭 메일 목록 콘솔 출력.
"""
import imaplib
import email
import email.utils
from email.header import decode_header
import os
import sys
import argparse
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vendor_registry  # noqa: E402

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "output" / "sourcing"


def _load_env():
    env = {}
    p = ROOT / (".e" + "nv")
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    return env


def _decode(s):
    if not s:
        return ""
    parts = decode_header(s)
    out = ""
    for text, enc in parts:
        if isinstance(text, bytes):
            try:
                out += text.decode(enc or "utf-8", errors="replace")
            except Exception:
                out += text.decode("utf-8", errors="replace")
        else:
            out += text
    return out


def mask_id(user: str) -> str:
    """계정 아이디를 앞 두 글자만 남기고 가린다 — 화면·녹화·배포본에 계정이 남지 않게."""
    return f"{user[:2]}***" if user else ""


def _connect(env):
    """네이버 IMAP 로그인. 앱 비번 → 실패하거나 비어 있으면 로그인 PW."""
    user = env.get("NAVER_LOGIN_ID", "")
    if not user:
        print("❌ 네이버 메일 계정이 없습니다 — `.env.example` 을 복사해 `.env` 를 만들고 NAVER_LOGIN_ID 와 앱 비밀번호(NAVER_MAIL_APP_PW)를 넣으세요")
        sys.exit(1)
    # 네이버 앱 비번은 화면에 공백 섞여 표시됨 → 접속 시 공백 제거 필수
    app_pw = env.get("NAVER_MAIL_APP_PW", "").replace(" ", "")
    login_pw = env.get("NAVER_LOGIN_PW", "").replace(" ", "")
    # ⛔ 아이디 전체·비밀번호 글자 수는 찍지 않는다 — 있는지 없는지만 알려도 진단에는 충분하다
    print(f"  ℹ️ 계정: {mask_id(user)} · 앱 비밀번호 {'있음' if app_pw else '없음'} · 로그인 비밀번호 {'있음' if login_pw else '없음'}")
    pw_candidates = [
        ("앱 비번", app_pw),        # 앱 비번 우선 (2단계 인증 계정)
        ("로그인 PW", login_pw),
    ]
    for label, pw in pw_candidates:
        if not pw:
            continue
        try:
            M = imaplib.IMAP4_SSL("imap.naver.com", 993)
            M.login(user, pw)
            print(f"  ✅ IMAP 로그인 성공 ({label})")
            return M
        except imaplib.IMAP4.error as e:
            print(f"  ↪ {label} 실패: {str(e)[:80]}")
    print("\n❌ 네이버 IMAP 로그인 실패.")
    print("   조치: ① 네이버 메일 → 환경설정 → POP3/IMAP 설정 → 'IMAP/SMTP 사용' ON")
    print("        ② 2단계 인증 사용 시 → 네이버 내정보 → 보안설정 → 애플리케이션 비밀번호 생성")
    print("           → .env NAVER_MAIL_APP_PW 에 입력")
    sys.exit(1)


def _match_seqs(M, folder, keywords, senders):
    """폴더 전체 시퀀스 → 헤더(제목·발신자) 로컬 fetch → 한글 키워드 매칭.
    네이버 IMAP의 한국어 SEARCH 미지원 우회 + UID 불안정 회피(시퀀스 통일)."""
    try:
        typ, _ = M.select(f'"{folder}"', readonly=True)
        if typ != "OK":
            return []
    except Exception:
        return []
    try:
        typ, data = M.search(None, "ALL")
    except Exception:
        return []
    if typ != "OK" or not data or not data[0]:
        return []
    seqs = data[0].split()
    if not seqs:
        return []
    matched = set()
    kw = [k.lower() for k in keywords]
    sd = [s.lower() for s in senders]
    # ASCII 발신자(이메일·영문)는 서버 FROM 검색 병행 — 네이버 대량 배치 헤더
    # fetch가 일부 메일을 누락시키는 문제 보완(거래처E BRAND-NAME 누락 사례).
    # 한글 SEARCH는 imaplib이 ascii 인코딩만 지원해 불가 → 로컬 필터로만 처리.
    for s in senders:
        if s.isascii():
            try:
                typ2, d2 = M.search(None, "FROM", s)
                if typ2 == "OK" and d2 and d2[0]:
                    matched.update(d2[0].split())
            except Exception:
                pass
    for i in range(0, len(seqs), 500):
        batch = b",".join(seqs[i:i + 500])
        try:
            typ, hdrs = M.fetch(
                batch, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
        except Exception:
            continue
        if typ != "OK" or not hdrs:
            continue
        for part in hdrs:
            if isinstance(part, tuple):
                meta = part[0].decode("utf-8", "replace")
                # 시퀀스 fetch 응답: 'N (BODY[...] {size}' → 맨 앞 N = 시퀀스번호
                m = re.match(r"\s*(\d+)\s+\(", meta)
                seq = m.group(1) if m else None
                raw = part[1].decode("utf-8", "replace")
                subj = _decode_hdr_line(raw, "Subject")
                frm = _decode_hdr_line(raw, "From")
                if seq and header_matches(subj, frm, kw, sd):
                    matched.add(seq.encode())
    return list(matched)


def header_matches(subj, frm, keywords, senders):
    """제목+발신자에 키워드나 발신자 문자열이 하나라도 들어 있나 (소문자 비교)."""
    hay = ((subj or "") + " " + (frm or "")).lower()
    return any(k.lower() in hay for k in keywords) or any(s.lower() in hay for s in senders)


def _mail_timestamp(date_header):
    """메일 Date 머리글 → 초 단위 시각. 같은 시행일 단가표가 여러 번 오면 intake 가 «가장 늦게 받은 파일»을 고르는 근거. 못 읽으면 None."""
    try:
        return email.utils.parsedate_to_datetime(date_header).timestamp()
    except (TypeError, ValueError):
        return None


def fetch_folder(M, folder, seqs, keywords, senders, seen_msgids):
    """2단계 — 시퀀스 번호로 본문을 받아 첨부를 저장한다. 반환: (매칭 메일 수, 저장 첨부 수, 어긋난 메일 수)

    ⛔ 받은 메일의 제목·발신자가 필터와 안 맞으면 **저장하지 않는다** (2026-09-18 리허설 사고):
       받은메일함이 IMAP 노출 상한(5,000통)에 걸려 있으면 새 메일 한 통에 전체 시퀀스 번호가 밀려,
       1단계에서 모은 번호가 2단계에선 바로 옆 메일을 가리킨다 — 단가표 12통 대신 같은 날짜의 뉴스레터·주문알림을
       받아 «첨부 저장 4개(광고 브로셔)»로 조용히 끝났다.
    """
    hits = saved = mismatched = 0
    M.select(f'"{folder}"', readonly=True)
    for seq in seqs:
        try:
            typ, data = M.fetch(seq, "(RFC822)")
            if typ != "OK" or not data or not data[0]:
                continue
            msg = email.message_from_bytes(data[0][1])
            subj = _decode(msg.get("Subject"))
            frm = _decode(msg.get("From"))
            if not header_matches(subj, frm, keywords, senders):
                mismatched += 1
                continue
            mid = msg.get("Message-ID", str(seq))
            if mid in seen_msgids:
                continue
            seen_msgids.add(mid)
            date = msg.get("Date", "")
            received = _mail_timestamp(date)
            atts = []
            for part in msg.walk():
                fn = part.get_filename()
                if not fn:
                    continue
                fn = _decode(fn)
                if re.search(r"\.(xlsx?|pdf|csv)$", fn, re.I):
                    payload = part.get_payload(decode=True)
                    if payload:
                        safe = re.sub(r"[^\w가-힣.\-]", "_", fn)[:80]
                        dest = OUT_DIR / f"{folder}_{safe}"
                        n = 1
                        while dest.exists():
                            dest = OUT_DIR / f"{folder}_{n}_{safe}"; n += 1
                        dest.write_bytes(payload)
                        if received:
                            os.utime(dest, (received, received))     # 파일의 «수정한 날짜» = 메일 받은 날짜
                        atts.append(dest.name)
                        saved += 1
            hits += 1
            print(f"  📧 [{folder}] {date[:16]} | {frm[:30]} | {subj[:45]}")
            if atts:
                print(f"       첨부: {', '.join(atts)}")
        except Exception as e:
            print(f"     ⚠️ seq {seq} 처리 실패: {str(e)[:40]}")
    return hits, saved, mismatched


def collect_folder(M, folder, keywords, senders, seen_msgids):
    """폴더 하나: 헤더 스캔 → 본문·첨부. 번호가 밀렸으면 **한 번 다시 스캔**한다. 반환: (매칭, 저장, 끝내 어긋난 수)"""
    seqs = _match_seqs(M, folder, keywords, senders)
    if not seqs:
        return 0, 0, 0
    print(f"  📁 [{folder}] 헤더 매칭 {len(seqs)}건 → 본문·첨부 확인")
    hits, saved, mismatched = fetch_folder(M, folder, seqs, keywords, senders, seen_msgids)
    if mismatched:
        print(f"  🔁 [{folder}] 받아 온 메일 {mismatched}건이 필터와 안 맞습니다 — 새 메일 도착으로 번호가 밀렸습니다. 다시 스캔합니다.")
        seqs = _match_seqs(M, folder, keywords, senders)
        h2, s2, mismatched = fetch_folder(M, folder, seqs, keywords, senders, seen_msgids)
        hits, saved = hits + h2, saved + s2
        if mismatched:
            print(f"  ⚠️ [{folder}] 다시 스캔해도 {mismatched}건이 어긋납니다 — 저장하지 않았습니다. 잠시 뒤 다시 실행하세요.")
    return hits, saved, mismatched


def _decode_hdr_line(raw, field):
    """raw 헤더 텍스트에서 특정 필드 값 추출 + MIME 디코드."""
    for line in raw.split("\n"):
        if line.lower().startswith(field.lower() + ":"):
            val = line.split(":", 1)[1].strip()
            return _decode(val)
    return ""


# 기본은 제목 글자로 찾지 않는다 — 종전 기본값 «단가표,견적서,견적,가격표,단가» 는 고객 견적 문의·
# 남의 사업자등록증까지 받아 왔다(실측 58개). 거래처 문서에 적힌 거래처가 보낸 메일만 받는 것이 기본이다.
DEFAULT_KEYWORDS = ""


def _split(text):
    return [x.strip() for x in (text or "").split(",") if x.strip()]


def build_filters(vendor, senders, keywords, vendors):
    """→ (제목 키워드, 발신자 글자). 우선순위: --vendor > --senders > 거래처 문서 전체.

    --vendor 는 **그 거래처가 보낸 메일만** 받는다 — 키워드를 쓰지 않는다(쓰면 제목에 «단가표»가 있는
    다른 거래처 메일까지 받는다). 공문·성적서도 같이 오지만 단가표인지는 다음 단계(intake)가 가린다."""
    if vendor:
        picked = []
        for name in _split(vendor):
            v = vendor_registry.find(vendors, name)
            if v is None:
                raise SystemExit(f"❌ 거래처 문서에 없는 거래처: {name}\n"
                                 f"   sourcing-channels.md 거래처 표에 먼저 적습니다 (지금 적힌 곳: {[x.name for x in vendors]})")
            if not v.emails:
                raise SystemExit(f"❌ {v.name} — 거래처 문서에 메일 주소가 없습니다.\n"
                                 "   메일로 받지 않는 거래처면 받은 파일을 수신함 폴더(output/sourcing/)에 직접 넣습니다.")
            picked.append(v)
        return [], vendor_registry.mail_filters(picked)
    if senders:
        return _split(keywords), _split(senders)
    if not vendors:
        raise SystemExit("❌ 거래처 문서에 단가표 거래처가 없습니다.\n"
                         "   sourcing-channels.md 거래처 표에 거래처 이름(정식 상호)과 단가표를 보내는 메일 주소를 먼저 적습니다.")
    return _split(keywords), vendor_registry.mail_filters(vendors)


def main():
    ap = argparse.ArgumentParser(description="네이버 메일 단가표 첨부 수집")
    ap.add_argument("--keywords", default=DEFAULT_KEYWORDS,
                    help="제목 글자로도 찾는다 (쉼표 구분). 기본은 쓰지 않는다 — 주면 문서에 없는 발신자 메일까지 받는다")
    ap.add_argument("--vendor", default="",
                    help="거래처 문서에 적힌 거래처 이름 — 그 거래처가 보낸 메일만 받는다 (쉼표 구분)")
    ap.add_argument("--senders", default="",
                    help="발신자 글자를 직접 준다 (쉼표 구분). 생략하면 거래처 문서의 전 거래처")
    ap.add_argument("--all", action="store_true",
                    help="보낸편지함·삭제함·세금계산서함까지 전체 스캔 (기본: 매입 폴더만)")
    args = ap.parse_args()

    try:
        vendors = vendor_registry.load_vendors()
    except (FileNotFoundError, ValueError) as e:
        raise SystemExit(f"❌ {e}")
    keywords, senders = build_filters(args.vendor, args.senders, args.keywords, vendors)   # 접속 전에 먼저 멈춘다

    env = _load_env()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    M = _connect(env)

    # 소싱(매입) 단가표 수집이 목적 → 우리 발송물·스팸·알림 폴더 제외.
    # Sent/Drafts = 우리가 보낸 견적서(소싱 아님), Deleted = 스팸,
    # &zK2..(세금계산서함) = 계산서 도착 알림만(단가표 첨부 없음). --all 이면 전체 스캔.
    SKIP_FOLDERS = {"Sent Messages", "Drafts", "Deleted Messages",
                    "&zK2tbAC3rLDIHA-"}
    folders = ["INBOX"]
    try:
        typ, boxes = M.list()
        if typ == "OK":
            for b in boxes:
                m = re.search(r'"([^"]+)"$', b.decode("utf-8", "replace"))
                if m and m.group(1) not in folders:
                    folders.append(m.group(1))
    except Exception:
        pass
    if not args.all:
        folders = [f for f in folders if f not in SKIP_FOLDERS]

    print(f"\n🔍 '단가표' 관련 메일 스캔 (폴더 {len(folders)}개): 키워드={','.join(keywords) or '(없음 — 거래처 메일만)'} / 발신자={','.join(senders)}")
    seen_msgids = set()
    hits = saved = unresolved = 0
    for folder in folders:
        h, s, u = collect_folder(M, folder, keywords, senders, seen_msgids)
        hits, saved, unresolved = hits + h, saved + s, unresolved + u
    M.logout()
    print(f"\n✅ 완료: 매칭 메일 {hits}건, 첨부 저장 {saved}개 → {OUT_DIR}")
    if unresolved:
        print(f"   ⚠️ 번호 밀림으로 못 받은 메일 {unresolved}건 — 다시 실행하세요 (저장된 것은 전부 필터와 일치하는 메일입니다).")
    if saved == 0 and hits == 0:
        print("   ℹ️ 매칭 0건 — 거래처 문서의 메일 주소를 확인하거나, 메일이 다른 폴더에 있을 수 있음(--all).")


if __name__ == "__main__":
    main()

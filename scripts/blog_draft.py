"""네이버 블로그 글 초안 자동 생성기.

사용법:
    python3 scripts/blog_draft.py              # 이번 주 접수 시작/예정 대회 모음 글
    python3 scripts/blog_draft.py 울산         # 특정 대회 단독 소개 글 (이름 검색)

출력된 글을 복사해서 네이버 블로그에 붙여넣으면 됨.
제목 후보도 함께 출력됨 — 네이버 검색 노출엔 제목이 제일 중요.
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://www.runandtrail.kr"
DOW = "월화수목금토일"


def kdate(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.month}월 {d.day}일({DOW[d.weekday()]})"


def race_block(r: dict) -> str:
    lines = [f"🏃 {r['name']}"]
    lines.append(f"· 대회일: {kdate(r['date'])}")
    if r.get("location"):
        lines.append(f"· 장소: {r['location']} ({r.get('region', '')})")
    if r.get("events"):
        lines.append(f"· 종목: {r['events']}")
    if r.get("reg_period"):
        lines.append(f"· 접수기간: {r['reg_period']}")
    if r.get("homepage"):
        lines.append(f"· 접수/안내: {r['homepage']}")
    return "\n".join(lines)


def main() -> None:
    races = json.loads((ROOT / "data" / "races.json").read_text(encoding="utf-8"))["races"]
    today = date.today()

    if len(sys.argv) > 1:  # 특정 대회 단독 글
        kw = sys.argv[1]
        hits = [r for r in races if kw in r["name"]]
        if not hits:
            sys.exit(f"'{kw}'로 검색된 대회가 없습니다.")
        r = hits[0]
        year = r["date"][:4]
        name_y = r["name"] if year in r["name"] else f"{year} {r['name']}"
        print("=" * 50)
        print("📌 제목 후보 (하나 골라 쓰세요)")
        print(f"  1. {name_y} 접수 일정·코스 총정리")
        print(f"  2. {name_y} 접수 시작! 놓치지 마세요")
        print(f"  3. {name_y} 참가 신청 방법 (접수기간·종목·장소)")
        print("=" * 50)
        print()
        print(f"가을 러닝 시즌이 다가오고 있습니다! 오늘은 {r['name']} 소식을 정리해봤어요.")
        print()
        print(race_block(r))
        if r.get("description"):
            print(f"\n{r['description']}")
        print(f"""
접수 기간을 놓치면 1년을 기다려야 하니 미리 캘린더에 저장해두세요!

📅 전국 마라톤 일정을 한눈에 보고 싶다면?
👉 런앤트레일: {SITE}
매일 자동 업데이트되는 대회 캘린더 · 지역별 필터 · 접수중 대회 모아보기
""")
        return

    # 이번 주 모음 글: 접수가 곧 시작되거나 갓 시작된 대회
    week_end = today + timedelta(days=7)
    opening = [r for r in races if r.get("reg_start") and today <= date.fromisoformat(r["reg_start"]) <= week_end]
    just_opened = [r for r in races if r.get("reg_start") and today - timedelta(days=7) <= date.fromisoformat(r["reg_start"]) < today
                   and (not r.get("reg_end") or date.fromisoformat(r["reg_end"]) >= today)]
    opening.sort(key=lambda r: r["reg_start"])
    just_opened.sort(key=lambda r: r["reg_start"])

    m, d_ = today.month, today.day
    print("=" * 50)
    print("📌 제목 후보 (하나 골라 쓰세요)")
    print(f"  1. {m}월 {d_}일 기준, 이번 주 접수 시작하는 마라톤 대회 총정리")
    print(f"  2. 이번 주 놓치면 안 되는 마라톤 접수 일정 ({m}/{d_} 업데이트)")
    print(f"  3. {m}월 마라톤 접수 캘린더 — 이번 주 오픈 대회 모음")
    print("=" * 50)
    print()
    print("안녕하세요, 런앤트레일입니다 🏃")
    print("이번 주 접수가 시작되는 대회들을 정리했습니다. 인기 대회는 오픈런이 필수니 알림 설정하세요!")
    if opening:
        print("\n" + "─" * 30)
        print("🔔 이번 주 접수 시작")
        print("─" * 30)
        for r in opening:
            print()
            print(race_block(r))
    if just_opened:
        print("\n" + "─" * 30)
        print("✅ 현재 접수중 (최근 오픈)")
        print("─" * 30)
        for r in just_opened[:5]:
            print()
            print(race_block(r))
    print(f"""
─────────────────────────────
📅 전국 마라톤 일정을 한눈에!
👉 런앤트레일: {SITE}
매일 자동 업데이트 · 지역별 지도 검색 · 접수중 대회 필터
─────────────────────────────
""")


if __name__ == "__main__":
    main()

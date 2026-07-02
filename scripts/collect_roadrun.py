# /// script
# requires-python = ">=3.10"
# dependencies = ["beautifulsoup4"]
# ///
"""로드런(roadrun.co.kr) 대회 일정을 수집해서 data/races.json으로 저장.

사용법:
    uv run scripts/collect_roadrun.py            # 목록 + 새 대회만 상세 수집 (증분)
    uv run scripts/collect_roadrun.py --refresh  # 모든 대회 상세 다시 수집

로드런 목록/상세는 발견(discovery)용으로만 사용한다.
최종 확인은 각 대회 공식 홈페이지 기준.
"""

import calendar
import json
import re
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup

LIST_URL = "http://www.roadrun.co.kr/schedule/list.php"
DETAIL_URL = "http://www.roadrun.co.kr/schedule/view.php?no={no}"
FETCH_DELAY = 0.3  # 상대 서버 배려용 요청 간격(초)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = PROJECT_ROOT / "data" / "races.json"

# 상세 페이지에서 새로 얻는 필드 — 이 키가 있으면 이미 상세 수집된 대회로 판단
DETAIL_FIELDS = ("region", "reg_period", "reg_start", "reg_end", "start_time", "description")


def fetch_html(url: str) -> str:
    # 오래된 사이트라 인증서가 유효하지 않고 인코딩이 EUC-KR이라 curl 사용
    result = subprocess.run(
        ["curl", "-sk", "--max-time", "30", url],
        capture_output=True, check=True,
    )
    return result.stdout.decode("euc-kr", errors="replace")


def parse_races(html: str, base_year: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    races = []
    prev_month = None
    year = base_year

    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) != 4:
            continue

        # 1열: 날짜 (예: "7/1 (수)") — 연도가 없어서 월이 줄어들면 해가 넘어간 것으로 판단
        date_text = tds[0].get_text(" ", strip=True)
        m = re.match(r"(\d{1,2})/(\d{1,2})", date_text)
        if not m:
            continue
        month, day = int(m.group(1)), int(m.group(2))
        if prev_month is not None and month < prev_month:
            year += 1
        prev_month = month

        # 2열: 대회명 링크 + 종목
        link = tds[1].find("a")
        if not link:
            continue
        name = link.get_text(strip=True)
        no_match = re.search(r"view\.php\?no=(\d+)", link.get("href", ""))
        detail_no = no_match.group(1) if no_match else None
        events_font = tds[1].find("font", attrs={"color": "#990000"})
        events = events_font.get_text(strip=True) if events_font else ""

        # 3열: 장소
        location = tds[2].get_text(" ", strip=True)

        # 4열: 주최, 전화, 홈페이지
        org_text = tds[3].get_text("\n", strip=True)
        org_lines = [line.strip() for line in org_text.split("\n") if line.strip()]
        organizer = org_lines[0] if org_lines else ""
        phone_match = re.search(r"☎\s*([\d\-\s]+)", org_text)
        phone = phone_match.group(1).strip() if phone_match else ""
        homepage = ""
        for a in tds[3].find_all("a"):
            href = a.get("href", "")
            if href.startswith("http") and "roadrun" not in href:
                homepage = href
                break

        try:
            race_date = date(year, month, day).isoformat()
        except ValueError:
            continue

        races.append({
            "id": f"roadrun-{detail_no}" if detail_no else f"roadrun-{year}{month:02d}{day:02d}-{name}",
            "name": name,
            "date": race_date,
            "events": events,
            "location": location,
            "organizer": organizer,
            "phone": phone,
            "homepage": homepage,
            "detail_no": detail_no,
            "source": f"{LIST_URL} (발견용)",
            "source_detail": DETAIL_URL.format(no=detail_no) if detail_no else "",
        })
    return races


def parse_kr_date(text: str) -> str:
    """'2026년6월31일' → '2026-06-30' (존재하지 않는 날짜는 월말로 보정)."""
    m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if not m:
        return ""
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not 1 <= mo <= 12:
        return ""
    d = min(d, calendar.monthrange(y, mo)[1])
    return date(y, mo, d).isoformat()


def parse_detail(html: str) -> dict:
    """상세 페이지의 라벨 셀(대회지역, 접수기간 등) 다음 셀 값을 읽는다."""
    soup = BeautifulSoup(html, "html.parser")
    fields = {}
    for td in soup.find_all("td"):
        label = td.get_text(strip=True)
        if label in ("대회일시", "대회지역", "접수기간", "기타소개"):
            value_td = td.find_next_sibling("td")
            if value_td and label not in fields:
                fields[label] = value_td.get_text("\n", strip=True)

    region = fields.get("대회지역", "").strip()
    if region in ("지역", "기타", "-"):  # 로드런 쪽 입력 오류 방어
        region = ""
    info: dict = {
        "region": region,
        "reg_period": " ".join(fields.get("접수기간", "").split()),
        "start_time": "",
        "description": fields.get("기타소개", "")[:300].strip(),
    }
    st = re.search(r"출발시간\s*:\s*(\S+)", fields.get("대회일시", ""))
    if st:
        info["start_time"] = st.group(1)

    dates = [parse_kr_date(part) for part in re.split(r"[~〜]", fields.get("접수기간", ""), maxsplit=1)]
    info["reg_start"] = dates[0] if dates else ""
    info["reg_end"] = dates[1] if len(dates) > 1 else ""
    return info


def main() -> None:
    refresh = "--refresh" in sys.argv

    # 기존 데이터 로드 (증분 수집용)
    existing: dict[str, dict] = {}
    if OUT_PATH.exists() and not refresh:
        for r in json.loads(OUT_PATH.read_text(encoding="utf-8")).get("races", []):
            existing[r["id"]] = r

    print(f"목록 수집: {LIST_URL}")
    races = parse_races(fetch_html(LIST_URL), base_year=date.today().year)
    if not races:
        sys.exit("파싱된 대회가 0개입니다. 페이지 구조가 바뀌었는지 확인하세요.")

    need_detail = [r for r in races
                   if r["detail_no"] and not all(k in existing.get(r["id"], {}) for k in DETAIL_FIELDS)]
    print(f"목록 {len(races)}개 / 상세 수집 대상 {len(need_detail)}개 (예상 {len(need_detail) * (FETCH_DELAY + 0.5):.0f}초)")

    for i, race in enumerate(races):
        cached = existing.get(race["id"], {})
        if race in need_detail:
            try:
                race.update(parse_detail(fetch_html(DETAIL_URL.format(no=race["detail_no"]))))
            except Exception as e:
                print(f"  상세 실패 ({race['name']}): {e}")
            time.sleep(FETCH_DELAY)
            done = sum(1 for r in races[:i + 1] if r in need_detail)
            if done % 20 == 0:
                print(f"  상세 {done}/{len(need_detail)}...")
        else:
            for k in DETAIL_FIELDS:
                if k in cached:
                    race[k] = cached[k]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "source": LIST_URL,
        "count": len(races),
        "races": races,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"완료: {len(races)}개 대회 → {OUT_PATH}")
    print(f"기간: {races[0]['date']} ~ {races[-1]['date']}")
    regions = sorted({r.get("region", "") for r in races if r.get("region")})
    print(f"지역: {', '.join(regions)}")


if __name__ == "__main__":
    main()

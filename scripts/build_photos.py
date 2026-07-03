"""대회사진 게시판 빌드 (네이버 MYBOX 앨범 링크 방식).

구조: 사진 원본은 네이버 MYBOX에 올리고, 사이트에는 앨범당 대표 썸네일 1장과
공유 링크만 올린다 → 저장소 용량이 거의 늘지 않음.

사용법:
    1. 앨범 대표사진 1장을 photos/original/ 에 넣는다 (파일명 = 앨범 구분용, 예: 2026-07-05-nowon.jpg)
    2. python3 scripts/build_photos.py   → 썸네일 생성 + data/photos.json에 항목 추가
    3. data/photos.json 에서 해당 항목의 link(MYBOX 공유주소), race(대회명), date를 채운다
    4. git add -A && git commit -m "사진 앨범 추가" && git push

photos/original/은 git에 올라가지 않는다. 이미 등록된 앨범의 link/race/date/title은
다시 실행해도 그대로 유지된다. macOS 기본 도구 sips 사용 (별도 설치 불필요).
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "photos" / "original"
THUMB = ROOT / "photos" / "thumb"
OUT = ROOT / "data" / "photos.json"
EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}
THUMB_PX = 640  # 카드용 대표 이미지 크기


def make_thumb(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "80",
         "-Z", str(THUMB_PX), str(src), "--out", str(dst)],
        check=True, capture_output=True,
    )


def photo_date(src: Path) -> str:
    r = subprocess.run(["sips", "-g", "creation", str(src)], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if "creation:" in line:
            val = line.split("creation:", 1)[1].strip()
            try:
                return datetime.strptime(val, "%Y:%m:%d %H:%M:%S").date().isoformat()
            except ValueError:
                pass
    return datetime.fromtimestamp(src.stat().st_mtime).date().isoformat()


def main() -> None:
    SRC.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in SRC.iterdir() if p.suffix.lower() in EXTS)
    if not files:
        sys.exit(f"대표사진이 없습니다. 이 폴더에 앨범당 1장씩 넣어주세요: {SRC}")

    existing = {}
    if OUT.exists():
        for it in json.loads(OUT.read_text(encoding="utf-8")).get("items", []):
            existing[it["id"]] = it

    items = []
    for src in files:
        pid = src.stem
        thumb = THUMB / f"{pid}.jpg"
        if not thumb.exists():
            make_thumb(src, thumb)
            print(f"  썸네일 생성: {src.name} → thumb/{pid}.jpg")
        prev = existing.get(pid, {})
        item = {
            "id": pid,
            "thumb": f"photos/thumb/{pid}.jpg",
            "race": prev.get("race", ""),          # 대회명 (예: 2026 안동마라톤)
            "title": prev.get("title", ""),        # 한 줄 설명 (선택)
            "date": prev.get("date") or photo_date(src),
            "link": prev.get("link", ""),          # 네이버 MYBOX 공유 링크
            "count": prev.get("count", ""),        # 앨범 사진 장수 (선택, 예: "58장")
        }
        items.append(item)
        if not item["link"]:
            print(f"  ⚠️  '{pid}' 항목의 link(MYBOX 공유주소)가 비어 있습니다 → data/photos.json에서 채워주세요")

    items.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
    OUT.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"완료: 앨범 {len(items)}개 → {OUT}")


if __name__ == "__main__":
    main()

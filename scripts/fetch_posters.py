# /// script
# requires-python = ">=3.10"
# dependencies = ["beautifulsoup4"]
# ///
"""대회 공식 홈페이지에서 포스터 이미지를 수집해 카드 뷰에 입힌다.

사용법:
    uv run scripts/fetch_posters.py

동작:
- data/races.json의 각 대회 homepage에 접속해 대표 이미지(og:image 등)를 찾음
- 찾으면 posters/{id}.jpg 로 축소 저장(sips)하고 races.json에 poster 필드 기록
- 이미 포스터가 있는 대회는 건너뜀 (증분)
- 포스터를 못 찾은 대회는 기존 자동 생성 커버가 그대로 쓰임

포스터는 대회 홍보물이므로 출처(공식 홈페이지) 기준으로만 수집한다.
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
RACES = ROOT / "data" / "races.json"
OUT_DIR = ROOT / "posters"
MAX_PX = 640          # 카드용 크기
FETCH_DELAY = 0.3
MIN_BYTES = 8_000     # 너무 작은 이미지(아이콘 등)는 포스터가 아님


def curl(url: str, out: Path | None = None, timeout: int = 20) -> bytes:
    cmd = ["curl", "-skL", "--max-time", str(timeout),
           "-A", "Mozilla/5.0 (Macintosh) RunAndTrail/1.0", url]
    if out:
        cmd += ["-o", str(out)]
    r = subprocess.run(cmd, capture_output=True, check=True)
    return r.stdout


def decode_html(raw: bytes) -> str:
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def find_poster_candidates(html: str, base_url: str) -> list[str]:
    """포스터일 가능성이 높은 순서로 이미지 URL 후보를 최대 4개 반환."""
    soup = BeautifulSoup(html, "html.parser")
    cands: list[str] = []
    for sel in ('meta[property="og:image"]', 'meta[name="twitter:image"]'):
        tag = soup.select_one(sel)
        if tag and tag.get("content"):
            cands.append(urljoin(base_url, tag["content"].strip()))
    for img in soup.find_all("img"):
        src = (img.get("src") or "").strip()
        if not src or src.startswith("data:"):
            continue
        if re.search(r"poster|대회|banner|main|visual|event", src, re.I):
            cands.append(urljoin(base_url, src))
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out[:4]


def img_dims(p: Path) -> tuple[int, int]:
    r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(p)],
                       capture_output=True, text=True)
    w = h = 0
    for line in r.stdout.splitlines():
        if "pixelWidth:" in line:
            w = int(line.split(":")[1])
        if "pixelHeight:" in line:
            h = int(line.split(":")[1])
    return w, h


def save_poster(img_url: str, dst: Path) -> bool:
    tmp = dst.with_suffix(".tmp")
    try:
        curl(img_url, out=tmp, timeout=25)
        if not tmp.exists() or tmp.stat().st_size < MIN_BYTES:
            return False
        w, h = img_dims(tmp)
        # 품질 검사: 너무 작은 이미지(로고)나 가로로 긴 배너는 카드에 안 어울림
        if min(w, h) < 300 or (h and w / h > 2.2):
            return False
        target = min(MAX_PX, max(w, h))  # 확대(업스케일) 금지
        subprocess.run(
            ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "78",
             "-Z", str(target), str(tmp), "--out", str(dst)],
            check=True, capture_output=True,
        )
        return dst.exists() and dst.stat().st_size >= MIN_BYTES
    except Exception:
        return False
    finally:
        tmp.unlink(missing_ok=True)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    data = json.loads(RACES.read_text(encoding="utf-8"))
    races = data["races"]
    targets = [r for r in races if r.get("homepage") and not r.get("poster")]
    print(f"포스터 수집 대상: {len(targets)}개")

    ok = 0
    for i, r in enumerate(targets, 1):
        dst = OUT_DIR / f"{r['id']}.jpg"
        if dst.exists():  # 이전 실행에서 받아둔 경우
            r["poster"] = f"posters/{dst.name}"
            ok += 1
            continue
        try:
            html = decode_html(curl(r["homepage"]))
            for img_url in find_poster_candidates(html, r["homepage"]):
                if save_poster(img_url, dst):
                    r["poster"] = f"posters/{dst.name}"
                    ok += 1
                    break
        except Exception:
            pass
        if i % 20 == 0:
            print(f"  진행 {i}/{len(targets)} (성공 {ok})")
        time.sleep(FETCH_DELAY)

    RACES.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(1 for r in races if r.get("poster"))
    print(f"완료: 이번에 {ok}개 수집, 전체 {total}/{len(races)}개 대회에 포스터 있음")


if __name__ == "__main__":
    main()

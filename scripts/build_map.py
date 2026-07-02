"""시도 경계 GeoJSON → 클릭 가능한 SVG 지도(data/korea_map.svg) 생성.

사용법:
    python3 scripts/build_map.py <provinces_geojson_path>

GeoJSON 출처: github.com/southkorea/southkorea-maps (kostat 2013 simple).
한 번 생성해두면 다시 실행할 일은 없다.
"""

import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = PROJECT_ROOT / "data" / "korea_map.svg"

SHORT_NAMES = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
    "강원도": "강원", "충청북도": "충북", "충청남도": "충남",
    "전라북도": "전북", "전라남도": "전남", "경상북도": "경북",
    "경상남도": "경남", "제주특별자치도": "제주",
}
# 라벨 위치 수동 보정 (SVG 좌표계 px, 지역 중심점 기준 이동)
LABEL_NUDGE = {
    "경기": (10, 14), "인천": (-16, -2), "세종": (4, -12), "대전": (8, 10),
    "대구": (-2, 4), "울산": (10, 0), "부산": (8, 8), "광주": (-10, 6),
    "충남": (-10, 12),
}
WIDTH = 420.0
MIN_RING_SPAN = 0.04  # 이보다 작은 섬(경도/위도 폭 기준)은 생략


def rings_of(geom):
    if geom["type"] == "Polygon":
        yield geom["coordinates"][0]
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            yield poly[0]


def main() -> None:
    src = Path(sys.argv[1])
    features = json.loads(src.read_text(encoding="utf-8"))["features"]

    # 전체 경계 계산 (한반도 위도 기준 경도 축척 보정)
    all_pts = [pt for f in features for ring in rings_of(f["geometry"]) for pt in ring]
    lons = [p[0] for p in all_pts]
    lats = [p[1] for p in all_pts]
    lon0, lat1 = min(lons), max(lats)
    kx = math.cos(math.radians((min(lats) + max(lats)) / 2))
    scale = WIDTH / ((max(lons) - lon0) * kx)
    height = (lat1 - min(lats)) * scale

    def project(lon, lat):
        return ((lon - lon0) * kx * scale, (lat1 - lat) * scale)

    paths, labels = [], []
    for f in features:
        name = SHORT_NAMES.get(f["properties"]["name"], f["properties"]["name"])
        d_parts = []
        biggest, biggest_span = None, 0.0
        for ring in rings_of(f["geometry"]):
            xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
            span = (max(xs) - min(xs)) + (max(ys) - min(ys))
            if span > biggest_span:
                biggest, biggest_span = ring, span
            if span < MIN_RING_SPAN:
                continue
            pts, last = [], None
            for lon, lat in ring:
                x, y = project(lon, lat)
                pt = (round(x, 1), round(y, 1))
                if pt != last:
                    pts.append(pt)
                    last = pt
            if len(pts) < 4:
                continue
            d_parts.append("M" + " ".join(f"{x},{y}" for x, y in pts) + "Z")
        if not d_parts:
            continue
        paths.append(f'<path data-region="{name}" d="{"".join(d_parts)}"><title>{name}</title></path>')

        cx = sum(p[0] for p in biggest) / len(biggest)
        cy = sum(p[1] for p in biggest) / len(biggest)
        x, y = project(cx, cy)
        nx, ny = LABEL_NUDGE.get(name, (0, 0))
        labels.append(f'<text x="{x + nx:.0f}" y="{y + ny:.0f}">{name}</text>')

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH:.0f} {height:.0f}">'
        f'<g class="map-regions">{"".join(paths)}</g>'
        f'<g class="map-labels">{"".join(labels)}</g>'
        "</svg>"
    )
    OUT_PATH.write_text(svg, encoding="utf-8")
    print(f"완료: {len(paths)}개 지역 → {OUT_PATH} ({OUT_PATH.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()

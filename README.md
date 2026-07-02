# 런앤트레일 — 러닝 정보 사이트

전국 러닝/마라톤 대회 일정을 중심으로 러닝화·러닝크루 정보까지 모아 보여주는 웹사이트.

## 게시판 구조

- `index.html` — **대회 일정**: 검색, 종목/지역/접수상태 필터, 클릭 가능한 대한민국 지도, 목록·캘린더 뷰, D-day, 접수 상태 배지, 대회 상세 모달
- `shoes.html` — **러닝화 정보**: `data/shoes.json`에 항목을 추가하면 자동 반영 (용도별 필터: 데일리/템포/레이스/트레일)
- `crews.html` — **러닝크루**: `data/crews.json`에 항목을 추가하면 자동 반영 (지역별 필터)
- `assets/site.css` — 전 페이지 공용 스타일 (상단 메뉴 포함). 새 게시판을 만들 땐 기존 페이지를 복사해서 topnav에 링크만 추가하면 됨.

## 데이터/스크립트

- `scripts/collect_roadrun.py` — 로드런(roadrun.co.kr)에서 대회 목록 + 상세(지역, 접수기간, 출발시간, 소개)를 수집해 `data/races.json`으로 저장. 증분 수집(새 대회만 상세 요청).
- `scripts/build_map.py` — 시도 경계 GeoJSON → `data/korea_map.svg` 생성 (한 번만 실행하면 됨. 원본: github.com/southkorea/southkorea-maps)
- `data/shoes.json`, `data/crews.json` — 러닝화/크루 게시판 데이터 (현재 예시 항목, 직접 채우면 됨)

## 사용법

```bash
# 1. 대회 데이터 수집 (주 1회 정도 갱신, 새 대회만 상세 요청)
uv run scripts/collect_roadrun.py
# 전체 상세 다시 수집하려면:
uv run scripts/collect_roadrun.py --refresh

# 2. 로컬에서 보기
python3 -m http.server 8766
# → http://localhost:8766
```

## 데이터 정책

- 로드런 목록은 **대회 발견용**으로만 사용. 각 대회의 상세 정보(접수기간, 참가비)는
  공식 홈페이지(`homepage` 필드)에서 확인해 채운다.
- 다른 정리 사이트의 DB를 통째로 복제하지 않는다.

## 다음 단계 아이디어

- [ ] 참가비 필드 (공식 홈페이지 확인 후 입력)
- [ ] 새 대회 감지 자동화 (주 1회 수집 → 기존 데이터와 비교 → 새 대회 알림)
- [ ] GitHub Pages 무료 배포

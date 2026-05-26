# 거북이 - 순찰 (Patrol)

## 함수
`generate_stage1.make_turtle(am, name, x1, x2, y, speed, stomp_br_name, stomp_br_id, BR)`

## 역할
발판 또는 바닥 위를 좌우로 왕복 순찰

## 동작
1. "스테이지1" 브로드캐스트 수신 → **코스튬 "koopa"로 리셋** + 위치/크기 설정 + 표시
2. x1 → x2 이동 (glide)
3. 방향 전환 → x2 → x1 이동 → 반복 (forever)

## 재시작 시 동작
- 게임 재시작 시 "스테이지1" 브로드캐스트 재수신
- **코스튬을 "koopa"(원래 모습)로 복구** → 등껍질 상태 초기화
- 위치, 크기, 방향 모두 초기 상태로 리셋

## 위치 (Stage 1)
| 이름 | x1 | x2 | y | 속도 | 위치 |
|------|----|----|---|------|------|
| Turtle1 | 220 | -220 | GY+8 | 4.0초 | 바닥 위 |
| Turtle2 | -70 | -10 | **-7** (Plat2 표면에 발이 닿도록) | 1.5초 | Plat2 위 |

## Y좌표 보정
거북이 스프라이트가 바닥/발판 위에 확실히 올라오도록 +8px 보정

## 크기
- 기본 **45%** (Turtle1, Turtle2 — Stage 1·2 공통)
- Stage 2 Turtle3는 55% 유지 (보스급 등껍질 구분용)

## 스프라이트 파일
- `sprites/turtle/koopa_walk_1.png` — Stage 1 순찰 거북이
- `sprites/koopa/bowser_walk_1.png` — Stage 2 등껍질 거북이

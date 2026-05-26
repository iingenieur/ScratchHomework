# Stage 1 - 깃발 (Flag)

## 함수
`generate_stage1.make_flag(am, BR, sounds)`

## 역할
Stage 1 끝의 클리어 깃발. 마리오가 닿으면 스테이지 클리어 트리거.

## 동작
1. 게임 시작 시 `hide()`
2. "스테이지1" 브로드캐스트 수신 → 지정 위치로 이동 + `show()`
3. 마리오의 `touching("Flag")` 판정은 마리오 측 스크립트 (`mario_flag_clear`)에서 처리

## 위치 및 크기
| 항목 | 값 |
|------|-----|
| x | **223** |
| y | **132** |
| size | **150%** |

## 스프라이트
- `svg_flag()` (common.py의 SVG 깃발)

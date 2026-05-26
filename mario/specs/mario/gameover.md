# 마리오 - 게임오버 / 클리어 (Game Over)

## 게임오버
`mechanics.mario_gameover(m, V, hide_mario=False)`

- 조건: 하트 < 1
- 동작: 게임상태="gameover", 게임오버 백드롭
- `hide_mario=True` → 마리오 숨김 (Stage 1)
- `hide_mario=False` → stop_all (Stage 2/3)

## 깃발 클리어
`mechanics.mario_flag_clear(m, V, flag_name="Flag", clear_msg, msg_time=2)`

- 조건: touching(깃발)
- 동작: 클리어 메시지 → 게임상태="clear" → 클리어 백드롭 → stop_all
- 사용: Stage 1 전용

## 사용 변수
`하트` (읽기), `게임상태` (쓰기)

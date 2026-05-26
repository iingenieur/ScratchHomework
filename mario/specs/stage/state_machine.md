# 스테이지 - 상태 머신 (State Machine)

## 역할
게임 전체 흐름을 관리하는 상태 기계

## 상태 흐름
```
start → stageN → gameover → stageN (재시작)
                → clear    → stageN (재시작)
                → win      → stageN (Stage 3)
```

## 상태 전환
| 현재 | 트리거 | 다음 | 동작 |
|------|--------|------|------|
| start | SPACE | stageN | 변수 초기화, 백드롭 전환, 브로드캐스트 |
| stageN | 하트==0 | gameover | 게임오버 백드롭 |
| stageN | 클리어 조건 | clear/win | 클리어 백드롭 |
| gameover | SPACE | stageN | 변수 초기화, 재시작 |
| clear/win | SPACE | stageN | 변수 초기화, 재시작 |

## 브로드캐스트
"스테이지N" 브로드캐스트 발송 시 모든 스프라이트가 동시에 초기화:
- Mario: 위치/변수 리셋, 표시
- Turtle: 코스튬 리셋, 위치 리셋, 순찰 시작
- Platform: 위치 설정, 표시
- Flag: 위치 설정, 표시
- Hearts: 코스튬 h5로 리셋

## 백드롭 전환 시 스프라이트 숨김
게임이 끝(gameover / clear / win)에 도달해 **백드롭이 "게임오버" / "클리어" / "승리"로 전환**되면,
모든 스프라이트는 자기 자신을 hide 한다. 화면에는 백드롭만 남아야 한다.

구현: 각 스프라이트의 BB에 `when backdrop switches to <게임오버/클리어/승리>` hat을 등록하고
hat 안에서 `hide()` 호출. `mechanics.hide_on_end(b, backdrops)`가 이 작업을 묶어준다.

| 스테이지 | 끝 백드롭 |
|----------|-----------|
| Stage 1 | "게임오버", "클리어" |
| Stage 2 | "게임오버", "클리어" |
| Stage 3 | "게임오버", "승리" |

## 공유 변수
| 변수 | 초기값 | 용도 |
|------|--------|------|
| 하트 | 5 | 남은 생명 |
| 게임상태 | "start" | 현재 상태 |
| 속도Y | 0 | 마리오 수직 속도 |
| 점프중 | 0 | 마리오 점프 상태 |
| 무적 | 0 | 무적 상태 |
| 쿠파HP | 3 | Stage 3 전용 |

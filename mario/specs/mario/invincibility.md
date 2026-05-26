# 마리오 - 무적 (Invincibility)

## 함수
`mechanics.mario_invincibility(m, V, BR, duration=1.0)`

## 역할
피격 후 1초간 추가 피격을 받지 않는 무적 상태 제공.
**무적 중에도 이동/점프는 정상 작동.**

## 동작 (별도 스크립트)
```
when I receive "피격"
  무적 = 1
  wait(1.0)
  무적 = 0
```

## 무적 중 동작 보장
- 무적 타이머는 **별도 스크립트**(broadcast hat)에서 실행
- 메인 forever 루프는 중단되지 않음 → 이동/점프 계속 가능
- `mario_side_hit`의 피격 처리에서 `wait()` 사용하지 않음
  (wait가 있으면 forever 루프가 멈춰 이동 불가)

## 중복 피격 방지 (넉백 + 무적 조합)
1. **넉백** (`mario_side_hit`): 피격 즉시 반대 방향으로 30px 밀림 → 적과 거리 확보
2. **무적 1초** (`mario_invincibility`): 다시 닿아도 피격 무시

## 연동
- `mario_side_hit`, `mario_enemy_hit`이 V에 "무적" 키가 있으면 자동으로 `무적==0` 조건 추가
- "피격" 브로드캐스트는 피격 함수들이 발송, Hearts 스프라이트도 수신

## 필요 설정
- V에 `"무적"` 키 추가
- BR에 `"피격"` 키 추가
- gvars에 `("무적", 0)` 초기값
- 스테이지 시작 시 `set_var("무적", 0)`

## 사용 변수
`무적` (쓰기)

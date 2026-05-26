# 마리오 - 적 충돌 (Enemy Collision)

적과의 접촉은 3가지 함수로 구분:

## 1. mario_stomp — 위에서 밟기
`mechanics.mario_stomp(m, V, enemy_name, stomp_br_name, stomp_br_id, bounce_velocity=10, sound="Jump")`

- 조건: touching(적) AND 속도Y < 0 (낙하 중)
- 동작:
  1. 밟기 브로드캐스트 → 적이 등껍질로 변신
  2. 마리오 바운스 (속도Y = bounce_velocity)
  3. 사운드 재생
- **하트 차감 없음** — 밟기는 공격이므로 피격이 아님
- 사용: Stage 1 (거북이)

## 2. mario_side_hit — 옆에서 피격 (넉백 포함)
`mechanics.mario_side_hit(m, V, enemy_name, BR, knockback=30, ...)`

- 조건: touching(적) AND 속도Y == 0 (바닥에 서있을 때) AND 무적==0
- 속도Y == 0 조건 이유: stomp 바운스 후 속도Y=10이 되므로 같은 프레임에서 충돌 방지.
  점프 상승 중(속도Y > 0)이나 낙하 중(속도Y < 0)에는 발동하지 않음.
- 동작:
  1. 하트 -1 감소
  2. "피격" 브로드캐스트 발송
  3. 피격 사운드 재생
  4. **걷던 방향 반대로 넉백** — 현재 방향(90이면 오른쪽)의 반대로 knockback px 밀려남
  5. 속도Y=0, 점프중=0 리셋
  6. 코스튬 복구
  7. 무적 시간 대기 (1초)
- 넉백 효과: 적과 즉시 거리가 벌어져 중복 피격 방지
- 사용: Stage 1 (거북이)

## 3. mario_enemy_hit — 무조건 피격
`mechanics.mario_enemy_hit(m, V, enemy_name, ...)`

- 조건: touching(적) AND 무적==0
- 동작: 하트-1, 위치 리셋
- 사용: Stage 2 (등껍질), Stage 3 (쿠파)

## 루프 내 순서
밟기(stomp) → 피격(side_hit/enemy_hit) → 게임오버

밟기를 먼저 체크하여, 낙하 중 접촉 시 밟기가 우선 발동.
밟기가 발동하면 바운스로 적에게서 멀어지므로 side_hit은 발동하지 않음.

## 무적 연동
V에 "무적" 키가 있으면 자동으로 무적 조건 추가

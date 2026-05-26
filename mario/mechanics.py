"""
공유 게임 메카닉 함수 모음
모든 스테이지에서 import하여 사용하는 마리오 기능별 독립 함수
각 함수는 BB 인스턴스와 변수 딕셔너리를 받아 블록 ID를 반환
"""

from common import GY


def mario_physics(m, V, ground_y=GY, landing_costume=None):
    """중력 적용 + 속도 반영 + 바닥 착지 스냅

    Args:
        m: BB 인스턴스 (마리오)
        V: 변수 ID 딕셔너리 (속도Y, 점프중 필요)
        ground_y: 바닥 Y 좌표
        landing_costume: 착지 시 전환할 코스튬 (None이면 전환 안함)

    Returns:
        [grav, apply_v, if_ground] 블록 ID 리스트
    """
    grav = m.change_var("속도Y", V["속도Y"], -1)
    # 터미널 벨로시티: 낙하 속도 제한 (발판 뚫기 방지)
    tv_cond = m.lt_var("속도Y", V["속도Y"], -8)
    tv_set = m.set_var("속도Y", V["속도Y"], -8)
    tv_if = m.if_then(tv_cond, tv_set)
    apply_v = m.change_y_var("속도Y", V["속도Y"])

    # 점프 후 착지: 점프중==1 → 코스튬 전환 포함
    if landing_costume:
        cg1 = m.lt_ypos(ground_y)
        was_jumping = m.eq_var("점프중", V["점프중"], 1)
        cg_jump = m.op_and(cg1, was_jumping)
        gs_jump = [m.set_y(ground_y),
                   m.set_var("속도Y", V["속도Y"], 0),
                   m.set_var("점프중", V["점프중"], 0),
                   m.costume(landing_costume)]
        m.chain(gs_jump)
        ifg_jump = m.if_then(cg_jump, gs_jump[0])

        # 바닥 유지: 점프중==0 → 코스튬 변경 없음
        cg2 = m.lt_ypos(ground_y)
        not_jumping = m.eq_var("점프중", V["점프중"], 0)
        cg_ground = m.op_and(cg2, not_jumping)
        gs_ground = [m.set_y(ground_y),
                     m.set_var("속도Y", V["속도Y"], 0)]
        m.chain(gs_ground)
        ifg_ground = m.if_then(cg_ground, gs_ground[0])

        return [grav, tv_if, apply_v, ifg_jump, ifg_ground]
    else:
        cg = m.lt_ypos(ground_y)
        gs = [m.set_y(ground_y),
              m.set_var("속도Y", V["속도Y"], 0),
              m.set_var("점프중", V["점프중"], 0)]
        m.chain(gs)
        ifg = m.if_then(cg, gs[0])
        return [grav, tv_if, apply_v, ifg]


def mario_movement(m, V=None, speed=5, with_direction=True, walk_mode="next",
                   walk_count=5):
    """좌우 이동 + 걷기 애니메이션

    Args:
        m: BB 인스턴스
        V: 변수 ID 딕셔너리 (점프중, 걸음 키 필요)
        speed: 이동 속도 (픽셀/프레임)
        with_direction: 방향 전환 여부 (point_dir)
        walk_mode: "next"=걸음 카운터로 걷기 코스튬만 순환,
                   문자열=해당 코스튬 고정, None=코스튬 변경 없음
        walk_count: 걷기 코스튬 개수 (점프 코스튬 제외, 기본 5)

    Returns:
        [if_right, if_left] 블록 ID 리스트
    """
    def _walk_anim():
        """걷기 애니메이션 블록 생성 (점프 중이면 스킵)
        걸음 카운터(1~walk_count)로 걷기 코스튬만 순환, 점프 코스튬 건너뜀.
        """
        if walk_mode is None:
            return None
        if walk_mode != "next":
            if V and "점프중" in V:
                cnj = m.eq_var("점프중", V["점프중"], 0)
                return m.if_then(cnj, m.costume(walk_mode))
            else:
                return m.costume(walk_mode)

        # walk_mode == "next": 걸음 카운터로 순환
        if V and "걸음" in V and "점프중" in V:
            cnj = m.eq_var("점프중", V["점프중"], 0)
            # 걸음 += 1, if 걸음 > walk_count: 걸음 = 1, costume = 걸음
            inc = m.change_var("걸음", V["걸음"], 1)
            wrap_cond = m.gt_var("걸음", V["걸음"], walk_count)
            wrap_set = m.set_var("걸음", V["걸음"], 1)
            wrap_if = m.if_then(wrap_cond, wrap_set)
            set_cos = m.costume_var("걸음", V["걸음"])
            m.chain([inc, wrap_if, set_cos])
            return m.if_then(cnj, inc)
        else:
            return m.next_costume()

    # 오른쪽 이동
    kr = m.key_pressed("right arrow")
    mvr = [m.change_x(speed)]
    if with_direction:
        mvr.append(m.point_dir(90))
    anim_r = _walk_anim()
    if anim_r:
        mvr.append(anim_r)
    m.chain(mvr)
    ifr = m.if_then(kr, mvr[0])

    # 왼쪽 이동
    kl = m.key_pressed("left arrow")
    mvl = [m.change_x(-speed)]
    if with_direction:
        mvl.append(m.point_dir(-90))
    anim_l = _walk_anim()
    if anim_l:
        mvl.append(anim_l)
    m.chain(mvl)
    ifl = m.if_then(kl, mvl[0])

    return [ifr, ifl]


def mario_jump(m, V, velocity=14, jump_costume=None, sound="Jump"):
    """점프 (이중 점프 방지 포함)

    Args:
        m: BB 인스턴스
        V: 변수 ID 딕셔너리 (속도Y, 점프중 필요)
        velocity: 점프 초기 속도
        jump_costume: 점프 시 전환할 코스튬 (None이면 전환 안함)
        sound: 점프 사운드 이름

    Returns:
        if_jump 블록 ID
    """
    kj = m.key_pressed("space")
    cnj = m.eq_var("점프중", V["점프중"], 0)
    cj = m.op_and(kj, cnj)

    jb = [m.set_var("속도Y", V["속도Y"], velocity),
          m.set_var("점프중", V["점프중"], 1)]
    if jump_costume:
        jb.append(m.costume(jump_costume))
    jb.append(m.play_sound(sound))
    m.chain(jb)

    return m.if_then(cj, jb[0])


def mario_enemy_hit(m, V, enemy_name, reset_x=None, reset_y=None,
                    velocity_after=0, BR=None, hit_sound="Hit",
                    wait_time=0.5, reset_costume=None):
    """적 충돌 → 하트 감소 + 위치 리셋 (무조건 피격, 밟기 구분 없음)
    밟기/피격 구분이 필요 없는 스테이지(Stage 2/3)에서 사용.
    V에 "무적" 키가 있으면 무적 상태일 때 피격 무시.

    Args:
        m: BB 인스턴스
        V: 변수 ID 딕셔너리 (하트, 속도Y, 점프중 필요, 무적 선택)
        enemy_name: 적 스프라이트 이름
        reset_x: 리셋 X 좌표 (None이면 X 변경 안함)
        reset_y: 리셋 Y 좌표 (None이면 Y 변경 안함)
        velocity_after: 피격 후 Y속도 (0=정지, 양수=바운스)
        BR: 브로드캐스트 딕셔너리 ("피격" 키가 있으면 브로드캐스트)
        hit_sound: 피격 사운드 이름
        wait_time: 피격 후 무적 시간
        reset_costume: 피격 후 전환할 코스튬 (None이면 전환 안함)

    Returns:
        if_hit 블록 ID
    """
    tt = m.touching(enemy_name)
    cond = tt
    if "무적" in V:
        not_invincible = m.eq_var("무적", V["무적"], 0)
        cond = m.op_and(tt, not_invincible)

    hit = [m.change_var("하트", V["하트"], -1)]
    if BR and "피격" in BR:
        hit.append(m.broadcast("피격", BR["피격"]))
    hit.append(m.play_sound(hit_sound))

    if reset_x is not None and reset_y is not None:
        hit.append(m.goto(reset_x, reset_y))
    elif reset_y is not None:
        hit.append(m.set_y(reset_y))

    hit.append(m.set_var("속도Y", V["속도Y"], velocity_after))
    hit.append(m.set_var("점프중", V["점프중"], 0))
    if reset_costume:
        hit.append(m.costume(reset_costume))
    hit.append(m.wait(wait_time))
    m.chain(hit)

    return m.if_then(cond, hit[0])


def mario_stomp(m, V, enemy_name, stomp_br_name, stomp_br_id,
                bounce_velocity=10, sound="Jump"):
    """위에서 밟기: 낙하 중 접촉 → 밟기 브로드캐스트 + 바운스
    적을 밟으면 적에게 밟기 브로드캐스트를 보내고, 마리오는 위로 튕긴다.

    Args:
        m: BB 인스턴스
        V: 변수 ID 딕셔너리 (속도Y 필요)
        enemy_name: 적 스프라이트 이름
        stomp_br_name: 밟기 브로드캐스트 이름 (예: "밟기1")
        stomp_br_id: 밟기 브로드캐스트 ID
        bounce_velocity: 밟은 후 바운스 속도 (기본 10)
        sound: 밟기 사운드 이름

    Returns:
        if_stomp 블록 ID
    """
    tt = m.touching(enemy_name)
    falling = m.lt_var("속도Y", V["속도Y"], 0)
    cond = m.op_and(tt, falling)

    actions = [m.broadcast(stomp_br_name, stomp_br_id),
               m.set_var("속도Y", V["속도Y"], bounce_velocity),
               m.play_sound(sound)]
    m.chain(actions)

    return m.if_then(cond, actions[0])


def mario_side_hit(m, V, enemy_name, BR=None, knockback=30,
                   hit_sound="Hit", wait_time=1.0,
                   reset_costume=None):
    """옆에서 피격: 낙하가 아닐 때 접촉 → 하트 감소 + 넉백
    걷다가 적에게 부딪히거나 위로 점프하다가 닿았을 때 발동.
    걷던 방향 반대로 넉백하여 중복 피격을 방지.
    V에 "무적" 키가 있으면 무적 상태일 때 피격 무시.

    Args:
        m: BB 인스턴스
        V: 변수 ID 딕셔너리 (하트, 속도Y, 점프중 필요, 무적 선택)
        enemy_name: 적 스프라이트 이름
        BR: 브로드캐스트 딕셔너리 ("피격" 키가 있으면 브로드캐스트)
        knockback: 넉백 거리 (px, 걷던 방향 반대로)
        hit_sound: 피격 사운드 이름
        wait_time: 피격 후 무적 시간 (초)
        reset_costume: 피격 후 전환할 코스튬 (None이면 전환 안함)

    Returns:
        if_hit 블록 ID
    """
    tt = m.touching(enemy_name)
    on_ground = m.eq_var("속도Y", V["속도Y"], 0)
    cond = m.op_and(tt, on_ground)
    if "무적" in V:
        not_invincible = m.eq_var("무적", V["무적"], 0)
        cond = m.op_and(cond, not_invincible)

    hit = [m.change_var("하트", V["하트"], -1)]
    if BR and "피격" in BR:
        hit.append(m.broadcast("피격", BR["피격"]))
    hit.append(m.play_sound(hit_sound))
    # 넉백: 현재 방향 반대로 밀려남 (move -knockback = 뒤로)
    hit.append(m.move(-knockback))
    hit.append(m.set_var("속도Y", V["속도Y"], 0))
    hit.append(m.set_var("점프중", V["점프중"], 0))
    if reset_costume:
        hit.append(m.costume(reset_costume))
    # wait 없음: 무적은 mario_invincibility 별도 스크립트가 처리
    # wait가 있으면 forever 루프가 멈춰 이동 불가
    m.chain(hit)

    return m.if_then(cond, hit[0])


def mario_gameover(m, V, hide_mario=False):
    """하트 0 → 게임오버

    Args:
        m: BB 인스턴스
        V: 변수 ID 딕셔너리 (하트 필요)
        hide_mario: True면 마리오를 숨김, False면 stop_all

    Returns:
        if_gameover 블록 ID
    """
    ch = m.lt_var("하트", V["하트"], 1)
    die = [m.set_var("게임상태", V["게임상태"], "gameover"),
           m.backdrop("게임오버")]
    if hide_mario:
        die.append(m.hide())
    # stop_all 제거: backdrop_hat이 트리거되어 다른 스프라이트가 hide될 수 있도록.
    # forever 루프는 게임상태=="stageN" 가드로 자연스럽게 멈춤.
    m.chain(die)

    return m.if_then(ch, die[0])


def mario_platform_landing(m, V, plat_positions):
    """발판 착지 판정

    Args:
        m: BB 인스턴스
        V: 변수 ID 딕셔너리 (속도Y, 점프중 필요)
        plat_positions: [(name, x, y, sprite), ...] 발판 정보

    Returns:
        [if_plat1, if_plat2, ...] 블록 ID 리스트
    """
    checks = []
    for pname, _, plat_y, _ in plat_positions:
        tp = m.touching(pname)
        fl = m.lt_var("속도Y", V["속도Y"], 0)
        above = m.gt_ypos(plat_y + 10)
        ca = m.op_and(tp, m.op_and(fl, above))
        sn = [m.change_y(1),
              m.set_var("속도Y", V["속도Y"], 0),
              m.set_var("점프중", V["점프중"], 0),
              m.costume("걷기1")]
        m.chain(sn)
        checks.append(m.if_then(ca, sn[0]))
    return checks


def mario_platform_block(m, V, plat_positions):
    """발판 아래에서 점프 시 머리 막힘 처리

    위로 올라가며 발판에 닿으면 속도Y를 0으로 설정하여
    발판을 뚫고 올라가지 못하게 한다.

    Args:
        m: BB 인스턴스
        V: 변수 ID 딕셔너리 (속도Y 필요)
        plat_positions: [(name, x, y, sprite), ...] 발판 정보

    Returns:
        [if_block1, if_block2, ...] 블록 ID 리스트
    """
    checks = []
    for pname, _, plat_y, _ in plat_positions:
        tp = m.touching(pname)
        rising = m.gt_var("속도Y", V["속도Y"], 0)
        below = m.lt_ypos(plat_y)
        cond = m.op_and(tp, m.op_and(rising, below))
        block = m.set_var("속도Y", V["속도Y"], 0)
        checks.append(m.if_then(cond, block))
    return checks


def mario_flag_clear(m, V, flag_name="Flag",
                     clear_msg="스테이지 1 클리어!", msg_time=2):
    """깃발 터치 → 스테이지 클리어

    Args:
        m: BB 인스턴스
        V: 변수 ID 딕셔너리 (게임상태 필요)
        flag_name: 깃발 스프라이트 이름
        clear_msg: 클리어 시 표시할 메시지
        msg_time: 메시지 표시 시간 (초)

    Returns:
        if_clear 블록 ID
    """
    tfl = m.touching(flag_name)
    # stop_all 제거: backdrop_hat 트리거가 hide 보장하도록.
    s_clear = [m.say_for(clear_msg, msg_time),
               m.set_var("게임상태", V["게임상태"], "clear"),
               m.backdrop("클리어"),
               m.hide()]
    m.chain(s_clear)

    return m.if_then(tfl, s_clear[0])


def mario_invincibility(m, V, BR, duration=0.5):
    """피격 후 무적 시간 처리 (별도 스크립트)

    "피격" 브로드캐스트를 수신하면 무적 상태를 활성화하고,
    일정 시간 후 해제한다. 무적 중에는 mario_side_hit, mario_enemy_hit이
    자동으로 피격을 무시한다 (V에 "무적" 키가 있을 때).

    이 함수는 forever 루프와 별도의 독립 스크립트를 생성한다.
    반환값은 broadcast hat 블록 ID (top-level).

    Args:
        m: BB 인스턴스 (마리오)
        V: 변수 ID 딕셔너리 (무적 필요)
        BR: 브로드캐스트 딕셔너리 (피격 필요)
        duration: 무적 지속 시간 (초)

    Returns:
        broadcast hat 블록 ID (top-level script)
    """
    hat = m.bcast_hat("피격", BR["피격"])
    actions = [m.set_var("무적", V["무적"], 1),
               m.wait(duration),
               m.set_var("무적", V["무적"], 0)]
    m.chain([hat] + actions)
    return hat


def hide_on_end(b, backdrops=("게임오버", "클리어")):
    """스테이지 종료(게임오버/클리어/승리) 백드롭으로 전환되면 스프라이트를 숨김.

    각 종료 백드롭마다 `when backdrop switches to <bd>` hat을 만들고
    그 안에서 hide()를 실행한다. 백드롭만 보이도록 전체 스프라이트에 적용.

    Args:
        b: BB 인스턴스 (적용할 스프라이트)
        backdrops: 숨김 트리거가 되는 백드롭 이름 튜플
    """
    for bd in backdrops:
        h = b.backdrop_hat(bd)
        b.chain([h, b.hide()])

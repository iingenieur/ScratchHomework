"""
스테이지 2 — 정통 마리오식 진행 스테이지.

레벨 흐름: 시작 평지 → Plat1(좌우 이동, 추종) → Plat2(고정)
        → Plat3(고정) → Plat5(수직 이동, 추종) → Plat4(고정)
        → Pipe(↓ 키로 클리어)

빌드: python3 generate_stage2.py → Stage2.sb3
"""

from common import *
from mechanics import (
    mario_physics, mario_movement, mario_jump,
    mario_stomp, mario_side_hit, mario_gameover,
    mario_platform_landing, mario_platform_block,
    mario_pipe_clear, mario_invincibility, hide_on_end,
)


MARIO_START_X = -210
MARIO_START_Y = GY + 7

PLAT_POSITIONS = [
    # 고정 발판
    ("Plat2", -195,   0, "background/plat_3.png"),   # Plat1 왼쪽 끝(-125)에서 점프
    ("Plat3",  -65,  50, "background/plat_3.png"),   # Plat2에서 x 130 이동·y 50 상승 → 점프 가능
    ("Plat4",  200,  30, "background/plat_3.png"),
]

# 움직이는 발판: (name, x1, y1, x2, y2, speed_seconds)
#   x1==x2 → 수직(위아래), y1==y2 → 수평(좌우)
MOVING_PLATS = [
    ("Plat1",  170, -70, -125, -70, 5.0),   # 수평 (느림, 마리오 추종 ON)
    ("Plat5",   70,  90,   70,  10, 2.5),   # 수직 (위→아래) 폭 확대. 마리오 수직 추종 ON
]
# mario_platform_landing/block용 — 이동 발판은 평균 y를 정적 plat_y로 사용.
# 단, Plat5는 별도 수직 추종 로직으로 처리하므로 제외.
# Pipe (스테이지 끝)도 발판처럼 위에 올라설 수 있도록 추가.
PLAT_POSITIONS_PHYS = PLAT_POSITIONS + [
    (name, (x1 + x2) // 2, (y1 + y2) // 2, "")
    for name, x1, y1, x2, y2, _ in MOVING_PLATS
    if name != "Plat5"
] + [("Pipe", 210, 65, "")]   # Pipe sprite top 근처 (y=55 + size 15 기준)

NORMAL_TURTLES = [
    # name, x1, x2, y, speed
    ("Turtle1", -100, -220, -133, 4.0),
    ("Turtle2", 12, 224, -133, 4.0),
]
NORMAL_TURTLE_NAMES = ["Turtle1", "Turtle2"]


def svg_shell_large():
    return svg(60, 40,
        '<ellipse cx="30" cy="20" rx="28" ry="18" fill="#2E7D32" stroke="#1B5E20" stroke-width="2"/>'
        '<ellipse cx="30" cy="16" rx="20" ry="14" fill="#4CAF50"/>'
        '<line x1="15" y1="10" x2="15" y2="28" stroke="#1B5E20" stroke-width="2"/>'
        '<line x1="30" y1="6" x2="30" y2="28" stroke="#1B5E20" stroke-width="2"/>'
        '<line x1="45" y1="10" x2="45" y2="28" stroke="#1B5E20" stroke-width="2"/>'
        '<ellipse cx="30" cy="30" rx="24" ry="8" fill="#FFCC02"/>'
    )


def bg_start_s2():
    return svg(480, 360,
        '<rect width="480" height="360" fill="#1a237e"/>'
        '<circle cx="400" cy="60" r="30" fill="#FFD700" opacity="0.3"/>'
        '<text x="240" y="130" text-anchor="middle" font-size="36" font-weight="bold" fill="#FFD700">STAGE 2</text>'
        '<text x="240" y="175" text-anchor="middle" font-size="18" fill="#DDD">깃발까지 도달하라!</text>'
        '<text x="240" y="240" text-anchor="middle" font-size="16" fill="#AAA">SPACE 키를 눌러 시작</text>')


def bg_stage2_clear():
    return svg(480, 360,
        '<rect width="480" height="360" fill="#1565C0"/>'
        '<text x="240" y="160" text-anchor="middle" font-size="40" font-weight="bold" fill="#FFD700">스테이지 2 클리어!</text>'
        '<text x="240" y="220" text-anchor="middle" font-size="18" fill="#FFF">수고했어요, 마리오!</text>'
    )


# ════════════════════════════════════════════════════════════════════════
# Stage 백드롭 + 상태머신
# ════════════════════════════════════════════════════════════════════════
def build_stage(am, V, BR, stage_bcast):
    b = BB()
    f0 = b.flag()
    init = [b.backdrop("시작화면"),
            b.set_var("게임상태", V["게임상태"], "start"),
            b.set_var("하트", V["하트"], 5),
            b.set_var("속도Y", V["속도Y"], 0),
            b.set_var("점프중", V["점프중"], 0),
            b.set_var("무적", V["무적"], 0),
            b.set_var("걸음", V["걸음"], 1),
            b.set_var("Plat1_x_prev", V["Plat1_x_prev"], 170),
            b.set_var("Plat1_dx", V["Plat1_dx"], 0),
            b.set_var("Plat5_y_prev", V["Plat5_y_prev"], 90),
            b.set_var("Plat5_dy", V["Plat5_dy"], 0)]
    init.append(b.stop_sounds())
    b.chain([f0] + init)

    sp = b.key_hat("space")
    c1 = b.eq_var("게임상태", V["게임상태"], "start")
    s1 = [b.set_var("게임상태", V["게임상태"], stage_bcast),
          b.backdrop("스테이지2"),
          b.broadcast(stage_bcast, BR[stage_bcast])]
    b.chain(s1); if1 = b.if_then(c1, s1[0])

    def restart_seq():
        seq = [b.set_var("하트", V["하트"], 5),
               b.set_var("속도Y", V["속도Y"], 0),
               b.set_var("점프중", V["점프중"], 0),
               b.set_var("무적", V["무적"], 0),
               b.set_var("Plat1_x_prev", V["Plat1_x_prev"], 170),
               b.set_var("Plat1_dx", V["Plat1_dx"], 0),
               b.set_var("Plat5_y_prev", V["Plat5_y_prev"], 90),
               b.set_var("Plat5_dy", V["Plat5_dy"], 0)]
        seq += [b.set_var("게임상태", V["게임상태"], stage_bcast),
                b.backdrop("스테이지2"),
                b.broadcast(stage_bcast, BR[stage_bcast])]
        b.chain(seq)
        return seq[0]

    c2 = b.eq_var("게임상태", V["게임상태"], "gameover")
    if2 = b.if_then(c2, restart_seq())
    c3 = b.eq_var("게임상태", V["게임상태"], "clear")
    if3 = b.if_then(c3, restart_seq())
    b.chain([sp, if1, if2, if3])

    gvars_init = [("하트", 5), ("속도Y", 0), ("점프중", 0),
                  ("게임상태", "start"), ("무적", 0), ("걸음", 1),
                  ("Plat1_x_prev", 170), ("Plat1_dx", 0),
                  ("Plat5_y_prev", 90), ("Plat5_dy", 0)]
    gvars = {V[k]: [k, v] for k, v in gvars_init}

    return {
        "isStage": True, "name": "Stage", "variables": gvars,
        "lists": {}, "comments": {},
        "broadcasts": {v: k for k, v in BR.items()},
        "blocks": b.blocks, "currentCostume": 0,
        "costumes": [am.reg_png_backdrop("시작화면", "background/bg_stage.png"),
                     am.reg_png_backdrop("스테이지2", "background/bg_stage.png"),
                     am.reg("게임오버", bg_gameover(), 240, 180),
                     am.reg("클리어", bg_stage2_clear(), 240, 180)],
        "sounds": [], "volume": 100, "layerOrder": 0, "tempo": 60,
        "videoTransparency": 50, "videoState": "off",
        "textToSpeechLanguage": None
    }


# ════════════════════════════════════════════════════════════════════════
# Platform
# ════════════════════════════════════════════════════════════════════════
def make_plat(am, name, x, y, sprite, BR, stage_bcast):
    p = BB()
    pf = p.flag()
    p.chain([pf, p.hide()])
    ph = p.bcast_hat(stage_bcast, BR[stage_bcast])
    p.chain([ph, p.goto(x, y), p.set_size(75), p.show()])
    hide_on_end(p)
    return {
        "isStage": False, "name": name,
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": p.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("plat", sprite)],
        "sounds": [], "volume": 100, "layerOrder": 2, "visible": False,
        "x": x, "y": y, "size": 75, "direction": 90,
        "draggable": False, "rotationStyle": "don't rotate",
    }


# ════════════════════════════════════════════════════════════════════════
# 움직이는 발판 (좌우 왕복, 마리오 추종 없음)
# ════════════════════════════════════════════════════════════════════════
def make_moving_plat(am, name, x1, y1, x2, y2, speed, sprite, BR, stage_bcast,
                     follow_var=None, block_below_V=None, size=75):
    """수평·수직 어디든 가능한 좌표 두 점 사이 왕복 발판.

    follow_var: (prev_name, prev_id, dx_name, dx_id) 튜플이면 발판의 한 프레임
                x 변화량을 글로벌 변수 `dx_name`에 매 프레임 기록 (마리오 추종용).
    block_below_V: V dict면 마리오가 발판 아래에서 위로 부딪힐 때 속도Y=0 처리
                   (sensing으로 마리오 y와 자기 y 비교).
    """
    p = BB()
    pf = p.flag()
    p.chain([pf, p.hide()])
    ph = p.bcast_hat(stage_bcast, BR[stage_bcast])
    init = [p.goto(x1, y1), p.set_size(size), p.show()]
    gl1 = p.glide(speed, x2, y2)
    gl2 = p.glide(speed, x1, y1)
    p.chain([gl1, gl2])
    fl = p.forever(gl1)
    p.chain([ph] + init + [fl])

    # 마리오 추종용 변수 갱신 (별도 forever)
    if follow_var:
        prev_n, prev_i, dx_n, dx_i = follow_var
        pf2 = p.flag()
        sub = p.op_sub(p.xpos(), p.var_ref(prev_n, prev_i))
        set_dx = p.set_var_block(dx_n, dx_i, sub)
        set_prev = p.set_var_block(prev_n, prev_i, p.xpos())
        p.chain([set_dx, set_prev])
        fl2 = p.forever(set_dx)
        p.chain([pf2, fl2])

    # 마리오 머리 막힘 (마리오가 발판 아래에서 위로 부딪힐 때)
    if block_below_V is not None:
        pf3 = p.flag()
        tm = p.touching("Mario")
        rising = p.gt_var("속도Y", block_below_V["속도Y"], 0)
        mario_below = p.op_gt_block(p.ypos(), p.sense_of_ypos("Mario"))
        cand = p.op_and(tm, p.op_and(rising, mario_below))
        hit_block = p.set_var("속도Y", block_below_V["속도Y"], 0)
        if_block = p.if_then(cand, hit_block)
        fl3 = p.forever(if_block)
        p.chain([pf3, fl3])

    hide_on_end(p)
    return {
        "isStage": False, "name": name,
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": p.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("plat", sprite)],
        "sounds": [], "volume": 100, "layerOrder": 2, "visible": False,
        "x": x1, "y": y1, "size": size, "direction": 90,
        "draggable": False, "rotationStyle": "don't rotate",
    }


# ════════════════════════════════════════════════════════════════════════
# 굼바 (Plat3 위에서 좌우 patrol, 위에서 밟으면 squish)
# ════════════════════════════════════════════════════════════════════════
def make_goomba(am, BR, stage_bcast):
    """Plat3 위(-65, 50) 좌우 patrol. walk 2-frame cycle로 걷는 모션."""
    g = BB()
    gf = g.flag()
    g.chain([gf, g.hide()])
    gh = g.bcast_hat(stage_bcast, BR[stage_bcast])
    # Plat3 위. plat 폭 따라 patrol 범위.
    x1, x2, gy = -90, -40, 69
    gi = [g.costume("walk1"), g.goto(x1, gy), g.set_size(40),
          g.point_dir(90), g.show()]
    first_go = g.glide(2, x2, gy)
    turn_back = g.point_dir(-90)
    go_back = g.glide(2, x1, gy)
    turn_fwd = g.point_dir(90)
    go_fwd = g.glide(2, x2, gy)
    g.chain([turn_back, go_back, turn_fwd, go_fwd])
    gfl = g.forever(turn_back)
    g.chain([gh] + gi + [first_go, gfl])

    # walking 애니메이션 — 별도 thread로 walk1↔walk2 cycle
    gh_anim = g.bcast_hat(stage_bcast, BR[stage_bcast])
    cycle = [g.costume("walk1"), g.wait(0.2),
             g.costume("walk2"), g.wait(0.2)]
    g.chain(cycle)
    walk_forever = g.forever(cycle[0])
    g.chain([gh_anim, walk_forever])

    # 밟혔을 때
    gsh = g.bcast_hat("굼바밟기", BR["굼바밟기"])
    squish = [g.stop_other(), g.costume("squish"), g.set_y(70),
              g.wait(2), g.hide()]
    g.chain([gsh] + squish)
    hide_on_end(g)
    return {
        "isStage": False, "name": "Goomba",
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": g.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("walk1", "enemies/goomba/goomba_001.png"),
                     am.reg_png("walk2", "enemies/goomba/goomba_002.png"),
                     am.reg_png("squish", "enemies/goomba/goomba_082.png")],
        "sounds": [], "volume": 100, "layerOrder": 5, "visible": False,
        "x": x1, "y": gy, "size": 40, "direction": 90,
        "draggable": False, "rotationStyle": "left-right",
    }


# ════════════════════════════════════════════════════════════════════════
# 일반 거북이 (Stage 1 패턴 — 밟기로 등껍질)
# ════════════════════════════════════════════════════════════════════════
def make_normal_turtle(am, name, x1, x2, y, speed, stomp_br_name, stomp_br_id,
                       BR, stage_bcast):
    t = BB()
    tf = t.flag()
    t.chain([tf, t.hide()])
    th = t.bcast_hat(stage_bcast, BR[stage_bcast])
    face_left = 90
    face_right = -90
    start_face = face_left if x2 < x1 else face_right
    ti = [t.costume("walk1"), t.goto(x1, y), t.set_size(45),
          t.point_dir(start_face), t.show()]
    first_go = t.glide(speed, x2, y)
    turn_back = t.point_dir(face_right if x2 < x1 else face_left)
    go_back = t.glide(speed, x1, y)
    turn_fwd = t.point_dir(start_face)
    go_fwd = t.glide(speed, x2, y)
    t.chain([turn_back, go_back, turn_fwd, go_fwd])
    tfl = t.forever(turn_back)
    t.chain([th] + ti + [first_go, tfl])

    # walking 애니메이션 — 별도 thread로 코스튬 walk1~4 무한 cycle
    th_anim = t.bcast_hat(stage_bcast, BR[stage_bcast])
    cycle_chain = []
    for i in [1, 2, 3, 4]:
        cycle_chain += [t.costume(f"walk{i}"), t.wait(0.15)]
    t.chain(cycle_chain)
    walk_forever = t.forever(cycle_chain[0])
    t.chain([th_anim, walk_forever])

    tsh = t.bcast_hat(stomp_br_name, stomp_br_id)
    stomp_response = [t.stop_other(), t.costume("shell"), t.goto_front(),
                      t.set_y(-124),
                      t.wait(2), t.hide()]
    t.chain([tsh] + stomp_response)

    hide_on_end(t)
    return {
        "isStage": False, "name": name,
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": t.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("walk1", "turtle/koopa_walk_1.png"),
                     am.reg_png("walk2", "turtle/koopa_walk_2.png"),
                     am.reg_png("walk3", "turtle/koopa_walk_3.png"),
                     am.reg_png("walk4", "turtle/koopa_walk_4.png"),
                     am.reg("shell", svg_shell_large(), 30, 20)],
        "sounds": [], "volume": 100, "layerOrder": 4, "visible": False,
        "x": x1, "y": y, "size": 45, "direction": 90,
        "draggable": False, "rotationStyle": "left-right",
    }


# ════════════════════════════════════════════════════════════════════════
# Pipe (스테이지 종료 지점) — 마리오가 위에서 ↓ 누르면 클리어
# ════════════════════════════════════════════════════════════════════════
def make_pipe(am, BR, sounds, stage_bcast):
    p = BB()
    pf = p.flag()
    p.chain([pf, p.hide()])
    ph = p.bcast_hat(stage_bcast, BR[stage_bcast])
    p.chain([ph, p.goto(210, 54), p.set_size(15), p.show()])
    hide_on_end(p)
    return {
        "isStage": False, "name": "Pipe",
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": p.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("pipe", "background/pipe_green.png")],
        "sounds": sounds, "volume": 100, "layerOrder": 3, "visible": False,
        "x": 210, "y": 54, "size": 15, "direction": 90,
        "draggable": False, "rotationStyle": "don't rotate",
    }


# ════════════════════════════════════════════════════════════════════════
# Mario
# ════════════════════════════════════════════════════════════════════════
def build_mario(am, V, BR, sounds, stage_bcast):
    m = BB()
    mf = m.flag()
    m.chain([mf, m.goto(MARIO_START_X, MARIO_START_Y), m.set_size(45),
             m.costume("걷기1"), m.hide()])

    mh = m.bcast_hat(stage_bcast, BR[stage_bcast])
    m_init = [m.goto(MARIO_START_X, MARIO_START_Y),
              m.set_var("속도Y", V["속도Y"], 0),
              m.set_var("점프중", V["점프중"], 0),
              m.set_var("무적", V["무적"], 0),
              m.set_var("걸음", V["걸음"], 1),
              m.show()]

    physics_blocks = mario_physics(m, V, ground_y=GY+7, landing_costume="걷기1")
    landing_blocks = mario_platform_landing(m, V, PLAT_POSITIONS_PHYS)
    block_blocks = mario_platform_block(m, V, PLAT_POSITIONS_PHYS)
    move_blocks = mario_movement(m, V=V, speed=5, with_direction=True, walk_mode="next")
    jump_block = mario_jump(m, V, velocity=14, jump_costume="점프1")

    # Plat1 추종 — 매 프레임 dx 갱신 (조건 무관), touching 시 change_x 적용.
    # 이렇게 분리하면 prev가 항상 정확히 한 프레임 직전의 Plat1.x를 가리킨다.
    sub_x = m.op_sub(m.sense_of_xpos("Plat1"),
                     m.var_ref("Plat1_x_prev", V["Plat1_x_prev"]))
    update_dx = m.set_var_block("Plat1_dx", V["Plat1_dx"], sub_x)
    update_prev = m.set_var_block("Plat1_x_prev", V["Plat1_x_prev"],
                                   m.sense_of_xpos("Plat1"))
    m.chain([update_dx, update_prev])

    # touching(Plat1)이면 dx만큼 change_x (속도Y 조건 제거 — touching만으로도 추종)
    cond_follow = m.touching("Plat1")
    follow_action = m.change_x_var("Plat1_dx", V["Plat1_dx"])
    if_follow = m.if_then(cond_follow, follow_action)

    # Plat5 수직 추종 — landing/block에서 제외했으므로 여기서 모두 처리
    sub_y = m.op_sub(m.sense_of_ypos("Plat5"),
                     m.var_ref("Plat5_y_prev", V["Plat5_y_prev"]))
    update_dy = m.set_var_block("Plat5_dy", V["Plat5_dy"], sub_y)
    update_prev_y = m.set_var_block("Plat5_y_prev", V["Plat5_y_prev"],
                                     m.sense_of_ypos("Plat5"))

    # Plat5 추종 — mario_platform_landing 패턴 (sensing 기반 동적 plat_y).
    # 조건: touching(Plat5) AND 속도Y<=0 AND mario.y > Plat5.y + 10 (마리오 발이 발판 top 위)
    # 액션: change_y(Plat5_dy + 1) — grav apply_v(-1) cancel + 발판 dy 추적 → 평형.
    not_rising = m.op_not(m.gt_var("속도Y", V["속도Y"], 0))
    plat5_top_margin = m.op_add_block_const(m.sense_of_ypos("Plat5"), 10)
    above_plat5_top = m.op_gt_block(m.ypos(), plat5_top_margin)
    cond_p5 = m.op_and(m.touching("Plat5"),
                       m.op_and(not_rising, above_plat5_top))
    follow_p5 = [m.change_y_var("Plat5_dy", V["Plat5_dy"]),
                 m.change_y(1),
                 m.set_var("속도Y", V["속도Y"], 0),
                 m.set_var("점프중", V["점프중"], 0),
                 m.costume("걷기1")]
    m.chain(follow_p5)
    if_follow_p5 = m.if_then(cond_p5, follow_p5[0])


    stomp_blocks = [mario_stomp(m, V, tn, f"밟기_{tn}", BR[f"밟기_{tn}"])
                    for tn in NORMAL_TURTLE_NAMES]
    normal_hit_blocks = [mario_side_hit(m, V, tn, BR=BR, knockback=30,
                                        reset_costume="걷기1")
                         for tn in NORMAL_TURTLE_NAMES]
    # 굼바: 위에서 밟으면 squish, 옆은 hit
    goomba_stomp = mario_stomp(m, V, "Goomba", "굼바밟기", BR["굼바밟기"])
    goomba_hit = mario_side_hit(m, V, "Goomba", BR=BR, knockback=30,
                                reset_costume="걷기1")
    stomp_blocks.append(goomba_stomp)
    normal_hit_blocks.append(goomba_hit)

    gameover_block = mario_gameover(m, V, hide_mario=True)
    clear_block = mario_pipe_clear(m, V, pipe_name="Pipe",
                                   clear_msg="다음 스테이지로!", msg_time=1)

    all_blocks = (physics_blocks + landing_blocks + block_blocks
                  + [update_dx, if_follow, update_prev,
                     update_dy, if_follow_p5, update_prev_y]
                  + move_blocks + [jump_block]
                  + stomp_blocks + normal_hit_blocks
                  + [gameover_block, clear_block])
    m.chain(all_blocks)
    cs = m.eq_var("게임상태", V["게임상태"], stage_bcast)
    ifs = m.if_then(cs, all_blocks[0])
    fs = m.forever(ifs)
    m.chain([mh] + m_init + [fs])

    mario_invincibility(m, V, BR, duration=1.0)
    hide_on_end(m)

    return {
        "isStage": False, "name": "Mario",
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": m.blocks, "currentCostume": 0,
        "costumes": [
            am.reg_png("걷기1", "mario/mario3_walk_1.png"),
            am.reg_png("걷기3", "mario/mario3_walk_3.png"),
            am.reg_png("걷기4", "mario/mario3_walk_4.png"),
            am.reg_png("걷기5", "mario/mario3_walk_5.png"),
            am.reg_png("걷기6", "mario/mario3_walk_6.png"),
            am.reg_png("점프1", "mario/mario3_jump_5.png"),
        ],
        "sounds": sounds, "volume": 100, "layerOrder": 8, "visible": False,
        "x": MARIO_START_X, "y": MARIO_START_Y, "size": 45, "direction": 90,
        "draggable": False, "rotationStyle": "left-right",
    }


# ════════════════════════════════════════════════════════════════════════
# BUILD
# ════════════════════════════════════════════════════════════════════════
def build():
    am = AssetManager()

    stage_bcast = "스테이지2"
    br_keys = [stage_bcast, "피격", "굼바밟기"]
    for tn in NORMAL_TURTLE_NAMES:
        br_keys.append(f"밟기_{tn}")
    BR = {k: uid() for k in br_keys}

    v_keys = ["하트", "속도Y", "점프중", "게임상태", "무적", "걸음",
              "Plat1_x_prev", "Plat1_dx",
              "Plat5_y_prev", "Plat5_dy"]
    V = {k: uid() for k in v_keys}

    snd_jump = am.reg_snd("Jump", gen_beep(600, 0.1))
    snd_hit = am.reg_snd("Hit", gen_beep(200, 0.2))
    snd_win = am.reg_snd("Win", gen_beep(900, 0.3))

    stage_target = build_stage(am, V, BR, stage_bcast)
    platforms = [make_plat(am, n, x, y, s, BR, stage_bcast)
                 for n, x, y, s in PLAT_POSITIONS]
    moving_platforms = [
        make_moving_plat(am, n, x1, y1, x2, y2, sp,
                         "background/plat_3.png", BR, stage_bcast)
        for n, x1, y1, x2, y2, sp in MOVING_PLATS
    ]
    normal_turtles = [
        make_normal_turtle(am, n, x1, x2, y, sp,
                           f"밟기_{n}", BR[f"밟기_{n}"], BR, stage_bcast)
        for n, x1, x2, y, sp in NORMAL_TURTLES
    ]
    pipe_sprite = make_pipe(am, BR, [snd_win], stage_bcast)
    goomba_sprite = make_goomba(am, BR, stage_bcast)
    mario_sprite = build_mario(am, V, BR, [snd_jump, snd_hit, snd_win],
                               stage_bcast)
    hearts = make_hearts(am, V, BR, restart_br_key="스테이지2")

    project = {
        "targets": [stage_target, *platforms, *moving_platforms, pipe_sprite,
                    goomba_sprite, *normal_turtles, mario_sprite, hearts],
        "monitors": [], "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "0.2.0",
                 "agent": "stage2-generator"},
    }
    return project, am.assets


def main():
    print("Generating Stage 2...")
    proj, assets = build()
    save_sb3("Stage2.sb3", proj, assets)
    print("Controls: ← → move | SPACE jump | ↓ on pipe to clear")


if __name__ == "__main__":
    main()

"""
Stage 1 Standalone Generator: 계단을 넘어라!
4개 발판을 올라가 깃발에 도달! 거북이가 발판 위를 순찰하며 방해.
거북이에 닿으면 하트 -1, 처음 위치로 리셋. 하트 0 = 게임오버.
"""

from common import (
    BB, AssetManager, GY, gen_beep, uid, svg,
    bg_gameover, svg_flag, make_hearts, save_sb3,
)
from mechanics import (
    mario_physics, mario_movement, mario_jump,
    mario_stomp, mario_side_hit, mario_gameover,
    mario_platform_landing, mario_platform_block,
    mario_flag_clear, mario_invincibility, hide_on_end,
)


MARIO_START_X = -200
MARIO_START_Y = GY + 7

PLAT_POSITIONS = [
    ("Plat1", -145, -80, "background/plat_3.png"),
    ("Plat2",  -40, -30, "background/plat_3.png"),
    ("Plat3",   80,  20, "background/plat_3.png"),
    ("Plat4",  200,  70, "background/plat_3.png"),
]

TURTLE_PATROLS = [
    ("Turtle1", 220, -220, -133, 4.0),
    ("Turtle2", -70,  -10, -7, 1.5),
]

TURTLE_NAMES = ["Turtle1", "Turtle2"]


def bg_stage1_clear():
    return svg(480, 360,
        '<rect width="480" height="360" fill="#1565C0"/>'
        '<text x="240" y="160" text-anchor="middle" font-size="40" font-weight="bold" fill="#FFD700">스테이지 1 클리어!</text>'
        '<text x="240" y="220" text-anchor="middle" font-size="18" fill="#FFF">수고했어요, 마리오!</text>'
    )


def svg_shell_large():
    return svg(60, 40,
        '<ellipse cx="30" cy="20" rx="28" ry="18" fill="#2E7D32" stroke="#1B5E20" stroke-width="2"/>'
        '<ellipse cx="30" cy="16" rx="20" ry="14" fill="#4CAF50"/>'
        '<line x1="15" y1="10" x2="15" y2="28" stroke="#1B5E20" stroke-width="2"/>'
        '<line x1="30" y1="6" x2="30" y2="28" stroke="#1B5E20" stroke-width="2"/>'
        '<line x1="45" y1="10" x2="45" y2="28" stroke="#1B5E20" stroke-width="2"/>'
        '<ellipse cx="30" cy="30" rx="24" ry="8" fill="#FFCC02"/>'
    )


# ════════════════════════════════════════════════════════════════════════
# Stage 스프라이트 (백드롭 + 상태머신)
# ════════════════════════════════════════════════════════════════════════
def build_stage(am, V, BR):
    b = BB()
    f0 = b.flag()
    init = [
        b.backdrop("시작화면"),
        b.set_var("게임상태", V["게임상태"], "start"),
        b.set_var("하트", V["하트"], 5),
        b.set_var("속도Y", V["속도Y"], 0),
        b.set_var("점프중", V["점프중"], 0),
        b.set_var("무적", V["무적"], 0),
    ]
    b.chain([f0] + init)

    sp = b.key_hat("space")
    c_start = b.eq_var("게임상태", V["게임상태"], "start")
    s_start = [
        b.set_var("하트", V["하트"], 5),
        b.set_var("속도Y", V["속도Y"], 0),
        b.set_var("점프중", V["점프중"], 0),
        b.set_var("무적", V["무적"], 0),
        b.set_var("게임상태", V["게임상태"], "stage1"),
        b.backdrop("스테이지1"),
        b.broadcast("스테이지1", BR["스테이지1"]),
    ]
    b.chain(s_start)
    if_start = b.if_then(c_start, s_start[0])

    c_go = b.eq_var("게임상태", V["게임상태"], "gameover")
    s_go = [
        b.set_var("하트", V["하트"], 5),
        b.set_var("속도Y", V["속도Y"], 0),
        b.set_var("점프중", V["점프중"], 0),
        b.set_var("무적", V["무적"], 0),
        b.set_var("게임상태", V["게임상태"], "stage1"),
        b.backdrop("스테이지1"),
        b.broadcast("스테이지1", BR["스테이지1"]),
    ]
    b.chain(s_go)
    if_go = b.if_then(c_go, s_go[0])

    b.chain([sp, if_start, if_go])

    gvars = {V[k]: [k, v] for k, v in [("하트", 5), ("게임상태", "start"), ("속도Y", 0), ("점프중", 0), ("무적", 0), ("걸음", 1)]}

    return {
        "isStage": True, "name": "Stage",
        "variables": gvars, "lists": {}, "comments": {},
        "broadcasts": {v: k for k, v in BR.items()},
        "blocks": b.blocks, "currentCostume": 0,
        "costumes": [
            am.reg_png_backdrop("시작화면", "background/bg_stage.png"),
            am.reg_png_backdrop("스테이지1", "background/bg_stage.png"),
            am.reg("게임오버", bg_gameover(), 240, 180),
            am.reg("클리어", bg_stage1_clear(), 240, 180),
        ],
        "sounds": [], "volume": 100, "layerOrder": 0,
        "tempo": 60, "videoTransparency": 50, "videoState": "off",
        "textToSpeechLanguage": None,
    }


# ════════════════════════════════════════════════════════════════════════
# Platform 스프라이트
# ════════════════════════════════════════════════════════════════════════
def make_plat(am, name, x, y, sprite, BR):
    p = BB()
    pf = p.flag()
    p.chain([pf, p.hide()])
    ph = p.bcast_hat("스테이지1", BR["스테이지1"])
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
# Mario 스프라이트 (mechanics 함수 사용)
# ════════════════════════════════════════════════════════════════════════
def build_mario(am, V, BR, sounds):
    m = BB()

    # 초기화: 깃발 클릭
    mf = m.flag()
    m.chain([mf, m.goto(MARIO_START_X, MARIO_START_Y), m.set_size(45), m.costume("걷기1"), m.hide()])

    # 초기화: 스테이지 시작
    mh1 = m.bcast_hat("스테이지1", BR["스테이지1"])
    m1_init = [
        m.goto(MARIO_START_X, MARIO_START_Y),
        m.set_var("속도Y", V["속도Y"], 0),
        m.set_var("점프중", V["점프중"], 0),
        m.set_var("무적", V["무적"], 0),
        m.set_var("걸음", V["걸음"], 1),
        m.show(),
    ]

    # 기능별 독립 함수 호출
    physics_blocks  = mario_physics(m, V, ground_y=GY+7, landing_costume="걷기1")
    landing_blocks  = mario_platform_landing(m, V, PLAT_POSITIONS)
    block_blocks    = mario_platform_block(m, V, PLAT_POSITIONS)
    move_blocks     = mario_movement(m, V=V, speed=5, with_direction=True, walk_mode="next")
    jump_block      = mario_jump(m, V, velocity=14, jump_costume="점프1")
    # 밟기: 낙하 중 접촉 → 거북이 등껍질 변신 + 바운스
    stomp_blocks    = [mario_stomp(m, V, tn, f"밟기{i+1}", BR[f"밟기{i+1}"])
                       for i, tn in enumerate(TURTLE_NAMES)]
    # 피격: 낙하가 아닐 때 접촉 → 하트 감소 + 리셋
    hit_blocks      = [mario_side_hit(m, V, tn,
                                      BR=BR, knockback=30,
                                      reset_costume="걷기1")
                       for tn in TURTLE_NAMES]
    gameover_block  = mario_gameover(m, V, hide_mario=True)
    clear_block     = mario_flag_clear(m, V, clear_msg="스테이지 1 클리어!")

    # forever 루프 조립 (순서: 물리 → 착지 → 발판막힘 → 이동 → 점프 → 밟기 → 피격 → 게임오버 → 클리어)
    all_blocks = physics_blocks + landing_blocks + block_blocks + move_blocks + [jump_block] + stomp_blocks + hit_blocks + [gameover_block, clear_block]
    m.chain(all_blocks)

    cs1 = m.eq_var("게임상태", V["게임상태"], "stage1")
    ifs1 = m.if_then(cs1, all_blocks[0])
    fs1 = m.forever(ifs1)
    m.chain([mh1] + m1_init + [fs1])

    # 무적 처리 (별도 스크립트: 피격 브로드캐스트 수신 → 무적 0.5초)
    mario_invincibility(m, V, BR, duration=1.0)

    # 종료 백드롭 전환 시 hide
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
        "sounds": sounds, "volume": 100, "layerOrder": 5, "visible": False,
        "x": MARIO_START_X, "y": MARIO_START_Y, "size": 45, "direction": 90,
        "draggable": False, "rotationStyle": "left-right",
    }


# ════════════════════════════════════════════════════════════════════════
# Flag 스프라이트
# ════════════════════════════════════════════════════════════════════════
def make_flag(am, BR, sounds):
    fl = BB()
    flf = fl.flag()
    fl.chain([flf, fl.hide()])
    flh = fl.bcast_hat("스테이지1", BR["스테이지1"])
    fl.chain([flh, fl.goto(213, 94), fl.set_size(6), fl.point_dir(-90), fl.show()])
    hide_on_end(fl)
    return {
        "isStage": False, "name": "Flag",
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": fl.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("flag", "background/flag_mario.png")],
        "sounds": sounds, "volume": 100, "layerOrder": 3, "visible": False,
        "x": 213, "y": 94, "size": 6, "direction": -90,
        "draggable": False, "rotationStyle": "left-right",
    }


# ════════════════════════════════════════════════════════════════════════
# Turtle 스프라이트
# ════════════════════════════════════════════════════════════════════════
def make_turtle(am, name, x1, x2, y, speed, stomp_br_name, stomp_br_id, BR):
    t = BB()
    tf = t.flag()
    t.chain([tf, t.hide()])
    th = t.bcast_hat("스테이지1", BR["스테이지1"])

    face_left = 90
    face_right = -90
    start_face = face_left if x2 < x1 else face_right
    ti = [t.costume("walk1"), t.goto(x1, y), t.set_size(45), t.point_dir(start_face), t.show()]

    first_go = t.glide(speed, x2, y)
    turn_back = t.point_dir(face_right if x2 < x1 else face_left)
    go_back = t.glide(speed, x1, y)
    turn_fwd = t.point_dir(start_face)
    go_fwd = t.glide(speed, x2, y)
    t.chain([turn_back, go_back, turn_fwd, go_fwd])
    tfl = t.forever(turn_back)
    t.chain([th] + ti + [first_go, tfl])

    # walking 애니메이션 — 별도 thread로 코스튬 walk1~4 무한 cycle
    th_anim = t.bcast_hat("스테이지1", BR["스테이지1"])
    cycle_chain = []
    for i in [1, 2, 3, 4]:
        cycle_chain += [t.costume(f"walk{i}"), t.wait(0.15)]
    t.chain(cycle_chain)
    walk_forever = t.forever(cycle_chain[0])
    t.chain([th_anim, walk_forever])

    tsh = t.bcast_hat(stomp_br_name, stomp_br_id)
    stomp_response = [t.stop_other(), t.costume("shell"), t.goto_front()]
    if name == "Turtle1":
        stomp_response.append(t.set_y(-123))
    elif name == "Turtle2":
        stomp_response.append(t.set_y(3))
    stomp_response += [t.wait(2), t.hide()]
    t.chain([tsh] + stomp_response)

    hide_on_end(t)

    return {
        "isStage": False, "name": name,
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": t.blocks, "currentCostume": 0,
        "costumes": [
            am.reg_png("walk1", "turtle/koopa_walk_1.png"),
            am.reg_png("walk2", "turtle/koopa_walk_2.png"),
            am.reg_png("walk3", "turtle/koopa_walk_3.png"),
            am.reg_png("walk4", "turtle/koopa_walk_4.png"),
            am.reg("shell", svg_shell_large(), 30, 20),
        ],
        "sounds": [], "volume": 100, "layerOrder": 4, "visible": False,
        "x": x1, "y": y, "size": 45, "direction": 90,
        "draggable": False, "rotationStyle": "left-right",
    }


# ════════════════════════════════════════════════════════════════════════
# BUILD + MAIN
# ════════════════════════════════════════════════════════════════════════
def build():
    am = AssetManager()

    BR = {k: uid() for k in ["시작", "스테이지1", "게임오버", "클리어", "리셋", "밟기1", "밟기2", "피격"]}
    V  = {k: uid() for k in ["하트", "게임상태", "속도Y", "점프중", "무적", "걸음"]}

    snd_jump = am.reg_snd("Jump", gen_beep(600, 0.1))
    snd_hit  = am.reg_snd("Hit",  gen_beep(200, 0.2))
    snd_win  = am.reg_snd("Win",  gen_beep(900, 0.3))

    stage_target = build_stage(am, V, BR)
    platforms = [make_plat(am, n, x, y, s, BR) for n, x, y, s in PLAT_POSITIONS]
    flag_sprite = make_flag(am, BR, [snd_win])
    turtles = [make_turtle(am, name, x1, x2, y, speed, f"밟기{i+1}", BR[f"밟기{i+1}"], BR)
               for i, (name, x1, x2, y, speed) in enumerate(TURTLE_PATROLS)]
    mario_sprite = build_mario(am, V, BR, [snd_jump, snd_hit, snd_win])
    hearts = make_hearts(am, V, BR)

    project = {
        "targets": [stage_target, *platforms, flag_sprite, *turtles, mario_sprite, hearts],
        "monitors": [], "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "stage1-generator"},
    }

    return project, am.assets


def main():
    proj, assets = build()
    save_sb3("Stage1.sb3", proj, assets)


if __name__ == "__main__":
    main()

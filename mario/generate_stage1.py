"""
Stage 1 Standalone Generator: 계단을 넘어라!
4개 발판을 올라가 깃발에 도달! 거북이가 발판 위를 순찰하며 방해.
거북이에 닿으면 하트 -1, 처음 위치로 리셋. 하트 0 = 게임오버.
"""

from common import (
    BB, AssetManager, GY, gen_beep, uid, svg,
    bg_gameover, svg_flag, make_hearts, save_sb3,
)


def bg_stage1_clear():
    from common import svg
    return svg(480, 360,
        '<rect width="480" height="360" fill="#1565C0"/>'
        '<text x="240" y="160" text-anchor="middle" font-size="40" font-weight="bold" fill="#FFD700">스테이지 1 클리어!</text>'
        '<text x="240" y="220" text-anchor="middle" font-size="18" fill="#FFF">수고했어요, 마리오!</text>'
    )


MARIO_START_X = -200
MARIO_START_Y = GY


def svg_shell_large():
    """거북이 등껍질 SVG (밟혔을 때 표시용, 60x40px)"""
    return svg(60, 40,
        '<ellipse cx="30" cy="20" rx="28" ry="18" fill="#2E7D32" stroke="#1B5E20" stroke-width="2"/>'
        '<ellipse cx="30" cy="16" rx="20" ry="14" fill="#4CAF50"/>'
        '<line x1="15" y1="10" x2="15" y2="28" stroke="#1B5E20" stroke-width="2"/>'
        '<line x1="30" y1="6" x2="30" y2="28" stroke="#1B5E20" stroke-width="2"/>'
        '<line x1="45" y1="10" x2="45" y2="28" stroke="#1B5E20" stroke-width="2"/>'
        '<ellipse cx="30" cy="30" rx="24" ry="8" fill="#FFCC02"/>'
    )


def main():
    am = AssetManager()

    BR = {k: uid() for k in ["시작", "스테이지1", "게임오버", "클리어", "리셋", "밟기1", "밟기2"]}
    V  = {k: uid() for k in ["하트", "게임상태", "속도Y", "점프중"]}

    snd_jump = am.reg_snd("Jump", gen_beep(600, 0.1))
    snd_hit  = am.reg_snd("Hit",  gen_beep(200, 0.2))
    snd_win  = am.reg_snd("Win",  gen_beep(900, 0.3))

    gvars = {V[k]: [k, v] for k, v in [("하트", 5), ("게임상태", "start"), ("속도Y", 0), ("점프중", 0)]}

    # ════════════════════════════════════════════════════════════════════════
    # STAGE
    # ════════════════════════════════════════════════════════════════════════
    b = BB()
    f0 = b.flag()
    init = [
        b.backdrop("시작화면"),
        b.set_var("게임상태", V["게임상태"], "start"),
        b.set_var("하트", V["하트"], 5),
        b.set_var("속도Y", V["속도Y"], 0),
        b.set_var("점프중", V["점프중"], 0),
    ]
    b.chain([f0] + init)

    sp = b.key_hat("space")
    c_start = b.eq_var("게임상태", V["게임상태"], "start")
    s_start = [
        b.set_var("하트", V["하트"], 5),
        b.set_var("속도Y", V["속도Y"], 0),
        b.set_var("점프중", V["점프중"], 0),
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
        b.set_var("게임상태", V["게임상태"], "stage1"),
        b.backdrop("스테이지1"),
        b.broadcast("스테이지1", BR["스테이지1"]),
    ]
    b.chain(s_go)
    if_go = b.if_then(c_go, s_go[0])

    b.chain([sp, if_start, if_go])

    stage_target = {
        "isStage": True, "name": "Stage",
        "variables": gvars, "lists": {}, "comments": {},
        "broadcasts": {v: k for k, v in BR.items()},
        "blocks": b.blocks, "currentCostume": 0,
        "costumes": [
            am.reg_png_backdrop("시작화면", "bg_stage.png"),
            am.reg_png_backdrop("스테이지1", "bg_stage.png"),
            am.reg("게임오버", bg_gameover(), 240, 180),
            am.reg("클리어", bg_stage1_clear(), 240, 180),
        ],
        "sounds": [], "volume": 100, "layerOrder": 0,
        "tempo": 60, "videoTransparency": 50, "videoState": "off",
        "textToSpeechLanguage": None,
    }

    # ════════════════════════════════════════════════════════════════════════
    # PLATFORMS (4개 - 우상향 계단, 120px 간격 + 75% 축소 → 갭 48px)
    # ════════════════════════════════════════════════════════════════════════
    # plat_3.png=96px, 75%=72px 실효폭, 갭=48px
    # 걸어서 48px 이동 중 충분히 낙하 → 점프 필수
    # 인접 발판 120px(점프 가능) / 건너뛰기 240px(점프 불가, 최대 112px)
    PLAT_POSITIONS = [
        ("Plat1", -160, -80, "plat_3.png"),
        ("Plat2",  -40, -30, "plat_3.png"),
        ("Plat3",   80,  20, "plat_3.png"),
        ("Plat4",  200,  70, "plat_3.png"),
    ]

    def make_plat(name, x, y, sprite):
        p = BB()
        pf = p.flag()
        p.chain([pf, p.hide()])
        ph = p.bcast_hat("스테이지1", BR["스테이지1"])
        p.chain([ph, p.goto(x, y), p.set_size(75), p.show()])
        return {
            "isStage": False, "name": name,
            "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
            "blocks": p.blocks, "currentCostume": 0,
            "costumes": [am.reg_png("plat", sprite)],
            "sounds": [], "volume": 100, "layerOrder": 2, "visible": False,
            "x": x, "y": y, "size": 75, "direction": 90,
            "draggable": False, "rotationStyle": "don't rotate",
        }

    platforms = [make_plat(*p) for p in PLAT_POSITIONS]

    # ════════════════════════════════════════════════════════════════════════
    # MARIO
    # ════════════════════════════════════════════════════════════════════════
    m = BB()
    mf = m.flag()
    m.chain([mf, m.goto(MARIO_START_X, MARIO_START_Y), m.set_size(45), m.costume("걷기1"), m.hide()])

    mh1 = m.bcast_hat("스테이지1", BR["스테이지1"])
    m1_init = [
        m.goto(MARIO_START_X, MARIO_START_Y),
        m.set_var("속도Y", V["속도Y"], 0),
        m.set_var("점프중", V["점프중"], 0),
        m.show(),
    ]

    # ── Physics ──
    grav    = m.change_var("속도Y", V["속도Y"], -1)
    apply_v = m.change_y_var("속도Y", V["속도Y"])

    # Ground snap (착지 시 걷기 코스튬 복귀)
    cg  = m.lt_ypos(GY)
    gs  = [m.set_y(GY), m.set_var("속도Y", V["속도Y"], 0), m.set_var("점프중", V["점프중"], 0), m.costume("걷기1")]
    m.chain(gs)
    ifg = m.if_then(cg, gs[0])

    # Platform landing checks
    # 조건: 낙하 중 + 발판 닿음 + 마리오 Y > 발판 Y+10 (위에서만 착지)
    # change_y(1) = 매 프레임 중력(-1) 정확히 상쇄 → 안정, 떨림 없음
    def plat_check(pname, plat_y):
        tp = m.touching(pname)
        fl = m.lt_var("속도Y", V["속도Y"], 0)
        above = m.gt_ypos(plat_y + 10)
        ca = m.op_and(tp, m.op_and(fl, above))
        sn = [m.change_y(1), m.set_var("속도Y", V["속도Y"], 0), m.set_var("점프중", V["점프중"], 0), m.costume("걷기1")]
        m.chain(sn)
        return m.if_then(ca, sn[0])

    plat_checks = [plat_check(n, y) for n, _, y, _ in PLAT_POSITIONS]

    # ── Movement (걷기 애니메이션 포함) ──
    kr  = m.key_pressed("right arrow")
    mvr = [m.change_x(5), m.point_dir(90), m.next_costume()]
    m.chain(mvr)
    ifr = m.if_then(kr, mvr[0])

    kl  = m.key_pressed("left arrow")
    mvl = [m.change_x(-5), m.point_dir(-90), m.next_costume()]
    m.chain(mvl)
    ifl = m.if_then(kl, mvl[0])

    # ── Jump (점프 코스튬 전환) ──
    kj  = m.key_pressed("space")
    cnj = m.eq_var("점프중", V["점프중"], 0)
    cj  = m.op_and(kj, cnj)
    jb  = [m.set_var("속도Y", V["속도Y"], 14), m.set_var("점프중", V["점프중"], 1), m.costume("점프1"), m.play_sound("Jump")]
    m.chain(jb)
    ifj = m.if_then(cj, jb[0])

    # ── Flag touch ──
    tfl = m.touching("Flag")
    s1_clear = [
        m.say_for("스테이지 1 클리어!", 2),
        m.set_var("게임상태", V["게임상태"], "clear"),
        m.backdrop("클리어"),
        m.stop_all(),
    ]
    m.chain(s1_clear)
    iff = m.if_then(tfl, s1_clear[0])

    # ── Turtle collision: 밟기(위에서 낙하) → 등껍질 / 옆 충돌 → 데미지 ──
    TURTLE_NAMES = ["Turtle1", "Turtle2"]

    def turtle_hit(tname, stomp_br_name, stomp_br_id):
        # 밟기: 거북이에 닿음 + 낙하 중 → 바운스 + 밟기 브로드캐스트
        tt1 = m.touching(tname)
        falling = m.lt_var("속도Y", V["속도Y"], 0)
        stomp_cond = m.op_and(tt1, falling)
        stomp_actions = [
            m.set_var("속도Y", V["속도Y"], 10),
            m.change_y(15),
            m.broadcast(stomp_br_name, stomp_br_id),
            m.play_sound("Jump"),
        ]
        m.chain(stomp_actions)
        if_stomp = m.if_then(stomp_cond, stomp_actions[0])

        # 옆 충돌: 밟기가 먼저 실행 → Mario +15px 이동 → touching 해제
        # 밟기 안 됐으면 여전히 touching → 데미지
        tt2 = m.touching(tname)
        hit = [
            m.change_var("하트", V["하트"], -1),
            m.play_sound("Hit"),
            m.goto(MARIO_START_X, MARIO_START_Y),
            m.set_var("속도Y", V["속도Y"], 0),
            m.set_var("점프중", V["점프중"], 0),
            m.costume("걷기1"),
            m.wait(0.5),
        ]
        m.chain(hit)
        if_side = m.if_then(tt2, hit[0])

        return [if_stomp, if_side]

    turtle_hits = []
    for i, tn in enumerate(TURTLE_NAMES):
        turtle_hits.extend(turtle_hit(tn, f"밟기{i+1}", BR[f"밟기{i+1}"]))

    # ── Heart / game-over ──
    ch1  = m.lt_var("하트", V["하트"], 1)
    die1 = [
        m.set_var("게임상태", V["게임상태"], "gameover"),
        m.backdrop("게임오버"),
        m.hide(),
    ]
    m.chain(die1)
    ifd1 = m.if_then(ch1, die1[0])

    # ── Assemble forever loop ──
    physics = [grav, apply_v, ifg] + plat_checks + [ifr, ifl, ifj] + turtle_hits + [ifd1, iff]
    m.chain(physics)
    cs1  = m.eq_var("게임상태", V["게임상태"], "stage1")
    ifs1 = m.if_then(cs1, grav)
    fs1  = m.forever(ifs1)
    m.chain([mh1] + m1_init + [fs1])

    mario_sprite = {
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
        "sounds": [snd_jump, snd_hit, snd_win],
        "volume": 100, "layerOrder": 5, "visible": False,
        "x": MARIO_START_X, "y": MARIO_START_Y, "size": 45, "direction": 90,
        "draggable": False, "rotationStyle": "left-right",
    }

    # ════════════════════════════════════════════════════════════════════════
    # FLAG (4단 발판 위)
    # ════════════════════════════════════════════════════════════════════════
    fl  = BB()
    flf = fl.flag()
    fl.chain([flf, fl.hide()])
    flh = fl.bcast_hat("스테이지1", BR["스테이지1"])
    # Plat4(x=200, y=70, plat_3 75%) 오른쪽 끝에 깃발
    fl.chain([flh, fl.goto(220, 130), fl.show()])

    flag_sprite = {
        "isStage": False, "name": "Flag",
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": fl.blocks, "currentCostume": 0,
        "costumes": [am.reg("flag", svg_flag(), 10, 25)],
        "sounds": [snd_win], "volume": 100, "layerOrder": 3, "visible": False,
        "x": 220, "y": 130, "size": 200, "direction": 90,
        "draggable": False, "rotationStyle": "don't rotate",
    }

    # ════════════════════════════════════════════════════════════════════════
    # TURTLES (발판 위 순찰 - 좌우로 왔다갔다)
    # ════════════════════════════════════════════════════════════════════════
    # Turtle1: 바닥 순찰 (맵 끝에서 끝까지)
    # Turtle2: Plat2(x=-40,y=-30) 위에서 순찰
    TURTLE_PATROLS = [
        ("Turtle1", 220, -220, GY, 4.0),       # 바닥: 맵 끝↔끝 순찰
        ("Turtle2", -70,  -10, -10, 1.5),       # Plat2 위 순찰
    ]

    def make_turtle(name, x1, x2, y, speed, stomp_br_name, stomp_br_id):
        t = BB()
        tf = t.flag()
        t.chain([tf, t.hide()])
        th = t.bcast_hat("스테이지1", BR["스테이지1"])
        # 스프라이트 기본=왼쪽 바라봄(dir 90), 반전=오른쪽(dir -90)
        face_left = 90     # 원본 그대로 = 왼쪽
        face_right = -90   # 좌우반전 = 오른쪽
        start_face = face_left if x2 < x1 else face_right
        ti = [t.goto(x1, y), t.set_size(55), t.point_dir(start_face), t.show()]
        # 첫 이동
        first_go = t.glide(speed, x2, y)
        # 도착 후 방향 전환 → 반대로 이동 → 반복
        turn_back = t.point_dir(face_right if x2 < x1 else face_left)
        go_back = t.glide(speed, x1, y)
        turn_fwd = t.point_dir(start_face)
        go_fwd = t.glide(speed, x2, y)
        t.chain([turn_back, go_back, turn_fwd, go_fwd])
        tfl = t.forever(turn_back)
        t.chain([th] + ti + [first_go, tfl])

        # 밟기 브로드캐스트 수신 → 등껍질로 변신, 순찰 중지
        tsh = t.bcast_hat(stomp_br_name, stomp_br_id)
        stomp_response = [
            t.stop_other(),
            t.costume("shell"),
            t.wait(2),
            t.hide(),
        ]
        t.chain([tsh] + stomp_response)

        return {
            "isStage": False, "name": name,
            "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
            "blocks": t.blocks, "currentCostume": 0,
            "costumes": [
                am.reg_png("koopa", "koopa/koopa_walk_1.png"),
                am.reg("shell", svg_shell_large(), 30, 20),
            ],
            "sounds": [], "volume": 100, "layerOrder": 4, "visible": False,
            "x": x1, "y": y, "size": 55, "direction": 90,
            "draggable": False, "rotationStyle": "left-right",
        }

    turtles = []
    for i, (name, x1, x2, y, speed) in enumerate(TURTLE_PATROLS):
        turtles.append(make_turtle(name, x1, x2, y, speed, f"밟기{i+1}", BR[f"밟기{i+1}"]))

    # ════════════════════════════════════════════════════════════════════════
    # HEARTS
    # ════════════════════════════════════════════════════════════════════════
    hearts = make_hearts(am, V)

    # ════════════════════════════════════════════════════════════════════════
    # PROJECT
    # ════════════════════════════════════════════════════════════════════════
    project = {
        "targets": [
            stage_target,
            *platforms,
            flag_sprite,
            *turtles,
            mario_sprite,
            hearts,
        ],
        "monitors": [],
        "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "stage1-generator"},
    }

    save_sb3("Stage1.sb3", project, am.assets)


if __name__ == "__main__":
    main()

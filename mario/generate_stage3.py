"""
스테이지 3 - 쿠파를 물리쳐라!
?블록 발판 머리로 부수기 → 파이어 꽃 → 화이트 마리오 변신 → Z키 파이어볼로 쿠파 처치
"""

from common import *
from mechanics import (
    mario_physics, mario_movement, mario_jump, mario_side_hit,
    mario_gameover, mario_invincibility, hide_on_end,
    mario_platform_landing, mario_platform_block,
)


QBLOCK_X, QBLOCK_Y = -115, -75
BLOCK_SIZE = 75            # block1 sprite 32x32 → size 75이면 24x24 화면
FLOWER_X, FLOWER_Y = QBLOCK_X, -54

# Pipe: 사용자 지정 (-215, -133) sprite 중심. size 15 → 화면 ~38px height. 위 표면 ≈ -114.
PIPE_X, PIPE_Y, PIPE_SIZE = -215, -133, 15
PIPE_TOP_Y = -114          # 파이프 위 표면 (mario_platform_landing plat_y로 사용)

# 마리오는 파이프 위에서 시작 → 파이프 위 표면 위에 sprite 중심을 둠.
# sprite alpha padding 보정 +6
MARIO_START_X, MARIO_START_Y = PIPE_X, PIPE_TOP_Y + 28

# 3개 단일 블록 sprite: BrickLeft + QBlock(가운데, ?블록) + BrickRight.
# 헤딩 발동은 가운데 QBlock만 — 양옆 brick은 발판 역할만.
PLAT_POSITIONS_PHYS = [
    ("BrickLeft",  -138, QBLOCK_Y, ""),
    ("QBlock",     QBLOCK_X, QBLOCK_Y, ""),
    ("BrickRight", -91, QBLOCK_Y, ""),
    ("Pipe",       PIPE_X, PIPE_TOP_Y, ""),
]


def bg_start_s3():
    return svg(480, 360,
        '<rect width="480" height="360" fill="#B71C1C"/>'
        '<rect x="0" y="0" width="480" height="40" fill="#222"/>'
        '<text x="240" y="130" text-anchor="middle" font-size="36" font-weight="bold" fill="#FFD700">STAGE 3</text>'
        '<text x="240" y="175" text-anchor="middle" font-size="18" fill="#FFF">쿠파를 물리쳐라!</text>'
        '<text x="240" y="240" text-anchor="middle" font-size="16" fill="#DDD">SPACE 키를 눌러 시작</text>')


# ════════════════════════════════════════════════════════════════════════
# Stage 스프라이트
# ════════════════════════════════════════════════════════════════════════
def build_stage(am, V, BR):
    b = BB()
    f0 = b.flag()
    init = [b.backdrop("시작화면"), b.set_var("게임상태", V["게임상태"], "start"),
            b.set_var("하트", V["하트"], 5), b.set_var("속도Y", V["속도Y"], 0),
            b.set_var("점프중", V["점프중"], 0), b.set_var("무적", V["무적"], 0),
            b.set_var("쿠파HP", V["쿠파HP"], 10),
            b.set_var("파이어", V["파이어"], 0),
            b.set_var("꽃등장됨", V["꽃등장됨"], 0),
            b.stop_sounds()]
    b.chain([f0] + init)

    sp = b.key_hat("space")
    c1 = b.eq_var("게임상태", V["게임상태"], "start")
    s1 = [b.set_var("게임상태", V["게임상태"], "stage3"), b.backdrop("스테이지3"),
          b.broadcast("스테이지3", BR["스테이지3"])]
    b.chain(s1); if1 = b.if_then(c1, s1[0])

    def restart_seq():
        seq = [b.set_var("하트", V["하트"], 5), b.set_var("쿠파HP", V["쿠파HP"], 10),
               b.set_var("속도Y", V["속도Y"], 0), b.set_var("점프중", V["점프중"], 0),
               b.set_var("무적", V["무적"], 0),
               b.set_var("파이어", V["파이어"], 0),
               b.set_var("꽃등장됨", V["꽃등장됨"], 0),
               b.set_var("게임상태", V["게임상태"], "stage3"),
               b.backdrop("스테이지3"),
               b.broadcast("스테이지3", BR["스테이지3"])]
        b.chain(seq)
        return seq[0]

    c2 = b.eq_var("게임상태", V["게임상태"], "gameover")
    if2 = b.if_then(c2, restart_seq())
    # 엔딩(win) 후 재시작 없음 — 게임 종료
    b.chain([sp, if1, if2])

    # stage clicked → "발사" broadcast (사용자 마우스 클릭으로 파이어볼 발동)
    sc = b._add("event_whenstageclicked", top=True)
    b.chain([sc, b.broadcast("발사", BR["발사"])])

    gvars = {V[k]: [k, v] for k, v in [("하트", 5), ("속도Y", 0), ("점프중", 0),
                                       ("게임상태", "start"), ("쿠파HP", 10),
                                       ("무적", 0), ("걸음", 1),
                                       ("파이어", 0), ("꽃등장됨", 0)]}

    return {
        "isStage": True, "name": "Stage", "variables": gvars, "lists": {}, "comments": {},
        "broadcasts": {v: k for k, v in BR.items()},
        "blocks": b.blocks, "currentCostume": 0,
        "costumes": [am.reg_png_backdrop("시작화면", "background/bg_stage.png"),
                     am.reg_png_backdrop("스테이지3", "background/bg_stage.png"),
                     am.reg("게임오버", bg_gameover(), 240, 180),
                     am.reg("승리", bg_victory(), 240, 180)],
        "sounds": [], "volume": 100, "layerOrder": 0, "tempo": 60,
        "videoTransparency": 50, "videoState": "off", "textToSpeechLanguage": None
    }


# ════════════════════════════════════════════════════════════════════════
# Mario (일반)
# ════════════════════════════════════════════════════════════════════════
def _build_mario_body(m, V, BR, costume_walk1, costume_jump, sprite_active_when_fire):
    """일반/화이트 마리오 공통 메카닉 빌더.
    sprite_active_when_fire: 0 또는 1 — 파이어 변수가 이 값일 때만 forever 활성.
    """
    physics_blocks = mario_physics(m, V, ground_y=GY+7, landing_costume=costume_walk1)
    landing_blocks = mario_platform_landing(m, V, PLAT_POSITIONS_PHYS, reset_costume=costume_walk1)
    block_blocks   = mario_platform_block(m, V, PLAT_POSITIONS_PHYS)
    move_blocks    = mario_movement(m, V=V, speed=5, with_direction=True, walk_mode="next")
    jump_block     = mario_jump(m, V, velocity=14, jump_costume=costume_jump)
    # Stage 1, 2와 동일 방식: mario_side_hit (walking 중 옆 접촉 시 차감)
    enemy_block    = mario_side_hit(m, V, "Bowser", BR=BR, knockback=30,
                                    reset_costume=costume_walk1)
    gameover_block = mario_gameover(m, V)

    cwin = m.lt_var("쿠파HP", V["쿠파HP"], 1)
    # 쿠파 멘트(2) + 도망(2) + 피치 걸어오기(3) + 멘트(4) 끝난 뒤 승리 화면 전환 → 총 ~13초 대기
    win3 = [m.wait(13),
            m.set_var("게임상태", V["게임상태"], "win"),
            m.backdrop("승리"),
            m.hide()]
    m.chain(win3)
    ifw3 = m.if_then(cwin, win3[0])

    ck_qb = m.touching("QBlock")
    ck_rising = m.gt_var("속도Y", V["속도Y"], 0)
    ck_unused = m.eq_var("꽃등장됨", V["꽃등장됨"], 0)
    cand_qb = m.op_and(ck_qb, m.op_and(ck_rising, ck_unused))
    hit_qb = [m.set_var("꽃등장됨", V["꽃등장됨"], 1),
              m.broadcast("꽃등장", BR["꽃등장"]),
              m.set_var("속도Y", V["속도Y"], 0)]
    m.chain(hit_qb)
    if_qb = m.if_then(cand_qb, hit_qb[0])

    # 추가 안전망: 거리 기반 충돌 (낙하/공중 등 side_hit이 못 잡는 경우 대비)
    d_bw = m.distance_to("Bowser")
    cond_d = m.lt_block_const(d_bw, 55)
    not_inv = m.eq_var("무적", V["무적"], 0)
    cand_d = m.op_and(cond_d, not_inv)
    hit_d = [m.change_var("하트", V["하트"], -1),
             m.broadcast("피격", BR["피격"]),
             m.play_sound("Hit"),
             m.move(-30),
             m.set_var("속도Y", V["속도Y"], 0),
             m.set_var("점프중", V["점프중"], 0)]
    m.chain(hit_d)
    if_d_bw = m.if_then(cand_d, hit_d[0])

    all_blocks = (physics_blocks + landing_blocks + [if_qb] + block_blocks
                  + move_blocks
                  + [jump_block, enemy_block, if_d_bw, gameover_block, ifw3])

    # 일반 마리오만 파이어 꽃 접촉 처리
    if sprite_active_when_fire == 0:
        ck_fl = m.touching("FireFlower")
        ck_not_fire = m.eq_var("파이어", V["파이어"], 0)
        cand_fl = m.op_and(ck_fl, ck_not_fire)
        hit_fl = [m.set_var("파이어", V["파이어"], 1),
                  m.broadcast("파이어변신", BR["파이어변신"])]
        m.chain(hit_fl)
        if_fl = m.if_then(cand_fl, hit_fl[0])
        all_blocks.append(if_fl)

    return all_blocks


def build_mario(am, V, BR, sounds):
    m = BB()
    mf = m.flag()
    # 시작 화면에서는 hide. "스테이지3" broadcast 받을 때만 show.
    m.chain([mf, m.goto(MARIO_START_X, MARIO_START_Y), m.set_size(45),
             m.costume("걷기1"), m.hide()])

    mh3 = m.bcast_hat("스테이지3", BR["스테이지3"])
    m3_init = [m.goto(MARIO_START_X, MARIO_START_Y), m.costume("걷기1"),
               m.set_var("속도Y", V["속도Y"], 0), m.set_var("점프중", V["점프중"], 0),
               m.set_var("무적", V["무적"], 0), m.set_var("걸음", V["걸음"], 1),
               m.show()]

    all_blocks = _build_mario_body(m, V, BR, "걷기1", "점프1", sprite_active_when_fire=0)
    m.chain(all_blocks)

    # forever cond: 게임상태=="stage3" AND 파이어==0 (변신 전만 활성)
    cs3 = m.eq_var("게임상태", V["게임상태"], "stage3")
    not_fire = m.eq_var("파이어", V["파이어"], 0)
    cand_active = m.op_and(cs3, not_fire)
    ifs3 = m.if_then(cand_active, all_blocks[0])
    fs3 = m.forever(ifs3)
    m.chain([mh3] + m3_init + [fs3])

    # 변신 broadcast → hide
    fhat = m.bcast_hat("파이어변신", BR["파이어변신"])
    m.chain([fhat, m.hide()])

    # 디버그: Z 키 누르면 마리오가 "Z!" 표시
    ztest = m.key_hat("x")
    m.chain([ztest, m.say_for("X!", 0.5)])

    mario_invincibility(m, V, BR, duration=1.0)
    hide_on_end(m, ("게임오버", "승리"))

    return {
        "isStage": False, "name": "Mario", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": m.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("걷기1", "mario/mario3_walk_1.png"),
                     am.reg_png("걷기3", "mario/mario3_walk_3.png"),
                     am.reg_png("걷기4", "mario/mario3_walk_4.png"),
                     am.reg_png("걷기5", "mario/mario3_walk_5.png"),
                     am.reg_png("걷기6", "mario/mario3_walk_6.png"),
                     am.reg_png("점프1", "mario/mario3_jump_5.png")],
        "sounds": sounds, "volume": 100, "layerOrder": 8, "visible": False,
        "x": MARIO_START_X, "y": MARIO_START_Y, "size": 45, "direction": 90, "draggable": False, "rotationStyle": "left-right"
    }


# ════════════════════════════════════════════════════════════════════════
# 화이트 마리오 (변신 후 표시 — 일반 마리오 위치 추종)
# ════════════════════════════════════════════════════════════════════════
def build_white_mario(am, V, BR):
    w = BB()
    wf = w.flag()
    w.chain([wf, w.hide()])

    # 변신 broadcast → 마리오 위치로 + show. 이후 자체 메카닉으로 동작.
    wfh = w.bcast_hat("파이어변신", BR["파이어변신"])
    w.chain([wfh,
             w.set_x_block(w.sense_of_xpos("Mario")),
             w.set_y_block(w.sense_of_ypos("Mario")),
             w.show()])

    # 자체 메카닉: 일반 마리오와 동일. 파이어==1일 때만 forever 활성.
    mh3 = w.bcast_hat("스테이지3", BR["스테이지3"])
    w_init = [w.hide()]   # 게임 (재)시작 시 hide (변신 전)

    all_blocks = _build_mario_body(w, V, BR, "흰걷기1", "흰점프1", sprite_active_when_fire=1)
    w.chain(all_blocks)

    cs3 = w.eq_var("게임상태", V["게임상태"], "stage3")
    is_fire = w.eq_var("파이어", V["파이어"], 1)
    cand_active = w.op_and(cs3, is_fire)
    ifs3 = w.if_then(cand_active, all_blocks[0])
    fl = w.forever(ifs3)
    w.chain([mh3] + w_init + [fl])

    mario_invincibility(w, V, BR, duration=1.0)
    hide_on_end(w, ("게임오버", "승리"))

    return {
        "isStage": False, "name": "WhiteMario", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": w.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("흰걷기1", "white-mario/mario3_white_walk_1.png"),
                     am.reg_png("흰걷기3", "white-mario/mario3_white_walk_3.png"),
                     am.reg_png("흰걷기4", "white-mario/mario3_white_walk_4.png"),
                     am.reg_png("흰걷기5", "white-mario/mario3_white_walk_5.png"),
                     am.reg_png("흰걷기6", "white-mario/mario3_white_walk_6.png"),
                     am.reg_png("흰점프1", "white-mario/mario3_white_jump_5.png")],
        "sounds": [], "volume": 100, "layerOrder": 9, "visible": False,
        "x": MARIO_START_X, "y": MARIO_START_Y, "size": 45, "direction": 90, "draggable": False, "rotationStyle": "left-right"
    }


# ════════════════════════════════════════════════════════════════════════
# ?블록 (머리 충돌 → 파이어 꽃 등장)
# ════════════════════════════════════════════════════════════════════════
def make_brick(am, V, BR, name, x):
    """단일 brick block (32x32). 발판 역할만, 헤딩 발동 없음."""
    b = BB()
    bf = b.flag()
    b.chain([bf, b.hide()])
    bh = b.bcast_hat("스테이지3", BR["스테이지3"])
    b.chain([bh, b.goto(x, QBLOCK_Y), b.set_size(BLOCK_SIZE),
             b.costume("brick"), b.show()])
    hide_on_end(b, ("게임오버", "승리"))
    return {
        "isStage": False, "name": name,
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": b.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("brick", "background/block1_brick.png")],
        "sounds": [], "volume": 100, "layerOrder": 2, "visible": False,
        "x": x, "y": QBLOCK_Y, "size": BLOCK_SIZE, "direction": 90,
        "draggable": False, "rotationStyle": "don't rotate",
    }


def make_pipe(am, V, BR):
    """녹색 파이프 sprite. 발판 역할 (mario_platform_landing 처리)."""
    p = BB()
    pf = p.flag()
    p.chain([pf, p.hide()])
    ph = p.bcast_hat("스테이지3", BR["스테이지3"])
    p.chain([ph, p.goto(PIPE_X, PIPE_Y), p.set_size(PIPE_SIZE),
             p.costume("pipe"), p.show()])
    hide_on_end(p, ("게임오버", "승리"))
    return {
        "isStage": False, "name": "Pipe",
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": p.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("pipe", "background/pipe_clean.png")],
        "sounds": [], "volume": 100, "layerOrder": 2, "visible": False,
        "x": PIPE_X, "y": PIPE_Y, "size": PIPE_SIZE, "direction": 90,
        "draggable": False, "rotationStyle": "don't rotate",
    }


def make_qblock(am, V, BR):
    """가운데 ?블록 단일 sprite. 헤딩(머리 충돌) 시 잠긴 박스로 코스튬 전환."""
    q = BB()
    qf = q.flag()
    q.chain([qf, q.hide()])
    qh = q.bcast_hat("스테이지3", BR["스테이지3"])
    q.chain([qh, q.goto(QBLOCK_X, QBLOCK_Y), q.set_size(BLOCK_SIZE),
             q.costume("물음표"), q.show()])
    # 꽃등장 broadcast 수신 → 잠긴 박스 코스튬 + 크기/위치 조정
    qb = q.bcast_hat("꽃등장", BR["꽃등장"])
    q.chain([qb, q.costume("잠김"), q.set_size(76), q.goto(-115, -75)])
    hide_on_end(q, ("게임오버", "승리"))
    return {
        "isStage": False, "name": "QBlock",
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": q.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("물음표", "background/block1_q.png"),
                     am.reg_png("잠김", "background/block1_e.png")],
        "sounds": [], "volume": 100, "layerOrder": 2, "visible": False,
        "x": QBLOCK_X, "y": QBLOCK_Y, "size": BLOCK_SIZE, "direction": 90,
        "draggable": False, "rotationStyle": "don't rotate",
    }


# ════════════════════════════════════════════════════════════════════════
# 파이어 꽃 (꽃등장 broadcast 시 등장)
# ════════════════════════════════════════════════════════════════════════
def make_fire_flower(am, V, BR):
    fw = BB()
    fwf = fw.flag()
    fw.chain([fwf, fw.hide()])

    fh = fw.bcast_hat("스테이지3", BR["스테이지3"])
    fw.chain([fh, fw.hide()])

    feh = fw.bcast_hat("꽃등장", BR["꽃등장"])
    fw.chain([feh, fw.goto(FLOWER_X, FLOWER_Y), fw.set_size(3), fw.show()])

    # forever: 마리오 접촉 → 파이어변신
    # 마리오 측이 touching 감지 후 "파이어변신" broadcast 발송 → 꽃 hide
    fhv = fw.bcast_hat("파이어변신", BR["파이어변신"])
    fw.chain([fhv, fw.hide()])

    hide_on_end(fw, ("게임오버", "승리"))
    return {
        "isStage": False, "name": "FireFlower",
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": fw.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("flower", "items/fire_flower.png")],
        "sounds": [], "volume": 100, "layerOrder": 5, "visible": False,
        "x": FLOWER_X, "y": FLOWER_Y, "size": 3, "direction": 90,
        "draggable": False, "rotationStyle": "don't rotate",
    }


# ════════════════════════════════════════════════════════════════════════
# 파이어변신 → 파이어=1로 set하는 헬퍼 sprite (또는 stage에서 처리)
# 여기선 Mario sprite에서 hat 등록 (별도 sprite 불필요)
# 화이트 마리오 sprite에 변신 hat 추가하는 게 자연스럽지만 글로벌 변수라
# 한 곳(어떤 sprite든)에서 set하면 됨. Stage에서 처리.
# ════════════════════════════════════════════════════════════════════════


# ════════════════════════════════════════════════════════════════════════
# Bowser
# ════════════════════════════════════════════════════════════════════════
def make_bowser(am, V, BR, sounds):
    bw = BB()
    bwf = bw.flag(); bw.chain([bwf, bw.hide()])

    # 스테이지3 시작: 화면 오른쪽 밖(280,-136)에서 등장 → 걸어와서 (160,-136) 도착 → 덤벼라 멘트
    bwh3 = bw.bcast_hat("스테이지3", BR["스테이지3"])
    intro_chain = [
        bw.goto(280, -136),
        bw.set_size(85),
        bw.point_dir(90),                    # 재시작 시 방향 초기화 (마리오 쪽 향함)
        bw.set_var("쿠파HP", V["쿠파HP"], 10),
        bw.costume("걷기4"),
        bw.show(),
    ]
    # walk-in: 10 step × change_x(-12) = -120 → 280→160. 더 천천히 (각 step 0.25s).
    cycle = ["걷기4", "걷기5", "걷기6"]
    for i in range(10):
        intro_chain += [bw.change_x(-12), bw.costume(cycle[i % 3]), bw.wait(0.25)]
    intro_chain += [
        bw.goto(160, -136),
        bw.costume("쿠파"),
        bw.say_for("덤벼라 마리오!", 3.5),
    ]
    bw.chain([bwh3] + intro_chain)

    # 쿠파맞음 broadcast 받으면 으악
    bwh_hit = bw.bcast_hat("쿠파맞음", BR["쿠파맞음"])
    bw.chain([bwh_hit, bw.say_for("으악!", 0.4)])

    # 쿠파 패배 시퀀스: 일어선 자세에서 멘트 → 반대 방향으로 돌아 걸어 퇴장 → hide
    bwh_defeat = bw.bcast_hat("쿠파패배", BR["쿠파패배"])
    defeat_chain = [
        bw.costume("쿠파"),                 # 일어선 stand 자세
        bw.say_for("두고보자 마리오!", 2),
        bw.point_dir(-90),                  # 반대 방향 (left-right rotationStyle → 좌우 flip)
    ]
    # 걸어서 화면 밖으로: 10 step × change_x(+12) = +120 → 160→280
    cycle = ["걷기4", "걷기5", "걷기6"]
    for i in range(10):
        defeat_chain += [bw.change_x(12), bw.costume(cycle[i % 3]), bw.wait(0.2)]
    defeat_chain.append(bw.hide())
    bw.chain([bwh_defeat] + defeat_chain)

    hide_on_end(bw, ("게임오버", "승리"))

    return {
        "isStage": False, "name": "Bowser", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": bw.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("쿠파", "koopa/bowser_stand_1.png"),
                     am.reg_png("걷기4", "koopa/bowser_run_4.png"),
                     am.reg_png("걷기5", "koopa/bowser_run_5.png"),
                     am.reg_png("걷기6", "koopa/bowser_run_6.png"),
                     am.reg_png("패배",  "koopa/bowser_run_9.png")],
        "sounds": sounds, "volume": 100, "layerOrder": 6, "visible": False,
        "x": 280, "y": -136, "size": 85, "direction": 90, "draggable": False, "rotationStyle": "left-right"
    }


# ════════════════════════════════════════════════════════════════════════
# Peach
# ════════════════════════════════════════════════════════════════════════
def make_peach(am, V, BR):
    p = BB()
    pf = p.flag(); p.chain([pf, p.hide()])

    ph3 = p.bcast_hat("스테이지3", BR["스테이지3"])
    pi3 = [p.goto(180, GY), p.hide()]
    p.chain([ph3] + pi3)

    # 피치 등장 시퀀스: "쿠파패배" broadcast 받으면 쿠파 멘트(2초) + 도망(2초) 후
    # 오른쪽 화면 밖에서 등장 → 마리오 쪽으로 걸어오기 → 감사 멘트
    ph_defeat = p.bcast_hat("쿠파패배", BR["쿠파패배"])
    p.chain([ph_defeat,
             p.wait(4),
             p.goto(260, GY),
             p.point_dir(-90),
             p.show(),
             p.glide_xy(3, 60, GY),
             p.point_dir(90),
             p.say_for("구해줘서 고마워요 마리오!", 4)])

    hide_on_end(p, ("게임오버", "승리"))

    return {
        "isStage": False, "name": "Peach", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": p.blocks, "currentCostume": 0, "costumes": [am.reg_png("피치", "peach/peach_idle.png")],
        "sounds": [], "volume": 100, "layerOrder": 7, "visible": False,
        "x": 180, "y": GY, "size": 45, "direction": 90, "draggable": False, "rotationStyle": "don't rotate"
    }


# ════════════════════════════════════════════════════════════════════════
# Fireball (Z키 발사, 파이어==1일 때만)
# ════════════════════════════════════════════════════════════════════════
def make_fireball(am, V, BR, sounds):
    fb = BB(); fbf = fb.flag(); fb.chain([fbf, fb.hide()])

    # 파이어볼 발사: forever + 매 프레임 move + 충돌 체크
    fbc = fb.bcast_hat("발사", BR["발사"])
    cfire = fb.eq_var("파이어", V["파이어"], 1)

    # 발사 setup — 마리오 정중앙에서 출발. 시각은 PNG에 167°가 baked-in 되어 있고
    # direction은 point_towards로 쿠파 방향. 블록 위 발사 시 자연스럽게 대각선.
    setup = [fb.set_x_block(fb.sense_of_xpos("WhiteMario")),
             fb.set_y_block(fb.op_add_block_const(fb.sense_of_ypos("WhiteMario"), 8)),
             fb.set_size(5),
             fb.point_towards("Bowser"),
             fb.show(), fb.play_sound("Fire")]
    fb.chain(setup)

    # forever 안: direction(쿠파 향함) 방향으로 move → 평지면 수평, 블록 위면 자동 대각선.
    move_step = fb.move(10)
    d_b = fb.distance_to("Bowser")
    tt_b = fb.touching("Bowser")
    dist_cond = fb.lt_block_const(d_b, 50)
    hit_cond = fb.op_or(tt_b, dist_cond)
    # 쿠파HP -1 + 맞음 broadcast. 마지막 hit (HP<1) 시 "쿠파패배" broadcast로 엔딩 트리거.
    defeat_cond = fb.lt_var("쿠파HP", V["쿠파HP"], 1)
    defeat_br = fb.broadcast("쿠파패배", BR["쿠파패배"])
    if_defeat = fb.if_then(defeat_cond, defeat_br)
    hit_act = [fb.change_var("쿠파HP", V["쿠파HP"], -1),
               fb.broadcast("쿠파맞음", BR["쿠파맞음"]),
               if_defeat,
               fb.hide(),
               fb.stop_this()]
    fb.chain(hit_act)
    if_hit = fb.if_then(hit_cond, hit_act[0])

    edge_cond = fb.touching("_edge_")
    edge_act = [fb.hide(), fb.stop_this()]
    fb.chain(edge_act)
    if_edge = fb.if_then(edge_cond, edge_act[0])

    fb.chain([move_step, if_hit, if_edge])
    fl = fb.forever(move_step)

    # 전체 chain: 발사 hat → if_fire → setup → forever
    if_fire = fb.if_then(cfire, setup[0])
    fb.chain([fbc, if_fire])
    # setup의 마지막(play_sound) 다음에 forever 연결
    setup[-1] = setup[-1]  # noop. play_sound.next = fl
    # chain again to ensure setup → fl
    fb.chain([setup[-1], fl])

    hide_on_end(fb, ("게임오버", "승리"))

    return {
        "isStage": False, "name": "Fireball", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": fb.blocks, "currentCostume": 0, "costumes": [am.reg_png("fire", "items/fireball.png")],
        "sounds": sounds, "volume": 100, "layerOrder": 5, "visible": False,
        "x": 0, "y": 0, "size": 100, "direction": 90, "draggable": False, "rotationStyle": "don't rotate"
    }


# ════════════════════════════════════════════════════════════════════════
# 파이어변신 broadcast 핸들러 — Stage sprite에서 처리 (set 파이어=1)
# build_stage에서 hat 추가하는 게 깔끔. 또는 별도 sprite.
# Stage의 backdrop은 변경되니까 stage hat에. 다만 stage build 함수가 이미 정의됨.
# 마리오 sprite에 hat 추가.
# ════════════════════════════════════════════════════════════════════════
def add_fire_transform_hat(mario_sprite_blocks_bb, V, BR):
    """별도 함수로 두지 않고 build_mario 안에서 처리."""
    pass


# ════════════════════════════════════════════════════════════════════════
# BUILD + MAIN
# ════════════════════════════════════════════════════════════════════════
def build():
    am = AssetManager()
    BR = {k: uid() for k in ["스테이지3", "피격", "꽃등장", "파이어변신", "발사", "쿠파맞음", "쿠파패배"]}
    V = {k: uid() for k in ["하트", "속도Y", "점프중", "게임상태", "쿠파HP",
                            "무적", "걸음", "파이어", "꽃등장됨"]}

    snd_jump = am.reg_snd("Jump", gen_beep(600, 0.1))
    snd_hit = am.reg_snd("Hit", gen_beep(200, 0.2))
    snd_win = am.reg_snd("Win", gen_beep(900, 0.3))
    snd_fire = am.reg_snd("Fire", gen_beep(400, 0.1))

    stage_target = build_stage(am, V, BR)
    mario = build_mario(am, V, BR, [snd_jump, snd_hit, snd_win])

    brick_left  = make_brick(am, V, BR, "BrickLeft",  -138)
    qblock      = make_qblock(am, V, BR)
    brick_right = make_brick(am, V, BR, "BrickRight", -91)
    pipe        = make_pipe(am, V, BR)
    flower = make_fire_flower(am, V, BR)
    white_mario = build_white_mario(am, V, BR)
    bowser = make_bowser(am, V, BR, [snd_hit])
    peach = make_peach(am, V, BR)
    fireball = make_fireball(am, V, BR, [snd_fire])
    hearts = make_hearts(am, V, BR=BR, restart_br_key="스테이지3")

    # 쿠파 체력 sprite (검은 하트). 코스튬 인덱스 0..10 = HP 10..0 (역순).
    # 메커니즘: "쿠파맞음" broadcast 받으면 next_costume — 가장 단순/확실.
    bh = BB()
    bhf = bh.flag()
    bh.chain([bhf, bh.goto(180, 150), bh.set_size(100),
              bh.costume("hp10"), bh.show()])
    # 게임 (재)시작 broadcast 시 다시 show + 코스튬 리셋
    bhrh = bh.bcast_hat("스테이지3", BR["스테이지3"])
    bh.chain([bhrh, bh.goto(180, 150), bh.set_size(100),
              bh.costume("hp10"), bh.show()])
    # 쿠파 맞을 때마다 다음 코스튬으로 (HP 10→9→8→...→0)
    bhhit = bh.bcast_hat("쿠파맞음", BR["쿠파맞음"])
    bh.chain([bhhit, bh.next_costume()])
    hide_on_end(bh, ("게임오버", "승리"))
    # 코스튬 순서: hp10 (모두 검정) → hp9 → ... → hp0 (모두 회색)
    bowser_hearts = {
        "isStage": False, "name": "BowserHearts",
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": bh.blocks, "currentCostume": 0,
        "costumes": [am.reg(f"hp{10-n}", svg_dark_hearts(10-n), 57, 22) for n in range(11)],
        "sounds": [], "volume": 100, "layerOrder": 11, "visible": True,
        "x": 180, "y": 150, "size": 100, "direction": 90,
        "draggable": False, "rotationStyle": "don't rotate"
    }

    project = {
        "targets": [stage_target, brick_left, qblock, brick_right, pipe, flower,
                    bowser, peach, fireball, mario, white_mario, hearts,
                    bowser_hearts],
        "monitors": [],
        "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "Mario Stage 3"}
    }
    return project, am.assets


def main():
    print("Generating Stage 3 - 쿠파를 물리쳐라!...")
    proj, assets = build()
    save_sb3("Stage3.sb3", proj, assets)
    print("Controls: ← → move | SPACE jump | 마우스 클릭 fireball")
    print("Goal: Break ? block → eat fire flower → hit Bowser 3 times!")


if __name__ == "__main__":
    main()

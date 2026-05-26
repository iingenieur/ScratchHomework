"""
스테이지 2 단독 테스트 - 거북이를 피해라!
20초 동안 오른쪽에서 돌진하는 거북이 등껍질을 점프로 피하기
"""

from common import *
from mechanics import mario_physics, mario_movement, mario_jump, mario_enemy_hit, mario_gameover, mario_invincibility, hide_on_end


def bg_start_s2():
    return svg(480, 360,
        '<rect width="480" height="360" fill="#1a237e"/>'
        '<circle cx="400" cy="60" r="30" fill="#FFD700" opacity="0.3"/>'
        '<text x="240" y="130" text-anchor="middle" font-size="36" font-weight="bold" fill="#FFD700">STAGE 2</text>'
        '<text x="240" y="175" text-anchor="middle" font-size="18" fill="#DDD">거북이를 피해라!</text>'
        '<text x="240" y="240" text-anchor="middle" font-size="16" fill="#AAA">SPACE 키를 눌러 시작</text>')


# ════════════════════════════════════════════════════════════════════════
# Stage 스프라이트
# ════════════════════════════════════════════════════════════════════════
def build_stage(am, V, BR):
    b = BB()
    f0 = b.flag()
    init = [b.backdrop("시작화면"), b.set_var("게임상태", V["게임상태"], "start"),
            b.set_var("하트", V["하트"], 5), b.set_var("속도Y", V["속도Y"], 0),
            b.set_var("점프중", V["점프중"], 0), b.set_var("무적", V["무적"], 0),
            b.stop_sounds()]
    b.chain([f0] + init)

    sp = b.key_hat("space")
    c1 = b.eq_var("게임상태", V["게임상태"], "start")
    s1 = [b.set_var("게임상태", V["게임상태"], "stage2"), b.backdrop("스테이지2"),
          b.broadcast("스테이지2", BR["스테이지2"])]
    b.chain(s1); if1 = b.if_then(c1, s1[0])

    c2 = b.eq_var("게임상태", V["게임상태"], "gameover")
    s2 = [b.set_var("하트", V["하트"], 5), b.set_var("속도Y", V["속도Y"], 0),
          b.set_var("점프중", V["점프중"], 0), b.set_var("무적", V["무적"], 0),
          b.set_var("게임상태", V["게임상태"], "stage2"), b.backdrop("스테이지2"),
          b.broadcast("스테이지2", BR["스테이지2"])]
    b.chain(s2); if2 = b.if_then(c2, s2[0])

    c3 = b.eq_var("게임상태", V["게임상태"], "clear")
    s3 = [b.set_var("하트", V["하트"], 5), b.set_var("속도Y", V["속도Y"], 0),
          b.set_var("점프중", V["점프중"], 0), b.set_var("무적", V["무적"], 0),
          b.set_var("게임상태", V["게임상태"], "stage2"), b.backdrop("스테이지2"),
          b.broadcast("스테이지2", BR["스테이지2"])]
    b.chain(s3); if3 = b.if_then(c3, s3[0])
    b.chain([sp, if1, if2, if3])

    # 20초 타이머
    s2_timer = BB()
    s2h = s2_timer.bcast_hat("스테이지2", BR["스테이지2"])
    s2t = [s2_timer.wait(20), s2_timer.set_var("게임상태", V["게임상태"], "clear"),
           s2_timer.backdrop("클리어")]
    s2_timer.chain([s2h] + s2t)

    gvars = {V[k]: [k, v] for k, v in [("하트", 5), ("속도Y", 0), ("점프중", 0), ("게임상태", "start"), ("무적", 0), ("걸음", 1)]}
    blocks = {**b.blocks, **s2_timer.blocks}

    return {
        "isStage": True, "name": "Stage", "variables": gvars, "lists": {}, "comments": {},
        "broadcasts": {v: k for k, v in BR.items()},
        "blocks": blocks, "currentCostume": 0,
        "costumes": [am.reg_png_backdrop("시작화면", "background/bg_stage.png"),
                     am.reg_png_backdrop("스테이지2", "background/bg_stage.png"),
                     am.reg("게임오버", bg_gameover(), 240, 180),
                     am.reg("클리어", bg_victory(), 240, 180)],
        "sounds": [], "volume": 100, "layerOrder": 0, "tempo": 60,
        "videoTransparency": 50, "videoState": "off", "textToSpeechLanguage": None
    }


# ════════════════════════════════════════════════════════════════════════
# Mario 스프라이트
# ════════════════════════════════════════════════════════════════════════
def build_mario(am, V, BR, sounds):
    m = BB()
    mf = m.flag()
    m.chain([mf, m.goto(-150, GY + 7), m.set_size(45), m.costume("걷기1"), m.show()])

    mh2 = m.bcast_hat("스테이지2", BR["스테이지2"])
    m2_init = [m.goto(-150, GY + 7), m.set_var("속도Y", V["속도Y"], 0), m.set_var("점프중", V["점프중"], 0), m.set_var("무적", V["무적"], 0), m.set_var("걸음", V["걸음"], 1)]

    # 기능별 독립 함수 호출 (Stage 1과 동일한 기본 동작)
    physics_blocks = mario_physics(m, V, ground_y=GY+7, landing_costume="걷기1")
    move_blocks    = mario_movement(m, V=V, speed=5, with_direction=True, walk_mode="next")
    jump_block     = mario_jump(m, V, velocity=14, jump_costume="점프1")
    enemy_blocks   = [mario_enemy_hit(m, V, tn,
                                      reset_y=GY + 30, velocity_after=8,
                                      BR=BR, wait_time=0.8)
                      for tn in ["Turtle1", "Turtle2", "Turtle3"]]
    gameover_block = mario_gameover(m, V)

    # forever 루프 조립
    all_blocks = physics_blocks + move_blocks + [jump_block] + enemy_blocks + [gameover_block]
    m.chain(all_blocks)
    cs2 = m.eq_var("게임상태", V["게임상태"], "stage2")
    ifs2 = m.if_then(cs2, all_blocks[0])
    fs2 = m.forever(ifs2)
    m.chain([mh2] + m2_init + [fs2])

    # 무적 처리 (별도 스크립트)
    mario_invincibility(m, V, BR, duration=1.0)

    # 종료 백드롭 전환 시 hide
    hide_on_end(m)

    return {
        "isStage": False, "name": "Mario", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": m.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("걷기1", "mario/mario3_walk_1.png"), am.reg_png("걷기3", "mario/mario3_walk_3.png"),
                     am.reg_png("걷기4", "mario/mario3_walk_4.png"), am.reg_png("걷기5", "mario/mario3_walk_5.png"),
                     am.reg_png("걷기6", "mario/mario3_walk_6.png"), am.reg_png("점프1", "mario/mario3_jump_5.png")],
        "sounds": sounds, "volume": 100, "layerOrder": 8, "visible": True,
        "x": -150, "y": GY, "size": 45, "direction": 90, "draggable": False, "rotationStyle": "left-right"
    }


# ════════════════════════════════════════════════════════════════════════
# Shell Turtle 스프라이트
# ════════════════════════════════════════════════════════════════════════
def make_shell(am, name, speed, start_delay, BR, size=55):
    t = BB(); tf = t.flag(); t.chain([tf, t.hide()])
    th = t.bcast_hat("스테이지2", BR["스테이지2"])
    ti = [t.goto(260, GY + 5), t.set_size(size), t.show(), t.wait(start_delay)]
    tgl = t.glide(speed, -260, GY + 5); treset = t.goto(260, GY + 5); tw = t.wait(0.3)
    t.chain([tgl, treset, tw]); tfl = t.forever(tgl)
    t.chain([th] + ti + [tfl])
    hide_on_end(t)
    return {
        "isStage": False, "name": name, "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": t.blocks, "currentCostume": 0, "costumes": [am.reg_png("koopa", "koopa/bowser_walk_1.png")],
        "sounds": [], "volume": 100, "layerOrder": 4, "visible": False,
        "x": 260, "y": GY + 5, "size": size, "direction": 90, "draggable": False, "rotationStyle": "don't rotate"
    }


# ════════════════════════════════════════════════════════════════════════
# BUILD + MAIN
# ════════════════════════════════════════════════════════════════════════
def build():
    am = AssetManager()
    BR = {k: uid() for k in ["스테이지2", "클리어", "피격"]}
    V = {k: uid() for k in ["하트", "속도Y", "점프중", "게임상태", "무적", "걸음"]}

    snd_jump = am.reg_snd("Jump", gen_beep(600, 0.1))
    snd_hit = am.reg_snd("Hit", gen_beep(200, 0.2))
    snd_win = am.reg_snd("Win", gen_beep(900, 0.3))

    stage_target = build_stage(am, V, BR)
    mario = build_mario(am, V, BR, [snd_jump, snd_hit])
    turtle1 = make_shell(am, "Turtle1", 1.8, 0, BR, size=45)
    turtle2 = make_shell(am, "Turtle2", 1.5, 2.5, BR, size=45)
    turtle3 = make_shell(am, "Turtle3", 1.2, 5, BR)
    hearts = make_hearts(am, V)

    project = {
        "targets": [stage_target, mario, turtle1, turtle2, turtle3, hearts],
        "monitors": [], "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "Mario Stage 2"}
    }
    return project, am.assets


def main():
    print("Generating Stage 2 - 거북이를 피해라!...")
    proj, assets = build()
    save_sb3("Stage2.sb3", proj, assets)
    print("Controls: ← → move | SPACE jump")
    print("Goal: Survive 20 seconds!")

if __name__ == "__main__": main()

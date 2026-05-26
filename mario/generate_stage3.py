"""
스테이지 3 단독 테스트 - 쿠파를 물리쳐라!
파이어 마리오로 변신, Z키로 파이어볼을 던져 쿠파를 3번 맞히면 승리
피치 공주 구출
"""

from common import *
from mechanics import mario_physics, mario_movement, mario_jump, mario_enemy_hit, mario_gameover, mario_invincibility, hide_on_end


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
            b.set_var("쿠파HP", V["쿠파HP"], 3), b.stop_sounds()]
    b.chain([f0] + init)

    sp = b.key_hat("space")
    c1 = b.eq_var("게임상태", V["게임상태"], "start")
    s1 = [b.set_var("게임상태", V["게임상태"], "stage3"), b.backdrop("스테이지3"),
          b.broadcast("스테이지3", BR["스테이지3"])]
    b.chain(s1); if1 = b.if_then(c1, s1[0])

    c2 = b.eq_var("게임상태", V["게임상태"], "gameover")
    s2 = [b.set_var("하트", V["하트"], 5), b.set_var("쿠파HP", V["쿠파HP"], 3),
          b.set_var("속도Y", V["속도Y"], 0), b.set_var("점프중", V["점프중"], 0),
          b.set_var("무적", V["무적"], 0),
          b.set_var("게임상태", V["게임상태"], "stage3"), b.backdrop("스테이지3"),
          b.broadcast("스테이지3", BR["스테이지3"])]
    b.chain(s2); if2 = b.if_then(c2, s2[0])

    c3 = b.eq_var("게임상태", V["게임상태"], "win")
    s3 = [b.set_var("하트", V["하트"], 5), b.set_var("쿠파HP", V["쿠파HP"], 3),
          b.set_var("속도Y", V["속도Y"], 0), b.set_var("점프중", V["점프중"], 0),
          b.set_var("무적", V["무적"], 0),
          b.set_var("게임상태", V["게임상태"], "stage3"), b.backdrop("스테이지3"),
          b.broadcast("스테이지3", BR["스테이지3"])]
    b.chain(s3); if3 = b.if_then(c3, s3[0])
    b.chain([sp, if1, if2, if3])

    gvars = {V[k]: [k, v] for k, v in [("하트", 5), ("속도Y", 0), ("점프중", 0), ("게임상태", "start"), ("쿠파HP", 3), ("무적", 0), ("걸음", 1)]}

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
# Mario 스프라이트
# ════════════════════════════════════════════════════════════════════════
def build_mario(am, V, BR, sounds):
    m = BB()
    mf = m.flag()
    m.chain([mf, m.goto(-150, GY + 7), m.set_size(45), m.costume("걷기1"), m.show()])

    mh3 = m.bcast_hat("스테이지3", BR["스테이지3"])
    m3_init = [m.goto(-150, GY + 7), m.costume("걷기1"),
               m.set_var("속도Y", V["속도Y"], 0), m.set_var("점프중", V["점프중"], 0),
               m.set_var("무적", V["무적"], 0), m.set_var("걸음", V["걸음"], 1)]

    # 기능별 독립 함수 호출 (Stage 1과 동일한 기본 동작)
    physics_blocks = mario_physics(m, V, ground_y=GY+7, landing_costume="걷기1")
    move_blocks    = mario_movement(m, V=V, speed=5, with_direction=True, walk_mode="next")
    jump_block     = mario_jump(m, V, velocity=14, jump_costume="점프1")
    enemy_block    = mario_enemy_hit(m, V, "Bowser", reset_x=-150, reset_y=GY, BR=BR)
    gameover_block = mario_gameover(m, V)

    # 승리 판정 (Stage 3 전용: 쿠파HP < 1)
    cwin = m.lt_var("쿠파HP", V["쿠파HP"], 1)
    win3 = [m.say_for("피치 공주를 구했다!", 2), m.set_var("게임상태", V["게임상태"], "win"),
            m.backdrop("승리"), m.hide()]
    m.chain(win3)
    ifw3 = m.if_then(cwin, win3[0])

    # forever 루프 조립
    all_blocks = physics_blocks + move_blocks + [jump_block, enemy_block, gameover_block, ifw3]
    m.chain(all_blocks)
    cs3 = m.eq_var("게임상태", V["게임상태"], "stage3")
    ifs3 = m.if_then(cs3, all_blocks[0])
    fs3 = m.forever(ifs3)
    m.chain([mh3] + m3_init + [fs3])

    # 무적 처리 (별도 스크립트)
    mario_invincibility(m, V, BR, duration=1.0)

    # 종료 백드롭 전환 시 hide
    hide_on_end(m, ("게임오버", "승리"))

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
# Bowser 스프라이트
# ════════════════════════════════════════════════════════════════════════
def make_bowser(am, V, BR, sounds):
    bw = BB()
    bwf = bw.flag(); bw.chain([bwf, bw.hide()])

    bwh3 = bw.bcast_hat("스테이지3", BR["스테이지3"])
    bwi3 = [bw.goto(120, GY), bw.show(), bw.set_var("쿠파HP", V["쿠파HP"], 3)]
    bwgl = bw.glide(1.5, 60, GY); bwgr = bw.glide(1.5, 180, GY)
    bw.chain([bwgl, bwgr]); bwf3 = bw.forever(bwgl)
    bw.chain([bwh3] + bwi3 + [bwf3])

    # 패배 체크
    bwh4 = bw.flag()
    cd = bw.lt_var("쿠파HP", V["쿠파HP"], 1)
    bwd = [bw.say_for("으아아악!!", 1), bw.hide()]
    bw.chain(bwd); ifbd = bw.if_then(cd, bwd[0])
    bww = bw.wait(0.3); bw.chain([ifbd, bww])
    cs3b = bw.eq_var("게임상태", V["게임상태"], "stage3")
    ifs3b = bw.if_then(cs3b, ifbd); fbw = bw.forever(ifs3b)
    bw.chain([bwh4, fbw])

    hide_on_end(bw, ("게임오버", "승리"))

    return {
        "isStage": False, "name": "Bowser", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": bw.blocks, "currentCostume": 0, "costumes": [am.reg_png("쿠파", "koopa/bowser_stand_1.png")],
        "sounds": sounds, "volume": 100, "layerOrder": 6, "visible": False,
        "x": 200, "y": 200, "size": 70, "direction": 90, "draggable": False, "rotationStyle": "don't rotate"
    }


# ════════════════════════════════════════════════════════════════════════
# Peach 스프라이트
# ════════════════════════════════════════════════════════════════════════
def make_peach(am, V, BR):
    p = BB()
    pf = p.flag(); p.chain([pf, p.hide()])

    ph3 = p.bcast_hat("스테이지3", BR["스테이지3"])
    pi3 = [p.goto(180, GY), p.hide()]
    p.chain([ph3] + pi3)

    ph3b = p.flag()
    cw3 = p.lt_var("쿠파HP", V["쿠파HP"], 1)
    pw3 = [p.show(), p.say("고마워요 마리오!")]
    p.chain(pw3); ifw = p.if_then(cw3, pw3[0])
    pw = p.wait(0.5); p.chain([ifw, pw])
    cs3p = p.eq_var("게임상태", V["게임상태"], "stage3")
    ifs3p = p.if_then(cs3p, ifw); fps = p.forever(ifs3p)
    p.chain([ph3b, fps])

    hide_on_end(p, ("게임오버", "승리"))

    return {
        "isStage": False, "name": "Peach", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": p.blocks, "currentCostume": 0, "costumes": [am.reg_png("피치", "peach/peach_idle.png")],
        "sounds": [], "volume": 100, "layerOrder": 7, "visible": False,
        "x": 180, "y": GY, "size": 45, "direction": 90, "draggable": False, "rotationStyle": "don't rotate"
    }


# ════════════════════════════════════════════════════════════════════════
# Fireball 스프라이트
# ════════════════════════════════════════════════════════════════════════
def make_fireball(am, V, BR, sounds):
    fb = BB(); fbf = fb.flag(); fb.chain([fbf, fb.hide()])

    fbz = fb.key_hat("z")
    cs3f = fb.eq_var("게임상태", V["게임상태"], "stage3")
    fire = [fb.goto(-130, GY + 10), fb.show(), fb.play_sound("Fire"),
            fb.glide(0.5, 200, GY + 10)]
    tbw = fb.touching("Bowser")
    fhit = [fb.change_var("쿠파HP", V["쿠파HP"], -1), fb.play_sound("Hit")]
    fb.chain(fhit); ifhit = fb.if_then(tbw, fhit[0])
    fb.chain(fire + [ifhit, fb.hide()])
    iffs = fb.if_then(cs3f, fire[0])
    fb.chain([fbz, iffs])

    hide_on_end(fb, ("게임오버", "승리"))

    return {
        "isStage": False, "name": "Fireball", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": fb.blocks, "currentCostume": 0, "costumes": [am.reg("fire", svg_fireball(), 8, 8)],
        "sounds": sounds, "volume": 100, "layerOrder": 5, "visible": False,
        "x": 0, "y": 0, "size": 100, "direction": 90, "draggable": False, "rotationStyle": "don't rotate"
    }


# ════════════════════════════════════════════════════════════════════════
# BUILD + MAIN
# ════════════════════════════════════════════════════════════════════════
def build():
    am = AssetManager()
    BR = {k: uid() for k in ["스테이지3", "피격"]}
    V = {k: uid() for k in ["하트", "속도Y", "점프중", "게임상태", "쿠파HP", "무적", "걸음"]}

    snd_jump = am.reg_snd("Jump", gen_beep(600, 0.1))
    snd_hit = am.reg_snd("Hit", gen_beep(200, 0.2))
    snd_win = am.reg_snd("Win", gen_beep(900, 0.3))
    snd_fire = am.reg_snd("Fire", gen_beep(400, 0.1))

    stage_target = build_stage(am, V, BR)
    mario = build_mario(am, V, BR, [snd_jump, snd_hit, snd_win])
    bowser = make_bowser(am, V, BR, [snd_hit])
    peach = make_peach(am, V, BR)
    fireball = make_fireball(am, V, BR, [snd_fire])
    hearts = make_hearts(am, V)

    project = {
        "targets": [stage_target, mario, bowser, peach, fireball, hearts],
        "monitors": [], "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "Mario Stage 3"}
    }
    return project, am.assets


def main():
    print("Generating Stage 3 - 쿠파를 물리쳐라!...")
    proj, assets = build()
    save_sb3("Stage3.sb3", proj, assets)
    print("Controls: ← → move | SPACE jump | Z fireball")
    print("Goal: Hit Bowser 3 times with fireballs!")

if __name__ == "__main__": main()

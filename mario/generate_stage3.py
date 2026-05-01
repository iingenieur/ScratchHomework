"""
스테이지 3 단독 테스트 - 쿠파를 물리쳐라!
파이어 마리오로 변신, Z키로 파이어볼을 던져 쿠파를 3번 맞히면 승리
피치 공주 구출
"""

from common import *


def bg_start_s3():
    return svg(480, 360,
        '<rect width="480" height="360" fill="#B71C1C"/>'
        '<rect x="0" y="0" width="480" height="40" fill="#222"/>'
        '<text x="240" y="130" text-anchor="middle" font-size="36" font-weight="bold" fill="#FFD700">STAGE 3</text>'
        '<text x="240" y="175" text-anchor="middle" font-size="18" fill="#FFF">쿠파를 물리쳐라!</text>'
        '<text x="240" y="240" text-anchor="middle" font-size="16" fill="#DDD">SPACE 키를 눌러 시작</text>')


def build():
    am = AssetManager()
    BR = {k: uid() for k in ["스테이지3"]}
    V = {k: uid() for k in ["하트", "속도Y", "점프중", "게임상태", "쿠파HP"]}
    gvars = {V[k]: [k, v] for k, v in [("하트", 5), ("속도Y", 0), ("점프중", 0), ("게임상태", "start"), ("쿠파HP", 3)]}

    snd_jump = am.reg_snd("Jump", gen_beep(600, 0.1))
    snd_hit = am.reg_snd("Hit", gen_beep(200, 0.2))
    snd_win = am.reg_snd("Win", gen_beep(900, 0.3))
    snd_fire = am.reg_snd("Fire", gen_beep(400, 0.1))

    # ==================== STAGE ====================
    b = BB()
    f0 = b.flag()
    init = [b.backdrop("시작화면"), b.set_var("게임상태", V["게임상태"], "start"),
            b.set_var("하트", V["하트"], 5), b.set_var("속도Y", V["속도Y"], 0),
            b.set_var("점프중", V["점프중"], 0), b.set_var("쿠파HP", V["쿠파HP"], 3),
            b.stop_sounds()]
    b.chain([f0] + init)

    # SPACE to start
    sp = b.key_hat("space")
    c1 = b.eq_var("게임상태", V["게임상태"], "start")
    s1 = [b.set_var("게임상태", V["게임상태"], "stage3"), b.backdrop("스테이지3"),
          b.broadcast("스테이지3", BR["스테이지3"])]
    b.chain(s1); if1 = b.if_then(c1, s1[0])
    # Restart from gameover
    c2 = b.eq_var("게임상태", V["게임상태"], "gameover")
    s2 = [b.set_var("하트", V["하트"], 5), b.set_var("쿠파HP", V["쿠파HP"], 3),
          b.set_var("속도Y", V["속도Y"], 0), b.set_var("점프중", V["점프중"], 0),
          b.set_var("게임상태", V["게임상태"], "stage3"), b.backdrop("스테이지3"),
          b.broadcast("스테이지3", BR["스테이지3"])]
    b.chain(s2); if2 = b.if_then(c2, s2[0])
    # Restart from win
    c3 = b.eq_var("게임상태", V["게임상태"], "win")
    s3 = [b.set_var("하트", V["하트"], 5), b.set_var("쿠파HP", V["쿠파HP"], 3),
          b.set_var("속도Y", V["속도Y"], 0), b.set_var("점프중", V["점프중"], 0),
          b.set_var("게임상태", V["게임상태"], "stage3"), b.backdrop("스테이지3"),
          b.broadcast("스테이지3", BR["스테이지3"])]
    b.chain(s3); if3 = b.if_then(c3, s3[0])
    b.chain([sp, if1, if2, if3])

    stage_target = {
        "isStage": True, "name": "Stage", "variables": gvars, "lists": {}, "comments": {},
        "broadcasts": {v: k for k, v in BR.items()},
        "blocks": b.blocks, "currentCostume": 0,
        "costumes": [am.reg_png_backdrop("시작화면", "bg_stage.png"),
                     am.reg_png_backdrop("스테이지3", "bg_stage.png"),
                     am.reg("게임오버", bg_gameover(), 240, 180),
                     am.reg("승리", bg_victory(), 240, 180)],
        "sounds": [], "volume": 100, "layerOrder": 0, "tempo": 60,
        "videoTransparency": 50, "videoState": "off", "textToSpeechLanguage": None
    }

    # ==================== MARIO ====================
    m = BB()
    mf = m.flag(); m.chain([mf, m.goto(-150, GY), m.set_size(100), m.costume("걷기1"), m.show()])

    mh3 = m.bcast_hat("스테이지3", BR["스테이지3"])
    m3_init = [m.goto(-150, GY), m.costume("걷기1"),
               m.set_var("속도Y", V["속도Y"], 0), m.set_var("점프중", V["점프중"], 0)]

    # Physics
    grav3 = m.change_var("속도Y", V["속도Y"], -1)
    av3 = m.change_y_var("속도Y", V["속도Y"])
    cg3 = m.lt_ypos(GY)
    gs3 = [m.set_y(GY), m.set_var("속도Y", V["속도Y"], 0), m.set_var("점프중", V["점프중"], 0)]
    m.chain(gs3); ifg3 = m.if_then(cg3, gs3[0])
    # Movement
    kr3 = m.key_pressed("right arrow"); mvr3 = m.change_x(4); ifr3 = m.if_then(kr3, mvr3)
    kl3 = m.key_pressed("left arrow"); mvl3 = m.change_x(-4); ifl3 = m.if_then(kl3, mvl3)
    # Jump
    kj3 = m.key_pressed("space"); cnj3 = m.eq_var("점프중", V["점프중"], 0); cj3 = m.op_and(kj3, cnj3)
    jb3 = [m.set_var("속도Y", V["속도Y"], 13), m.set_var("점프중", V["점프중"], 1), m.play_sound("Jump")]
    m.chain(jb3); ifj3 = m.if_then(cj3, jb3[0])
    # Bowser touch
    tb3 = m.touching("Bowser")
    bh3 = [m.change_var("하트", V["하트"], -1), m.play_sound("Hit"), m.goto(-150, GY), m.wait(0.5)]
    m.chain(bh3); ifb3 = m.if_then(tb3, bh3[0])
    # Heart check
    ch3 = m.lt_var("하트", V["하트"], 1)
    die3 = [m.set_var("게임상태", V["게임상태"], "gameover"), m.backdrop("게임오버"), m.stop_all()]
    m.chain(die3); ifd3 = m.if_then(ch3, die3[0])
    # Win check
    cwin = m.lt_var("쿠파HP", V["쿠파HP"], 1)
    win3 = [m.say_for("피치 공주를 구했다!", 2), m.set_var("게임상태", V["게임상태"], "win"),
            m.backdrop("승리"), m.stop_all()]
    m.chain(win3); ifw3 = m.if_then(cwin, win3[0])

    m.chain([grav3, av3, ifg3, ifr3, ifl3, ifj3, ifb3, ifd3, ifw3])
    cs3 = m.eq_var("게임상태", V["게임상태"], "stage3")
    ifs3 = m.if_then(cs3, grav3); fs3 = m.forever(ifs3)
    m.chain([mh3] + m3_init + [fs3])

    mario = {"isStage": False, "name": "Mario", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": m.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("걷기1", "mario/mario3_walk_1.png"), am.reg_png("걷기3", "mario/mario3_walk_3.png"),
                     am.reg_png("걷기4", "mario/mario3_walk_4.png"), am.reg_png("걷기5", "mario/mario3_walk_5.png"),
                     am.reg_png("걷기6", "mario/mario3_walk_6.png"), am.reg_png("점프1", "mario/mario3_jump_5.png")],
        "sounds": [snd_jump, snd_hit, snd_win], "volume": 100, "layerOrder": 8, "visible": True,
        "x": -150, "y": GY, "size": 100, "direction": 90, "draggable": False, "rotationStyle": "left-right"}

    # ==================== BOWSER ====================
    bw = BB()
    bwf = bw.flag(); bw.chain([bwf, bw.hide()])

    bwh3 = bw.bcast_hat("스테이지3", BR["스테이지3"])
    bwi3 = [bw.goto(120, GY), bw.show(), bw.set_var("쿠파HP", V["쿠파HP"], 3)]
    bwgl = bw.glide(1.5, 60, GY); bwgr = bw.glide(1.5, 180, GY)
    bw.chain([bwgl, bwgr]); bwf3 = bw.forever(bwgl)
    bw.chain([bwh3] + bwi3 + [bwf3])

    # Defeat check
    bwh4 = bw.flag()
    cd = bw.lt_var("쿠파HP", V["쿠파HP"], 1)
    bwd = [bw.say_for("으아아악!!", 1), bw.hide()]
    bw.chain(bwd); ifbd = bw.if_then(cd, bwd[0])
    bww = bw.wait(0.3); bw.chain([ifbd, bww])
    cs3b = bw.eq_var("게임상태", V["게임상태"], "stage3")
    ifs3b = bw.if_then(cs3b, ifbd); fbw = bw.forever(ifs3b)
    bw.chain([bwh4, fbw])

    bowser = {"isStage": False, "name": "Bowser", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": bw.blocks, "currentCostume": 0, "costumes": [am.reg_png("쿠파", "bowser/bowser_stand_1.png")],
        "sounds": [snd_hit], "volume": 100, "layerOrder": 6, "visible": False,
        "x": 200, "y": 200, "size": 100, "direction": 90, "draggable": False, "rotationStyle": "don't rotate"}

    # ==================== PEACH ====================
    p = BB()
    pf = p.flag(); p.chain([pf, p.hide()])

    ph3 = p.bcast_hat("스테이지3", BR["스테이지3"])
    pi3 = [p.goto(180, GY), p.hide()]
    p.chain([ph3] + pi3)

    # Show when Bowser HP reaches 0
    ph3b = p.flag()
    cw3 = p.lt_var("쿠파HP", V["쿠파HP"], 1)
    pw3 = [p.show(), p.say("고마워요 마리오!")]
    p.chain(pw3); ifw = p.if_then(cw3, pw3[0])
    pw = p.wait(0.5); p.chain([ifw, pw])
    cs3p = p.eq_var("게임상태", V["게임상태"], "stage3")
    ifs3p = p.if_then(cs3p, ifw); fps = p.forever(ifs3p)
    p.chain([ph3b, fps])

    peach = {"isStage": False, "name": "Peach", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": p.blocks, "currentCostume": 0, "costumes": [am.reg_png("피치", "peach/peach_idle.png")],
        "sounds": [], "volume": 100, "layerOrder": 7, "visible": False,
        "x": 180, "y": GY, "size": 90, "direction": 90, "draggable": False, "rotationStyle": "don't rotate"}

    # ==================== FIREBALL ====================
    fb = BB(); fbf = fb.flag(); fb.chain([fbf, fb.hide()])

    fbz = fb.key_hat("z")
    cs3f = fb.eq_var("게임상태", V["게임상태"], "stage3")
    fire = [fb.goto(-130, GY + 10), fb.show(), fb.play_sound("Fire"),
            fb.glide(0.5, 200, GY + 10)]
    # Hit Bowser check
    tbw = fb.touching("Bowser")
    fhit = [fb.change_var("쿠파HP", V["쿠파HP"], -1), fb.play_sound("Hit")]
    fb.chain(fhit); ifhit = fb.if_then(tbw, fhit[0])
    fb.chain(fire + [ifhit, fb.hide()])
    iffs = fb.if_then(cs3f, fire[0])
    fb.chain([fbz, iffs])

    fireball = {"isStage": False, "name": "Fireball", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": fb.blocks, "currentCostume": 0, "costumes": [am.reg("fire", svg_fireball(), 8, 8)],
        "sounds": [snd_fire], "volume": 100, "layerOrder": 5, "visible": False,
        "x": 0, "y": 0, "size": 100, "direction": 90, "draggable": False, "rotationStyle": "don't rotate"}

    # ==================== HEARTS ====================
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

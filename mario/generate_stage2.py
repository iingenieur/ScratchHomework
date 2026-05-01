"""
스테이지 2 단독 테스트 - 거북이를 피해라!
20초 동안 오른쪽에서 돌진하는 거북이 등껍질을 점프로 피하기
"""

from common import *


def bg_start_s2():
    return svg(480, 360,
        '<rect width="480" height="360" fill="#1a237e"/>'
        '<circle cx="400" cy="60" r="30" fill="#FFD700" opacity="0.3"/>'
        '<text x="240" y="130" text-anchor="middle" font-size="36" font-weight="bold" fill="#FFD700">STAGE 2</text>'
        '<text x="240" y="175" text-anchor="middle" font-size="18" fill="#DDD">거북이를 피해라!</text>'
        '<text x="240" y="240" text-anchor="middle" font-size="16" fill="#AAA">SPACE 키를 눌러 시작</text>')


def build():
    am = AssetManager()
    BR = {k: uid() for k in ["스테이지2", "클리어"]}
    V = {k: uid() for k in ["하트", "속도Y", "점프중", "게임상태"]}
    gvars = {V[k]: [k, v] for k, v in [("하트", 5), ("속도Y", 0), ("점프중", 0), ("게임상태", "start")]}

    snd_jump = am.reg_snd("Jump", gen_beep(600, 0.1))
    snd_hit = am.reg_snd("Hit", gen_beep(200, 0.2))
    snd_win = am.reg_snd("Win", gen_beep(900, 0.3))

    # ==================== STAGE ====================
    b = BB()
    f0 = b.flag()
    init = [b.backdrop("시작화면"), b.set_var("게임상태", V["게임상태"], "start"),
            b.set_var("하트", V["하트"], 5), b.set_var("속도Y", V["속도Y"], 0),
            b.set_var("점프중", V["점프중"], 0), b.stop_sounds()]
    b.chain([f0] + init)

    # SPACE to start
    sp = b.key_hat("space")
    c1 = b.eq_var("게임상태", V["게임상태"], "start")
    s1 = [b.set_var("게임상태", V["게임상태"], "stage2"), b.backdrop("스테이지2"),
          b.broadcast("스테이지2", BR["스테이지2"])]
    b.chain(s1); if1 = b.if_then(c1, s1[0])
    # Restart from gameover
    c2 = b.eq_var("게임상태", V["게임상태"], "gameover")
    s2 = [b.set_var("하트", V["하트"], 5), b.set_var("속도Y", V["속도Y"], 0),
          b.set_var("점프중", V["점프중"], 0),
          b.set_var("게임상태", V["게임상태"], "stage2"), b.backdrop("스테이지2"),
          b.broadcast("스테이지2", BR["스테이지2"])]
    b.chain(s2); if2 = b.if_then(c2, s2[0])
    # Restart from clear
    c3 = b.eq_var("게임상태", V["게임상태"], "clear")
    s3 = [b.set_var("하트", V["하트"], 5), b.set_var("속도Y", V["속도Y"], 0),
          b.set_var("점프중", V["점프중"], 0),
          b.set_var("게임상태", V["게임상태"], "stage2"), b.backdrop("스테이지2"),
          b.broadcast("스테이지2", BR["스테이지2"])]
    b.chain(s3); if3 = b.if_then(c3, s3[0])
    b.chain([sp, if1, if2, if3])

    stage_target = {
        "isStage": True, "name": "Stage", "variables": gvars, "lists": {}, "comments": {},
        "broadcasts": {v: k for k, v in BR.items()},
        "blocks": b.blocks, "currentCostume": 0,
        "costumes": [am.reg_png_backdrop("시작화면", "bg_stage.png"),
                     am.reg_png_backdrop("스테이지2", "bg_stage.png"),
                     am.reg("게임오버", bg_gameover(), 240, 180),
                     am.reg("클리어", bg_victory(), 240, 180)],
        "sounds": [], "volume": 100, "layerOrder": 0, "tempo": 60,
        "videoTransparency": 50, "videoState": "off", "textToSpeechLanguage": None
    }

    # Stage 2 timer (20 seconds → clear)
    s2_timer = BB()
    s2h = s2_timer.bcast_hat("스테이지2", BR["스테이지2"])
    s2t = [s2_timer.wait(20), s2_timer.set_var("게임상태", V["게임상태"], "clear"),
           s2_timer.backdrop("클리어")]
    s2_timer.chain([s2h] + s2t)
    stage_target["blocks"].update(s2_timer.blocks)

    # ==================== MARIO ====================
    m = BB()
    mf = m.flag(); m.chain([mf, m.goto(-150, GY), m.set_size(100), m.costume("걷기1"), m.show()])

    mh2 = m.bcast_hat("스테이지2", BR["스테이지2"])
    m2_init = [m.goto(-150, GY), m.set_var("속도Y", V["속도Y"], 0), m.set_var("점프중", V["점프중"], 0)]

    # Physics
    grav2 = m.change_var("속도Y", V["속도Y"], -1)
    av2 = m.change_y_var("속도Y", V["속도Y"])
    cg2 = m.lt_ypos(GY)
    gs2 = [m.set_y(GY), m.set_var("속도Y", V["속도Y"], 0), m.set_var("점프중", V["점프중"], 0)]
    m.chain(gs2); ifg2 = m.if_then(cg2, gs2[0])
    # Movement
    kr2 = m.key_pressed("right arrow"); mvr2 = [m.change_x(5), m.costume("걷기1")]; m.chain(mvr2); ifr2 = m.if_then(kr2, mvr2[0])
    kl2 = m.key_pressed("left arrow"); mvl2 = [m.change_x(-5), m.costume("걷기1")]; m.chain(mvl2); ifl2 = m.if_then(kl2, mvl2[0])
    # Jump
    kj2 = m.key_pressed("space"); cnj2 = m.eq_var("점프중", V["점프중"], 0); cj2 = m.op_and(kj2, cnj2)
    jb2 = [m.set_var("속도Y", V["속도Y"], 14), m.set_var("점프중", V["점프중"], 1), m.play_sound("Jump")]
    m.chain(jb2); ifj2 = m.if_then(cj2, jb2[0])
    # Turtle collision
    def turtle_hit(tn):
        tt = m.touching(tn)
        hit = [m.change_var("하트", V["하트"], -1), m.play_sound("Hit"),
               m.set_y(GY + 30), m.set_var("속도Y", V["속도Y"], 8), m.wait(0.8)]
        m.chain(hit); return m.if_then(tt, hit[0])
    it1 = turtle_hit("Turtle1"); it2 = turtle_hit("Turtle2"); it3 = turtle_hit("Turtle3")
    # Heart check
    ch0 = m.lt_var("하트", V["하트"], 1)
    die2 = [m.set_var("게임상태", V["게임상태"], "gameover"), m.backdrop("게임오버"), m.stop_all()]
    m.chain(die2); ifd2 = m.if_then(ch0, die2[0])

    m.chain([grav2, av2, ifg2, ifr2, ifl2, ifj2, it1, it2, it3, ifd2])
    cs2 = m.eq_var("게임상태", V["게임상태"], "stage2")
    ifs2 = m.if_then(cs2, grav2); fs2 = m.forever(ifs2)
    m.chain([mh2] + m2_init + [fs2])

    mario = {"isStage": False, "name": "Mario", "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": m.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("걷기1", "mario/mario3_walk_1.png"), am.reg_png("걷기3", "mario/mario3_walk_3.png"),
                     am.reg_png("걷기4", "mario/mario3_walk_4.png"), am.reg_png("걷기5", "mario/mario3_walk_5.png"),
                     am.reg_png("걷기6", "mario/mario3_walk_6.png"), am.reg_png("점프1", "mario/mario3_jump_5.png")],
        "sounds": [snd_jump, snd_hit], "volume": 100, "layerOrder": 8, "visible": True,
        "x": -150, "y": GY, "size": 100, "direction": 90, "draggable": False, "rotationStyle": "left-right"}

    # ==================== SHELL TURTLES ====================
    def make_shell(name, speed, start_delay):
        t = BB(); tf = t.flag(); t.chain([tf, t.hide()])
        th = t.bcast_hat("스테이지2", BR["스테이지2"])
        ti = [t.goto(260, GY + 5), t.set_size(140), t.show(), t.wait(start_delay)]
        tgl = t.glide(speed, -260, GY + 5); treset = t.goto(260, GY + 5); tw = t.wait(0.3)
        t.chain([tgl, treset, tw]); tfl = t.forever(tgl)
        t.chain([th] + ti + [tfl])
        return {"isStage": False, "name": name, "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
            "blocks": t.blocks, "currentCostume": 0, "costumes": [am.reg_png("koopa", "bowser/bowser_walk_1.png")],
            "sounds": [], "volume": 100, "layerOrder": 4, "visible": False,
            "x": 260, "y": GY + 5, "size": 140, "direction": 90, "draggable": False, "rotationStyle": "don't rotate"}
    turtle1 = make_shell("Turtle1", 1.8, 0)
    turtle2 = make_shell("Turtle2", 1.5, 2.5)
    turtle3 = make_shell("Turtle3", 1.2, 5)

    # ==================== HEARTS ====================
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

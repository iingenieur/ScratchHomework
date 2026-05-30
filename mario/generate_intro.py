"""
Super Mario: Intro Cutscene (Standalone)
어느 평화로운 날 마리오와 피치가 산책 중, 쿠파가 나타나 피치를 납치한다.
마리오: "꼭 구하러 갈게!"
"""

from common import (
    BB, AssetManager, GY, uid, save_sb3,
    svg_ground, svg_hearts,
    bg_intro, bg_gameover,
    gen_beep
)


def bg_start():
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">'
        '<rect width="480" height="360" fill="#87CEEB"/>'
        '<rect x="0" y="280" width="480" height="80" fill="#4CAF50"/>'
        '<rect x="0" y="310" width="480" height="50" fill="#8B4513"/>'
        '<ellipse cx="100" cy="60" rx="40" ry="20" fill="white" opacity="0.7"/>'
        '<ellipse cx="350" cy="50" rx="50" ry="22" fill="white" opacity="0.6"/>'
        '<text x="240" y="130" text-anchor="middle" font-size="36" font-weight="bold" fill="#E02020">Super Mario</text>'
        '<text x="240" y="175" text-anchor="middle" font-size="18" fill="#333">인트로 컷씬</text>'
        '<text x="240" y="240" text-anchor="middle" font-size="16" fill="#555">SPACE 키를 눌러 시작</text>'
        '</svg>'
    )


def bg_intro_end():
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">'
        '<rect width="480" height="360" fill="#87CEEB"/>'
        '<rect x="0" y="280" width="480" height="80" fill="#4CAF50"/>'
        '<rect x="0" y="310" width="480" height="50" fill="#8B4513"/>'
        '<text x="240" y="160" text-anchor="middle" font-size="40" font-weight="bold" fill="#1565C0">인트로 끝!</text>'
        ''
        '</svg>'
    )


def build():
    am = AssetManager()

    BR = {k: uid() for k in ["인트로", "인트로끝", "리셋", "carry"]}
    V  = {k: uid() for k in ["게임상태"]}

    gvars = {V["게임상태"]: ["게임상태", "start"]}

    # ==================== SOUNDS ====================
    snd_hit = am.reg_snd("Hit", gen_beep(200, 0.2))

    # ==================== STAGE (backdrops + flow logic) ====================
    b = BB()
    f0 = b.flag()
    init = [
        b.backdrop("시작화면"),
        b.set_var("게임상태", V["게임상태"], "start"),
        b.stop_sounds(),
    ]
    b.chain([f0] + init)

    # SPACE to start intro
    sp = b.key_hat("space")
    c1 = b.eq_var("게임상태", V["게임상태"], "start")
    s1 = [
        b.set_var("게임상태", V["게임상태"], "intro"),
        b.backdrop("인트로"),
        b.broadcast("인트로", BR["인트로"]),
    ]
    b.chain(s1)
    if1 = b.if_then(c1, s1[0])

    # SPACE to replay from end screen
    c2 = b.eq_var("게임상태", V["게임상태"], "end")
    s2 = [
        b.set_var("게임상태", V["게임상태"], "intro"),
        b.backdrop("인트로"),
        b.broadcast("인트로", BR["인트로"]),
    ]
    b.chain(s2)
    if2 = b.if_then(c2, s2[0])

    b.chain([sp, if1, if2])

    # When intro broadcast finishes → show end screen
    bh_end = b.bcast_hat("인트로끝", BR["인트로끝"])
    end_seq = [
        b.backdrop("인트로끝"),
        b.set_var("게임상태", V["게임상태"], "end"),
    ]
    b.chain([bh_end] + end_seq)

    def reg_svg(name, svg_str, cx, cy):
        import hashlib
        d = svg_str.encode("utf-8")
        md5 = hashlib.md5(d).hexdigest()
        am.assets[f"{md5}.svg"] = d
        return {
            "name": name, "assetId": md5, "md5ext": f"{md5}.svg",
            "dataFormat": "svg", "rotationCenterX": cx, "rotationCenterY": cy,
        }

    stage_target = {
        "isStage": True, "name": "Stage",
        "variables": gvars, "lists": {}, "comments": {},
        "broadcasts": {v: k for k, v in BR.items()},
        "blocks": b.blocks, "currentCostume": 0,
        "costumes": [
            reg_svg("시작화면", bg_start(),    240, 180),
            am.reg_png_backdrop("인트로", "background/bg_stage.png"),
            reg_svg("인트로끝", bg_intro_end(), 240, 180),
        ],
        "sounds": [], "volume": 100, "layerOrder": 0,
        "tempo": 60, "videoTransparency": 50, "videoState": "off",
        "textToSpeechLanguage": None,
    }

    # ==================== TIMING PLAN ====================
    # Mario(뒤) + Peach(앞) LEFT→RIGHT 걸어감, Bowser RIGHT에서 등장
    # 0.0-1.2s: Mario+Peach walk from left to center-right
    # 1.2-3.2s: Mario says "피치, 오늘 날씨가 좋다!"
    # 3.2-5.2s: Peach says "네, 정말 좋아요!"
    # 5.2-6.2s: Bowser flies down from right
    # 6.2-7.2s: Peach says "으악! 쿠파!!"
    # 7.2-9.2s: Bowser says "하하하! 피치는 내꺼다!"
    # 9.2-10.7s: Bowser + Peach fly away right
    # 10.7-12.7s: Mario says "피치!!!! 안돼!!"
    # 12.7-14.7s: Mario says "꼭 구하러 갈게!"

    WALK_TIME = 1.2
    WALK_STEPS = 10
    STEP_DELAY = WALK_TIME / WALK_STEPS  # 0.12s

    # ==================== MARIO ====================
    m = BB()
    mf = m.flag()
    m.chain([mf, m.hide()])

    mh = m.bcast_hat("인트로", BR["인트로"])
    # Mario starts at same position as Peach (together)
    intro_m = [
        m.goto(-180, GY), m.set_size(80), m.show(),
        m.point_dir(90), m.costume("걷기1"),
    ]
    # Walk animation: 10 steps RIGHT, arrive at ~-30
    walk_steps = []
    costumes_walk = ["걷기1", "걷기3", "걷기4", "걷기5", "걷기6"]
    for i in range(WALK_STEPS):
        walk_steps.append(m.costume(costumes_walk[i % len(costumes_walk)]))
        walk_steps.append(m.change_x(17))
        walk_steps.append(m.wait(STEP_DELAY))

    # Mario walk takes ~1.5s (1.2s in waits + block execution overhead)
    # Peach glide = 1.5s to match
    # After walk: Mario says first, then Peach (no overlap)
    talk_seq = [
        m.costume("걷기1"),
        m.say_for("피치, 오늘 날씨가 좋다!", 2),        # +1.5 ~ +3.5s
        m.say_nothing(),
        m.wait(2.3),                                    # gap + peach says 2s + buffer
        m.wait(1),                                      # bowser arrives
        m.wait(1),                                      # peach reacts
        m.wait(2),                                      # bowser talks
        m.wait(1.5),                                    # they fly away
        m.say_for("피치!!!! 안돼!!", 2),
        m.costume("점프1"),
        m.say_for("꼭 구하러 갈게!", 2),
        m.say_nothing(),
        m.costume("걷기1"),
        m.broadcast_wait("인트로끝", BR["인트로끝"]),
    ]
    m.chain([mh] + intro_m + walk_steps + talk_seq)

    mario = {
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
            am.reg_png("점프2", "mario/mario3_jump_6.png"),
            am.reg_png("점프3", "mario/mario3_jump_7.png"),
        ],
        "sounds": [snd_hit], "volume": 100, "layerOrder": 8,
        "visible": False, "x": -180, "y": GY, "size": 80,
        "direction": 90, "draggable": False, "rotationStyle": "left-right",
    }

    # ==================== PEACH ====================
    p = BB()
    pf = p.flag()
    p.chain([pf, p.hide()])

    ph = p.bcast_hat("인트로", BR["인트로"])
    # Mario와 같은 step/timing(10 step × 17, 0.12s)으로 나란히 걷기.
    # Peach 시작 -145 (Mario -180과 35px 차이) → 끝 25.
    pi = [
        p.goto(-145, GY), p.set_size(70), p.show(),
        p.point_dir(90), p.costume("walk1"),
    ]
    for i in range(WALK_STEPS):
        pi += [p.change_x(17), p.costume(f"walk{(i % 7) + 1}"), p.wait(STEP_DELAY)]
    pi += [
        p.goto(25, GY),
        p.costume("peach"),                             # 멘트 칠 때 정지 자세
        p.wait(2),                                      # mario says (2s)
        p.wait(0.3),                                    # gap after mario's bubble gone
        p.say_for("네, 정말 좋아요!", 2),                # peach responds
        p.say_nothing(),
        p.wait(1),                                      # bowser arrives
        p.say_for("으악! 쿠파!!", 1),                    # peach reacts
        p.say_nothing(),
        # carry는 별도 broadcast hat이 처리(쿠파와 동기) → 멘트 후 그 자리에 머무름.
    ]
    p.chain([ph] + pi)

    # broadcast "carry"를 받으면 즉시 bowser 옆으로 이동 + 함께 우상단으로 glide → hide.
    ph_carry = p.bcast_hat("carry", BR["carry"])
    p.chain([ph_carry,
             p.goto(30, GY),                            # bowser(80) 옆 50px (sprite 폭 만큼 떨어짐)
             p.glide(1.5, 230, 200),                    # bowser(280)와 50px 평행 유지
             p.hide()])

    peach = {
        "isStage": False, "name": "Peach",
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": p.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("peach", "peach/peach_idle.png")]
                    + [am.reg_png(f"walk{i+1}", f"peach/peach_walk_{i+1}.png") for i in range(7)],
        "sounds": [], "volume": 100, "layerOrder": 7,
        "visible": False, "x": -180, "y": GY, "size": 70,
        "direction": 90, "draggable": False, "rotationStyle": "left-right",
    }

    # ==================== BOWSER ====================
    bw = BB()
    bwf = bw.flag()
    bw.chain([bwf, bw.hide()])

    bwh = bw.bcast_hat("인트로", BR["인트로"])
    bwi = [
        bw.goto(250, 200), bw.set_size(100),
        bw.wait(5.8),                                  # wait for walk+conversation
        bw.show(),                                      # show 직전에만 등장 (시작 시 안 보임)
        bw.glide(1, 70, GY),                           # peach(25) 우측 45px에 land (겹치지 않음)
        bw.wait(1.5),                                  # peach가 "으악!" 다 말할 때까지 대기 (말풍선 겹침 방지)
        bw.say_for("하하하! 피치는 내꺼다!", 2),        # peach 멘트 후 bowser 단독 멘트
        bw.broadcast("carry", BR["carry"]),            # peach와 동기화 시작 신호
        bw.glide(1.5, 270, 200),                       # carry-away — peach(230)와 40px 평행 유지 (동일 거리)
        bw.hide(),
    ]
    bw.chain([bwh] + bwi)

    bowser = {
        "isStage": False, "name": "Bowser",
        "variables": {}, "lists": {}, "broadcasts": {}, "comments": {},
        "blocks": bw.blocks, "currentCostume": 0,
        "costumes": [am.reg_png("쿠파", "koopa/bowser_stand_1.png")],
        "sounds": [snd_hit], "volume": 100, "layerOrder": 6,
        "visible": False, "x": 200, "y": 200, "size": 100,
        "direction": 90, "draggable": False, "rotationStyle": "don't rotate",
    }

    # ==================== PROJECT ====================
    project = {
        "targets": [stage_target, mario, peach, bowser],
        "monitors": [],
        "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "Mario Intro Standalone"},
    }
    return project, am.assets


def main():
    print("Generating Super Mario Intro Cutscene...")
    proj, assets = build()
    save_sb3("Intro.sb3", proj, assets)
    print()
    print("=== INTRO STRUCTURE ===")
    print("시작화면: SPACE 키를 눌러 인트로 시작")
    print("인트로: 마리오와 피치 산책 → 쿠파 등장 → 피치 납치")
    print("       마리오: '꼭 구하러 갈게!'")
    print("인트로끝: SPACE 키를 눌러 다시 보기")


if __name__ == "__main__":
    main()

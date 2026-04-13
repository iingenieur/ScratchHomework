"""
F1 Grand Prix Racer v3 - Bird's-eye view circuit racing
NO CLONES - all objects are individual sprites
Track: oval circuit with real curves
Controls: arrow keys to steer and accelerate
"""

import json, zipfile, hashlib, uuid, os, struct, math

def uid(): return uuid.uuid4().hex[:20]

# ============================================================
# Block Builder (proven working for non-clone blocks)
# ============================================================
class BB:
    def __init__(self):
        self.blocks = {}

    def _add(self, opcode, inputs=None, fields=None, top=False, shadow=False, mutation=None):
        bid = uid()
        b = {"opcode": opcode, "next": None, "parent": None,
             "inputs": inputs or {}, "fields": fields or {},
             "shadow": shadow, "topLevel": top}
        if top: b["x"], b["y"] = 0, 0
        if mutation: b["mutation"] = mutation
        self.blocks[bid] = b
        return bid

    def _parent(self, child, par):
        if child and child in self.blocks:
            self.blocks[child]["parent"] = par
            self.blocks[child]["topLevel"] = False
            self.blocks[child].pop("x", None)
            self.blocks[child].pop("y", None)

    def chain(self, ids):
        for i in range(len(ids)):
            if i < len(ids)-1:
                self.blocks[ids[i]]["next"] = ids[i+1]
            if i > 0:
                self.blocks[ids[i]]["parent"] = ids[i-1]
                self.blocks[ids[i]]["topLevel"] = False
                self.blocks[ids[i]].pop("x", None)
                self.blocks[ids[i]].pop("y", None)
        if ids and self.blocks[ids[0]]["parent"] is None:
            self.blocks[ids[0]]["topLevel"] = True
            self.blocks[ids[0]].setdefault("x", 0)
            self.blocks[ids[0]].setdefault("y", 0)

    # Hats
    def flag(self): return self._add("event_whenflagclicked", top=True)
    def key_hat(self, k): return self._add("event_whenkeypressed", fields={"KEY_OPTION":[k,None]}, top=True)
    def broadcast_hat(self, name, bid):
        return self._add("event_whenbroadcastreceived", fields={"BROADCAST_OPTION":[name,bid]}, top=True)

    # Control
    def forever(self, sub):
        b = self._add("control_forever", inputs={"SUBSTACK":[2,sub]})
        self._parent(sub, b); return b
    def if_then(self, cond, sub):
        inp = {"CONDITION":[2,cond]}
        if sub: inp["SUBSTACK"] = [2,sub]
        b = self._add("control_if", inputs=inp)
        self._parent(cond, b); self._parent(sub, b); return b
    def if_else(self, cond, sub1, sub2):
        inp = {"CONDITION":[2,cond]}
        if sub1: inp["SUBSTACK"] = [2,sub1]
        if sub2: inp["SUBSTACK2"] = [2,sub2]
        b = self._add("control_if_else", inputs=inp)
        self._parent(cond, b); self._parent(sub1, b); self._parent(sub2, b); return b
    def wait(self, s): return self._add("control_wait", inputs={"DURATION":[1,[5,str(s)]]})
    def stop_all(self):
        return self._add("control_stop", fields={"STOP_OPTION":["all",None]},
                         mutation={"tagName":"mutation","children":[],"hasnext":"false"})

    # Motion
    def goto(self, x, y):
        return self._add("motion_gotoxy", inputs={"X":[1,[4,str(x)]],"Y":[1,[4,str(y)]]})
    def glide(self, secs, x, y):
        return self._add("motion_glidesecstoxy", inputs={
            "SECS":[1,[4,str(secs)]], "X":[1,[4,str(x)]], "Y":[1,[4,str(y)]]})
    def move(self, steps):
        return self._add("motion_movesteps", inputs={"STEPS":[1,[4,str(steps)]]})
    def move_var(self, vn, vi):
        vr = self.var_ref(vn, vi)
        b = self._add("motion_movesteps", inputs={"STEPS":[3,vr,[4,"0"]]})
        self._parent(vr, b); return b
    def turn_right(self, deg):
        return self._add("motion_turnright", inputs={"DEGREES":[1,[4,str(deg)]]})
    def turn_left(self, deg):
        return self._add("motion_turnleft", inputs={"DEGREES":[1,[4,str(deg)]]})
    def point_dir(self, d):
        return self._add("motion_pointindirection", inputs={"DIRECTION":[1,[4,str(d)]]})
    def point_towards(self, name):
        menu = self._add("motion_pointtowards_menu", fields={"TOWARDS":[name,None]}, shadow=True)
        b = self._add("motion_pointtowards", inputs={"TOWARDS":[1,menu]})
        self._parent(menu, b); return b
    def set_x(self, v): return self._add("motion_setx", inputs={"X":[1,[4,str(v)]]})
    def set_y(self, v): return self._add("motion_sety", inputs={"Y":[1,[4,str(v)]]})
    def change_x(self, v): return self._add("motion_changexby", inputs={"DX":[1,[4,str(v)]]})
    def change_y(self, v): return self._add("motion_changeyby", inputs={"DY":[1,[4,str(v)]]})
    def if_on_edge_bounce(self): return self._add("motion_ifonedgebounce")
    def x_pos(self): return self._add("motion_xposition")
    def y_pos(self): return self._add("motion_yposition")
    def direction(self): return self._add("motion_direction")

    # Looks
    def show(self): return self._add("looks_show")
    def hide(self): return self._add("looks_hide")
    def costume(self, n): return self._add("looks_switchcostumeto", inputs={"COSTUME":[1,[10,n]]})
    def backdrop(self, n): return self._add("looks_switchbackdropto", inputs={"BACKDROP":[1,[10,n]]})
    def set_size(self, p): return self._add("looks_setsizeto", inputs={"SIZE":[1,[4,str(p)]]})
    def say(self, msg): return self._add("looks_say", inputs={"MESSAGE":[1,[10,str(msg)]]})
    def say_for(self, msg, s):
        return self._add("looks_sayforsecs", inputs={"MESSAGE":[1,[10,str(msg)]],"SECS":[1,[4,str(s)]]})
    def set_effect(self, eff, v):
        return self._add("looks_seteffectto", inputs={"VALUE":[1,[4,str(v)]]}, fields={"EFFECT":[eff,None]})
    def clear_fx(self): return self._add("looks_cleargraphiceffects")

    # Sound
    def play_sound(self, n):
        m = self._add("sound_sounds_menu", fields={"SOUND_MENU":[n,None]}, shadow=True)
        b = self._add("sound_play", inputs={"SOUND_MENU":[1,m]})
        self._parent(m, b); return b
    def play_until_done(self, n):
        m = self._add("sound_sounds_menu", fields={"SOUND_MENU":[n,None]}, shadow=True)
        b = self._add("sound_playuntildone", inputs={"SOUND_MENU":[1,m]})
        self._parent(m, b); return b
    def stop_sounds(self): return self._add("sound_stopallsounds")

    # Sensing
    def key_pressed(self, k):
        m = self._add("sensing_keyoptions", fields={"KEY_OPTION":[k,None]}, shadow=True)
        b = self._add("sensing_keypressed", inputs={"KEY_OPTION":[1,m]})
        self._parent(m, b); return b
    def touching(self, name):
        m = self._add("sensing_touchingobjectmenu", fields={"TOUCHINGOBJECTMENU":[name,None]}, shadow=True)
        b = self._add("sensing_touchingobject", inputs={"TOUCHINGOBJECTMENU":[1,m]})
        self._parent(m, b); return b
    def touching_color(self, hex_color):
        # Color format: "#RRGGBB" converted to decimal
        color_val = int(hex_color.lstrip('#'), 16)
        return self._add("sensing_touchingcolor", inputs={"COLOR": [1, [9, f"#{hex_color.lstrip('#')}"]]})
    def distance_to(self, name):
        m = self._add("sensing_distanceto_menu", fields={"DISTANCETOMENU":[name,None]}, shadow=True)
        b = self._add("sensing_distanceto", inputs={"DISTANCETOMENU":[1,m]})
        self._parent(m, b); return b

    # Data
    def set_var(self, n, i, v):
        return self._add("data_setvariableto", fields={"VARIABLE":[n,i]}, inputs={"VALUE":[1,[10,str(v)]]})
    def change_var(self, n, i, v):
        return self._add("data_changevariableby", fields={"VARIABLE":[n,i]}, inputs={"VALUE":[1,[4,str(v)]]})
    def var_ref(self, n, i):
        return self._add("data_variable", fields={"VARIABLE":[n,i]})

    # Operators
    def eq_var(self, n, i, v):
        vr = self.var_ref(n, i)
        b = self._add("operator_equals", inputs={"OPERAND1":[3,vr,[10,""]],"OPERAND2":[1,[10,str(v)]]})
        self._parent(vr, b); return b
    def lt_var(self, n, i, v):
        vr = self.var_ref(n, i)
        b = self._add("operator_lt", inputs={"OPERAND1":[3,vr,[10,""]],"OPERAND2":[1,[10,str(v)]]})
        self._parent(vr, b); return b
    def gt_var(self, n, i, v):
        vr = self.var_ref(n, i)
        b = self._add("operator_gt", inputs={"OPERAND1":[3,vr,[10,""]],"OPERAND2":[1,[10,str(v)]]})
        self._parent(vr, b); return b
    def op_and(self, a, b_id):
        b = self._add("operator_and", inputs={"OPERAND1":[2,a],"OPERAND2":[2,b_id]})
        self._parent(a, b); self._parent(b_id, b); return b
    def op_not(self, a):
        b = self._add("operator_not", inputs={"OPERAND":[2,a]})
        self._parent(a, b); return b
    def op_random(self, lo, hi):
        return self._add("operator_random", inputs={"FROM":[1,[4,str(lo)]],"TO":[1,[4,str(hi)]]})

    # Events
    def broadcast(self, n, i):
        return self._add("event_broadcast", inputs={"BROADCAST_INPUT":[1,[11,n,i]]})
    def broadcast_wait(self, n, i):
        return self._add("event_broadcastandwait", inputs={"BROADCAST_INPUT":[1,[11,n,i]]})


# ============================================================
# SVG Generators
# ============================================================
def svg(w, h, content):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{content}</svg>'

def svg_car_topdown(body="#E02020", stripe="#FFF"):
    """Top-down F1 car facing RIGHT (44x22) - detailed design"""
    return svg(44, 22, f'''
    <!-- Rear wing -->
    <rect x="1" y="2" width="3" height="18" rx="1" fill="#222"/>
    <!-- Body -->
    <rect x="4" y="5" width="30" height="12" rx="2" fill="{body}"/>
    <!-- Cockpit -->
    <ellipse cx="22" cy="11" rx="5" ry="4" fill="#111"/>
    <ellipse cx="23" cy="11" rx="3" ry="2.5" fill="#2c3e50"/>
    <!-- Nose cone -->
    <polygon points="34,7 42,11 34,15" fill="{body}"/>
    <polygon points="40,9 44,11 40,13" fill="{stripe}"/>
    <!-- Front wing -->
    <rect x="38" y="1" width="4" height="6" rx="1" fill="#222"/>
    <rect x="38" y="15" width="4" height="6" rx="1" fill="#222"/>
    <!-- Rear wheels -->
    <rect x="5" y="0" width="8" height="5" rx="1.5" fill="#111"/>
    <rect x="5" y="17" width="8" height="5" rx="1.5" fill="#111"/>
    <!-- Front wheels -->
    <rect x="32" y="1" width="6" height="4" rx="1" fill="#111"/>
    <rect x="32" y="17" width="6" height="4" rx="1" fill="#111"/>
    <!-- Racing stripe -->
    <rect x="8" y="9" width="20" height="4" rx="1" fill="{stripe}" opacity="0.5"/>
    <!-- Number circle -->
    <circle cx="16" cy="11" r="3" fill="{stripe}"/>
    <!-- Exhaust -->
    <circle cx="2" cy="8" r="1" fill="#E74C3C" opacity="0.6"/>
    <circle cx="2" cy="14" r="1" fill="#E74C3C" opacity="0.6"/>
    ''')

def svg_fuel_can():
    return svg(18, 22, '''
    <rect x="2" y="4" width="14" height="16" rx="2" fill="#E74C3C"/>
    <rect x="5" y="0" width="8" height="6" rx="2" fill="#C0392B"/>
    <text x="9" y="16" text-anchor="middle" font-size="10" font-weight="bold" fill="white">F</text>
    ''')

def svg_finish_line():
    """Checkered finish line (60x10)"""
    checks = ""
    for i in range(12):
        for j in range(2):
            color = "#000" if (i+j)%2==0 else "#FFF"
            checks += f'<rect x="{i*5}" y="{j*5}" width="5" height="5" fill="{color}"/>'
    return svg(60, 10, checks)

def svg_drs_item():
    """Flame-shaped booster with B"""
    return svg(24, 30, '''
    <path d="M12,1 C7,8 2,14 2,20 C2,26 6,29 12,29 C18,29 22,26 22,20 C22,14 17,8 12,1Z" fill="#FF6600"/>
    <path d="M12,8 C9,13 5,16 5,20 C5,25 8,27 12,27 C16,27 19,25 19,20 C19,16 15,13 12,8Z" fill="#FFCC00"/>
    <text x="12" y="23" text-anchor="middle" font-size="11" font-weight="bold" fill="white">B</text>
    ''')

def svg_traffic_light(state):
    c = {0:["#333"]*3, 1:["#E02020","#333","#333"], 2:["#E02020","#E02020","#333"],
         3:["#E02020"]*3, 4:["#27AE60"]*3}[state]
    go = '<text x="45" y="65" text-anchor="middle" font-size="20" font-weight="bold" fill="#27AE60">GO!</text>' if state==4 else ''
    return svg(90, 70, f'''
    <rect x="5" y="5" width="80" height="35" rx="6" fill="#222"/>
    <circle cx="22" cy="22" r="10" fill="{c[0]}"/>
    <circle cx="45" cy="22" r="10" fill="{c[1]}"/>
    <circle cx="68" cy="22" r="10" fill="{c[2]}"/>
    {go}''')

def svg_minimap_dot(color):
    return svg(8, 8, f'<circle cx="4" cy="4" r="3" fill="{color}" stroke="#FFF" stroke-width="1"/>')

def svg_track_backdrop():
    """Bird's-eye view rounded rectangle circuit track"""
    return svg(480, 360, '''
    <!-- Grass -->
    <rect width="480" height="360" fill="#2d6b1e"/>

    <!-- Track outer curbing -->
    <rect x="37" y="27" width="406" height="306" rx="93" ry="93"
          fill="none" stroke="#E02020" stroke-width="6"/>

    <!-- Track road surface (wide) -->
    <rect x="80" y="70" width="320" height="220" rx="50" ry="50"
          fill="none" stroke="#555" stroke-width="80"/>

    <!-- Track inner curbing -->
    <rect x="118" y="108" width="244" height="144" rx="12" ry="12"
          fill="none" stroke="#E02020" stroke-width="5"/>

    <!-- Inner grass -->
    <rect x="123" y="113" width="234" height="134" rx="7" ry="7"
          fill="#2d6b1e"/>

    <!-- Center line (dashed) -->
    <rect x="80" y="70" width="320" height="220" rx="50" ry="50"
          fill="none" stroke="white" stroke-width="2" stroke-dasharray="15,10" opacity="0.3"/>

    <!-- Start/finish line at bottom center -->
    <rect x="237" y="280" width="6" height="12" fill="white"/>
    <rect x="237" y="292" width="6" height="12" fill="black"/>
    <rect x="237" y="304" width="6" height="12" fill="white"/>

    <!-- Corner markers -->
    <text x="395" y="100" font-size="9" fill="rgba(255,255,255,0.3)">T1</text>
    <text x="395" y="275" font-size="9" fill="rgba(255,255,255,0.3)">T2</text>
    <text x="75" y="275" font-size="9" fill="rgba(255,255,255,0.3)">T3</text>
    <text x="75" y="100" font-size="9" fill="rgba(255,255,255,0.3)">T4</text>

    <!-- Minimap (top-right) -->
    <rect x="375" y="8" width="96" height="64" rx="5" fill="rgba(0,0,0,0.6)"/>
    <rect x="390" y="18" width="66" height="44" rx="12" ry="12"
          fill="none" stroke="#555" stroke-width="6"/>

    <text x="240" y="352" text-anchor="middle" font-size="10" fill="rgba(255,255,255,0.5)">START / FINISH</text>
    ''')

def svg_start_screen():
    return svg(480, 360, '''
    <rect width="480" height="360" fill="#1a1a2e"/>
    <text x="240" y="90" text-anchor="middle" font-size="38" font-weight="bold" fill="#E02020">F1 GRAND PRIX</text>
    <text x="240" y="130" text-anchor="middle" font-size="28" font-weight="bold" fill="#FFD700">RACER</text>
    <rect x="150" y="145" width="180" height="3" fill="#E02020" rx="1"/>
    <text x="240" y="190" text-anchor="middle" font-size="13" fill="#AAA">Inspired by F1: The Movie</text>
    <text x="240" y="240" text-anchor="middle" font-size="18" fill="#FFF">SPACE 키를 눌러 시작</text>
    <text x="240" y="275" text-anchor="middle" font-size="13" fill="#888">↑ 가속  ← → 조향</text>
    <text x="240" y="300" text-anchor="middle" font-size="11" fill="#555">3랩 완주하면 승리!</text>
    ''')

def svg_gameover():
    return svg(480, 360, '''
    <rect width="480" height="360" fill="#1a1a1a"/>
    <text x="240" y="130" text-anchor="middle" font-size="42" font-weight="bold" fill="#E02020">GAME OVER</text>
    <text x="240" y="175" text-anchor="middle" font-size="16" fill="#AAA">연료가 바닥났습니다!</text>
    <text x="240" y="240" text-anchor="middle" font-size="16" fill="#FFD700">SPACE 키를 눌러 재시작</text>
    ''')

def svg_win():
    return svg(480, 360, '''
    <rect width="480" height="360" fill="#1a1a2e"/>
    <text x="240" y="80" text-anchor="middle" font-size="16" fill="#AAA">CONGRATULATIONS!</text>
    <text x="240" y="130" text-anchor="middle" font-size="48" font-weight="bold" fill="#FFD700">CHAMPION!</text>
    <text x="240" y="175" text-anchor="middle" font-size="18" fill="#27AE60">3 Laps Completed!</text>
    <text x="240" y="240" text-anchor="middle" font-size="16" fill="#AAA">SPACE 키를 눌러 재시작</text>
    ''')

def generate_beep(freq=800, dur=0.15, sr=22050):
    n = int(sr*dur)
    raw = b''.join(struct.pack('<h', max(-32768, min(32767,
        int(16000*math.sin(2*math.pi*freq*i/sr)*(1-i/n*0.5))))) for i in range(n))
    w = bytearray(b'RIFF')
    w.extend(struct.pack('<I',36+len(raw))); w.extend(b'WAVEfmt ')
    w.extend(struct.pack('<IHHIIHH',16,1,1,sr,sr*2,2,16))
    w.extend(b'data'); w.extend(struct.pack('<I',len(raw))); w.extend(raw)
    return bytes(w)


# ============================================================
# Oval track waypoints (8 points around the ellipse)
# Center (240,180) -> offset to Scratch coords (0,0)
# Ellipse: rx=167, ry=108 (center of track)
# ============================================================
# Rounded rectangle track waypoints (16 points, clockwise from bottom-right)
WAYPOINTS = [
    (80, -110),     # 0: bottom right straight
    (135, -100),    # 1: approaching BR corner
    (158, -65),     # 2: BR corner
    (160, -15),     # 3: right side
    (160, 35),      # 4: right side
    (155, 75),      # 5: approaching TR corner
    (125, 105),     # 6: TR corner
    (60, 110),      # 7: top right straight
    (-60, 110),     # 8: top left straight
    (-125, 105),    # 9: approaching TL corner
    (-155, 75),     # 10: TL corner
    (-160, 35),     # 11: left side
    (-160, -15),    # 12: left side
    (-155, -65),    # 13: approaching BL corner
    (-125, -100),   # 14: BL corner
    (-60, -110),    # 15: bottom left straight
]
START_POS = (0, -110)
NUM_WP = len(WAYPOINTS)


# ============================================================
# Build Project
# ============================================================
def build():
    BR = {k: uid() for k in ["시작신호","레이싱시작","BGM","게임오버","승리"]}
    V = {k: uid() for k in ["연료","점수","현재랩","게임상태","속도","쿨다운","부스터","보유부스터"]}

    assets = {}
    def reg_svg(name, svg_str, cx, cy, is_backdrop=False):
        d = svg_str.encode("utf-8"); md5 = hashlib.md5(d).hexdigest()
        assets[f"{md5}.svg"] = d
        c = {"name":name,"assetId":md5,"md5ext":f"{md5}.svg","dataFormat":"svg",
             "rotationCenterX":cx,"rotationCenterY":cy}
        return c

    def reg_sound(name, data):
        md5 = hashlib.md5(data).hexdigest()
        assets[f"{md5}.wav"] = data
        return {"name":name,"assetId":md5,"md5ext":f"{md5}.wav","dataFormat":"wav","rate":22050,"sampleCount":0}

    # MP3
    mp3_path = "Lose My Mind (feat. Doja Cat) (From F1 The Movie).mp3"
    with open(mp3_path, "rb") as f: mp3_data = f.read()
    mp3_md5 = hashlib.md5(mp3_data).hexdigest()
    assets[f"{mp3_md5}.mp3"] = mp3_data
    snd_bgm = {"name":"F1 BGM","assetId":mp3_md5,"md5ext":f"{mp3_md5}.mp3",
               "dataFormat":"mp3","rate":44100,"sampleCount":0}

    snd_beep = reg_sound("Beep", generate_beep(800, 0.15))
    snd_go = reg_sound("Go", generate_beep(1200, 0.3))
    snd_crash = reg_sound("Crash", generate_beep(200, 0.2))
    snd_collect = reg_sound("Collect", generate_beep(1000, 0.1))

    gvars = {V[k]: [k, v] for k, v in [
        ("연료",100),("점수",0),("현재랩",0),("게임상태","start"),("속도",2),("쿨다운",0),("부스터",0),("보유부스터",0)]}

    # ==================== STAGE ====================
    b = BB()

    # Flag -> init
    f0 = b.flag()
    init = [b.backdrop("시작화면"), b.set_var("게임상태",V["게임상태"],"start"),
            b.set_var("연료",V["연료"],100), b.set_var("점수",V["점수"],0),
            b.set_var("현재랩",V["현재랩"],0), b.set_var("속도",V["속도"],2),
            b.set_var("쿨다운",V["쿨다운"],0),
            b.set_var("부스터",V["부스터"],0),
            b.set_var("보유부스터",V["보유부스터"],0), b.stop_sounds()]
    b.chain([f0]+init)

    # Space -> start/restart
    sp = b.key_hat("space")
    c1 = b.eq_var("게임상태",V["게임상태"],"start")
    s1 = [b.backdrop("트랙"), b.set_var("게임상태",V["게임상태"],"countdown"),
          b.broadcast_wait("시작신호",BR["시작신호"])]
    b.chain(s1)
    if1 = b.if_then(c1, s1[0])

    c2 = b.eq_var("게임상태",V["게임상태"],"gameover")
    s2 = [b.set_var("연료",V["연료"],100), b.set_var("점수",V["점수"],0),
          b.set_var("현재랩",V["현재랩"],0), b.set_var("속도",V["속도"],2),
          b.set_var("쿨다운",V["쿨다운"],0),
          b.backdrop("트랙"), b.set_var("게임상태",V["게임상태"],"countdown"),
          b.broadcast_wait("시작신호",BR["시작신호"])]
    b.chain(s2)
    if2 = b.if_then(c2, s2[0])

    c3 = b.eq_var("게임상태",V["게임상태"],"win")
    s3 = [b.set_var("연료",V["연료"],100), b.set_var("점수",V["점수"],0),
          b.set_var("현재랩",V["현재랩"],0), b.set_var("속도",V["속도"],2),
          b.set_var("쿨다운",V["쿨다운"],0),
          b.backdrop("트랙"), b.set_var("게임상태",V["게임상태"],"countdown"),
          b.broadcast_wait("시작신호",BR["시작신호"])]
    b.chain(s3)
    if3 = b.if_then(c3, s3[0])
    b.chain([sp, if1, if2, if3])

    # Score (no fuel system - removed)
    sh = b.broadcast_hat("레이싱시작",BR["레이싱시작"])
    sw = b.wait(0.2)
    si = b.change_var("점수",V["점수"],1)
    # Cooldown decrease
    cc = b.gt_var("쿨다운",V["쿨다운"],0)
    cd = b.change_var("쿨다운",V["쿨다운"],-1)
    ifc = b.if_then(cc, cd)
    b.chain([sw, si, ifc])
    csp = b.eq_var("게임상태",V["게임상태"],"playing")
    ifs = b.if_then(csp, sw)
    fs = b.forever(ifs)
    b.chain([sh, fs])

    # BGM
    bh = b.broadcast_hat("BGM",BR["BGM"])
    cbp = b.eq_var("게임상태",V["게임상태"],"playing")
    pbgm = b.play_until_done("F1 BGM")
    ifb = b.if_then(cbp, pbgm)
    fb = b.forever(ifb)
    b.chain([bh, fb])

    stage = {
        "isStage":True,"name":"Stage","variables":gvars,"lists":{},"comments":{},
        "broadcasts":{v:k for k,v in BR.items()},
        "blocks":b.blocks,"currentCostume":0,
        "costumes":[reg_svg("시작화면",svg_start_screen(),240,180),
                    reg_svg("트랙",svg_track_backdrop(),240,180),
                    reg_svg("게임오버",svg_gameover(),240,180),
                    reg_svg("승리",svg_win(),240,180)],
        "sounds":[snd_bgm],"volume":100,"layerOrder":0,"tempo":60,
        "videoTransparency":50,"videoState":"off","textToSpeechLanguage":None
    }

    # ==================== PLAYER CAR ====================
    p = BB()
    # Init
    # Player starts at grid position 4 (back row, lower)
    PLAYER_GRID = (-10, -150, 80)
    pf = p.flag()
    p.chain([pf, p.goto(PLAYER_GRID[0], PLAYER_GRID[1]), p.point_dir(PLAYER_GRID[2]), p.set_size(80), p.show()])

    # Racing controls
    ph = p.broadcast_hat("레이싱시작",BR["레이싱시작"])
    # Steering: left/right arrows turn the car
    kr = p.key_pressed("right arrow")
    tr = p.turn_right(3)
    ifr = p.if_then(kr, tr)
    kl = p.key_pressed("left arrow")
    tl = p.turn_left(3)
    ifl = p.if_then(kl, tl)
    # Accelerate: up arrow moves forward in facing direction
    ku = p.key_pressed("up arrow")
    mv = p.move(4)
    ifu = p.if_then(ku, mv)
    # Booster: if 부스터 > 0, move extra 3 steps + decrement
    cboost = p.gt_var("부스터",V["부스터"],0)
    boost_body = [p.move(5), p.change_var("부스터",V["부스터"],-1)]
    p.chain(boost_body)
    ifboost = p.if_then(cboost, boost_body[0])

    # Collision: both cars scatter apart (player deflects + spins)
    te1 = p.touching("Enemy1")
    bounce1 = [p.move(-12), p.turn_right(20),
               p.play_sound("Crash"), p.wait(0.15)]
    p.chain(bounce1)
    ifb1 = p.if_then(te1, bounce1[0])

    # (Enemy2, Enemy3 removed - 1v1 mode)

    # Grass (green) slowdown: brief pause
    tgrass = p.touching_color("2d6b1e")
    grass_slow = p.wait(0.05)
    if_grass = p.if_then(tgrass, grass_slow)
    # Outer curbing (red) speed boost
    tcurb = p.touching_color("E02020")
    curb_boost = p.move(2)
    if_curb = p.if_then(tcurb, curb_boost)

    p.chain([ifr, ifl, ifu, ifboost, if_grass, if_curb, ifb1])
    cpl = p.eq_var("게임상태",V["게임상태"],"playing")
    ifpl = p.if_then(cpl, ifr)
    fpl = p.forever(ifpl)
    p.chain([ph, fpl])

    # Lap detection: when touching FinishLine and cooldown=0
    ph2 = p.broadcast_hat("레이싱시작",BR["레이싱시작"])
    tfl = p.touching("FinishLine")
    ccd = p.eq_var("쿨다운",V["쿨다운"],0)
    cand = p.op_and(tfl, ccd)
    lap_body = [p.change_var("현재랩",V["현재랩"],1), p.set_var("쿨다운",V["쿨다운"],15),
                p.play_sound("Collect")]
    # Check win
    cw = p.gt_var("현재랩",V["현재랩"],2)
    win = [p.set_var("게임상태",V["게임상태"],"win"), p.backdrop("승리"),
           p.stop_sounds(), p.stop_all()]
    p.chain(win)
    ifw = p.if_then(cw, win[0])
    p.chain(lap_body + [ifw])
    iflap = p.if_then(cand, lap_body[0])
    pw = p.wait(0.1)
    p.chain([iflap, pw])
    cpl2 = p.eq_var("게임상태",V["게임상태"],"playing")
    ifpl2 = p.if_then(cpl2, iflap)
    fpl2 = p.forever(ifpl2)
    p.chain([ph2, fpl2])

    # B key: activate stored booster
    pb_hat = p.key_hat("b")
    cb_have = p.gt_var("보유부스터",V["보유부스터"],0)
    cb_playing = p.eq_var("게임상태",V["게임상태"],"playing")
    cb_and = p.op_and(cb_have, cb_playing)
    activate = [p.set_var("보유부스터",V["보유부스터"],0),
                p.set_var("부스터",V["부스터"],30),
                p.say_for("BOOST!", 1),
                p.play_sound("Collect")]
    p.chain(activate)
    if_activate = p.if_then(cb_and, activate[0])
    p.chain([pb_hat, if_activate])

    player = {
        "isStage":False,"name":"Player","variables":{},"lists":{},"broadcasts":{},"comments":{},
        "blocks":p.blocks,"currentCostume":0,
        "costumes":[reg_svg("car",svg_car_topdown("#E02020","#FFF"),22,11)],
        "sounds":[snd_crash, snd_collect],"volume":100,"layerOrder":5,
        "visible":True,"x":PLAYER_GRID[0],"y":PLAYER_GRID[1],"size":80,"direction":PLAYER_GRID[2],
        "draggable":False,"rotationStyle":"all around"
    }

    # ==================== AI ENEMY CARS ====================
    def make_ai_car(name, color, speed_factor, start_wp, layer, grid_pos, lane=0):
        """AI car that follows rounded rect waypoints on its own lane"""
        gx, gy, gdir = grid_pos
        a = BB()
        af = a.flag()
        a.chain([af, a.goto(gx, gy), a.point_dir(gdir), a.set_size(75), a.show()])

        # Lane offset: scale each waypoint away from/toward center
        def lane_wp(wx, wy):
            d = math.sqrt(wx*wx + wy*wy)
            if d == 0: return (wx, wy)
            s = (d + lane) / d
            return (round(wx * s), round(wy * s))

        ah = a.broadcast_hat("레이싱시작",BR["레이싱시작"])
        import random
        random.seed(hash(name))
        blocks = []
        for i in range(NUM_WP):
            ci = (start_wp + i) % NUM_WP
            ni = (start_wp + i + 1) % NUM_WP
            cx, cy = lane_wp(*WAYPOINTS[ci])
            nx, ny = lane_wp(*WAYPOINTS[ni])
            # Random wobble for natural movement
            wobble_x = random.randint(-20, 20)
            wobble_y = random.randint(-20, 20)
            nx, ny = nx + wobble_x, ny + wobble_y
            dx, dy = nx - cx, ny - cy
            scratch_dir = 90 - math.degrees(math.atan2(dy, dx))
            pd = a.point_dir(round(scratch_dir))
            spd = speed_factor + random.uniform(-0.2, 0.2)
            g = a.glide(round(max(0.4, spd), 2), nx, ny)
            blocks.extend([pd, g])
        a.chain(blocks)
        fai = a.forever(blocks[0])
        a.chain([ah, fai])

        # Player collision only (no AI-to-AI collision)
        ah2 = a.broadcast_hat("레이싱시작",BR["레이싱시작"])
        tp = a.touching("Player")
        pbounce = [a.move(-15), a.turn_left(10), a.wait(0.15)]
        a.chain(pbounce)
        ifp = a.if_then(tp, pbounce[0])
        aw = a.wait(0.05)
        a.chain([ifp, aw])
        cpl = a.eq_var("게임상태",V["게임상태"],"playing")
        ifpl = a.if_then(cpl, ifp)
        fai2 = a.forever(ifpl)
        a.chain([ah2, fai2])

        return {
            "isStage":False,"name":name,"variables":{},"lists":{},"broadcasts":{},"comments":{},
            "blocks":a.blocks,"currentCostume":0,
            "costumes":[reg_svg("car",svg_car_topdown(color,"#ECF0F1"),22,11)],
            "sounds":[snd_crash],"volume":100,"layerOrder":layer,
            "visible":True,"x":gx,"y":gy,"size":75,"direction":gdir,
            "draggable":False,"rotationStyle":"all around"
        }

    # 1v1 grid: rival in front, player behind
    GRID_DIR = 80
    # Each AI car follows a different lane to avoid collisions
    # lane: -15=inner, 0=center, +15=outer
    # 1v1: one rival car, same speed as player
    enemy1 = make_ai_car("Enemy1", "#2980B9", 0.5, 0, 3,
                         (15, -130, GRID_DIR), lane=0)

    # ==================== DRS BOOSTER ====================
    # DRS positions on track center line (4 spots at different curves)
    DRS_SPOTS = [WAYPOINTS[1], WAYPOINTS[4], WAYPOINTS[7], WAYPOINTS[10]]

    dr = BB()
    drf = dr.flag()
    dr.chain([drf, dr.goto(DRS_SPOTS[0][0], DRS_SPOTS[0][1]), dr.set_size(100), dr.show()])

    # When racing starts: cycle positions and handle collection
    drh = dr.broadcast_hat("레이싱시작",BR["레이싱시작"])

    # Player pickup
    dt_player = dr.touching("Player")
    dp_body = [dr.set_var("보유부스터",V["보유부스터"],1), dr.play_sound("Collect"),
               dr.hide(), dr.wait(8)]
    # Move to next spot and show again
    dr_rand = dr.op_random(0, 3)
    # Can't easily index a list, so just cycle through positions
    dp_reappear = [dr.goto(DRS_SPOTS[1][0], DRS_SPOTS[1][1]), dr.show()]
    dr.chain(dp_body + dp_reappear)
    if_dp = dr.if_then(dt_player, dp_body[0])

    # AI pickup (any enemy eats it -> just hide and reappear)
    dt_e1 = dr.touching("Enemy1")
    de1_body = [dr.hide(), dr.wait(8), dr.goto(DRS_SPOTS[2][0], DRS_SPOTS[2][1]), dr.show()]
    dr.chain(de1_body)
    if_de1 = dr.if_then(dt_e1, de1_body[0])

    drw = dr.wait(0.1)
    dr.chain([if_dp, if_de1, drw])
    cdr_pl = dr.eq_var("게임상태",V["게임상태"],"playing")
    ifdr_pl = dr.if_then(cdr_pl, if_dp)
    fdr = dr.forever(ifdr_pl)
    dr.chain([drh, fdr])

    drs_booster = {
        "isStage":False,"name":"DRSBooster","variables":{},"lists":{},"broadcasts":{},"comments":{},
        "blocks":dr.blocks,"currentCostume":0,
        "costumes":[reg_svg("boost",svg_drs_item(),12,15)],
        "sounds":[snd_collect],"volume":100,"layerOrder":8,
        "visible":True,"x":DRS_SPOTS[0][0],"y":DRS_SPOTS[0][1],"size":100,"direction":90,
        "draggable":False,"rotationStyle":"don't rotate"
    }

    # ==================== FINISH LINE ====================
    fl = BB()
    flf = fl.flag()
    fl.chain([flf, fl.goto(0, START_POS[1]+15), fl.set_size(60), fl.show()])

    finish = {
        "isStage":False,"name":"FinishLine","variables":{},"lists":{},"broadcasts":{},"comments":{},
        "blocks":fl.blocks,"currentCostume":0,
        "costumes":[reg_svg("finish",svg_finish_line(),30,5)],
        "sounds":[],"volume":100,"layerOrder":1,
        "visible":True,"x":0,"y":START_POS[1]+15,"size":60,"direction":90,
        "draggable":False,"rotationStyle":"don't rotate"
    }

    # (Fuel item removed - booster only)

    # ==================== TRAFFIC LIGHT ====================
    t = BB()
    tf = t.flag()
    t.chain([tf, t.hide()])

    th = t.broadcast_hat("시작신호",BR["시작신호"])
    tl_body = [t.show(), t.goto(0,30), t.set_size(100),
               t.costume("빨강1"), t.play_sound("Beep"), t.wait(1),
               t.costume("빨강2"), t.play_sound("Beep"), t.wait(1),
               t.costume("빨강3"), t.play_sound("Beep"), t.wait(1),
               t.costume("초록"), t.play_sound("Go"), t.wait(0.7),
               t.hide(),
               t.set_var("게임상태",V["게임상태"],"playing"),
               t.broadcast("레이싱시작",BR["레이싱시작"]),
               t.broadcast("BGM",BR["BGM"])]
    t.chain([th]+tl_body)

    traffic = {
        "isStage":False,"name":"TrafficLight","variables":{},"lists":{},"broadcasts":{},"comments":{},
        "blocks":t.blocks,"currentCostume":0,
        "costumes":[reg_svg("꺼짐",svg_traffic_light(0),45,35),
                    reg_svg("빨강1",svg_traffic_light(1),45,35),
                    reg_svg("빨강2",svg_traffic_light(2),45,35),
                    reg_svg("빨강3",svg_traffic_light(3),45,35),
                    reg_svg("초록",svg_traffic_light(4),45,35)],
        "sounds":[snd_beep, snd_go],"volume":100,"layerOrder":10,
        "visible":False,"x":0,"y":30,"size":100,"direction":90,
        "draggable":False,"rotationStyle":"don't rotate"
    }

    # ==================== MINIMAP DOTS ====================
    def make_minimap_dot(name, color, track_sprite, layer):
        d = BB()
        df = d.flag()
        d.chain([df, d.goto(MINI_CX, MINI_CY), d.set_size(60), d.show()])

        # Follow track_sprite position scaled to minimap
        dh = d.broadcast_hat("레이싱시작",BR["레이싱시작"])
        # Approximate: set x to minimap_cx + sprite_x * scale
        # Since we can't do math easily, just point towards and use distance
        # Simpler: use the tracked sprite's position directly
        dpt = d.point_towards(track_sprite)
        # Actually, for minimap, we need to scale positions.
        # This is hard without complex math blocks.
        # Simple approach: just make the dot follow at a fixed offset
        # Actually, let's skip real minimap tracking for now and just show static dots
        dw = d.wait(0.5)
        d.chain([dpt, dw])
        cpl = d.eq_var("게임상태",V["게임상태"],"playing")
        ifpl = d.if_then(cpl, dpt)
        fpl = d.forever(ifpl)
        d.chain([dh, fpl])

        return {
            "isStage":False,"name":name,"variables":{},"lists":{},"broadcasts":{},"comments":{},
            "blocks":d.blocks,"currentCostume":0,
            "costumes":[reg_svg("dot",svg_minimap_dot(color),4,4)],
            "sounds":[],"volume":100,"layerOrder":layer,
            "visible":True,"x":MINI_CX,"y":MINI_CY,"size":60,"direction":90,
            "draggable":False,"rotationStyle":"don't rotate"
        }

    # Skip minimap dots for now to keep it simple
    # They can be added later once the core game works

    # ==================== MONITORS ====================
    monitors = [
        {"id":V["점수"],"mode":"default","opcode":"data_variable",
         "params":{"VARIABLE":"점수"},"spriteName":None,"value":0,
         "width":0,"height":0,"x":5,"y":5,"visible":True,
         "sliderMin":0,"sliderMax":100,"isDiscrete":True},
        {"id":V["현재랩"],"mode":"default","opcode":"data_variable",
         "params":{"VARIABLE":"현재랩"},"spriteName":None,"value":0,
         "width":0,"height":0,"x":5,"y":30,"visible":True,
         "sliderMin":0,"sliderMax":3,"isDiscrete":True},
        {"id":V["보유부스터"],"mode":"default","opcode":"data_variable",
         "params":{"VARIABLE":"보유부스터"},"spriteName":None,"value":0,
         "width":0,"height":0,"x":5,"y":55,"visible":True,
         "sliderMin":0,"sliderMax":1,"isDiscrete":True},
    ]

    project = {
        "targets":[stage, player, enemy1,
                   finish, drs_booster, traffic],
        "monitors":monitors, "extensions":[],
        "meta":{"semver":"3.0.0","vm":"0.2.0","agent":"F1 v3"}
    }
    return project, assets


def main():
    print("Generating F1 Grand Prix Racer v3 (circuit racing)...")
    proj, assets = build()
    out = "F1_GrandPrix_Racer.sb3"
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project.json", json.dumps(proj, ensure_ascii=True))
        for fn, data in assets.items():
            zf.writestr(fn, data)
    mb = os.path.getsize(out)/1024/1024
    print(f"Created: {out} ({mb:.1f} MB)")
    print(f"Sprites: Player, Enemy1-3, FinishLine, FuelItem, TrafficLight")
    print(f"\nTrack: Oval circuit with curves")
    print(f"Controls: ↑ accelerate, ← → steer")
    print(f"Goal: Complete 3 laps!")

if __name__ == "__main__":
    main()

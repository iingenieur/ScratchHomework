"""
Super Mario: Save Princess Peach!
Intro + 3 Stages + Ending
Stage 1: Platforming (stairs + flag)
Stage 2: Turtle dodge (jump over rushing turtles)
Stage 3: Boss fight (fireball vs Bowser)
5 hearts life system
"""

import json, zipfile, hashlib, uuid, os, struct, math

def uid(): return uuid.uuid4().hex[:20]

class BB:
    def __init__(self):
        self.blocks = {}
    def _add(self, op, inputs=None, fields=None, top=False, shadow=False, mutation=None):
        bid = uid()
        b = {"opcode":op,"next":None,"parent":None,"inputs":inputs or {},"fields":fields or {},
             "shadow":shadow,"topLevel":top}
        if top: b["x"],b["y"]=0,0
        if mutation: b["mutation"]=mutation
        self.blocks[bid]=b; return bid
    def _p(self,c,p):
        if c and c in self.blocks:
            self.blocks[c]["parent"]=p;self.blocks[c]["topLevel"]=False
            self.blocks[c].pop("x",None);self.blocks[c].pop("y",None)
    def chain(self,ids):
        for i in range(len(ids)):
            if i<len(ids)-1: self.blocks[ids[i]]["next"]=ids[i+1]
            if i>0: self.blocks[ids[i]]["parent"]=ids[i-1];self.blocks[ids[i]]["topLevel"]=False;self.blocks[ids[i]].pop("x",None);self.blocks[ids[i]].pop("y",None)
        if ids and self.blocks[ids[0]]["parent"] is None:
            self.blocks[ids[0]]["topLevel"]=True;self.blocks[ids[0]].setdefault("x",0);self.blocks[ids[0]].setdefault("y",0)
    def flag(self): return self._add("event_whenflagclicked",top=True)
    def key_hat(self,k): return self._add("event_whenkeypressed",fields={"KEY_OPTION":[k,None]},top=True)
    def bcast_hat(self,n,i): return self._add("event_whenbroadcastreceived",fields={"BROADCAST_OPTION":[n,i]},top=True)
    def forever(self,s): b=self._add("control_forever",inputs={"SUBSTACK":[2,s]});self._p(s,b);return b
    def if_then(self,c,s):
        inp={"CONDITION":[2,c]};
        if s: inp["SUBSTACK"]=[2,s]
        b=self._add("control_if",inputs=inp);self._p(c,b);self._p(s,b);return b
    def wait(self,s): return self._add("control_wait",inputs={"DURATION":[1,[5,str(s)]]})
    def stop_all(self): return self._add("control_stop",fields={"STOP_OPTION":["all",None]},mutation={"tagName":"mutation","children":[],"hasnext":"false"})
    def goto(self,x,y): return self._add("motion_gotoxy",inputs={"X":[1,[4,str(x)]],"Y":[1,[4,str(y)]]})
    def glide(self,s,x,y): return self._add("motion_glidesecstoxy",inputs={"SECS":[1,[4,str(s)]],"X":[1,[4,str(x)]],"Y":[1,[4,str(y)]]})
    def set_x(self,v): return self._add("motion_setx",inputs={"X":[1,[4,str(v)]]})
    def set_y(self,v): return self._add("motion_sety",inputs={"Y":[1,[4,str(v)]]})
    def change_x(self,v): return self._add("motion_changexby",inputs={"DX":[1,[4,str(v)]]})
    def change_y(self,v): return self._add("motion_changeyby",inputs={"DY":[1,[4,str(v)]]})
    def change_y_var(self,n,i):
        vr=self.var_ref(n,i);b=self._add("motion_changeyby",inputs={"DY":[3,vr,[4,"0"]]});self._p(vr,b);return b
    def move(self,s): return self._add("motion_movesteps",inputs={"STEPS":[1,[4,str(s)]]})
    def point_dir(self,d): return self._add("motion_pointindirection",inputs={"DIRECTION":[1,[4,str(d)]]})
    def show(self): return self._add("looks_show")
    def hide(self): return self._add("looks_hide")
    def costume(self,n): return self._add("looks_switchcostumeto",inputs={"COSTUME":[1,[10,n]]})
    def backdrop(self,n): return self._add("looks_switchbackdropto",inputs={"BACKDROP":[1,[10,n]]})
    def set_size(self,p): return self._add("looks_setsizeto",inputs={"SIZE":[1,[4,str(p)]]})
    def say(self,m): return self._add("looks_say",inputs={"MESSAGE":[1,[10,str(m)]]})
    def say_for(self,m,s): return self._add("looks_sayforsecs",inputs={"MESSAGE":[1,[10,str(m)]],"SECS":[1,[4,str(s)]]})
    def say_nothing(self): return self._add("looks_say",inputs={"MESSAGE":[1,[10,""]]})
    def play_sound(self,n):
        m=self._add("sound_sounds_menu",fields={"SOUND_MENU":[n,None]},shadow=True)
        b=self._add("sound_play",inputs={"SOUND_MENU":[1,m]});self._p(m,b);return b
    def stop_sounds(self): return self._add("sound_stopallsounds")
    def key_pressed(self,k):
        m=self._add("sensing_keyoptions",fields={"KEY_OPTION":[k,None]},shadow=True)
        b=self._add("sensing_keypressed",inputs={"KEY_OPTION":[1,m]});self._p(m,b);return b
    def touching(self,n):
        m=self._add("sensing_touchingobjectmenu",fields={"TOUCHINGOBJECTMENU":[n,None]},shadow=True)
        b=self._add("sensing_touchingobject",inputs={"TOUCHINGOBJECTMENU":[1,m]});self._p(m,b);return b
    def set_var(self,n,i,v): return self._add("data_setvariableto",fields={"VARIABLE":[n,i]},inputs={"VALUE":[1,[10,str(v)]]})
    def change_var(self,n,i,v): return self._add("data_changevariableby",fields={"VARIABLE":[n,i]},inputs={"VALUE":[1,[4,str(v)]]})
    def var_ref(self,n,i): return self._add("data_variable",fields={"VARIABLE":[n,i]})
    def eq_var(self,n,i,v):
        vr=self.var_ref(n,i);b=self._add("operator_equals",inputs={"OPERAND1":[3,vr,[10,""]],"OPERAND2":[1,[10,str(v)]]});self._p(vr,b);return b
    def lt_var(self,n,i,v):
        vr=self.var_ref(n,i);b=self._add("operator_lt",inputs={"OPERAND1":[3,vr,[10,""]],"OPERAND2":[1,[10,str(v)]]});self._p(vr,b);return b
    def gt_var(self,n,i,v):
        vr=self.var_ref(n,i);b=self._add("operator_gt",inputs={"OPERAND1":[3,vr,[10,""]],"OPERAND2":[1,[10,str(v)]]});self._p(vr,b);return b
    def op_and(self,a,b2):
        b=self._add("operator_and",inputs={"OPERAND1":[2,a],"OPERAND2":[2,b2]});self._p(a,b);self._p(b2,b);return b
    def op_not(self,a): b=self._add("operator_not",inputs={"OPERAND":[2,a]});self._p(a,b);return b
    def lt_ypos(self,v):
        yp=self._add("motion_yposition");b=self._add("operator_lt",inputs={"OPERAND1":[3,yp,[10,""]],"OPERAND2":[1,[10,str(v)]]});self._p(yp,b);return b
    def broadcast(self,n,i): return self._add("event_broadcast",inputs={"BROADCAST_INPUT":[1,[11,n,i]]})
    def broadcast_wait(self,n,i): return self._add("event_broadcastandwait",inputs={"BROADCAST_INPUT":[1,[11,n,i]]})

def svg(w,h,c): return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{c}</svg>'

def gen_beep(f=800,d=0.15,sr=22050):
    n=int(sr*d);raw=b''.join(struct.pack('<h',max(-32768,min(32767,int(16000*math.sin(2*math.pi*f*i/sr)*(1-i/n*0.5))))) for i in range(n))
    w=bytearray(b'RIFF');w.extend(struct.pack('<I',36+len(raw)));w.extend(b'WAVEfmt ');w.extend(struct.pack('<IHHIIHH',16,1,1,sr,sr*2,2,16));w.extend(b'data');w.extend(struct.pack('<I',len(raw)));w.extend(raw);return bytes(w)

# ==================== CHARACTERS ====================
def svg_mario(facing="right"):
    mirror = 'transform="translate(36,0) scale(-1,1)"' if facing=="left" else ''
    return svg(36, 44, f'<g {mirror}><rect x="6" y="0" width="24" height="6" rx="3" fill="#E02020"/><rect x="2" y="3" width="14" height="5" rx="2" fill="#E02020"/><text x="20" y="5" font-size="5" font-weight="bold" fill="#FFF">M</text><rect x="4" y="6" width="6" height="4" rx="1" fill="#4A2800"/><rect x="6" y="6" width="22" height="14" rx="3" fill="#FDBCB4"/><ellipse cx="22" cy="12" rx="3" ry="3.5" fill="#FFF"/><ellipse cx="23" cy="12" rx="1.5" ry="2" fill="#1565C0"/><circle cx="23" cy="11.5" r="0.8" fill="#000"/><ellipse cx="26" cy="14" rx="3" ry="2" fill="#FDBCB4"/><path d="M16,17 Q20,20 28,17" stroke="#4A2800" stroke-width="2.5" fill="none"/><rect x="6" y="20" width="24" height="12" rx="2" fill="#2040E0"/><rect x="2" y="20" width="8" height="10" rx="2" fill="#E02020"/><rect x="26" y="20" width="8" height="10" rx="2" fill="#E02020"/><circle cx="4" cy="31" r="3" fill="#FFF"/><circle cx="32" cy="31" r="3" fill="#FFF"/><circle cx="12" cy="24" r="1.5" fill="#FFD700"/><circle cx="24" cy="24" r="1.5" fill="#FFD700"/><rect x="8" y="32" width="8" height="8" rx="1" fill="#2040E0"/><rect x="20" y="32" width="8" height="8" rx="1" fill="#2040E0"/><rect x="5" y="38" width="12" height="6" rx="3" fill="#8B4513"/><rect x="19" y="38" width="12" height="6" rx="3" fill="#8B4513"/></g>')

def svg_peach():
    return svg(30, 48, '<polygon points="8,6 10,0 12,4 15,0 17,4 20,0 22,6" fill="#FFD700"/><rect x="8" y="5" width="14" height="4" rx="1" fill="#FFD700"/><circle cx="15" cy="4" r="2" fill="#E02020"/><ellipse cx="15" cy="14" rx="10" ry="8" fill="#FFD54F"/><rect x="5" y="14" width="4" height="12" rx="2" fill="#FFD54F"/><rect x="21" y="14" width="4" height="12" rx="2" fill="#FFD54F"/><ellipse cx="15" cy="15" rx="7" ry="7" fill="#FDBCB4"/><ellipse cx="12" cy="14" rx="2" ry="2.5" fill="#1565C0"/><ellipse cx="18" cy="14" rx="2" ry="2.5" fill="#1565C0"/><ellipse cx="15" cy="19" rx="2" ry="1" fill="#E57373"/><path d="M8,22 L5,46 Q15,50 25,46 L22,22 Z" fill="#F48FB1"/><rect x="8" y="22" width="14" height="8" rx="2" fill="#EC407A"/><circle cx="15" cy="25" r="2" fill="#1565C0"/><rect x="3" y="24" width="5" height="8" rx="2" fill="#FFF"/><rect x="22" y="24" width="5" height="8" rx="2" fill="#FFF"/>')

def svg_bowser():
    return svg(48, 50, '<ellipse cx="28" cy="26" rx="18" ry="16" fill="#2E7D32"/><ellipse cx="28" cy="24" rx="14" ry="12" fill="#388E3C"/><polygon points="18,12 20,4 22,12" fill="#FFF9C4"/><polygon points="25,10 27,2 29,10" fill="#FFF9C4"/><polygon points="32,12 34,4 36,12" fill="#FFF9C4"/><ellipse cx="12" cy="18" rx="12" ry="12" fill="#FFCC02"/><ellipse cx="8" cy="8" rx="8" ry="6" fill="#E65100"/><polygon points="3,10 0,0 8,7" fill="#FFF9C4"/><polygon points="17,10 20,0 12,7" fill="#FFF9C4"/><line x1="4" y1="13" x2="10" y2="11" stroke="#4A2800" stroke-width="2"/><line x1="14" y1="11" x2="20" y2="13" stroke="#4A2800" stroke-width="2"/><ellipse cx="8" cy="16" rx="3" ry="3.5" fill="#FFF"/><circle cx="9" cy="16" r="2" fill="#E02020"/><ellipse cx="16" cy="16" rx="3" ry="3.5" fill="#FFF"/><circle cx="17" cy="16" r="2" fill="#E02020"/><ellipse cx="12" cy="22" rx="6" ry="4" fill="#E8B830"/><path d="M5,26 Q12,32 19,26" fill="#B71C1C"/><polygon points="7,26 8,29 9,26" fill="#FFF"/><polygon points="16,26 17,29 18,26" fill="#FFF"/><ellipse cx="28" cy="34" rx="12" ry="10" fill="#FFCC02"/><ellipse cx="18" cy="47" rx="7" ry="3" fill="#FFCC02"/><ellipse cx="36" cy="47" rx="7" ry="3" fill="#FFCC02"/>')

def svg_turtle():
    """Koopa turtle walking"""
    return svg(30, 30, '<ellipse cx="15" cy="14" rx="13" ry="12" fill="#2E7D32"/><ellipse cx="15" cy="12" rx="9" ry="8" fill="#4CAF50"/><circle cx="7" cy="14" r="6" fill="#8BC34A"/><circle cx="5" cy="12" r="2" fill="#FFF"/><circle cx="5" cy="12" r="1" fill="#000"/><ellipse cx="10" cy="26" rx="4" ry="3" fill="#8BC34A"/><ellipse cx="20" cy="26" rx="4" ry="3" fill="#8BC34A"/>')

def svg_shell():
    """Spinning Koopa shell"""
    return svg(26, 20, '<ellipse cx="13" cy="10" rx="12" ry="9" fill="#2E7D32" stroke="#1B5E20" stroke-width="1"/><ellipse cx="13" cy="8" rx="8" ry="6" fill="#4CAF50"/><line x1="7" y1="6" x2="7" y2="14" stroke="#1B5E20" stroke-width="1"/><line x1="13" y1="4" x2="13" y2="14" stroke="#1B5E20" stroke-width="1"/><line x1="19" y1="6" x2="19" y2="14" stroke="#1B5E20" stroke-width="1"/><ellipse cx="13" cy="15" rx="10" ry="4" fill="#FFCC02"/>')

def svg_fireball():
    return svg(16, 16, '<circle cx="8" cy="8" r="7" fill="#FF6600"/><circle cx="8" cy="8" r="4" fill="#FFCC00"/><circle cx="8" cy="8" r="2" fill="#FFF"/>')

def svg_flag():
    return svg(20, 50, '<rect x="9" y="0" width="2" height="50" fill="#888"/><polygon points="11,2 11,18 1,10" fill="#27AE60"/><circle cx="10" cy="2" r="2" fill="#FFD700"/>')

def svg_ground():
    bricks=""
    for x in range(0,480,24):
        for y in range(0,30,15):
            c="#C46B2E" if (x//24+y//15)%2==0 else "#A0522D"
            bricks+=f'<rect x="{x}" y="{y}" width="23" height="14" fill="{c}" stroke="#8B4513" stroke-width="1"/>'
    return svg(480, 30, bricks)

def svg_platform():
    return svg(70, 14, '<rect width="70" height="14" rx="2" fill="#C46B2E" stroke="#8B4513" stroke-width="1"/><rect x="0" y="0" width="70" height="7" fill="#D4824A"/>')

def svg_hearts(n):
    hearts=""
    for i in range(5):
        c="#E02020" if i<n else "#555"
        x=i*22+2
        hearts+=f'<path d="M{x+10},{8} C{x+10},4 {x+4},2 {x+4},6 C{x+4},4 {x},6 {x+4},12 L{x+10},18 L{x+16},12 C{x+20},6 {x+16},4 {x+16},6 C{x+16},2 {x+10},4 {x+10},8 Z" fill="{c}"/>'
    return svg(112, 20, hearts)

# Backdrops
def bg_intro():
    return svg(480,360,'<rect width="480" height="360" fill="#87CEEB"/><rect x="0" y="280" width="480" height="80" fill="#4CAF50"/><rect x="0" y="310" width="480" height="50" fill="#8B4513"/><ellipse cx="100" cy="60" rx="40" ry="20" fill="white" opacity="0.7"/><ellipse cx="350" cy="50" rx="50" ry="22" fill="white" opacity="0.6"/><text x="240" y="30" text-anchor="middle" font-size="14" fill="#333">어느 평화로운 날...</text>')

def bg_stage1():
    return svg(480,360,'<defs><linearGradient id="s" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#87CEEB"/><stop offset="100%" stop-color="#E0F0FF"/></linearGradient></defs><rect width="480" height="360" fill="url(#s)"/><ellipse cx="80" cy="60" rx="40" ry="20" fill="white" opacity="0.8"/><ellipse cx="300" cy="40" rx="50" ry="18" fill="white" opacity="0.6"/><rect x="0" y="310" width="480" height="50" fill="#8B4513"/><text x="240" y="20" text-anchor="middle" font-size="12" fill="#555">STAGE 1 - 계단을 넘어라!</text>')

def bg_stage2():
    return svg(480,360,'<rect width="480" height="360" fill="#1a237e"/><rect x="0" y="310" width="480" height="50" fill="#4A2800"/><circle cx="400" cy="60" r="30" fill="#FFD700" opacity="0.3"/><text x="240" y="20" text-anchor="middle" font-size="12" fill="#DDD">STAGE 2 - 거북이를 피해라!</text>')

def bg_stage3():
    return svg(480,360,'<rect width="480" height="360" fill="#B71C1C"/><rect x="0" y="310" width="480" height="50" fill="#333"/><rect x="0" y="0" width="480" height="40" fill="#222"/><text x="240" y="20" text-anchor="middle" font-size="12" fill="#FFD700">STAGE 3 - 쿠파를 물리쳐라!</text><rect x="350" y="200" width="130" height="160" fill="#333" rx="5"/><rect x="360" y="210" width="50" height="60" rx="3" fill="#555"/><rect x="420" y="240" width="30" height="30" rx="3" fill="#555"/>')

def bg_gameover():
    return svg(480,360,'<rect width="480" height="360" fill="#1a1a1a"/><text x="240" y="140" text-anchor="middle" font-size="48" font-weight="bold" fill="#E02020">GAME OVER</text><text x="240" y="200" text-anchor="middle" font-size="16" fill="#AAA">SPACE 키를 눌러 재시작</text>')

def bg_victory():
    return svg(480,360,'<rect width="480" height="360" fill="#1565C0"/><text x="240" y="80" text-anchor="middle" font-size="16" fill="#FFF">피치 공주를 구했습니다!</text><text x="240" y="140" text-anchor="middle" font-size="48" font-weight="bold" fill="#FFD700">VICTORY!</text><text x="240" y="200" text-anchor="middle" font-size="20" fill="#FFF">Thank you, Mario!</text><text x="240" y="270" text-anchor="middle" font-size="14" fill="#DDD">SPACE 키를 눌러 재시작</text>')


def build():
    BR={k:uid() for k in ["인트로","스테이지1","스테이지2","스테이지3","게임오버","승리","리셋"]}
    V={k:uid() for k in ["하트","점수","게임상태","속도Y","점프중","쿠파HP"]}
    assets={}
    SPRITE_DIR = os.path.join(os.path.dirname(__file__), "sprites")
    def reg(name,svg_str,cx,cy):
        d=svg_str.encode("utf-8");md5=hashlib.md5(d).hexdigest();assets[f"{md5}.svg"]=d
        return {"name":name,"assetId":md5,"md5ext":f"{md5}.svg","dataFormat":"svg","rotationCenterX":cx,"rotationCenterY":cy}
    def reg_png(name, filename, cx=None, cy=None):
        """Register a PNG file as a costume"""
        path = os.path.join(SPRITE_DIR, filename)
        with open(path, "rb") as f: d = f.read()
        md5=hashlib.md5(d).hexdigest();assets[f"{md5}.png"]=d
        # Auto-center if not specified
        from PIL import Image; img=Image.open(path)
        if cx is None: cx = img.width // 2
        if cy is None: cy = img.height // 2
        return {"name":name,"assetId":md5,"md5ext":f"{md5}.png","dataFormat":"png",
                "rotationCenterX":cx,"rotationCenterY":cy,"bitmapResolution":1}
    def reg_snd(name,data):
        md5=hashlib.md5(data).hexdigest();assets[f"{md5}.wav"]=data
        return {"name":name,"assetId":md5,"md5ext":f"{md5}.wav","dataFormat":"wav","rate":22050,"sampleCount":0}

    snd_jump=reg_snd("Jump",gen_beep(600,0.1)); snd_coin=reg_snd("Coin",gen_beep(1200,0.08))
    snd_hit=reg_snd("Hit",gen_beep(200,0.2)); snd_win=reg_snd("Win",gen_beep(900,0.3))
    snd_fire=reg_snd("Fire",gen_beep(400,0.1))

    gvars={V[k]:[k,v] for k,v in [("하트",5),("점수",0),("게임상태","start"),("속도Y",0),("점프중",0),("쿠파HP",3)]}
    GY=-130 # ground Y

    # ==================== STAGE (backdrops + game logic) ====================
    b=BB()
    f0=b.flag()
    init=[b.backdrop("시작화면"),b.set_var("게임상태",V["게임상태"],"start"),b.set_var("하트",V["하트"],5),
          b.set_var("점수",V["점수"],0),b.set_var("속도Y",V["속도Y"],0),b.set_var("점프중",V["점프중"],0),
          b.set_var("쿠파HP",V["쿠파HP"],3),b.stop_sounds()]
    b.chain([f0]+init)

    # Space to start
    sp=b.key_hat("space")
    c1=b.eq_var("게임상태",V["게임상태"],"start")
    s1=[b.set_var("게임상태",V["게임상태"],"intro"),b.backdrop("인트로"),b.broadcast("인트로",BR["인트로"])]
    b.chain(s1); if1=b.if_then(c1,s1[0])
    # Space to restart from gameover
    c2=b.eq_var("게임상태",V["게임상태"],"gameover")
    s2=[b.set_var("하트",V["하트"],5),b.set_var("점수",V["점수"],0),b.set_var("쿠파HP",V["쿠파HP"],3),
        b.set_var("게임상태",V["게임상태"],"intro"),b.backdrop("인트로"),b.broadcast("인트로",BR["인트로"])]
    b.chain(s2); if2=b.if_then(c2,s2[0])
    c3=b.eq_var("게임상태",V["게임상태"],"win")
    s3=[b.set_var("하트",V["하트"],5),b.set_var("점수",V["점수"],0),b.set_var("쿠파HP",V["쿠파HP"],3),
        b.set_var("게임상태",V["게임상태"],"intro"),b.backdrop("인트로"),b.broadcast("인트로",BR["인트로"])]
    b.chain(s3); if3=b.if_then(c3,s3[0])
    b.chain([sp,if1,if2,if3])

    stage_target={
        "isStage":True,"name":"Stage","variables":gvars,"lists":{},"comments":{},
        "broadcasts":{v:k for k,v in BR.items()},
        "blocks":b.blocks,"currentCostume":0,
        "costumes":[reg("시작화면",bg_intro(),240,180),reg("인트로",bg_intro(),240,180),
                    reg("스테이지1",bg_stage1(),240,180),reg("스테이지2",bg_stage2(),240,180),
                    reg("스테이지3",bg_stage3(),240,180),reg("게임오버",bg_gameover(),240,180),
                    reg("승리",bg_victory(),240,180)],
        "sounds":[],"volume":100,"layerOrder":0,"tempo":60,
        "videoTransparency":50,"videoState":"off","textToSpeechLanguage":None
    }

    # ==================== MARIO ====================
    m=BB()
    mf=m.flag(); m.chain([mf,m.goto(-180,GY),m.set_size(100),m.costume("오른쪽"),m.show()])

    # INTRO: walk with Peach, Bowser appears
    mh_intro=m.bcast_hat("인트로",BR["인트로"])
    intro_m=[m.goto(-220,GY),m.show(),m.costume("오른쪽"),
             m.glide(2,-50,GY), m.say_for("피치, 오늘 날씨가 좋다!",2),
             m.wait(3), # Bowser takes Peach
             m.say_for("피치!!!! 안돼!!",2), m.say_for("꼭 구하러 갈게!",2),
             m.say_nothing(),
             m.set_var("게임상태",V["게임상태"],"stage1"),m.backdrop("스테이지1"),
             m.broadcast("스테이지1",BR["스테이지1"])]
    m.chain([mh_intro]+intro_m)

    # STAGE 1: platforming with gravity
    mh1=m.bcast_hat("스테이지1",BR["스테이지1"])
    m1_init=[m.goto(-200,GY),m.set_var("속도Y",V["속도Y"],0),m.set_var("점프중",V["점프중"],0)]
    # Physics loop
    grav=m.change_var("속도Y",V["속도Y"],-1)
    apply_v=m.change_y_var("속도Y",V["속도Y"])
    # Ground snap
    cg=m.lt_ypos(GY)
    gs=[m.set_y(GY),m.set_var("속도Y",V["속도Y"],0),m.set_var("점프중",V["점프중"],0)]
    m.chain(gs); ifg=m.if_then(cg,gs[0])
    # Platform checks
    def plat_check(pn):
        tp=m.touching(pn);fl=m.lt_var("속도Y",V["속도Y"],0);ca=m.op_and(tp,fl)
        sn=[m.change_y(6),m.set_var("속도Y",V["속도Y"],0),m.set_var("점프중",V["점프중"],0)]
        m.chain(sn); return m.if_then(ca,sn[0])
    ip1=plat_check("Plat1");ip2=plat_check("Plat2");ip3=plat_check("Plat3")
    # Movement
    kr=m.key_pressed("right arrow");mvr=[m.change_x(5),m.costume("오른쪽")];m.chain(mvr);ifr=m.if_then(kr,mvr[0])
    kl=m.key_pressed("left arrow");mvl=[m.change_x(-5),m.costume("왼쪽")];m.chain(mvl);ifl=m.if_then(kl,mvl[0])
    # Jump
    kj=m.key_pressed("space");cnj=m.eq_var("점프중",V["점프중"],0);cj=m.op_and(kj,cnj)
    jb=[m.set_var("속도Y",V["속도Y"],13),m.set_var("점프중",V["점프중"],1),m.play_sound("Jump")]
    m.chain(jb); ifj=m.if_then(cj,jb[0])
    # Flag check (stage 1 clear)
    tfl=m.touching("Flag")
    s1_clear=[m.say_for("스테이지 클리어!",1),m.set_var("게임상태",V["게임상태"],"stage2"),
              m.backdrop("스테이지2"),m.broadcast("스테이지2",BR["스테이지2"])]
    m.chain(s1_clear); iff=m.if_then(tfl,s1_clear[0])
    # Stage 1 turtle collision
    def s1_turtle_hit(tn):
        tt=m.touching(tn)
        hit=[m.change_var("하트",V["하트"],-1),m.play_sound("Hit"),m.set_y(GY+30),m.set_var("속도Y",V["속도Y"],8),m.wait(0.8)]
        m.chain(hit);return m.if_then(tt,hit[0])
    is1a=s1_turtle_hit("TurtleS1a");is1b=s1_turtle_hit("TurtleS1b")
    # Heart check stage 1
    ch1=m.lt_var("하트",V["하트"],1)
    die1=[m.set_var("게임상태",V["게임상태"],"gameover"),m.backdrop("게임오버"),m.stop_all()]
    m.chain(die1);ifd1=m.if_then(ch1,die1[0])
    m.chain([grav,apply_v,ifg,ip1,ip2,ip3,ifr,ifl,ifj,is1a,is1b,ifd1,iff])
    cs1=m.eq_var("게임상태",V["게임상태"],"stage1")
    ifs1=m.if_then(cs1,grav); fs1=m.forever(ifs1)
    m.chain([mh1]+m1_init+[fs1])

    # STAGE 2: dodge turtles (same physics, no platforms)
    mh2=m.bcast_hat("스테이지2",BR["스테이지2"])
    m2_init=[m.goto(-150,GY),m.set_var("속도Y",V["속도Y"],0),m.set_var("점프중",V["점프중"],0)]
    grav2=m.change_var("속도Y",V["속도Y"],-1)
    av2=m.change_y_var("속도Y",V["속도Y"])
    cg2=m.lt_ypos(GY);gs2=[m.set_y(GY),m.set_var("속도Y",V["속도Y"],0),m.set_var("점프중",V["점프중"],0)]
    m.chain(gs2);ifg2=m.if_then(cg2,gs2[0])
    # Left/right movement in stage 2
    kr2=m.key_pressed("right arrow");mvr2=[m.change_x(5),m.costume("오른쪽")];m.chain(mvr2);ifr2=m.if_then(kr2,mvr2[0])
    kl2=m.key_pressed("left arrow");mvl2=[m.change_x(-5),m.costume("왼쪽")];m.chain(mvl2);ifl2=m.if_then(kl2,mvl2[0])
    # Jump
    kj2=m.key_pressed("space");cnj2=m.eq_var("점프중",V["점프중"],0);cj2=m.op_and(kj2,cnj2)
    jb2=[m.set_var("속도Y",V["속도Y"],14),m.set_var("점프중",V["점프중"],1),m.play_sound("Jump")]
    m.chain(jb2);ifj2=m.if_then(cj2,jb2[0])
    # Turtle collision (with larger bounce to break contact)
    def turtle_hit(tn):
        tt=m.touching(tn)
        hit=[m.change_var("하트",V["하트"],-1),m.play_sound("Hit"),
             m.set_y(GY+30),m.set_var("속도Y",V["속도Y"],8),  # bounce up to break contact
             m.wait(0.8)]
        m.chain(hit);return m.if_then(tt,hit[0])
    it1=turtle_hit("Turtle1");it2=turtle_hit("Turtle2");it3=turtle_hit("Turtle3")
    # Stage 1 turtles also hurt in stage 2 area
    it4=turtle_hit("TurtleS1a");it5=turtle_hit("TurtleS1b")
    # Heart check
    ch0=m.lt_var("하트",V["하트"],1)
    die2=[m.set_var("게임상태",V["게임상태"],"gameover"),m.backdrop("게임오버"),m.stop_all()]
    m.chain(die2);ifd2=m.if_then(ch0,die2[0])
    m.chain([grav2,av2,ifg2,ifr2,ifl2,ifj2,it1,it2,it3,ifd2])
    cs2=m.eq_var("게임상태",V["게임상태"],"stage2")
    ifs2=m.if_then(cs2,grav2);fs2=m.forever(ifs2)
    m.chain([mh2]+m2_init+[fs2])

    # STAGE 3: boss fight (same physics + fireball)
    mh3=m.bcast_hat("스테이지3",BR["스테이지3"])
    m3_init=[m.goto(-150,GY),m.costume("파이어"),m.set_var("속도Y",V["속도Y"],0),m.set_var("점프중",V["점프중"],0)]
    grav3=m.change_var("속도Y",V["속도Y"],-1);av3=m.change_y_var("속도Y",V["속도Y"])
    cg3=m.lt_ypos(GY);gs3=[m.set_y(GY),m.set_var("속도Y",V["속도Y"],0),m.set_var("점프중",V["점프중"],0)]
    m.chain(gs3);ifg3=m.if_then(cg3,gs3[0])
    kr3=m.key_pressed("right arrow");mvr3=m.change_x(4);ifr3=m.if_then(kr3,mvr3)
    kl3=m.key_pressed("left arrow");mvl3=m.change_x(-4);ifl3=m.if_then(kl3,mvl3)
    kj3=m.key_pressed("space");cnj3=m.eq_var("점프중",V["점프중"],0);cj3=m.op_and(kj3,cnj3)
    jb3=[m.set_var("속도Y",V["속도Y"],13),m.set_var("점프중",V["점프중"],1),m.play_sound("Jump")]
    m.chain(jb3);ifj3=m.if_then(cj3,jb3[0])
    # Bowser touch = lose heart
    tb3=m.touching("Bowser")
    bh3=[m.change_var("하트",V["하트"],-1),m.play_sound("Hit"),m.goto(-150,GY),m.wait(0.5)]
    m.chain(bh3);ifb3=m.if_then(tb3,bh3[0])
    ch3=m.lt_var("하트",V["하트"],1)
    die3=[m.set_var("게임상태",V["게임상태"],"gameover"),m.backdrop("게임오버"),m.stop_all()]
    m.chain(die3);ifd3=m.if_then(ch3,die3[0])
    # Win check
    cwin=m.lt_var("쿠파HP",V["쿠파HP"],1)
    win3=[m.say_for("피치 공주를 구했다!",2),m.set_var("게임상태",V["게임상태"],"win"),m.backdrop("승리"),m.stop_all()]
    m.chain(win3);ifw3=m.if_then(cwin,win3[0])
    m.chain([grav3,av3,ifg3,ifr3,ifl3,ifj3,ifb3,ifd3,ifw3])
    cs3=m.eq_var("게임상태",V["게임상태"],"stage3")
    ifs3=m.if_then(cs3,grav3);fs3=m.forever(ifs3)
    m.chain([mh3]+m3_init+[fs3])

    mario={"isStage":False,"name":"Mario","variables":{},"lists":{},"broadcasts":{},"comments":{},
        "blocks":m.blocks,"currentCostume":0,
        "costumes":[reg_png("오른쪽","mario_right.png"),reg_png("왼쪽","mario_left.png"),
                    reg_png("달리기","mario_run.png"),reg_png("점프","mario_jump.png"),
                    reg_png("파이어","mario_fire.png")],
        "sounds":[snd_jump,snd_hit,snd_win],"volume":100,"layerOrder":8,"visible":True,
        "x":-180,"y":GY,"size":100,"direction":90,"draggable":False,"rotationStyle":"don't rotate"}

    # ==================== PEACH ====================
    p=BB()
    pf=p.flag();p.chain([pf,p.goto(-30,GY),p.set_size(90),p.show()])
    # Intro: walk, then get kidnapped
    ph=p.bcast_hat("인트로",BR["인트로"])
    pi=[p.goto(-200,GY),p.show(),p.glide(2,-30,GY),p.say_for("네, 정말 좋아요!",2),
        p.wait(1),p.say_for("으악! 쿠파!!",1),
        p.glide(1,100,GY+60), # grabbed by Bowser
        p.glide(1,250,200), # carried away
        p.hide()]
    p.chain([ph]+pi)
    # Stage 3: appear when Bowser defeated
    ph3=p.bcast_hat("스테이지3",BR["스테이지3"])
    pi3=[p.goto(180,GY),p.hide()]
    p.chain([ph3]+pi3)
    # Show when Bowser HP reaches 0
    ph3b=p.flag()
    cw3=p.lt_var("쿠파HP",V["쿠파HP"],1)
    pw3=[p.show(),p.say("고마워요 마리오!")]
    p.chain(pw3);ifw=p.if_then(cw3,pw3[0])
    pw=p.wait(0.5);p.chain([ifw,pw])
    cs3p=p.eq_var("게임상태",V["게임상태"],"stage3")
    ifs3p=p.if_then(cs3p,ifw);fps=p.forever(ifs3p)
    p.chain([ph3b,fps])

    peach={"isStage":False,"name":"Peach","variables":{},"lists":{},"broadcasts":{},"comments":{},
        "blocks":p.blocks,"currentCostume":0,"costumes":[reg_png("peach","peach.png")],
        "sounds":[],"volume":100,"layerOrder":7,"visible":True,
        "x":-30,"y":GY,"size":90,"direction":90,"draggable":False,"rotationStyle":"don't rotate"}

    # ==================== BOWSER ====================
    bw=BB()
    bwf=bw.flag();bw.chain([bwf,bw.hide()])
    # Intro: appear and kidnap Peach
    bwh=bw.bcast_hat("인트로",BR["인트로"])
    bwi=[bw.goto(200,200),bw.set_size(100),bw.show(),
         bw.wait(4), # wait for Mario+Peach to talk
         bw.glide(1,50,GY),bw.say_for("하하하! 피치는 내꺼다!",2),
         bw.glide(1,250,200),bw.hide()]
    bw.chain([bwh]+bwi)
    # Stage 3: boss fight patrol
    bwh3=bw.bcast_hat("스테이지3",BR["스테이지3"])
    bwi3=[bw.goto(120,GY),bw.show(),bw.set_var("쿠파HP",V["쿠파HP"],3)]
    bwgl=bw.glide(1.5,60,GY);bwgr=bw.glide(1.5,180,GY)
    bw.chain([bwgl,bwgr]);bwf3=bw.forever(bwgl)
    bw.chain([bwh3]+bwi3+[bwf3])
    # Hide when defeated
    bwh4=bw.flag()
    cd=bw.lt_var("쿠파HP",V["쿠파HP"],1)
    bwd=[bw.say_for("으아아악!!",1),bw.hide()]
    bw.chain(bwd);ifbd=bw.if_then(cd,bwd[0])
    bww=bw.wait(0.3);bw.chain([ifbd,bww])
    cs3b=bw.eq_var("게임상태",V["게임상태"],"stage3")
    ifs3b=bw.if_then(cs3b,ifbd);fbw=bw.forever(ifs3b)
    bw.chain([bwh4,fbw])

    bowser={"isStage":False,"name":"Bowser","variables":{},"lists":{},"broadcasts":{},"comments":{},
        "blocks":bw.blocks,"currentCostume":0,"costumes":[reg_png("bowser","bowser.png")],
        "sounds":[snd_hit],"volume":100,"layerOrder":6,"visible":False,
        "x":200,"y":200,"size":100,"direction":90,"draggable":False,"rotationStyle":"don't rotate"}

    # ==================== GROUND ====================
    g=BB();gf=g.flag();g.chain([gf,g.goto(0,GY-15),g.show()])
    ground={"isStage":False,"name":"Ground","variables":{},"lists":{},"broadcasts":{},"comments":{},
        "blocks":g.blocks,"currentCostume":0,"costumes":[reg("ground",svg_ground(),240,15)],
        "sounds":[],"volume":100,"layerOrder":1,"visible":True,
        "x":0,"y":GY-15,"size":100,"direction":90,"draggable":False,"rotationStyle":"don't rotate"}

    # ==================== PLATFORMS (Stage 1) ====================
    def make_plat(name,x,y):
        p=BB();pf=p.flag();p.chain([pf,p.hide()])
        ph=p.bcast_hat("스테이지1",BR["스테이지1"]);p.chain([ph,p.goto(x,y),p.show()])
        ph2=p.bcast_hat("스테이지2",BR["스테이지2"]);p.chain([ph2,p.hide()])
        return {"isStage":False,"name":name,"variables":{},"lists":{},"broadcasts":{},"comments":{},
            "blocks":p.blocks,"currentCostume":0,"costumes":[reg("plat",svg_platform(),35,7,)],
            "sounds":[],"volume":100,"layerOrder":2,"visible":False,
            "x":x,"y":y,"size":100,"direction":90,"draggable":False,"rotationStyle":"don't rotate"}
    plat1=make_plat("Plat1",-60,-70)
    plat2=make_plat("Plat2",50,-10)
    plat3=make_plat("Plat3",150,50)

    # ==================== FLAG (Stage 1 goal + final) ====================
    fl=BB();flf=fl.flag();fl.chain([flf,fl.hide()])
    flh=fl.bcast_hat("스테이지1",BR["스테이지1"]);fl.chain([flh,fl.goto(180,80),fl.show()])
    flh2=fl.bcast_hat("스테이지2",BR["스테이지2"]);fl.chain([flh2,fl.hide()])
    flag_s={"isStage":False,"name":"Flag","variables":{},"lists":{},"broadcasts":{},"comments":{},
        "blocks":fl.blocks,"currentCostume":0,"costumes":[reg("flag",svg_flag(),10,25)],
        "sounds":[snd_win],"volume":100,"layerOrder":3,"visible":False,
        "x":180,"y":80,"size":100,"direction":90,"draggable":False,"rotationStyle":"don't rotate"}

    # ==================== STAGE 1 GROUND TURTLES ====================
    def make_s1_turtle(name, x1, x2):
        """Turtle that patrols back and forth on ground in Stage 1"""
        t=BB();tf=t.flag();t.chain([tf,t.hide()])
        th=t.bcast_hat("스테이지1",BR["스테이지1"])
        ti=[t.goto(x1,GY),t.set_size(100),t.show()]
        tgl=t.glide(2,x2,GY);tgr=t.glide(2,x1,GY)
        t.chain([tgl,tgr]);tfl=t.forever(tgl)
        t.chain([th]+ti+[tfl])
        th2=t.bcast_hat("스테이지2",BR["스테이지2"]);t.chain([th2,t.hide()])
        return {"isStage":False,"name":name,"variables":{},"lists":{},"broadcasts":{},"comments":{},
            "blocks":t.blocks,"currentCostume":0,"costumes":[reg_png("koopa","koopa.png")],
            "sounds":[],"volume":100,"layerOrder":4,"visible":False,
            "x":x1,"y":GY,"size":100,"direction":90,"draggable":False,"rotationStyle":"don't rotate"}
    turtle_s1a=make_s1_turtle("TurtleS1a",-30,40)
    turtle_s1b=make_s1_turtle("TurtleS1b",90,160)

    # ==================== STAGE 2 SHELL TURTLES ====================
    def make_shell(name, speed, start_delay):
        """Koopa shell that rushes from right to left"""
        t=BB();tf=t.flag();t.chain([tf,t.hide()])
        th=t.bcast_hat("스테이지2",BR["스테이지2"])
        ti=[t.goto(260,GY+5),t.set_size(140),t.show(),t.wait(start_delay)]
        tgl=t.glide(speed,-260,GY+5); treset=t.goto(260,GY+5); tw=t.wait(0.3)
        t.chain([tgl,treset,tw]);tfl=t.forever(tgl)
        t.chain([th]+ti+[tfl])
        th3=t.bcast_hat("스테이지3",BR["스테이지3"]);t.chain([th3,t.hide()])
        return {"isStage":False,"name":name,"variables":{},"lists":{},"broadcasts":{},"comments":{},
            "blocks":t.blocks,"currentCostume":0,"costumes":[reg_png("koopa","koopa.png")],
            "sounds":[],"volume":100,"layerOrder":4,"visible":False,
            "x":260,"y":GY+5,"size":140,"direction":90,"draggable":False,"rotationStyle":"don't rotate"}

    turtle1=make_shell("Turtle1",1.8,0)
    turtle2=make_shell("Turtle2",1.5,2.5)
    turtle3=make_shell("Turtle3",1.2,5)

    # Stage 2 timer (auto-advance after 20 seconds)
    s2_timer=BB()
    s2h=s2_timer.bcast_hat("스테이지2",BR["스테이지2"])
    s2t=[s2_timer.wait(20),s2_timer.set_var("게임상태",V["게임상태"],"stage3"),
         s2_timer.backdrop("스테이지3"),s2_timer.broadcast("스테이지3",BR["스테이지3"])]
    s2_timer.chain([s2h]+s2t)
    stage_target["blocks"].update(s2_timer.blocks)

    # ==================== FIREBALL (Stage 3) ====================
    fb=BB();fbf=fb.flag();fb.chain([fbf,fb.hide()])
    # Z key to fire
    fbz=fb.key_hat("z")
    cs3f=fb.eq_var("게임상태",V["게임상태"],"stage3")
    fire=[fb.goto(-130,GY+10),fb.show(),fb.play_sound("Fire"),
          fb.glide(0.5,200,GY+10)]
    # Check if hit Bowser
    tbw=fb.touching("Bowser")
    fhit=[fb.change_var("쿠파HP",V["쿠파HP"],-1),fb.play_sound("Hit")]
    fb.chain(fhit);ifhit=fb.if_then(tbw,fhit[0])
    fb.chain(fire+[ifhit,fb.hide()])
    iffs=fb.if_then(cs3f,fire[0])
    fb.chain([fbz,iffs])

    fireball={"isStage":False,"name":"Fireball","variables":{},"lists":{},"broadcasts":{},"comments":{},
        "blocks":fb.blocks,"currentCostume":0,"costumes":[reg("fire",svg_fireball(),8,8)],
        "sounds":[snd_fire],"volume":100,"layerOrder":5,"visible":False,
        "x":0,"y":0,"size":100,"direction":90,"draggable":False,"rotationStyle":"don't rotate"}

    # ==================== HEARTS DISPLAY ====================
    ht=BB();htf=ht.flag();ht.chain([htf,ht.goto(-160,160),ht.set_size(100),ht.costume("5"),ht.show()])
    # Update hearts display
    hth=ht.flag()
    def heart_check(n):
        cv=ht.eq_var("하트",V["하트"],n);cc=ht.costume(str(n));return ht.if_then(cv,cc)
    ih5=heart_check(5);ih4=heart_check(4);ih3=heart_check(3);ih2=heart_check(2);ih1=heart_check(1);ih0=heart_check(0)
    hw=ht.wait(0.1);ht.chain([ih5,ih4,ih3,ih2,ih1,ih0,hw])
    fht=ht.forever(ih5);ht.chain([hth,fht])

    hearts={"isStage":False,"name":"Hearts","variables":{},"lists":{},"broadcasts":{},"comments":{},
        "blocks":ht.blocks,"currentCostume":0,
        "costumes":[reg("5",svg_hearts(5),56,10),reg("4",svg_hearts(4),56,10),
                    reg("3",svg_hearts(3),56,10),reg("2",svg_hearts(2),56,10),
                    reg("1",svg_hearts(1),56,10),reg("0",svg_hearts(0),56,10)],
        "sounds":[],"volume":100,"layerOrder":10,"visible":True,
        "x":-160,"y":160,"size":100,"direction":90,"draggable":False,"rotationStyle":"don't rotate"}

    # ==================== MONITORS ====================
    monitors=[
        {"id":V["점수"],"mode":"default","opcode":"data_variable","params":{"VARIABLE":"점수"},
         "spriteName":None,"value":0,"width":0,"height":0,"x":350,"y":5,"visible":True,
         "sliderMin":0,"sliderMax":100,"isDiscrete":True},
    ]

    project={
        "targets":[stage_target,mario,peach,bowser,ground,plat1,plat2,plat3,flag_s,
                   turtle_s1a,turtle_s1b,turtle1,turtle2,turtle3,fireball,hearts],
        "monitors":monitors,"extensions":[],
        "meta":{"semver":"3.0.0","vm":"0.2.0","agent":"Mario Adventure v2"}
    }
    return project,assets

def main():
    print("Generating Super Mario: Save Princess Peach!...")
    proj,assets=build()
    out="SuperMario_Platformer.sb3"
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project.json",json.dumps(proj,ensure_ascii=True))
        for fn,data in assets.items(): zf.writestr(fn,data)
    print(f"Created: {out} ({os.path.getsize(out)/1024:.0f} KB)")
    print("\n=== GAME STRUCTURE ===")
    print("INTRO: Mario & Peach walking → Bowser kidnaps Peach")
    print("STAGE 1: Jump across platforms → Reach the flag")
    print("STAGE 2: Dodge rushing turtles for 20 seconds")
    print("STAGE 3: Throw fireballs (Z key) at Bowser × 3 hits")
    print("\nControls: ← → move | SPACE jump | Z fireball (stage 3)")
    print("Lives: 5 hearts")

if __name__=="__main__": main()

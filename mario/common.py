"""
공통 모듈: BB 블록 빌더, SVG/PNG 헬퍼, 사운드 생성
모든 스테이지 생성기에서 import하여 사용
"""

import json, zipfile, hashlib, uuid, os, struct, math

def uid(): return uuid.uuid4().hex[:20]

SPRITE_DIR = os.path.join(os.path.dirname(__file__), "sprites")
GY = -140  # ground Y position


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
    def backdrop_hat(self,n): return self._add("event_whenbackdropswitchesto",fields={"BACKDROP":[n,None]},top=True)
    def forever(self,s): b=self._add("control_forever",inputs={"SUBSTACK":[2,s]});self._p(s,b);return b
    def if_then(self,c,s):
        inp={"CONDITION":[2,c]};
        if s: inp["SUBSTACK"]=[2,s]
        b=self._add("control_if",inputs=inp);self._p(c,b);self._p(s,b);return b
    def repeat_until(self,c,s): b=self._add("control_repeat_until",inputs={"CONDITION":[2,c],"SUBSTACK":[2,s]});self._p(c,b);self._p(s,b);return b
    def wait(self,s): return self._add("control_wait",inputs={"DURATION":[1,[5,str(s)]]})
    def stop_all(self): return self._add("control_stop",fields={"STOP_OPTION":["all",None]},mutation={"tagName":"mutation","children":[],"hasnext":"false"})
    def stop_other(self): return self._add("control_stop",fields={"STOP_OPTION":["other scripts in sprite",None]},mutation={"tagName":"mutation","children":[],"hasnext":"true"})
    def goto(self,x,y): return self._add("motion_gotoxy",inputs={"X":[1,[4,str(x)]],"Y":[1,[4,str(y)]]})
    def glide(self,s,x,y): return self._add("motion_glidesecstoxy",inputs={"SECS":[1,[4,str(s)]],"X":[1,[4,str(x)]],"Y":[1,[4,str(y)]]})
    def set_x(self,v): return self._add("motion_setx",inputs={"X":[1,[4,str(v)]]})
    def set_y(self,v): return self._add("motion_sety",inputs={"Y":[1,[4,str(v)]]})
    def change_x(self,v): return self._add("motion_changexby",inputs={"DX":[1,[4,str(v)]]})
    def change_y(self,v): return self._add("motion_changeyby",inputs={"DY":[1,[4,str(v)]]})
    def change_y_var(self,n,i):
        vr=self.var_ref(n,i);b=self._add("motion_changeyby",inputs={"DY":[3,vr,[4,"0"]]});self._p(vr,b);return b
    def change_x_var(self,n,i):
        vr=self.var_ref(n,i);b=self._add("motion_changexby",inputs={"DX":[3,vr,[4,"0"]]});self._p(vr,b);return b
    def xpos(self): return self._add("motion_xposition")
    def op_sub(self,a,b2):
        b=self._add("operator_subtract",inputs={"NUM1":[3,a,[10,""]],"NUM2":[3,b2,[10,""]]});self._p(a,b);self._p(b2,b);return b
    def set_var_block(self,n,i,src):
        b=self._add("data_setvariableto",fields={"VARIABLE":[n,i]},inputs={"VALUE":[3,src,[10,""]]});self._p(src,b);return b
    def sense_of_xpos(self,sprite_name):
        om=self._add("sensing_of_object_menu",fields={"OBJECT":[sprite_name,None]},shadow=True)
        b=self._add("sensing_of",fields={"PROPERTY":["x position",None]},inputs={"OBJECT":[1,om]})
        self._p(om,b);return b
    def sense_of_ypos(self,sprite_name):
        om=self._add("sensing_of_object_menu",fields={"OBJECT":[sprite_name,None]},shadow=True)
        b=self._add("sensing_of",fields={"PROPERTY":["y position",None]},inputs={"OBJECT":[1,om]})
        self._p(om,b);return b
    def ypos(self): return self._add("motion_yposition")
    def op_gt_block(self,a,b2):
        b=self._add("operator_gt",inputs={"OPERAND1":[3,a,[10,""]],"OPERAND2":[3,b2,[10,""]]});self._p(a,b);self._p(b2,b);return b
    def op_add_block_const(self,src,const):
        b=self._add("operator_add",inputs={"NUM1":[3,src,[10,""]],"NUM2":[1,[10,str(const)]]});self._p(src,b);return b
    def op_or(self,a,b2):
        b=self._add("operator_or",inputs={"OPERAND1":[2,a],"OPERAND2":[2,b2]});self._p(a,b);self._p(b2,b);return b
    def set_y_block(self,src):
        b=self._add("motion_sety",inputs={"Y":[3,src,[4,"0"]]});self._p(src,b);return b
    def set_x_block(self,src):
        b=self._add("motion_setx",inputs={"X":[3,src,[4,"0"]]});self._p(src,b);return b
    def move(self,s): return self._add("motion_movesteps",inputs={"STEPS":[1,[4,str(s)]]})
    def point_dir(self,d): return self._add("motion_pointindirection",inputs={"DIRECTION":[1,[4,str(d)]]})
    def show(self): return self._add("looks_show")
    def hide(self): return self._add("looks_hide")
    def costume(self,n): return self._add("looks_switchcostumeto",inputs={"COSTUME":[1,[10,n]]})
    def costume_var(self,n,i):
        vr=self.var_ref(n,i);b=self._add("looks_switchcostumeto",inputs={"COSTUME":[3,vr,[10,""]]});self._p(vr,b);return b
    def backdrop(self,n): return self._add("looks_switchbackdropto",inputs={"BACKDROP":[1,[10,n]]})
    def set_size(self,p): return self._add("looks_setsizeto",inputs={"SIZE":[1,[4,str(p)]]})
    def next_costume(self): return self._add("looks_nextcostume")
    def goto_front(self): return self._add("looks_gotofrontback",fields={"FRONT_BACK":["front",None]})
    def set_effect(self,effect,value):
        return self._add("looks_seteffectto",fields={"EFFECT":[effect,None]},inputs={"VALUE":[1,[4,str(value)]]})
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
    def mouse_down(self): return self._add("sensing_mousedown")
    def mouse_x(self): return self._add("sensing_mousex")
    def mouse_y(self): return self._add("sensing_mousey")
    def glide_block(self,secs,x_block,y_block):
        b=self._add("motion_glidesecstoxy",inputs={"SECS":[1,[4,str(secs)]],"X":[3,x_block,[4,"0"]],"Y":[3,y_block,[4,"0"]]})
        self._p(x_block,b);self._p(y_block,b);return b
    def stage_clicked(self): return self._add("event_whenstageclicked", top=True)
    def distance_to(self,sprite_name):
        om=self._add("sensing_distancetomenu",fields={"DISTANCETOMENU":[sprite_name,None]},shadow=True)
        b=self._add("sensing_distanceto",inputs={"DISTANCETOMENU":[1,om]});self._p(om,b);return b
    def lt_block_const(self,src,const):
        b=self._add("operator_lt",inputs={"OPERAND1":[3,src,[10,""]],"OPERAND2":[1,[10,str(const)]]});self._p(src,b);return b
    def point_towards(self,target):
        om=self._add("motion_pointtowards_menu",fields={"TOWARDS":[target,None]},shadow=True)
        b=self._add("motion_pointtowards",inputs={"TOWARDS":[1,om]});self._p(om,b);return b
    def stop_this(self): return self._add("control_stop",fields={"STOP_OPTION":["this script",None]},mutation={"tagName":"mutation","children":[],"hasnext":"false"})
    def glide_xy(self,secs,x,y):
        return self._add("motion_glidesecstoxy",inputs={"SECS":[1,[4,str(secs)]],"X":[1,[4,str(x)]],"Y":[1,[4,str(y)]]})
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
    def gt_ypos(self,v):
        yp=self._add("motion_yposition");b=self._add("operator_gt",inputs={"OPERAND1":[3,yp,[10,""]],"OPERAND2":[1,[10,str(v)]]});self._p(yp,b);return b
    def lt_xpos(self,v):
        xp=self._add("motion_xposition");b=self._add("operator_lt",inputs={"OPERAND1":[3,xp,[10,""]],"OPERAND2":[1,[10,str(v)]]});self._p(xp,b);return b
    def gt_xpos(self,v):
        xp=self._add("motion_xposition");b=self._add("operator_gt",inputs={"OPERAND1":[3,xp,[10,""]],"OPERAND2":[1,[10,str(v)]]});self._p(xp,b);return b
    def broadcast(self,n,i): return self._add("event_broadcast",inputs={"BROADCAST_INPUT":[1,[11,n,i]]})
    def broadcast_wait(self,n,i): return self._add("event_broadcastandwait",inputs={"BROADCAST_INPUT":[1,[11,n,i]]})


# ==================== SVG Helpers ====================
def svg(w,h,c): return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{c}</svg>'

def gen_beep(f=800,d=0.15,sr=22050):
    n=int(sr*d);raw=b''.join(struct.pack('<h',max(-32768,min(32767,int(16000*math.sin(2*math.pi*f*i/sr)*(1-i/n*0.5))))) for i in range(n))
    w=bytearray(b'RIFF');w.extend(struct.pack('<I',36+len(raw)));w.extend(b'WAVEfmt ');w.extend(struct.pack('<IHHIIHH',16,1,1,sr,sr*2,2,16));w.extend(b'data');w.extend(struct.pack('<I',len(raw)));w.extend(raw);return bytes(w)


# ==================== Asset Registration ====================
class AssetManager:
    def __init__(self):
        self.assets = {}

    def reg(self, name, svg_str, cx, cy):
        d = svg_str.encode("utf-8"); md5 = hashlib.md5(d).hexdigest()
        self.assets[f"{md5}.svg"] = d
        return {"name":name,"assetId":md5,"md5ext":f"{md5}.svg","dataFormat":"svg",
                "rotationCenterX":cx,"rotationCenterY":cy}

    def reg_png(self, name, filename, cx=None, cy=None):
        path = os.path.join(SPRITE_DIR, filename)
        with open(path, "rb") as f: d = f.read()
        md5 = hashlib.md5(d).hexdigest(); self.assets[f"{md5}.png"] = d
        from PIL import Image; img = Image.open(path)
        if cx is None: cx = img.width // 2
        if cy is None: cy = img.height
        return {"name":name,"assetId":md5,"md5ext":f"{md5}.png","dataFormat":"png",
                "rotationCenterX":cx,"rotationCenterY":cy,"bitmapResolution":1}

    def reg_png_backdrop(self, name, filename):
        path = os.path.join(SPRITE_DIR, filename)
        with open(path, "rb") as f: d = f.read()
        md5 = hashlib.md5(d).hexdigest(); self.assets[f"{md5}.png"] = d
        return {"name":name,"assetId":md5,"md5ext":f"{md5}.png","dataFormat":"png",
                "rotationCenterX":240,"rotationCenterY":180,"bitmapResolution":1}

    def reg_snd(self, name, data):
        md5 = hashlib.md5(data).hexdigest(); self.assets[f"{md5}.wav"] = data
        return {"name":name,"assetId":md5,"md5ext":f"{md5}.wav","dataFormat":"wav",
                "rate":22050,"sampleCount":0}


# ==================== Character SVGs ====================
def svg_mario(facing="right"):
    mirror = 'transform="translate(36,0) scale(-1,1)"' if facing=="left" else ''
    return svg(36, 44, f'<g {mirror}><rect x="6" y="0" width="24" height="6" rx="3" fill="#E02020"/><rect x="2" y="3" width="14" height="5" rx="2" fill="#E02020"/><text x="20" y="5" font-size="5" font-weight="bold" fill="#FFF">M</text><rect x="4" y="6" width="6" height="4" rx="1" fill="#4A2800"/><rect x="6" y="6" width="22" height="14" rx="3" fill="#FDBCB4"/><ellipse cx="22" cy="12" rx="3" ry="3.5" fill="#FFF"/><ellipse cx="23" cy="12" rx="1.5" ry="2" fill="#1565C0"/><circle cx="23" cy="11.5" r="0.8" fill="#000"/><ellipse cx="26" cy="14" rx="3" ry="2" fill="#FDBCB4"/><path d="M16,17 Q20,20 28,17" stroke="#4A2800" stroke-width="2.5" fill="none"/><rect x="6" y="20" width="24" height="12" rx="2" fill="#2040E0"/><rect x="2" y="20" width="8" height="10" rx="2" fill="#E02020"/><rect x="26" y="20" width="8" height="10" rx="2" fill="#E02020"/><circle cx="4" cy="31" r="3" fill="#FFF"/><circle cx="32" cy="31" r="3" fill="#FFF"/><circle cx="12" cy="24" r="1.5" fill="#FFD700"/><circle cx="24" cy="24" r="1.5" fill="#FFD700"/><rect x="8" y="32" width="8" height="8" rx="1" fill="#2040E0"/><rect x="20" y="32" width="8" height="8" rx="1" fill="#2040E0"/><rect x="5" y="38" width="12" height="6" rx="3" fill="#8B4513"/><rect x="19" y="38" width="12" height="6" rx="3" fill="#8B4513"/></g>')

def svg_peach():
    return svg(30, 48, '<polygon points="8,6 10,0 12,4 15,0 17,4 20,0 22,6" fill="#FFD700"/><rect x="8" y="5" width="14" height="4" rx="1" fill="#FFD700"/><circle cx="15" cy="4" r="2" fill="#E02020"/><ellipse cx="15" cy="14" rx="10" ry="8" fill="#FFD54F"/><rect x="5" y="14" width="4" height="12" rx="2" fill="#FFD54F"/><rect x="21" y="14" width="4" height="12" rx="2" fill="#FFD54F"/><ellipse cx="15" cy="15" rx="7" ry="7" fill="#FDBCB4"/><ellipse cx="12" cy="14" rx="2" ry="2.5" fill="#1565C0"/><ellipse cx="18" cy="14" rx="2" ry="2.5" fill="#1565C0"/><ellipse cx="15" cy="19" rx="2" ry="1" fill="#E57373"/><path d="M8,22 L5,46 Q15,50 25,46 L22,22 Z" fill="#F48FB1"/><rect x="8" y="22" width="14" height="8" rx="2" fill="#EC407A"/><circle cx="15" cy="25" r="2" fill="#1565C0"/><rect x="3" y="24" width="5" height="8" rx="2" fill="#FFF"/><rect x="22" y="24" width="5" height="8" rx="2" fill="#FFF"/>')

def svg_bowser():
    return svg(48, 50, '<ellipse cx="28" cy="26" rx="18" ry="16" fill="#2E7D32"/><ellipse cx="28" cy="24" rx="14" ry="12" fill="#388E3C"/><polygon points="18,12 20,4 22,12" fill="#FFF9C4"/><polygon points="25,10 27,2 29,10" fill="#FFF9C4"/><polygon points="32,12 34,4 36,12" fill="#FFF9C4"/><ellipse cx="12" cy="18" rx="12" ry="12" fill="#FFCC02"/><ellipse cx="8" cy="8" rx="8" ry="6" fill="#E65100"/><polygon points="3,10 0,0 8,7" fill="#FFF9C4"/><polygon points="17,10 20,0 12,7" fill="#FFF9C4"/><line x1="4" y1="13" x2="10" y2="11" stroke="#4A2800" stroke-width="2"/><line x1="14" y1="11" x2="20" y2="13" stroke="#4A2800" stroke-width="2"/><ellipse cx="8" cy="16" rx="3" ry="3.5" fill="#FFF"/><circle cx="9" cy="16" r="2" fill="#E02020"/><ellipse cx="16" cy="16" rx="3" ry="3.5" fill="#FFF"/><circle cx="17" cy="16" r="2" fill="#E02020"/><ellipse cx="12" cy="22" rx="6" ry="4" fill="#E8B830"/><path d="M5,26 Q12,32 19,26" fill="#B71C1C"/><polygon points="7,26 8,29 9,26" fill="#FFF"/><polygon points="16,26 17,29 18,26" fill="#FFF"/><ellipse cx="28" cy="34" rx="12" ry="10" fill="#FFCC02"/><ellipse cx="18" cy="47" rx="7" ry="3" fill="#FFCC02"/><ellipse cx="36" cy="47" rx="7" ry="3" fill="#FFCC02"/>')

def svg_turtle():
    return svg(30, 30, '<ellipse cx="15" cy="14" rx="13" ry="12" fill="#2E7D32"/><ellipse cx="15" cy="12" rx="9" ry="8" fill="#4CAF50"/><circle cx="7" cy="14" r="6" fill="#8BC34A"/><circle cx="5" cy="12" r="2" fill="#FFF"/><circle cx="5" cy="12" r="1" fill="#000"/><ellipse cx="10" cy="26" rx="4" ry="3" fill="#8BC34A"/><ellipse cx="20" cy="26" rx="4" ry="3" fill="#8BC34A"/>')

def svg_shell():
    return svg(26, 20, '<ellipse cx="13" cy="10" rx="12" ry="9" fill="#2E7D32" stroke="#1B5E20" stroke-width="1"/><ellipse cx="13" cy="8" rx="8" ry="6" fill="#4CAF50"/><line x1="7" y1="6" x2="7" y2="14" stroke="#1B5E20" stroke-width="1"/><line x1="13" y1="4" x2="13" y2="14" stroke="#1B5E20" stroke-width="1"/><line x1="19" y1="6" x2="19" y2="14" stroke="#1B5E20" stroke-width="1"/><ellipse cx="13" cy="15" rx="10" ry="4" fill="#FFCC02"/>')

def svg_spiky_turtle():
    # 일반 거북이 위에 가시(▲▲▲) 추가
    return svg(30, 32,
        '<polygon points="6,4 8,0 10,4" fill="#37474F"/>'
        '<polygon points="13,3 15,-1 17,3" fill="#37474F"/>'
        '<polygon points="20,4 22,0 24,4" fill="#37474F"/>'
        '<ellipse cx="15" cy="16" rx="13" ry="12" fill="#5D4037"/>'
        '<ellipse cx="15" cy="14" rx="9" ry="8" fill="#8D6E63"/>'
        '<circle cx="7" cy="16" r="6" fill="#FFCC80"/>'
        '<circle cx="5" cy="14" r="2" fill="#FFF"/>'
        '<circle cx="5" cy="14" r="1" fill="#000"/>'
        '<ellipse cx="10" cy="28" rx="4" ry="3" fill="#FFCC80"/>'
        '<ellipse cx="20" cy="28" rx="4" ry="3" fill="#FFCC80"/>'
    )

def svg_question_block():
    return svg(30, 30,
        '<rect x="1" y="1" width="28" height="28" rx="2" fill="#FFB300" stroke="#E65100" stroke-width="2"/>'
        '<rect x="3" y="3" width="24" height="24" rx="1" fill="#FFC107"/>'
        '<text x="15" y="22" text-anchor="middle" font-size="20" font-weight="bold" fill="#4E342E">?</text>'
        '<circle cx="6" cy="6" r="1.5" fill="#FFE082"/>'
        '<circle cx="24" cy="6" r="1.5" fill="#FFE082"/>'
        '<circle cx="6" cy="24" r="1.5" fill="#FFE082"/>'
        '<circle cx="24" cy="24" r="1.5" fill="#FFE082"/>'
    )

def svg_empty_block():
    return svg(30, 30,
        '<rect x="1" y="1" width="28" height="28" rx="2" fill="#757575" stroke="#424242" stroke-width="2"/>'
        '<rect x="3" y="3" width="24" height="24" rx="1" fill="#9E9E9E"/>'
        '<circle cx="6" cy="6" r="1.5" fill="#BDBDBD"/>'
        '<circle cx="24" cy="6" r="1.5" fill="#BDBDBD"/>'
        '<circle cx="6" cy="24" r="1.5" fill="#BDBDBD"/>'
        '<circle cx="24" cy="24" r="1.5" fill="#BDBDBD"/>'
    )

def svg_fire_flower():
    # 빨강+노랑 꽃잎 + 초록 줄기
    return svg(24, 28,
        '<rect x="11" y="14" width="2" height="14" fill="#2E7D32"/>'
        '<ellipse cx="8" cy="20" rx="4" ry="2" fill="#388E3C"/>'
        '<ellipse cx="16" cy="22" rx="4" ry="2" fill="#388E3C"/>'
        '<circle cx="12" cy="9" r="7" fill="#FFFFFF"/>'
        '<circle cx="12" cy="6" r="4" fill="#E53935"/>'
        '<circle cx="6" cy="11" r="4" fill="#E53935"/>'
        '<circle cx="18" cy="11" r="4" fill="#E53935"/>'
        '<circle cx="9" cy="14" r="3.5" fill="#FB8C00"/>'
        '<circle cx="15" cy="14" r="3.5" fill="#FB8C00"/>'
        '<circle cx="12" cy="10" r="3" fill="#FFEB3B"/>'
        '<circle cx="10" cy="9" r="0.8" fill="#000"/>'
        '<circle cx="14" cy="9" r="0.8" fill="#000"/>'
    )

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

def svg_dark_hearts(n, total=10, per_row=5):
    # 5 per row, 2 rows = 10 hearts. 각 하트 22x20.
    hearts=""
    for i in range(total):
        c="#111" if i<n else "#888"
        col = i % per_row
        row = i // per_row
        x = col * 22 + 2
        y = row * 22
        hearts+=f'<path d="M{x+10},{y+8} C{x+10},{y+4} {x+4},{y+2} {x+4},{y+6} C{x+4},{y+4} {x},{y+6} {x+4},{y+12} L{x+10},{y+18} L{x+16},{y+12} C{x+20},{y+6} {x+16},{y+4} {x+16},{y+6} C{x+16},{y+2} {x+10},{y+4} {x+10},{y+8} Z" fill="{c}"/>'
    return svg(per_row * 22 + 4, ((total + per_row - 1) // per_row) * 22 + 2, hearts)


# ==================== Backdrops ====================
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


# ==================== Common Sprites ====================
def make_ground(am):
    """바닥 스프라이트 생성"""
    g = BB(); gf = g.flag(); g.chain([gf, g.goto(0, GY-15), g.show()])
    return {"isStage":False,"name":"Ground","variables":{},"lists":{},"broadcasts":{},"comments":{},
        "blocks":g.blocks,"currentCostume":0,"costumes":[am.reg("ground", svg_ground(), 240, 15)],
        "sounds":[],"volume":100,"layerOrder":1,"visible":True,
        "x":0,"y":GY-15,"size":100,"direction":90,"draggable":False,"rotationStyle":"don't rotate"}

def make_hearts(am, V, BR=None, end_backdrops=("게임오버", "클리어", "승리"),
                restart_br_key="스테이지1"):
    """하트 표시 스프라이트 생성 (피격 브로드캐스트로 코스튬 전환).
    restart_br_key: 게임 재시작 broadcast 키 (Stage 1=스테이지1, Stage 3=스테이지3 등)"""
    ht = BB()
    # 초기화: 5개 하트 표시
    htf = ht.flag()
    ht.chain([htf, ht.goto(-160,160), ht.set_size(100), ht.costume("h5"), ht.show()])
    # 피격 시 다음 코스튬으로 (h5→h4→h3→h2→h1→h0)
    if BR and "피격" in BR:
        hth = ht.bcast_hat("피격", BR["피격"])
        ht.chain([hth, ht.next_costume()])
    # 게임 (재)시작 시 하트 풀 복구 + 다시 show
    if BR and restart_br_key in BR:
        htr = ht.bcast_hat(restart_br_key, BR[restart_br_key])
        ht.chain([htr, ht.costume("h5"), ht.show()])
    # 종료 백드롭 전환 시 hide
    for bd in end_backdrops:
        hb = ht.backdrop_hat(bd)
        ht.chain([hb, ht.hide()])
    return {"isStage":False,"name":"Hearts","variables":{},"lists":{},"broadcasts":{},"comments":{},
        "blocks":ht.blocks,"currentCostume":0,
        "costumes":[am.reg("h5",svg_hearts(5),56,10),am.reg("h4",svg_hearts(4),56,10),
                    am.reg("h3",svg_hearts(3),56,10),am.reg("h2",svg_hearts(2),56,10),
                    am.reg("h1",svg_hearts(1),56,10),am.reg("h0",svg_hearts(0),56,10)],
        "sounds":[],"volume":100,"layerOrder":10,"visible":True,
        "x":-160,"y":160,"size":100,"direction":90,"draggable":False,"rotationStyle":"don't rotate"}


# ==================== Save Helper ====================
def save_sb3(filename, project, assets):
    with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project.json", json.dumps(project, ensure_ascii=True))
        for fn, data in assets.items():
            zf.writestr(fn, data)
    print(f"Created: {filename} ({os.path.getsize(filename)/1024:.0f} KB)")

"""Minimal Scratch clone test - just a sprite spawning clones that fall down."""
import json, zipfile, hashlib, uuid

def uid(): return uuid.uuid4().hex[:20]

svg_circle = '<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30"><circle cx="15" cy="15" r="15" fill="red"/></svg>'
svg_bg = '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"><rect width="480" height="360" fill="#eee"/></svg>'

def asset(svg_str):
    data = svg_str.encode("utf-8")
    md5 = hashlib.md5(data).hexdigest()
    return md5, data

circle_md5, circle_data = asset(svg_circle)
bg_md5, bg_data = asset(svg_bg)

# ---- Build blocks manually for maximum correctness ----
blocks = {}
def blk(opcode, top=False, parent=None, nxt=None, inputs=None, fields=None, shadow=False, mutation=None):
    bid = uid()
    b = {"opcode": opcode, "next": nxt, "parent": parent,
         "inputs": inputs or {}, "fields": fields or {},
         "shadow": shadow, "topLevel": top}
    if top: b["x"], b["y"] = 0, 0
    if mutation: b["mutation"] = mutation
    blocks[bid] = b
    return bid

# === Script 1: when flag → forever { create clone of myself; wait 0.5 } ===
hat1 = blk("event_whenflagclicked", top=True)
menu1 = blk("control_create_clone_of_menu", shadow=True, fields={"CLONE_OPTION": ["_myself_", None]})
clone1 = blk("control_create_clone_of", inputs={"CLONE_OPTION": [1, menu1]})
blocks[menu1]["parent"] = clone1
wait1 = blk("control_wait", inputs={"DURATION": [1, [5, "0.5"]]})
# chain: clone1 → wait1
blocks[clone1]["next"] = wait1
blocks[wait1]["parent"] = clone1
# forever wrapping clone1
forever1 = blk("control_forever", inputs={"SUBSTACK": [2, clone1]})
blocks[clone1]["parent"] = forever1
# hat1 → forever1
blocks[hat1]["next"] = forever1
blocks[forever1]["parent"] = hat1

# === Script 2: when clone start → show → goto(random, 150) → forever { change y by -3 → if y<-180 del } ===
hat2 = blk("event_whenclonestartasclone", top=True)
show2 = blk("looks_show")
# goto random x, y=150
rand_x = blk("operator_random", inputs={"FROM": [1, [4, "-200"]], "TO": [1, [4, "200"]]})
goto2 = blk("motion_gotoxy", inputs={"X": [3, rand_x, [4, "0"]], "Y": [1, [4, "150"]]})
blocks[rand_x]["parent"] = goto2
# change y
move2 = blk("motion_changeyby", inputs={"DY": [1, [4, "-3"]]})
# y position < -170
ypos = blk("motion_yposition")
lt2 = blk("operator_lt", inputs={"OPERAND1": [3, ypos, [10, ""]], "OPERAND2": [1, [10, "-170"]]})
blocks[ypos]["parent"] = lt2
del2 = blk("control_delete_this_clone")
if2 = blk("control_if", inputs={"CONDITION": [2, lt2], "SUBSTACK": [2, del2]})
blocks[lt2]["parent"] = if2
blocks[del2]["parent"] = if2
# chain move2 → if2
blocks[move2]["next"] = if2
blocks[if2]["parent"] = move2
# forever2
forever2 = blk("control_forever", inputs={"SUBSTACK": [2, move2]})
blocks[move2]["parent"] = forever2
# hat2 → show → goto → forever2
blocks[hat2]["next"] = show2
blocks[show2]["parent"] = hat2
blocks[show2]["next"] = goto2
blocks[goto2]["parent"] = show2
blocks[goto2]["next"] = forever2
blocks[forever2]["parent"] = goto2

project = {
    "targets": [
        {
            "isStage": True, "name": "Stage",
            "variables": {}, "lists": {}, "broadcasts": {},
            "blocks": {}, "comments": {},
            "currentCostume": 0,
            "costumes": [{"name":"bg","assetId":bg_md5,"md5ext":f"{bg_md5}.svg",
                         "dataFormat":"svg","rotationCenterX":240,"rotationCenterY":180}],
            "sounds": [], "volume": 100, "layerOrder": 0,
            "tempo": 60, "videoTransparency": 50, "videoState": "off",
            "textToSpeechLanguage": None
        },
        {
            "isStage": False, "name": "Ball",
            "variables": {}, "lists": {}, "broadcasts": {},
            "blocks": blocks, "comments": {},
            "currentCostume": 0,
            "costumes": [{"name":"ball","assetId":circle_md5,"md5ext":f"{circle_md5}.svg",
                         "dataFormat":"svg","rotationCenterX":15,"rotationCenterY":15}],
            "sounds": [], "volume": 100, "layerOrder": 1,
            "visible": False,
            "x": 0, "y": 0, "size": 100, "direction": 90,
            "draggable": False, "rotationStyle": "all around"
        }
    ],
    "monitors": [], "extensions": [],
    "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": ""}
}

with zipfile.ZipFile("test_clone.sb3", "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("project.json", json.dumps(project, ensure_ascii=True))
    zf.writestr(f"{circle_md5}.svg", circle_data)
    zf.writestr(f"{bg_md5}.svg", bg_data)

print("Created test_clone.sb3 - open in Scratch to test clone mechanism")

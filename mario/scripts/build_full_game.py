#!/usr/bin/env python3
"""순차 통합 빌드: generate_*.py의 build()를 직접 호출해 합치는 방식.

기존 merge_sb3.py는 미리 만들어진 sb3 파일 4개를 unzip → 머지하는 방식.
이 스크립트는 generate_*.py의 build()를 직접 호출해 project + assets를 받아
중간 sb3 단계 없이 통합한다.

단계적 진행:
  1단계 (현재): 인트로 + Stage1
  2단계: + Stage2
  3단계: + Stage3
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import generate_intro  # noqa: E402
import generate_stage1  # noqa: E402
import generate_stage2  # noqa: E402
import generate_stage3  # noqa: E402
from common import save_sb3  # noqa: E402

# merge_sb3.py에서 공유 helper들을 가져온다.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from merge_sb3 import (  # noqa: E402
    remap_blocks,
    hide_non_intro_sprites_at_start,
    add_intro_hide_hats,
    add_transition_space_hat,
    _new_id,
)


def remove_legacy_space_hats(stage: dict) -> int:
    """Stage에 있는 모든 `when space pressed` 핸들러와 그 chain 블록을 제거.

    각 stage sb3가 가져온 자기-진입 space hat은 모두 `if 게임상태=="start"/"gameover"/...`로
    분기하기 때문에 stage2 게임오버 시 stage1 hat과 stage3 hat까지 동시 발동되는 race가 생긴다.
    build_full_game이 backdrop 기반 새 hat을 모두 채워주므로 기존 것을 통째로 제거.
    """
    blocks = stage["blocks"]
    # 1) 제거할 hat id 수집
    hat_ids: list[str] = []
    for bid, b in list(blocks.items()):
        if (isinstance(b, dict)
                and b.get("opcode") == "event_whenkeypressed"
                and b.get("fields", {}).get("KEY_OPTION", [""])[0] == "space"):
            hat_ids.append(bid)

    # 2) 각 hat의 reachable 블록(next chain + 모든 sub-block 참조) 집합 구축
    to_remove: set[str] = set()
    for hat_id in hat_ids:
        stack = [hat_id]
        while stack:
            cur = stack.pop()
            if cur in to_remove or cur not in blocks:
                continue
            to_remove.add(cur)
            blk = blocks[cur]
            if not isinstance(blk, dict):
                continue
            nxt = blk.get("next")
            if nxt:
                stack.append(nxt)
            for iname, ival in blk.get("inputs", {}).items():
                if not isinstance(ival, list):
                    continue
                for slot in ival:
                    if isinstance(slot, str):
                        stack.append(slot)
                    elif isinstance(slot, list):
                        if len(slot) >= 2 and isinstance(slot[1], str):
                            stack.append(slot[1])

    for bid in to_remove:
        blocks.pop(bid, None)
    return len(hat_ids)


def add_transition_space_hat_with_resets(
    stage: dict,
    from_backdrop_name: str,
    set_var_assignments: list[tuple[str, str]],
    to_backdrop_name: str,
    broadcast_name: str,
) -> None:
    """`when space pressed` → if backdrop_name == from_backdrop_name:
        for (var, value) in set_var_assignments: set var to value
        switch backdrop to to_backdrop_name
        broadcast broadcast_name
        stop other scripts in sprite
    """
    var_id_by_name: dict[str, str] = {}
    for vid, vdef in stage["variables"].items():
        var_id_by_name[vdef[0]] = vid
    for vname, _ in set_var_assignments:
        if vname not in var_id_by_name:
            raise KeyError(f"Variable {vname!r} not found in stage")
    br_id = next(bid for bid, bn in stage["broadcasts"].items() if bn == broadcast_name)

    blocks = stage["blocks"]
    hat_id = _new_id()
    if_id = _new_id()
    cur_bd_id = _new_id()
    eq_id = _new_id()
    set_bd_id = _new_id()
    bd_menu_id = _new_id()
    bcast_id = _new_id()
    stop_id = _new_id()

    blocks[hat_id] = {
        "opcode": "event_whenkeypressed",
        "next": if_id, "parent": None,
        "inputs": {},
        "fields": {"KEY_OPTION": ["space", None]},
        "shadow": False, "topLevel": True, "x": 50, "y": 50,
    }
    blocks[cur_bd_id] = {
        "opcode": "looks_backdropnumbername",
        "next": None, "parent": eq_id,
        "inputs": {}, "fields": {"NUMBER_NAME": ["name", None]},
        "shadow": False, "topLevel": False,
    }
    blocks[eq_id] = {
        "opcode": "operator_equals",
        "next": None, "parent": if_id,
        "inputs": {
            "OPERAND1": [3, cur_bd_id, [10, ""]],
            "OPERAND2": [1, [10, from_backdrop_name]],
        },
        "fields": {}, "shadow": False, "topLevel": False,
    }

    # set var chain
    first_set_id = None
    prev_id = if_id  # substack 첫 블록의 parent (control_if substack 시작)
    chain_prev = None
    for vname, vvalue in set_var_assignments:
        set_id = _new_id()
        if first_set_id is None:
            first_set_id = set_id
        blocks[set_id] = {
            "opcode": "data_setvariableto",
            "next": None,
            "parent": chain_prev if chain_prev else if_id,
            "inputs": {"VALUE": [1, [10, vvalue]]},
            "fields": {"VARIABLE": [vname, var_id_by_name[vname]]},
            "shadow": False, "topLevel": False,
        }
        if chain_prev:
            blocks[chain_prev]["next"] = set_id
        chain_prev = set_id

    # set backdrop
    blocks[bd_menu_id] = {
        "opcode": "looks_backdrops",
        "next": None, "parent": set_bd_id,
        "inputs": {}, "fields": {"BACKDROP": [to_backdrop_name, None]},
        "shadow": True, "topLevel": False,
    }
    blocks[set_bd_id] = {
        "opcode": "looks_switchbackdropto",
        "next": bcast_id, "parent": chain_prev,
        "inputs": {"BACKDROP": [1, bd_menu_id]},
        "fields": {}, "shadow": False, "topLevel": False,
    }
    blocks[chain_prev]["next"] = set_bd_id

    blocks[bcast_id] = {
        "opcode": "event_broadcast",
        "next": None, "parent": set_bd_id,
        "inputs": {"BROADCAST_INPUT": [1, [11, broadcast_name, br_id]]},
        "fields": {}, "shadow": False, "topLevel": False,
    }
    blocks[if_id] = {
        "opcode": "control_if",
        "next": None, "parent": hat_id,
        "inputs": {
            "CONDITION": [2, eq_id],
            "SUBSTACK": [2, first_set_id],
        },
        "fields": {}, "shadow": False, "topLevel": False,
    }
    # stop_id intentionally left out of chain; legacy hats already removed.
    _ = stop_id


def load_mp3(path: Path) -> tuple[str, str, bytes]:
    data = path.read_bytes()
    md5 = hashlib.md5(data).hexdigest()
    return md5, f"{md5}.mp3", data


def make_sound_def(name: str, md5: str, md5ext: str) -> dict:
    return {
        "name": name,
        "assetId": md5,
        "dataFormat": "mp3",
        "rate": 48000,
        "sampleCount": 0,  # Scratch will recompute on load; 0 is accepted.
        "md5ext": md5ext,
    }


def add_or_replace_sound(target: dict, sound_def: dict) -> None:
    sounds = target.setdefault("sounds", [])
    for i, s in enumerate(sounds):
        if s.get("name") == sound_def["name"]:
            sounds[i] = sound_def
            return
    sounds.append(sound_def)


def add_intro_reset_hats(sprites: list[dict[str, Any]], intro_backdrop_name: str) -> int:
    """비-intro sprite에 `when backdrop switches to <intro>` → hide + stop other scripts.
    승리 후 인트로 재진입 시 stage3 fireball/peach 등의 잔여 script가 발동되지 않게."""
    count = 0
    for sp in sprites:
        if sp["name"].startswith("intro_"):
            continue
        blocks = sp.setdefault("blocks", {})
        hat_id = _new_id()
        hide_id = _new_id()
        stop_id = _new_id()
        blocks[hat_id] = {
            "opcode": "event_whenbackdropswitchesto",
            "next": hide_id, "parent": None,
            "inputs": {}, "fields": {"BACKDROP": [intro_backdrop_name, None]},
            "shadow": False, "topLevel": True, "x": 50, "y": 700,
        }
        blocks[hide_id] = {
            "opcode": "looks_hide",
            "next": stop_id, "parent": hat_id,
            "inputs": {}, "fields": {},
            "shadow": False, "topLevel": False,
        }
        blocks[stop_id] = {
            "opcode": "control_stop",
            "next": None, "parent": hide_id,
            "inputs": {}, "fields": {"STOP_OPTION": ["other scripts in sprite", None]},
            "shadow": False, "topLevel": False,
            "mutation": {"tagName": "mutation", "children": [], "hasnext": "false"},
        }
        count += 1
    return count


def _build_play_sound_chain(
    blocks: dict, start_parent_id: str, sound_name: str, loop: bool,
    volume: int = 100,
) -> str:
    """play 체인. start_parent의 next로 stop_other (이전 BGM forever 중지) → setvol → play."""
    stop_other_id = _new_id()
    setvol_id = _new_id()
    sound_menu_id = _new_id()
    # stop other scripts in sprite — 이전 stage backdrop hat이 시작했던
    # forever play_until_done loop을 끊어서 새 BGM이 처음부터 시작되게 한다.
    blocks[stop_other_id] = {
        "opcode": "control_stop",
        "next": setvol_id, "parent": start_parent_id,
        "inputs": {},
        "fields": {"STOP_OPTION": ["other scripts in sprite", None]},
        "shadow": False, "topLevel": False,
        "mutation": {"tagName": "mutation", "children": [], "hasnext": "true"},
    }
    blocks[setvol_id] = {
        "opcode": "sound_setvolumeto",
        "next": None, "parent": stop_other_id,
        "inputs": {"VOLUME": [1, [4, str(volume)]]},
        "fields": {}, "shadow": False, "topLevel": False,
    }
    if loop:
        forever_id = _new_id()
        play_until_id = _new_id()
        blocks[setvol_id]["next"] = forever_id
        blocks[sound_menu_id] = {
            "opcode": "sound_sounds_menu",
            "next": None, "parent": play_until_id,
            "inputs": {}, "fields": {"SOUND_MENU": [sound_name, None]},
            "shadow": True, "topLevel": False,
        }
        blocks[play_until_id] = {
            "opcode": "sound_playuntildone",
            "next": None, "parent": forever_id,
            "inputs": {"SOUND_MENU": [1, sound_menu_id]},
            "fields": {}, "shadow": False, "topLevel": False,
        }
        blocks[forever_id] = {
            "opcode": "control_forever",
            "next": None, "parent": setvol_id,
            "inputs": {"SUBSTACK": [2, play_until_id]},
            "fields": {}, "shadow": False, "topLevel": False,
        }
    else:
        play_id = _new_id()
        blocks[setvol_id]["next"] = play_id
        blocks[sound_menu_id] = {
            "opcode": "sound_sounds_menu",
            "next": None, "parent": play_id,
            "inputs": {}, "fields": {"SOUND_MENU": [sound_name, None]},
            "shadow": True, "topLevel": False,
        }
        blocks[play_id] = {
            "opcode": "sound_play",
            "next": None, "parent": setvol_id,
            "inputs": {"SOUND_MENU": [1, sound_menu_id]},
            "fields": {}, "shadow": False, "topLevel": False,
        }
    return stop_other_id


def add_backdrop_play_sound_hat(
    target: dict, backdrop_name: str, sound_name: str,
    loop: bool = False, volume: int = 100,
) -> None:
    """`when backdrop switches to <backdrop_name>` → stop all sounds → set volume → play."""
    blocks = target.setdefault("blocks", {})
    hat_id = _new_id()
    stop_id = _new_id()
    blocks[hat_id] = {
        "opcode": "event_whenbackdropswitchesto",
        "next": stop_id, "parent": None, "inputs": {},
        "fields": {"BACKDROP": [backdrop_name, None]},
        "shadow": False, "topLevel": True, "x": 50, "y": 900,
    }
    blocks[stop_id] = {
        "opcode": "sound_stopallsounds",
        "next": None, "parent": hat_id,
        "inputs": {}, "fields": {},
        "shadow": False, "topLevel": False,
    }
    chain_first = _build_play_sound_chain(blocks, stop_id, sound_name, loop, volume)
    blocks[stop_id]["next"] = chain_first


def add_broadcast_play_sound_hat(
    target: dict, broadcast_name: str, broadcast_id: str,
    sound_name: str, loop: bool = False, volume: int = 100,
    stop_others: bool = True,
) -> None:
    """`when I receive <broadcast>` → (옵션) stop all sounds + stop other scripts → set volume → play.
    stop_others=False이면 기존 BGM과 동시에 재생(중첩 SE)."""
    blocks = target.setdefault("blocks", {})
    hat_id = _new_id()
    blocks[hat_id] = {
        "opcode": "event_whenbroadcastreceived",
        "next": None, "parent": None, "inputs": {},
        "fields": {"BROADCAST_OPTION": [broadcast_name, broadcast_id]},
        "shadow": False, "topLevel": True, "x": 50, "y": 1100,
    }
    if stop_others:
        stop_id = _new_id()
        blocks[stop_id] = {
            "opcode": "sound_stopallsounds",
            "next": None, "parent": hat_id,
            "inputs": {}, "fields": {},
            "shadow": False, "topLevel": False,
        }
        blocks[hat_id]["next"] = stop_id
        chain_first = _build_play_sound_chain(blocks, stop_id, sound_name, loop, volume)
        blocks[stop_id]["next"] = chain_first
    else:
        # stop 없이 setvol + play만. _build_play_sound_chain의 stop_other도 건너뛴다.
        setvol_id = _new_id()
        sound_menu_id = _new_id()
        play_id = _new_id()
        blocks[hat_id]["next"] = setvol_id
        blocks[setvol_id] = {
            "opcode": "sound_setvolumeto",
            "next": play_id, "parent": hat_id,
            "inputs": {"VOLUME": [1, [4, str(volume)]]},
            "fields": {}, "shadow": False, "topLevel": False,
        }
        blocks[sound_menu_id] = {
            "opcode": "sound_sounds_menu",
            "next": None, "parent": play_id,
            "inputs": {}, "fields": {"SOUND_MENU": [sound_name, None]},
            "shadow": True, "topLevel": False,
        }
        blocks[play_id] = {
            "opcode": "sound_play",
            "next": None, "parent": setvol_id,
            "inputs": {"SOUND_MENU": [1, sound_menu_id]},
            "fields": {}, "shadow": False, "topLevel": False,
        }


def wire_audio(
    proj: dict, assets: dict[str, bytes], bgms_dir: Path,
) -> None:
    """Stage/sprite의 sounds 리스트와 backdrop hat을 통해 모든 BGM/SE 연결.
    - 스테이지 1/2/3 backdrop: 슈퍼마리오OST 무한 loop
    - 게임오버 backdrop: 패배BGM 1회
    - 승리 backdrop: 승리BGM 1회
    - 마리오 점프(이미 코드에서 play_sound("Jump") 호출): 점프소리.mp3 sound로 교체
    - 파이어볼 발사(이미 play_sound("Fire") 호출): Fireball.mp3 sound로 교체
    """
    stage = proj["targets"][0]
    sprites = proj["targets"][1:]

    # 1) 자산 등록
    def reg(name, file):
        md5, md5ext, data = load_mp3(bgms_dir / file)
        assets[md5ext] = data
        return make_sound_def(name, md5, md5ext)

    sd_stage_bgm = reg("StageBGM", "슈퍼마리오OST.mp3")
    sd_gameover = reg("GameOverBGM", "패배BGM.mp3")
    sd_win = reg("WinBGM", "승리BGM.mp3")
    sd_jump = reg("Jump", "점프소리.mp3")
    sd_fire = reg("Fire", "Fireball.mp3")
    sd_fireflower = reg("FireFlower", "fireflower.mp3")

    # 2) Stage: BGM sound 리스트에 추가 + backdrop hat 연결
    for sd in (sd_stage_bgm, sd_gameover, sd_win, sd_fireflower):
        add_or_replace_sound(stage, sd)

    for bd in ("s1_스테이지1", "s2_스테이지2", "s3_스테이지3"):
        add_backdrop_play_sound_hat(stage, bd, "StageBGM", loop=True, volume=70)
    for bd in ("s1_게임오버", "s2_게임오버", "s3_게임오버"):
        # loop=True: playuntildone forever. 다음 backdrop 전환 시 stop_all_sounds + control_stop으로 자동 정리.
        # instant sound_play는 race로 BGM이 즉시 끊기는 경우가 있어 안전망.
        add_backdrop_play_sound_hat(stage, bd, "GameOverBGM", loop=True, volume=100)
    # 승리 BGM은 backdrop이 아니라 broadcast "쿠파패배" 시점(피치 등장 직전)에 재생.
    br_defeat = next((bid for bid, bn in stage["broadcasts"].items() if bn == "쿠파패배"), None)
    if br_defeat:
        add_broadcast_play_sound_hat(stage, "쿠파패배", br_defeat, "WinBGM", loop=False, volume=100)
    # 파이어 플라워 BGM: broadcast "파이어변신" 받을 때 재생.
    # stop_others=False → 기존 stage BGM(슈퍼마리오 OST) loop 안 끊고 동시 재생.
    br_fireflower = next((bid for bid, bn in stage["broadcasts"].items() if bn == "파이어변신"), None)
    if br_fireflower:
        add_broadcast_play_sound_hat(stage, "파이어변신", br_fireflower, "FireFlower",
                                     loop=False, volume=100, stop_others=False)

    # 3) 마리오 sprite에 Jump sound 등록(기존 "Jump" 이름 overwrite) + sprite volume 낮춤
    for sp in sprites:
        if sp["name"] in ("s1_Mario", "s2_Mario", "s3_Mario", "s3_WhiteMario"):
            add_or_replace_sound(sp, sd_jump)
            sp["volume"] = 20   # 점프 소리 더 줄임
        if sp["name"] == "s3_Fireball":
            add_or_replace_sound(sp, sd_fire)


def set_sprite_size(sprites: list[dict[str, Any]], sprite_name: str, size: float) -> bool:
    for sp in sprites:
        if sp["name"] == sprite_name:
            sp["size"] = size
            # 첫 init chain의 set_size 블록도 같이 갱신 (있다면).
            for b in sp.get("blocks", {}).values():
                if isinstance(b, dict) and b.get("opcode") == "looks_setsizeto":
                    sz = b.get("inputs", {}).get("SIZE")
                    if sz and isinstance(sz[1], list):
                        sz[1][1] = str(size)
            return True
    return False


def add_auto_intro_end_transition(
    stage: dict, wait_seconds: float,
    end_backdrop_name: str,
    set_var_name: str, set_var_value: str,
    to_backdrop_name: str, broadcast_name: str,
) -> None:
    """`when backdrop switches to <end_backdrop_name>` →
        wait <wait_seconds>
        if backdrop name == <end_backdrop_name>:
            set var, switch backdrop, broadcast, stop other scripts
    조건 검사로 사용자가 wait 동안 스페이스로 먼저 넘어간 경우엔 무동작."""
    var_id = next(vid for vid, vdef in stage["variables"].items() if vdef[0] == set_var_name)
    br_id = next(bid for bid, bn in stage["broadcasts"].items() if bn == broadcast_name)

    blocks = stage["blocks"]
    hat_id = _new_id()
    wait_id = _new_id()
    if_id = _new_id()
    cur_bd_id = _new_id()
    eq_id = _new_id()
    set_var_id = _new_id()
    set_bd_id = _new_id()
    bd_menu_id = _new_id()
    bcast_id = _new_id()
    stop_id = _new_id()

    blocks[hat_id] = {
        "opcode": "event_whenbackdropswitchesto",
        "next": wait_id, "parent": None,
        "inputs": {},
        "fields": {"BACKDROP": [end_backdrop_name, None]},
        "shadow": False, "topLevel": True, "x": 50, "y": 800,
    }
    blocks[wait_id] = {
        "opcode": "control_wait", "next": if_id, "parent": hat_id,
        "inputs": {"DURATION": [1, [5, str(wait_seconds)]]},
        "fields": {}, "shadow": False, "topLevel": False,
    }
    blocks[cur_bd_id] = {
        "opcode": "looks_backdropnumbername", "next": None, "parent": eq_id,
        "inputs": {}, "fields": {"NUMBER_NAME": ["name", None]},
        "shadow": False, "topLevel": False,
    }
    blocks[eq_id] = {
        "opcode": "operator_equals", "next": None, "parent": if_id,
        "inputs": {
            "OPERAND1": [3, cur_bd_id, [10, ""]],
            "OPERAND2": [1, [10, end_backdrop_name]],
        },
        "fields": {}, "shadow": False, "topLevel": False,
    }
    blocks[set_var_id] = {
        "opcode": "data_setvariableto", "next": set_bd_id, "parent": if_id,
        "inputs": {"VALUE": [1, [10, set_var_value]]},
        "fields": {"VARIABLE": [set_var_name, var_id]},
        "shadow": False, "topLevel": False,
    }
    blocks[bd_menu_id] = {
        "opcode": "looks_backdrops", "next": None, "parent": set_bd_id,
        "inputs": {}, "fields": {"BACKDROP": [to_backdrop_name, None]},
        "shadow": True, "topLevel": False,
    }
    blocks[set_bd_id] = {
        "opcode": "looks_switchbackdropto", "next": bcast_id, "parent": set_var_id,
        "inputs": {"BACKDROP": [1, bd_menu_id]},
        "fields": {}, "shadow": False, "topLevel": False,
    }
    blocks[bcast_id] = {
        "opcode": "event_broadcast", "next": None, "parent": set_bd_id,
        "inputs": {"BROADCAST_INPUT": [1, [11, broadcast_name, br_id]]},
        "fields": {}, "shadow": False, "topLevel": False,
    }
    _ = stop_id  # Intentionally not wired — legacy space hats already removed.
    blocks[if_id] = {
        "opcode": "control_if", "next": None, "parent": wait_id,
        "inputs": {
            "CONDITION": [2, eq_id],
            "SUBSTACK": [2, set_var_id],
        },
        "fields": {}, "shadow": False, "topLevel": False,
    }


def merge_loaded(sources: list[tuple[str, dict, dict]]) -> tuple[dict, dict]:
    """sources = [(prefix, project_dict, assets_dict), ...] → (merged_project, merged_assets)

    sb3 unzip 없이 dict 차원에서 바로 통합.
    """
    # ---- 변수/broadcast ID 통합 (같은 이름이면 ID 공유) ----
    unified_var_name_to_id: dict[str, str] = {}
    unified_var_defs: dict[str, list[Any]] = {}
    unified_broadcast_name_to_id: dict[str, str] = {}
    unified_broadcast_defs: dict[str, str] = {}
    per_src_var_id_map: list[dict[str, str]] = []
    per_src_broadcast_id_map: list[dict[str, str]] = []

    for _prefix, project, _assets in sources:
        stage = next(t for t in project["targets"] if t.get("isStage"))
        var_map: dict[str, str] = {}
        for old_vid, vinfo in stage.get("variables", {}).items():
            vname = vinfo[0]
            if vname in unified_var_name_to_id:
                new_vid = unified_var_name_to_id[vname]
            else:
                new_vid = old_vid
                unified_var_name_to_id[vname] = new_vid
                unified_var_defs[new_vid] = list(vinfo)
            var_map[old_vid] = new_vid
        per_src_var_id_map.append(var_map)

        bc_map: dict[str, str] = {}
        for old_bid, bname in stage.get("broadcasts", {}).items():
            if bname in unified_broadcast_name_to_id:
                new_bid = unified_broadcast_name_to_id[bname]
            else:
                new_bid = old_bid
                unified_broadcast_name_to_id[bname] = new_bid
                unified_broadcast_defs[new_bid] = bname
            bc_map[old_bid] = new_bid
        per_src_broadcast_id_map.append(bc_map)

    # ---- sprite-name 매핑 (prefix 적용) ----
    per_src_sprite_name_map: list[dict[str, str]] = []
    for prefix, project, _assets in sources:
        name_map: dict[str, str] = {}
        for t in project["targets"]:
            if t.get("isStage"):
                continue
            name_map[t["name"]] = f"{prefix}_{t['name']}"
        per_src_sprite_name_map.append(name_map)

    # ---- backdrop-name 매핑 (intro는 그대로, s1/s2/s3는 prefix) ----
    per_src_backdrop_name_map: list[dict[str, str]] = []
    for prefix, project, _assets in sources:
        stage = next(t for t in project["targets"] if t.get("isStage"))
        bdmap: dict[str, str] = {}
        for c in stage.get("costumes", []):
            old = c["name"]
            new = old if prefix == "intro" else f"{prefix}_{old}"
            bdmap[old] = new
        per_src_backdrop_name_map.append(bdmap)

    # ---- Stage 머지: backdrop 합치기 + block 통합 ----
    merged_costumes: list[dict[str, Any]] = []
    seen_costume_keys: set[tuple[str, str]] = set()
    merged_stage_blocks: dict[str, Any] = {}

    for idx, (prefix, project, _assets) in enumerate(sources):
        stage = next(t for t in project["targets"] if t.get("isStage"))
        backdrop_map = per_src_backdrop_name_map[idx]

        # backdrops (rename + dedupe)
        for c in stage.get("costumes", []):
            c_copy = dict(c)
            old_name = c_copy["name"]
            c_copy["name"] = backdrop_map.get(old_name, old_name)
            key = (c_copy["name"], c_copy.get("md5ext", ""))
            if key in seen_costume_keys:
                continue
            seen_costume_keys.add(key)
            merged_costumes.append(c_copy)

        # stage blocks (deepcopy + remap)
        stage_blocks = json.loads(json.dumps(stage.get("blocks", {})))
        remap_blocks(
            stage_blocks,
            per_src_var_id_map[idx],
            per_src_broadcast_id_map[idx],
            per_src_sprite_name_map[idx],
            backdrop_map,
        )
        # block id 충돌 시 rename
        rename: dict[str, str] = {}
        for bid in list(stage_blocks.keys()):
            if bid in merged_stage_blocks:
                rename[bid] = f"{prefix}_{bid}"
        if rename:
            renamed: dict[str, Any] = {}
            for bid, blk in stage_blocks.items():
                new_bid = rename.get(bid, bid)
                if isinstance(blk, dict):
                    if blk.get("parent") in rename:
                        blk["parent"] = rename[blk["parent"]]
                    if blk.get("next") in rename:
                        blk["next"] = rename[blk["next"]]
                renamed[new_bid] = blk
            stage_blocks = renamed
        merged_stage_blocks.update(stage_blocks)

    intro_stage = next(t for t in sources[0][1]["targets"] if t.get("isStage"))
    merged_stage_target: dict[str, Any] = {
        "isStage": True,
        "name": "Stage",
        "variables": {vid: list(vdef) for vid, vdef in unified_var_defs.items()},
        "lists": intro_stage.get("lists", {}),
        "broadcasts": dict(unified_broadcast_defs),
        "blocks": merged_stage_blocks,
        "comments": {},
        "currentCostume": 0,
        "costumes": merged_costumes,
        "sounds": intro_stage.get("sounds", []),
        "volume": intro_stage.get("volume", 100),
        "layerOrder": 0,
        "tempo": intro_stage.get("tempo", 60),
        "videoTransparency": intro_stage.get("videoTransparency", 50),
        "videoState": intro_stage.get("videoState", "on"),
        "textToSpeechLanguage": intro_stage.get("textToSpeechLanguage", None),
    }

    # ---- non-stage sprite 머지 ----
    merged_sprites: list[dict[str, Any]] = []
    next_layer = 1
    for idx, (prefix, project, _assets) in enumerate(sources):
        var_map = per_src_var_id_map[idx]
        bc_map = per_src_broadcast_id_map[idx]
        name_map = per_src_sprite_name_map[idx]
        backdrop_map = per_src_backdrop_name_map[idx]
        for t in project["targets"]:
            if t.get("isStage"):
                continue
            sprite = json.loads(json.dumps(t))
            sprite["name"] = name_map[sprite["name"]]
            remap_blocks(
                sprite.get("blocks", {}),
                var_map,
                bc_map,
                name_map,
                backdrop_map,
            )
            sprite["layerOrder"] = next_layer
            next_layer += 1
            merged_sprites.append(sprite)

    # ---- 자산 통합 ----
    merged_assets: dict[str, bytes] = {}
    for _prefix, _project, assets in sources:
        merged_assets.update(assets)

    merged_project: dict[str, Any] = {
        "targets": [merged_stage_target] + merged_sprites,
        "monitors": [],
        "extensions": [],
        "meta": {
            "semver": "3.0.0",
            "vm": "1.0.0",
            "agent": "build_full_game.py",
        },
    }
    return merged_project, merged_assets


def main() -> int:
    sources: list[tuple[str, dict, dict]] = []

    print("Building intro...")
    intro_proj, intro_assets = generate_intro.build()
    sources.append(("intro", intro_proj, intro_assets))

    print("Building stage1...")
    s1_proj, s1_assets = generate_stage1.build()
    sources.append(("s1", s1_proj, s1_assets))

    print("Building stage2...")
    s2_proj, s2_assets = generate_stage2.build()
    sources.append(("s2", s2_proj, s2_assets))

    print("Building stage3...")
    s3_proj, s3_assets = generate_stage3.build()
    sources.append(("s3", s3_proj, s3_assets))

    print(f"Merging {len(sources)} sources...")
    proj, assets = merge_loaded(sources)

    # ---- 후처리 ----
    sprites = [t for t in proj["targets"] if not t.get("isStage")]
    n_hidden = hide_non_intro_sprites_at_start(sprites)
    intro_sprites = [t for t in sprites if t["name"].startswith("intro_")]
    n_hats = add_intro_hide_hats(intro_sprites, "인트로끝")
    n_reset = add_intro_reset_hats(sprites, "인트로")
    print(f"Intro-reset hats added on {n_reset} non-intro sprites.")

    # 피치(인트로) 크기 75, 스테이지3 피치 크기 45
    set_sprite_size(sprites, "intro_Peach", 75)
    set_sprite_size(sprites, "s3_Peach", 45)

    stage = proj["targets"][0]

    # 기존 sb3가 가져온 모든 space hat 제거 → race condition 차단.
    n_removed = remove_legacy_space_hats(stage)

    # 인트로끝 backdrop 도달 → 5초 대기 후 자동으로 stage1 진입.
    add_auto_intro_end_transition(
        stage, wait_seconds=5,
        end_backdrop_name="인트로끝",
        set_var_name="게임상태", set_var_value="stage1",
        to_backdrop_name="s1_스테이지1", broadcast_name="스테이지1",
    )

    # ---- Backdrop 기반 space 전환 hat (진입 + 게임오버 재시작 분기) ----
    # 각 stage 진입 시 필요한 변수 reset을 hat 자체에 포함.
    stage1_resets = [
        ("게임상태", "stage1"), ("하트", "5"),
        ("속도Y", "0"), ("점프중", "0"), ("무적", "0"), ("걸음", "1"),
    ]
    stage2_resets = [
        ("게임상태", "스테이지2"), ("하트", "5"),
        ("속도Y", "0"), ("점프중", "0"), ("무적", "0"), ("걸음", "1"),
        ("Plat1_x_prev", "170"), ("Plat1_dx", "0"),
        ("Plat5_y_prev", "90"), ("Plat5_dy", "0"),
    ]
    stage3_resets = [
        ("게임상태", "stage3"), ("하트", "5"),
        ("속도Y", "0"), ("점프중", "0"), ("무적", "0"), ("걸음", "1"),
        ("쿠파HP", "10"), ("파이어", "0"), ("꽃등장됨", "0"),
        ("파이어볼활성", "0"),
    ]
    intro_resets = [("게임상태", "intro"), ("파이어", "0"), ("꽃등장됨", "0"), ("쿠파HP", "10"), ("파이어볼활성", "0")]
    transitions = [
        ("시작화면",       intro_resets,  "인트로",        "인트로"),
        ("인트로끝",       stage1_resets, "s1_스테이지1", "스테이지1"),
        ("s1_클리어",      stage2_resets, "s2_스테이지2", "스테이지2"),
        ("s2_클리어",      stage3_resets, "s3_스테이지3", "스테이지3"),
        ("s1_게임오버",    stage1_resets, "s1_스테이지1", "스테이지1"),
        ("s2_게임오버",    stage2_resets, "s2_스테이지2", "스테이지2"),
        ("s3_게임오버",    stage3_resets, "s3_스테이지3", "스테이지3"),
        # 승리 후 스페이스 → 인트로 배경으로 바로 전환 + 인트로 컷씬 재생.
        ("s3_승리",        [("게임상태", "intro")], "인트로", "인트로"),
    ]
    for from_bd, resets, to_bd, br in transitions:
        add_transition_space_hat_with_resets(stage, from_bd, resets, to_bd, br)
    print(f"Removed legacy space hats: {n_removed}; added {len(transitions)} backdrop-based transitions.")

    # ---- 오디오 연결 (BGM 및 효과음) ----
    wire_audio(proj, assets, REPO_ROOT / "bgms")

    # ---- 검증 출력 ----
    print(f"Backdrops ({len(stage['costumes'])}): "
          f"{[c['name'] for c in stage['costumes']]}")
    print(f"Sprites ({len(sprites)}): {[t['name'] for t in sprites]}")
    print(f"Variables: {[v[0] for v in stage['variables'].values()]}")
    print(f"Broadcasts: {list(stage['broadcasts'].values())}")
    print(f"Hidden at start: {n_hidden}, Intro hide hats: {n_hats}")

    out_path = REPO_ROOT / "MarioGame.sb3"
    save_sb3(str(out_path), proj, assets)
    print(f"Saved: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

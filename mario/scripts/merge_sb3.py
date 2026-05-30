#!/usr/bin/env python3
"""Merge Intro.sb3, Stage1.sb3, Stage2.sb3, Stage3.sb3 into a single MarioGame.sb3.

Strategy
--------
1. Unzip each sb3 to a temp dir, parse its project.json.
2. Merge assets by md5-named filenames (collisions OK -> identical bytes).
3. Merge the Stage (isStage=True) target:
   - Concatenate backdrops; currentCostume = 0 (intro's first backdrop).
   - Merge variables. Variables with the SAME NAME (e.g. "하트", "게임상태",
     "속도Y", "점프중", "무적", "걸음") are unified to a single shared ID so
     that all stages read/write the same variable.
   - Merge broadcasts. Same-name broadcasts (e.g. "피격", "리셋") share IDs
     across stages so an event in one stage can be received in another.
   - Merge Stage's own blocks. Update variable & broadcast ID references in
     those blocks to the unified IDs.
4. Merge non-stage sprites:
   - Prefix sprite name (intro_, s1_, s2_, s3_) to avoid name collisions
     when the same sprite name (e.g. "Mario", "Hearts") appears in several
     source files. Each stage keeps its own copy of those sprites.
   - Update every block's variable/broadcast references to unified IDs.
   - Update every block's SPRITE-NAME reference (touching/distance-to/
     point-towards/goto menus) to the prefixed sprite names.
5. Re-serialise project.json and re-zip alongside all assets into
   MarioGame.sb3 in the repo root.

This is a pure structural merge: it does not add stage-transition logic.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES = [
    ("intro", "Intro.sb3"),
    ("s1", "Stage1.sb3"),
    ("s2", "Stage2.sb3"),
    ("s3", "Stage3.sb3"),
]
OUTPUT = REPO_ROOT / "MarioGame.sb3"

# Sprite-name fields that need rewriting if the referenced sprite was renamed.
# (opcode -> field name that holds [sprite_name, None])
SPRITE_NAME_FIELDS = {
    "sensing_touchingobjectmenu": "TOUCHINGOBJECTMENU",
    "sensing_distancetomenu": "DISTANCETOMENU",
    "sensing_of_object_menu": "OBJECT",       # sense_of_xpos/ypos 등 cross-sprite property
    "motion_pointtowards_menu": "TOWARDS",
    "motion_goto_menu": "TO",
    "motion_glideto_menu": "TO",
    "control_create_clone_of_menu": "CLONE_OPTION",
    "looks_gotofrontback": None,  # no sprite ref; uses FRONT_BACK
}

# Opcodes whose `fields.BACKDROP = [backdrop_name, None]` we want to rename.
BACKDROP_NAME_OPCODES = {
    "looks_backdrops",                  # menu under looks_switchbackdropto / looks_switchbackdroptoandwait
    "event_whenbackdropswitchesto",     # hat block field
}


def _new_id() -> str:
    return uuid.uuid4().hex[:20]


def hide_non_intro_sprites_at_start(sprites: list[dict[str, Any]]) -> int:
    """Set visible=false on every sprite that isn't an intro_ sprite.
    Each non-intro sprite must wait for its stage's broadcast hat to show()."""
    count = 0
    for sp in sprites:
        if sp["name"].startswith("intro_"):
            continue
        sp["visible"] = False
        count += 1
    return count


def add_intro_hide_hats(sprites: list[dict[str, Any]], end_backdrop_name: str) -> int:
    """For every intro_ sprite, append `when backdrop switches to <end> → hide`.
    This clears the intro cast before the player presses space to enter stage1."""
    count = 0
    for sp in sprites:
        if not sp["name"].startswith("intro_"):
            continue
        blocks = sp.setdefault("blocks", {})
        hat_id = _new_id()
        hide_id = _new_id()
        blocks[hat_id] = {
            "opcode": "event_whenbackdropswitchesto",
            "next": hide_id,
            "parent": None,
            "inputs": {},
            "fields": {"BACKDROP": [end_backdrop_name, None]},
            "shadow": False,
            "topLevel": True,
            "x": 50,
            "y": 600,
        }
        blocks[hide_id] = {
            "opcode": "looks_hide",
            "next": None,
            "parent": hat_id,
            "inputs": {},
            "fields": {},
            "shadow": False,
            "topLevel": False,
        }
        count += 1
    return count


def add_transition_space_hat(
    stage: dict[str, Any],
    from_backdrop_name: str,
    set_var_name: str,
    set_var_value: str,
    to_backdrop_name: str,
    broadcast_name: str,
) -> None:
    """Add to the stage:
        when space pressed:
            if (current backdrop name == from_backdrop_name):
                set [var_name] to "set_var_value"
                switch backdrop to "to_backdrop_name"
                broadcast "broadcast_name"
    Looks up variable ID and broadcast ID from the stage's unified maps.
    """
    # Resolve variable id
    var_id = None
    for vid, vdef in stage["variables"].items():
        if vdef[0] == set_var_name:
            var_id = vid
            break
    if var_id is None:
        raise KeyError(f"Variable {set_var_name!r} not found in stage")

    # Resolve broadcast id
    br_id = None
    for bid, bname in stage["broadcasts"].items():
        if bname == broadcast_name:
            br_id = bid
            break
    if br_id is None:
        raise KeyError(f"Broadcast {broadcast_name!r} not found in stage")

    blocks = stage["blocks"]
    hat_id = _new_id()
    if_id = _new_id()
    cur_bd_id = _new_id()
    eq_id = _new_id()
    set_var_id = _new_id()
    set_bd_id = _new_id()
    bd_menu_id = _new_id()
    bcast_id = _new_id()
    stop_id = _new_id()

    blocks[hat_id] = {
        "opcode": "event_whenkeypressed",
        "next": if_id,
        "parent": None,
        "inputs": {},
        "fields": {"KEY_OPTION": ["space", None]},
        "shadow": False,
        "topLevel": True,
        "x": 50,
        "y": 50,
    }
    blocks[cur_bd_id] = {
        "opcode": "looks_backdropnumbername",
        "next": None,
        "parent": eq_id,
        "inputs": {},
        "fields": {"NUMBER_NAME": ["name", None]},
        "shadow": False,
        "topLevel": False,
    }
    blocks[eq_id] = {
        "opcode": "operator_equals",
        "next": None,
        "parent": if_id,
        "inputs": {
            "OPERAND1": [3, cur_bd_id, [10, ""]],
            "OPERAND2": [1, [10, from_backdrop_name]],
        },
        "fields": {},
        "shadow": False,
        "topLevel": False,
    }
    blocks[set_var_id] = {
        "opcode": "data_setvariableto",
        "next": set_bd_id,
        "parent": if_id,
        "inputs": {"VALUE": [1, [10, set_var_value]]},
        "fields": {"VARIABLE": [set_var_name, var_id]},
        "shadow": False,
        "topLevel": False,
    }
    blocks[bd_menu_id] = {
        "opcode": "looks_backdrops",
        "next": None,
        "parent": set_bd_id,
        "inputs": {},
        "fields": {"BACKDROP": [to_backdrop_name, None]},
        "shadow": True,
        "topLevel": False,
    }
    blocks[set_bd_id] = {
        "opcode": "looks_switchbackdropto",
        "next": bcast_id,
        "parent": set_var_id,
        "inputs": {"BACKDROP": [1, bd_menu_id]},
        "fields": {},
        "shadow": False,
        "topLevel": False,
    }
    blocks[bcast_id] = {
        "opcode": "event_broadcast",
        "next": stop_id,
        "parent": set_bd_id,
        "inputs": {"BROADCAST_INPUT": [1, [11, broadcast_name, br_id]]},
        "fields": {},
        "shadow": False,
        "topLevel": False,
    }
    # Stop other scripts in Stage → cancels any concurrently-firing legacy space hat
    # (e.g. stage2's `if 게임상태=="clear"` branch firing on s2_클리어 backdrop)
    # so we don't accidentally launch the wrong stage.
    blocks[stop_id] = {
        "opcode": "control_stop",
        "next": None,
        "parent": bcast_id,
        "inputs": {},
        "fields": {"STOP_OPTION": ["other scripts in sprite", None]},
        "shadow": False,
        "topLevel": False,
        "mutation": {
            "tagName": "mutation",
            "children": [],
            "hasnext": "false",
        },
    }
    blocks[if_id] = {
        "opcode": "control_if",
        "next": None,
        "parent": hat_id,
        "inputs": {
            "CONDITION": [2, eq_id],
            "SUBSTACK": [2, set_var_id],
        },
        "fields": {},
        "shadow": False,
        "topLevel": False,
    }


def add_all_transition_space_hats(stage: dict[str, Any]) -> None:
    """Add the four space-press transition hats wiring intro → s1 → s2 → s3."""
    # 인트로끝 → s1_스테이지1
    add_transition_space_hat(
        stage,
        from_backdrop_name="인트로끝",
        set_var_name="게임상태",
        set_var_value="stage1",
        to_backdrop_name="s1_스테이지1",
        broadcast_name="스테이지1",
    )
    # s1_클리어 → s2_스테이지2
    add_transition_space_hat(
        stage,
        from_backdrop_name="s1_클리어",
        set_var_name="게임상태",
        set_var_value="스테이지2",
        to_backdrop_name="s2_스테이지2",
        broadcast_name="스테이지2",
    )
    # s2_클리어 → s3_스테이지3
    add_transition_space_hat(
        stage,
        from_backdrop_name="s2_클리어",
        set_var_name="게임상태",
        set_var_value="stage3",
        to_backdrop_name="s3_스테이지3",
        broadcast_name="스테이지3",
    )
    # s3_승리: no transition (game ends, space ignored).


def load_source(prefix: str, sb3_path: Path, workdir: Path) -> dict[str, Any]:
    """Unzip an .sb3 and return {prefix, project, assets_dir}."""
    extract_to = workdir / prefix
    extract_to.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(sb3_path) as zf:
        zf.extractall(extract_to)
    with open(extract_to / "project.json", encoding="utf-8") as f:
        project = json.load(f)
    return {"prefix": prefix, "project": project, "dir": extract_to}


def remap_blocks(
    blocks: dict[str, Any],
    var_id_map: dict[str, str],
    broadcast_id_map: dict[str, str],
    sprite_name_map: dict[str, str],
    backdrop_name_map: dict[str, str] | None = None,
) -> None:
    """Rewrite variable IDs, broadcast IDs, sprite-name and backdrop-name fields in-place."""
    backdrop_name_map = backdrop_name_map or {}
    for _bid, block in blocks.items():
        if not isinstance(block, dict):
            # Top-level reporter shadow: list form. We don't touch.
            continue

        opcode = block.get("opcode", "")
        fields = block.get("fields", {}) or {}
        inputs = block.get("inputs", {}) or {}

        # ---- Fields: variables, broadcasts, sprite menus, backdrop menus ----
        for fname, fval in list(fields.items()):
            if not isinstance(fval, list) or len(fval) < 2:
                continue
            name, ref_id = fval[0], fval[1]

            # Variable references: VARIABLE field holds [name, var_id]
            if fname == "VARIABLE" and isinstance(ref_id, str):
                if ref_id in var_id_map:
                    fields[fname] = [name, var_id_map[ref_id]]
                continue
            # List references would go here similarly (none in source).

            # Broadcast references in fields (e.g. event_whenbroadcastreceived's
            # BROADCAST_OPTION = [name, broadcast_id])
            if fname in ("BROADCAST_OPTION",) and isinstance(ref_id, str):
                if ref_id in broadcast_id_map:
                    fields[fname] = [name, broadcast_id_map[ref_id]]
                continue

            # Backdrop name fields (looks_backdrops menu, event_whenbackdropswitchesto hat).
            if (opcode in BACKDROP_NAME_OPCODES
                    and fname == "BACKDROP"
                    and isinstance(name, str)
                    and name in backdrop_name_map):
                fields[fname] = [backdrop_name_map[name], ref_id]
                continue

            # Sprite-name fields: ref_id is None and name is the sprite name.
            menu_field = SPRITE_NAME_FIELDS.get(opcode)
            if menu_field and fname == menu_field and isinstance(name, str):
                if name in sprite_name_map:
                    fields[fname] = [sprite_name_map[name], ref_id]

        # ---- Inputs: variable/list/broadcast reporters embedded as primitives.
        # Format: input_name -> [shadow_type, primitive_or_block_id, ...]
        # primitive forms:
        #   [11, broadcast_name, broadcast_id]  -> broadcast
        #   [12, var_name, var_id]              -> variable
        #   [13, list_name, list_id]            -> list
        for iname, ival in list(inputs.items()):
            if not isinstance(ival, list):
                continue
            for i, slot in enumerate(ival):
                if not isinstance(slot, list) or not slot:
                    continue
                tag = slot[0]
                if tag == 12 and len(slot) >= 3 and isinstance(slot[2], str):
                    if slot[2] in var_id_map:
                        slot[2] = var_id_map[slot[2]]
                elif tag == 13 and len(slot) >= 3 and isinstance(slot[2], str):
                    # lists (none used, but handle defensively)
                    pass
                elif tag == 11 and len(slot) >= 3 and isinstance(slot[2], str):
                    if slot[2] in broadcast_id_map:
                        slot[2] = broadcast_id_map[slot[2]]

        # ---- Backdrop name literals inlined in switch_backdrop_to inputs.
        # Common builders inline `backdrop("이름")` as inputs={"BACKDROP":[1,[10,"이름"]]}
        # instead of using a looks_backdrops menu block, so handle it here.
        if opcode in ("looks_switchbackdropto", "looks_switchbackdroptoandwait"):
            bd_input = inputs.get("BACKDROP")
            if (isinstance(bd_input, list) and len(bd_input) >= 2
                    and isinstance(bd_input[1], list) and len(bd_input[1]) >= 2
                    and bd_input[1][0] == 10
                    and isinstance(bd_input[1][1], str)
                    and bd_input[1][1] in backdrop_name_map):
                bd_input[1][1] = backdrop_name_map[bd_input[1][1]]


def merge() -> dict[str, Any]:
    workdir = Path(tempfile.mkdtemp(prefix="mariomerge_"))
    try:
        sources = [load_source(p, REPO_ROOT / fn, workdir) for p, fn in SOURCES]

        # ---- Asset bucket: filename -> source path (last wins; identical bytes) ----
        assets: dict[str, Path] = {}
        for src in sources:
            for fp in src["dir"].iterdir():
                if fp.name == "project.json":
                    continue
                assets[fp.name] = fp

        # ---- Unified variables/broadcasts across all Stages ----
        # Map name -> canonical id (we keep the first occurrence's id).
        unified_var_name_to_id: dict[str, str] = {}
        unified_var_defs: dict[str, list[Any]] = {}  # id -> [name, value]
        unified_broadcast_name_to_id: dict[str, str] = {}
        unified_broadcast_defs: dict[str, str] = {}  # id -> name

        # First pass: walk each Stage and build unified id mappings.
        per_src_var_id_map: list[dict[str, str]] = []
        per_src_broadcast_id_map: list[dict[str, str]] = []

        for src in sources:
            project = src["project"]
            stage = next(t for t in project["targets"] if t.get("isStage"))

            var_map: dict[str, str] = {}
            for old_vid, vinfo in stage.get("variables", {}).items():
                vname = vinfo[0]
                vvalue = vinfo[1]
                if vname in unified_var_name_to_id:
                    new_vid = unified_var_name_to_id[vname]
                else:
                    new_vid = old_vid
                    unified_var_name_to_id[vname] = new_vid
                    unified_var_defs[new_vid] = [vname, vvalue]
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

        # ---- Build sprite-name rename maps (per source) ----
        # The Stage keeps the name "Stage". Other sprites get prefixed with
        # f"{src_prefix}_". This means each stage's "Mario" becomes a distinct
        # sprite ("intro_Mario", "s1_Mario", ...) — intentional.
        per_src_sprite_name_map: list[dict[str, str]] = []
        for src in sources:
            project = src["project"]
            name_map: dict[str, str] = {}
            for t in project["targets"]:
                if t.get("isStage"):
                    continue
                old_name = t["name"]
                new_name = f"{src['prefix']}_{old_name}"
                name_map[old_name] = new_name
            per_src_sprite_name_map.append(name_map)

        # ---- Build backdrop-name rename maps (per source) ----
        # Intro's backdrops keep their names (intro is the game's first screen).
        # Stage1/2/3 backdrops get prefixed (s1_/s2_/s3_) so that duplicate
        # names like "클리어" or "시작화면" don't collide in the merged Stage.
        # All `backdrop("클리어")` calls inside e.g. Stage1's blocks will be
        # rewritten to `backdrop("s1_클리어")` automatically.
        per_src_backdrop_name_map: list[dict[str, str]] = []
        for src in sources:
            project = src["project"]
            stage = next(t for t in project["targets"] if t.get("isStage"))
            name_map: dict[str, str] = {}
            for c in stage.get("costumes", []):
                old_name = c["name"]
                if src["prefix"] == "intro":
                    new_name = old_name
                else:
                    new_name = f"{src['prefix']}_{old_name}"
                name_map[old_name] = new_name
            per_src_backdrop_name_map.append(name_map)

        # ---- Build merged Stage target ----
        # Concatenate backdrops, dedupe by costume name within Stage.
        merged_costumes: list[dict[str, Any]] = []
        seen_costume_keys: set[tuple[str, str]] = set()
        merged_stage_blocks: dict[str, Any] = {}
        merged_stage_comments: dict[str, Any] = {}

        for idx, src in enumerate(sources):
            project = src["project"]
            stage = next(t for t in project["targets"] if t.get("isStage"))
            backdrop_map = per_src_backdrop_name_map[idx]

            # Backdrops: rename per-source, keep order; uniqueness key = (new_name, md5ext).
            for c in stage.get("costumes", []):
                c_copy = dict(c)
                old_name = c_copy["name"]
                c_copy["name"] = backdrop_map.get(old_name, old_name)
                key = (c_copy["name"], c_copy.get("md5ext", ""))
                if key in seen_costume_keys:
                    continue
                seen_costume_keys.add(key)
                merged_costumes.append(c_copy)

            # Remap and merge Stage blocks.
            stage_blocks = json.loads(json.dumps(stage.get("blocks", {})))
            remap_blocks(
                stage_blocks,
                per_src_var_id_map[idx],
                per_src_broadcast_id_map[idx],
                per_src_sprite_name_map[idx],
                backdrop_map,
            )
            # Block IDs are random-looking; collisions are extremely unlikely,
            # but rename if needed by prefixing with source prefix.
            block_id_rename: dict[str, str] = {}
            for old_bid in list(stage_blocks.keys()):
                if old_bid in merged_stage_blocks:
                    new_bid = f"{src['prefix']}_{old_bid}"
                    block_id_rename[old_bid] = new_bid
            if block_id_rename:
                renamed: dict[str, Any] = {}
                for old_bid, blk in stage_blocks.items():
                    new_bid = block_id_rename.get(old_bid, old_bid)
                    if isinstance(blk, dict):
                        # update parent/next references
                        if blk.get("parent") in block_id_rename:
                            blk["parent"] = block_id_rename[blk["parent"]]
                        if blk.get("next") in block_id_rename:
                            blk["next"] = block_id_rename[blk["next"]]
                    renamed[new_bid] = blk
                stage_blocks = renamed
            merged_stage_blocks.update(stage_blocks)

            # Merge stage comments (rare).
            for cid, c in stage.get("comments", {}).items():
                if cid in merged_stage_comments:
                    cid = f"{src['prefix']}_{cid}"
                merged_stage_comments[cid] = c

        # Construct unified Stage target structure based on intro's Stage.
        intro_stage = next(t for t in sources[0]["project"]["targets"] if t.get("isStage"))
        merged_stage_target: dict[str, Any] = {
            "isStage": True,
            "name": "Stage",
            "variables": {
                vid: list(vdef) for vid, vdef in unified_var_defs.items()
            },
            "lists": intro_stage.get("lists", {}),
            "broadcasts": dict(unified_broadcast_defs),
            "blocks": merged_stage_blocks,
            "comments": merged_stage_comments,
            "currentCostume": 0,  # intro's first backdrop (시작화면)
            "costumes": merged_costumes,
            "sounds": intro_stage.get("sounds", []),
            "volume": intro_stage.get("volume", 100),
            "layerOrder": 0,
            "tempo": intro_stage.get("tempo", 60),
            "videoTransparency": intro_stage.get("videoTransparency", 50),
            "videoState": intro_stage.get("videoState", "on"),
            "textToSpeechLanguage": intro_stage.get("textToSpeechLanguage", None),
        }

        # ---- Merge non-stage sprites ----
        merged_sprites: list[dict[str, Any]] = []
        next_layer = 1

        # When remapping a sprite's blocks, sprite-name references should map
        # using ALL sources' rename maps (e.g. Mario in stage1 references
        # "Plat1" which is now "s1_Plat1"). But each stage's sprites only ever
        # reference sprites from its OWN stage (Scratch projects are
        # self-contained). So we use the source's own sprite_name_map only.

        for idx, src in enumerate(sources):
            project = src["project"]
            var_map = per_src_var_id_map[idx]
            bc_map = per_src_broadcast_id_map[idx]
            name_map = per_src_sprite_name_map[idx]

            backdrop_map = per_src_backdrop_name_map[idx]
            for t in project["targets"]:
                if t.get("isStage"):
                    continue
                sprite = json.loads(json.dumps(t))  # deep copy
                sprite["name"] = name_map[sprite["name"]]

                # remap blocks: variable IDs (stage-scoped), broadcast IDs,
                # sprite-name menu fields, and backdrop-name fields.
                remap_blocks(sprite.get("blocks", {}), var_map, bc_map, name_map, backdrop_map)

                # ensure unique layerOrder
                sprite["layerOrder"] = next_layer
                next_layer += 1

                merged_sprites.append(sprite)

        # ---- Post-merge wiring ----
        # 1) Hide every non-intro sprite at flag-click start.
        n_hidden = hide_non_intro_sprites_at_start(merged_sprites)
        # 2) Intro sprites disappear when backdrop reaches "인트로끝".
        n_intro_hats = add_intro_hide_hats(merged_sprites, "인트로끝")
        # 3) Space-press transition hats wiring intro→s1→s2→s3.
        add_all_transition_space_hats(merged_stage_target)

        # ---- Assemble final project ----
        merged_project: dict[str, Any] = {
            "targets": [merged_stage_target] + merged_sprites,
            "monitors": [],
            "extensions": [],
            "meta": sources[0]["project"].get("meta", {
                "semver": "3.0.0",
                "vm": "1.0.0",
                "agent": "merge_sb3.py",
            }),
        }

        # ---- Write out MarioGame.sb3 ----
        out_dir = Path(tempfile.mkdtemp(prefix="mariomerge_out_"))
        try:
            project_json_path = out_dir / "project.json"
            with open(project_json_path, "w", encoding="utf-8") as f:
                json.dump(merged_project, f, ensure_ascii=False)

            # Copy assets into out_dir
            for fname, fpath in assets.items():
                shutil.copyfile(fpath, out_dir / fname)

            # Zip
            if OUTPUT.exists():
                OUTPUT.unlink()
            with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(project_json_path, "project.json")
                for fname in assets:
                    zf.write(out_dir / fname, fname)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

        # ---- Verification summary ----
        info = {
            "output": str(OUTPUT),
            "size_bytes": OUTPUT.stat().st_size,
            "n_targets": len(merged_project["targets"]),
            "sprites": [t["name"] for t in merged_project["targets"]],
            "n_assets": len(assets),
            "n_backdrops": len(merged_costumes),
            "backdrops": [c["name"] for c in merged_costumes],
            "n_variables": len(unified_var_defs),
            "variables": [v[0] for v in unified_var_defs.values()],
            "n_broadcasts": len(unified_broadcast_defs),
            "broadcasts": list(unified_broadcast_defs.values()),
            "n_sprites_hidden_at_start": n_hidden,
            "n_intro_hide_hats": n_intro_hats,
        }
        return info
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main() -> int:
    info = merge()
    print(json.dumps(info, ensure_ascii=False, indent=2))

    # Sanity check: re-open the output and validate project.json parses.
    with zipfile.ZipFile(OUTPUT) as zf:
        names = zf.namelist()
        assert "project.json" in names, "project.json missing in output"
        with zf.open("project.json") as f:
            parsed = json.load(f)
        assert parsed["targets"][0]["isStage"], "first target must be Stage"
        # Every costume's md5ext must exist as an entry in the zip
        zip_names = set(names)
        missing = []
        for t in parsed["targets"]:
            for c in t.get("costumes", []):
                if c.get("md5ext") and c["md5ext"] not in zip_names:
                    missing.append((t["name"], c["name"], c["md5ext"]))
            for s in t.get("sounds", []):
                if s.get("md5ext") and s["md5ext"] not in zip_names:
                    missing.append((t["name"], s["name"], s["md5ext"]))
        if missing:
            print("MISSING ASSETS:")
            for m in missing:
                print(" ", m)
            return 1
    print("Verification: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

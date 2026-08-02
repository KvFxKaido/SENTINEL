#!/usr/bin/env python3
"""Rotoscope reference: an articulated mannequin walking, rendered at the
canon body scale for tracing over (2026-08-02).

Runs INSIDE Blender (needs bpy), headless. Nothing here ships as art — it
produces the layer a pixel artist traces on top of.

WHY THIS EXISTS. Generated animation could not hold a walk: five attempts
gave same-side arms, facing drift, a 1px bob, a visible loop seam, and one
facing out of four (scripts/pixellab_cipher.json "dead_ends"). Every one of
those is a solved equation once there is a rig:

    contralateral swing   arm phase = its OWN leg's phase + pi
    vertical bob          abs(sin), so it peaks twice per stride
    loop closure          the cycle IS a sine; the last frame wraps exactly
    facing stability      the camera orbits; the body never turns

Validated at the source, not from pixels — see --validate. Reading phase off
projected pixel bands is strictly worse evidence than reading the joint
rotations we set: on a 45-degree view the limbs overlap in x and a band
metric reports the arms in phase with the legs when the rig guarantees they
are not (measured: +0.86 on SE while the rig read -1.0000).

Usage:
    blender --background --python scripts/roto_mannequin.py
    blender --background --python scripts/roto_mannequin.py -- --validate

Env:
    ROTO_OUT      output dir            ROTO_FRAMES   frames per cycle (8)
    ROTO_FACING   S SE E NE N NW W SW   ROTO_SCALE    camera ortho scale
"""
import json
import math
import os
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

OUT = os.environ.get("ROTO_OUT", ".")
N = int(os.environ.get("ROTO_FRAMES", "8"))
FACING = os.environ.get("ROTO_FACING", "S")
# ortho_scale maps to the LARGER render dimension (96), so body height scales
# inversely with it. 2.89 was calibrated by rendering and MEASURING, not by
# arithmetic: it puts the body at 34px, matching canon exactly.
SCALE = float(os.environ.get("ROTO_SCALE", "2.89"))

RES_W, RES_H = 96, 80          # the pack's canvas
CANON_GROUND_ROW = 58          # canon's last opaque row is 57
SWING_LEG = math.radians(26)
SWING_ARM = math.radians(18)
BOB = 0.045
ELEV = math.radians(26)
AZIMUTH = {"S": 0, "SE": 45, "E": 90, "NE": 135,
           "N": 180, "NW": 225, "W": 270, "SW": 315}


def clean():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials):
        for b in list(block):
            block.remove(b)


def box(name, size, loc, parent=None, pivot=None):
    """A limb segment. `pivot` moves the object origin to the JOINT: a leg
    swings from the hip, not from the middle of the thigh."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = tuple(s / 2 for s in size)
    if pivot is not None:
        for v in ob.data.vertices:
            v.co.z -= pivot
    if parent:
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()
    return ob


def build():
    """Roughly the pack's 2.3-head figure, in blocks."""
    clean()
    HEAD, TORSO, LIMB = 0.34, 0.46, 0.42
    root = bpy.data.objects.new("root", None)
    bpy.context.collection.objects.link(root)
    parts = {
        "torso": box("torso", (0.30, 0.18, TORSO), (0, 0, 0.62), root),
        "head": box("head", (HEAD, HEAD * 0.8, HEAD), (0, 0, 1.00), root),
        "arm_L": box("arm_L", (0.10, 0.10, LIMB), (-0.22, 0, 0.60), root, LIMB / 2),
        "arm_R": box("arm_R", (0.10, 0.10, LIMB), (0.22, 0, 0.60), root, LIMB / 2),
        "leg_L": box("leg_L", (0.12, 0.12, LIMB), (-0.09, 0, 0.20), root, LIMB / 2),
        "leg_R": box("leg_R", (0.12, 0.12, LIMB), (0.09, 0, 0.20), root, LIMB / 2),
    }
    mat = bpy.data.materials.new("flat")
    mat.use_nodes = False
    mat.diffuse_color = (0.75, 0.75, 0.78, 1)
    for ob in parts.values():
        ob.data.materials.append(mat)
    parts["root"] = root
    return parts


def animate(parts, n=N):
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, n
    for i in range(n):
        th = 2 * math.pi * (i / n)
        parts["leg_L"].rotation_euler = (math.sin(th) * SWING_LEG, 0, 0)
        parts["leg_R"].rotation_euler = (math.sin(th + math.pi) * SWING_LEG, 0, 0)
        # each arm opposes its SAME-SIDE leg. This one line is the whole
        # reason the rig route exists.
        parts["arm_L"].rotation_euler = (math.sin(th + math.pi) * SWING_ARM, 0, 0)
        parts["arm_R"].rotation_euler = (math.sin(th) * SWING_ARM, 0, 0)
        parts["root"].location = (0, 0, abs(math.sin(th)) * BOB)
        for k in ("leg_L", "leg_R", "arm_L", "arm_R"):
            parts[k].keyframe_insert("rotation_euler", frame=i + 1)
        parts["root"].keyframe_insert("location", frame=i + 1)


def place_camera(facing):
    R = 6.0
    a = math.radians(AZIMUTH[facing])
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = SCALE
    cam.location = (R * math.sin(a) * math.cos(ELEV),
                    -R * math.cos(a) * math.cos(ELEV),
                    R * math.sin(ELEV) + 0.55)
    d = Vector((0, 0, 0.62)) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def configure_render():
    bpy.ops.object.light_add(type="SUN", location=(3, -5, 7))
    bpy.context.object.data.energy = 3.0
    r = bpy.context.scene.render
    r.resolution_x, r.resolution_y = RES_W, RES_H
    r.resolution_percentage = 100
    r.film_transparent = True
    r.filter_size = 0.0          # no reconstruction blur — hard pixel edges
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.engine = "BLENDER_WORKBENCH"
    bpy.context.scene.display.shading.light = "FLAT"
    bpy.context.scene.display.shading.color_type = "MATERIAL"
    return r


def validate(parts, n=N):
    """Read the gait from the RIG. This is the claim's real evidence."""
    import statistics as st

    def corr(a, b):
        ma, mb = st.mean(a), st.mean(b)
        va = sum((x - ma) ** 2 for x in a) ** 0.5
        vb = sum((x - mb) ** 2 for x in b) ** 0.5
        return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (va * vb)

    scene = bpy.context.scene
    rot = {k: [] for k in ("leg_L", "leg_R", "arm_L", "arm_R")}
    bob = []
    for i in range(n):
        scene.frame_set(i + 1)
        bpy.context.view_layer.update()
        for k in rot:
            rot[k].append(parts[k].rotation_euler.x)
        bob.append(parts["root"].location.z)
    peaks = sum(1 for i in range(1, len(bob) - 1)
                if bob[i] >= bob[i - 1] and bob[i] >= bob[i + 1])
    checks = [
        ("left arm opposes left leg", corr(rot["arm_L"], rot["leg_L"]), -1.0),
        ("right arm opposes right leg", corr(rot["arm_R"], rot["leg_R"]), -1.0),
        ("left arm matches right leg", corr(rot["arm_L"], rot["leg_R"]), 1.0),
        ("legs are antiphase", corr(rot["leg_L"], rot["leg_R"]), -1.0),
    ]
    bad = 0
    for name, got, want in checks:
        ok = abs(got - want) < 1e-6
        bad += not ok
        print(f'{"PASS" if ok else "FAIL"}  {name}: {got:+.4f} (want {want:+.1f})')
    ok = peaks == 2
    bad += not ok
    print(f'{"PASS" if ok else "FAIL"}  bob peaks twice per stride: {peaks}')
    print("\nALL PASS" if not bad else f"\n{bad} FAILURES")
    return bad


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parts = build()
    animate(parts)
    if "--validate" in argv:
        return validate(parts)

    cam = place_camera(FACING)
    r = configure_render()
    os.makedirs(OUT, exist_ok=True)

    # The anchor comes from the RIG's ground origin, never from a frame's
    # silhouette. Per-frame silhouette anchoring subtracts a different amount
    # each frame (measured: S by 0,0,+1,0,0,0,+1,0 and E by -2,-1,0,-1,...),
    # which does not hide the bob — it EDITS it, differently per facing.
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    ndc = world_to_camera_view(bpy.context.scene, cam, Vector((0.0, 0.0, 0.0)))
    ground_row = (1.0 - ndc.y) * RES_H
    with open(os.path.join(OUT, f"ground_{FACING}.json"), "w") as fh:
        json.dump({"facing": FACING, "ground_row": ground_row, "frames": N,
                   "res": [RES_W, RES_H], "canon_ground_row": CANON_GROUND_ROW}, fh)

    for i in range(N):
        bpy.context.scene.frame_set(i + 1)
        r.filepath = os.path.join(OUT, f"roto_{FACING}_{i + 1:02d}.png")
        bpy.ops.render.render(write_still=True)
    print(f"ROTO_DONE {FACING} {N} ground_row={ground_row:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)

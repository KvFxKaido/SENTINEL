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

--validate is this file's ONLY guardrail and nothing in CI runs it: it needs
bpy, and the repo has no Blender job. Run it by hand after touching build(),
animate(), kneel() or settle(), or the checks below protect nothing.

Env:
    ROTO_OUT      output dir            ROTO_FRAMES   frames per cycle (8)
    ROTO_FACING   S SE E NE N NW W SW   ROTO_SCALE    camera ortho scale
    ROTO_POSE     walk | kneel          (rejected if unrecognised, never
                                         quietly downgraded to the walk)

Output goes to ROTO_OUT/{pose}/, one DIRECTORY per pose, holding
roto_{pose}_{facing}_{NN}.png and ground_{pose}_{facing}.json.

The directory is the part that matters. anchor_strip.py takes a src dir and
globs every PNG in it, sorted, applying one shared translation from a single
ground JSON — so a walk and a kneel sharing a directory get anchored as one
strip no matter what the files are called ("kneel" even sorts first). Distinct
names alone only prevent frame 01 from being overwritten; they do not stop the
mixing, which is why the pose owns the directory. The names stay pose-scoped
anyway, so a file that escapes its directory still says what it is.
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
POSE = os.environ.get("ROTO_POSE", "walk")   # walk | kneel
# ortho_scale maps to the LARGER render dimension (96), so body height scales
# inversely with it. 3.50 was calibrated by rendering and MEASURING, not by
# arithmetic: it puts the body at 34px, matching canon exactly. (It was 2.89
# while every part was accidentally half-size; fixing the geometry made the
# figure taller, so the camera had to pull back.)
SCALE = float(os.environ.get("ROTO_SCALE", "3.50"))

RES_W, RES_H = 96, 80          # the pack's canvas
# ortho_scale spans the LARGER dimension, so this converts figure units to
# rendered pixels. It is what lets a claim written in units ("under a pixel")
# be checked in the unit it actually claims.
PX_PER_UNIT = RES_W / SCALE
POSES = ("walk", "kneel")
# The row the FEET occupy, not the empty row beneath them: canon's standing
# verbs put their last opaque row at 57, and the rig's z=0 plane is where the
# soles sit, so the projection of z=0 must land on 57 to match.
CANON_GROUND_ROW = 57
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


def box(name, size, loc, parent=None, hang=False):
    """A block of exactly `size` world units.

    primitive_cube_add(size=1) spans +/-0.5, i.e. ONE unit across, so the
    object scale is `size` — not size/2. Halving it (the first version) made
    every part half its intended dimension and opened a 0.18-unit gap between
    torso and head: a disconnected mannequin that still validated, because
    the check read Euler angles and never looked at geometry.

    `hang=True` shifts the mesh down by its LOCAL half-extent (0.5, before
    scaling) so the object origin sits on the segment's TOP face. The object
    is then placed at the joint, and the limb hangs from it — a leg swings
    from the hip, not from a point inside the thigh. Offsetting by a
    figure-space value here instead is the bug fugu caught: it gets scaled
    again and lands ~0.044 units from centre, well inside the segment.
    """
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    if hang:
        for v in ob.data.vertices:
            v.co.z -= 0.5
    ob.scale = tuple(size)
    if parent:
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()
    return ob


def build():
    """Roughly the pack's 2.3-head figure, in blocks."""
    clean()
    # Anatomy from the ground up, so the parts actually meet:
    #   legs   0.00 .. 0.42   (hip at 0.42, limb hangs down)
    #   torso  0.42 .. 0.88
    #   arms   0.42 .. 0.84   (shoulder at 0.84)
    #   head   0.88 .. 1.22
    LIMB, TORSO_H, HEAD_H = 0.42, 0.46, 0.34
    HIP_Z, SHOULDER_Z = 0.42, 0.84
    root = bpy.data.objects.new("root", None)
    bpy.context.collection.objects.link(root)
    # Limbs are TWO segments. A single-segment leg cannot kneel — it can only
    # shorten, which is precisely the failure mode of the row-surgery kneel it
    # is meant to improve on (that one reads as a shorter man, not a crouching
    # one; see roster_mold.kneel_frames). The lower segment hangs from the
    # upper, so a knee bend is one rotation on a child.
    SEG = LIMB / 2
    parts = {
        "torso": box("torso", (0.30, 0.18, TORSO_H), (0, 0, HIP_Z + TORSO_H / 2), root),
        "head": box("head", (HEAD_H, HEAD_H * 0.8, HEAD_H),
                    (0, 0, HIP_Z + TORSO_H + HEAD_H / 2), root),
        "arm_L": box("arm_L", (0.10, 0.10, SEG), (-0.20, 0, SHOULDER_Z), root, hang=True),
        "arm_R": box("arm_R", (0.10, 0.10, SEG), (0.20, 0, SHOULDER_Z), root, hang=True),
        "leg_L": box("leg_L", (0.12, 0.12, SEG), (-0.08, 0, HIP_Z), root, hang=True),
        "leg_R": box("leg_R", (0.12, 0.12, SEG), (0.08, 0, HIP_Z), root, hang=True),
    }
    for side, x in (("L", -0.20), ("R", 0.20)):
        parts[f"fore_{side}"] = box(f"fore_{side}", (0.10, 0.10, SEG),
                                    (x, 0, SHOULDER_Z - SEG), parts[f"arm_{side}"], hang=True)
    for side, x in (("L", -0.08), ("R", 0.08)):
        parts[f"shin_{side}"] = box(f"shin_{side}", (0.12, 0.12, SEG),
                                    (x, 0, HIP_Z - SEG), parts[f"leg_{side}"], hang=True)
    # Colour-separated limbs. Once the parts actually touch, a single-material
    # figure renders as one undifferentiated blob at 34px and cannot be traced
    # — you cannot tell an arm from the torso it is flush against. Distinct
    # flat colours make the articulation readable at target size. Borrowed
    # from the Vinchy top-down template, which does exactly this and is the
    # one genuinely reusable idea in it.
    PALETTE = {
        "head": (0.92, 0.78, 0.60, 1),
        "torso": (0.35, 0.55, 0.85, 1),
        "arm_L": (0.85, 0.30, 0.30, 1),   # near arm  — warm
        "arm_R": (0.55, 0.35, 0.75, 1),   # far arm   — violet
        "leg_L": (0.35, 0.70, 0.40, 1),   # near leg  — green
        "leg_R": (0.90, 0.50, 0.70, 1),   # far leg   — pink
    }
    # lower segments take a darker shade of their parent so the JOINT reads
    PALETTE.update({k.replace("arm", "fore").replace("leg", "shin"):
                    tuple(c * 0.72 if i < 3 else c for i, c in enumerate(v))
                    for k, v in PALETTE.items() if k.startswith(("arm", "leg"))})
    for name, ob in parts.items():
        mat = bpy.data.materials.new(f"flat_{name}")
        mat.use_nodes = False
        mat.diffuse_color = PALETTE[name]
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


# Sign convention, stated once because guessing it cost a pose. A limb built
# with hang=True runs along local -Z, and a rotation of th about X sends it to
# (0, sin th, -cos th): POSITIVE pitches it toward +Y, NEGATIVE toward -Y. The
# camera for any facing sits on the -Y side (place_camera), so -Y is the
# direction the figure faces:
#
#     negative = FORWARD (toward camera)      positive = BACK
#
# The torso reads inverted only because it is not a hanging limb — its origin
# is its centre, so its +Z top swings the other way and +9 leans it forward.
# Child segments share the X axis with their parent, so a shin's world pitch is
# simply thigh + shin.
#
FORWARD, BACK = -1, 1

# THE HEAD-ON PROBLEM, and why the fix is split across two knobs.
#
# A one-knee kneel is built entirely in the sagittal plane. A camera on that
# plane projects the whole fold onto a line, so `down` — the facing preview()
# ships as the representative frame — rendered as a shorter standing man: the
# exact failure roster_mold.kneel_frames already bought once. It is the
# RELATIVE angle that is degenerate, so either side can move. Measured, at 96x80:
#
#   option                     bbox   leg-band rows showing two limbs
#   cardinal camera + pose      14px   5/15   unreadable
#   lead-knee splay only        14px   5/15   no change at ANY angle: the arms
#                                             are the widest part of the figure,
#                                             so a knee moves inside a silhouette
#                                             it never defined. REMOVED.
#   action-plane yaw only       17px   9/15   best leg separation, still reads
#                                             flat — head and torso stay frontal
#   camera nudge only           17px   7/15   reads, but every depth cue is paid
#                                             for in orientation continuity
#   BOTH (12 + 20)              19px   9/15   shipped
#
# Note the third row: it wins the metric and loses the read. Leg separation is
# not legibility, and nothing here — not these numbers, not validate_kneel —
# measures whether the pose reads at 34px. That judgement stayed human.
#
# Yaw is NEGATIVE so the lead leg (pointing -Y) swings further from the midline
# and the trail shin (+Y) swings the other way, opening the pair. Positive
# closes it: measured, knee separation fell 0.160 -> 0.074 at +20 because the
# lead leg crosses the body. Arms ride along, and that is load-bearing rather
# than cosmetic — with the legs alone the metric never moved off 5/15.
KNEEL_PLANE_YAW = -20
# Facings whose view axis lies IN the sagittal plane. The profiles (left/right,
# and every diagonal) already show the fold and are left exactly cardinal.
KNEEL_FACING_NUDGE = {"S": 12, "N": 12}


def world_bounds(ob):
    """(z_min, (dx, dy, dz)) of `ob`'s geometry in world space.

    Read from the transformed bound_box, not from the object origin: a limb's
    origin sits at its JOINT, so origins alone say nothing about where the
    metal actually is. The ground checks care about the lowest face; the
    EXTENTS are what separate a shin lying along the ground from one merely
    touching it at a corner, which a z_min alone cannot tell apart.

    Extents are returned per-axis rather than as y-vs-z because the kneel's
    action plane yaws (KNEEL_PLANE_YAW): a shin that lies flat now runs partly
    along X, and a check written as "y beats z" would read that as standing up.
    Horizontality is `max(dx, dy) > dz`, which no yaw can fool.
    """
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    return (min(zs), (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)))


def settle(parts):
    """Drop the root until the lowest geometry rests exactly on z=0.

    The height a fold costs is a function of every angle above it, so writing
    it as a literal is a claim that silently rots the moment a joint moves —
    the previous constant buried both shins ~0.1 units under the floor while
    the docstring said they rested on it. Measure it instead: the pose sits on
    the ground by construction, for any angles.
    """
    parts["root"].location = (0, 0, 0)
    bpy.context.view_layer.update()
    lowest = min(world_bounds(ob)[0] for name, ob in parts.items()
                 if name != "root")
    parts["root"].location = (0, 0, -lowest)
    bpy.context.view_layer.update()
    return -lowest


def kneel(parts):
    """A one-knee-down kneel: the pose row surgery cannot reach.

    Compressing an idle frame vertically shortens a standing man; it cannot
    fold a leg, pitch a torso, or move an arm to a raised knee. That is why
    roster_mold's kneel_frames needed a hem flare to sell a crouch its
    geometry never performed. Here the knee simply bends.

    R is the TRAIL leg: thigh near vertical, knee down and BACK, shin folded
    to horizontal so it lies along the ground behind. L is the LEAD leg: thigh
    swung FORWARD to near horizontal, knee up, shin dropped vertical onto a
    planted foot. Both contact points — trailing shin, leading sole — land
    within a pixel of each other, so the figure rests on the pair rather than
    balancing on one and hovering the other.
    """
    d = math.radians
    parts["leg_R"].rotation_euler = (BACK * d(14), 0, 0)     # trail thigh, near vertical
    parts["shin_R"].rotation_euler = (BACK * d(76), 0, 0)    # folds to horizontal behind
    parts["leg_L"].rotation_euler = (FORWARD * d(74), 0, 0)  # lead thigh, near horizontal
    parts["shin_L"].rotation_euler = (BACK * d(74), 0, 0)    # back to vertical: sole plants
    parts["arm_R"].rotation_euler = (BACK * d(10), 0, 0)
    parts["fore_R"].rotation_euler = (BACK * d(14), 0, 0)
    parts["arm_L"].rotation_euler = (FORWARD * d(22), 0, 0)  # reaches toward the raised knee
    parts["fore_L"].rotation_euler = (FORWARD * d(30), 0, 0)
    # The torso pitches about its own centre and the head is parented to root,
    # not to it, so the head does NOT follow. Kept small for that reason: at
    # 9 degrees the top face shifts ~0.036 units, under a pixel at canon scale.
    parts["torso"].rotation_euler = (d(9), 0, 0)             # a little weight forward
    # Yaw the whole action plane — limbs only. Head, torso and shoulder joints
    # stay square to the facing, so the figure still looks where it is aimed.
    for name in ("leg_L", "leg_R", "arm_L", "arm_R"):
        e = parts[name].rotation_euler
        parts[name].rotation_euler = (e.x, e.y, d(KNEEL_PLANE_YAW))
    settle(parts)


def place_camera(facing, nudge=0):
    """`nudge` steps the camera off the cardinal azimuth (see
    KNEEL_FACING_NUDGE). It cannot disturb the ground contract: the camera
    orbits at fixed radius and elevation about a fixed target, so the
    projection of the world origin — and therefore ground_row — is invariant
    under azimuth by symmetry. Asserted at the call site, not just here.
    """
    R = 6.0
    a = math.radians(AZIMUTH[facing] + nudge)
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
    # Flush before returning. world_to_camera_view reads matrix_world, and a
    # camera built after the last depsgraph flush still carries an identity
    # transform: it projects the world origin to dead centre, row 40 of 80.
    # That is what the ground-row drift check first "caught" — its own second
    # camera, not the nudge.
    bpy.context.view_layer.update()
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
    # CYCLIC neighbours: the walk is a loop, so the first and last samples
    # have neighbours too. A non-cyclic range drops them and miscounts at
    # small frame counts — at ROTO_FRAMES=4 the samples are [0,max,0,max] and
    # a range(1, n-1) scan reports one peak for a gait that plainly has two.
    peaks = sum(1 for i in range(len(bob))
                if bob[i] >= bob[i - 1] and bob[i] >= bob[(i + 1) % len(bob)])
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


def validate_kneel(parts):
    """Read the POSE from the rig. Same evidence rule as the walk.

    Every check here is a sentence the docstring already claimed. The two that
    earned their place by failing: the trail knee sat FORWARD of the hip and
    the lead knee BACK, because the angles were written with the sign
    convention inverted and the comments beside them asserted the opposite;
    and both shins hung ~0.1 units below the floor under a hardcoded drop that
    prose described as resting on it. Neither is visible in a joint-angle
    dump — you have to ask where the geometry LANDED.
    """
    bpy.context.view_layer.update()
    hip_z = 0.42 + parts["root"].location.z
    knee = {s: parts[f"shin_{s}"].matrix_world.translation for s in "LR"}
    box_ = {name: world_bounds(ob) for name, ob in parts.items() if name != "root"}
    ground = {name: b[0] for name, b in box_.items()}
    lowest = min(ground.values())

    def span(name):
        """(horizontal_extent, vertical_extent) — which way the part LIES.

        Horizontal is max(dx, dy), not dy: KNEEL_PLANE_YAW turns the action
        plane, so a flat shin runs partly along X and a dy-vs-dz test would
        report it standing up.
        """
        dx, dy, dz = box_[name][1]
        return max(dx, dy), dz

    def pitch(name):
        return parts[name].rotation_euler.x

    # Every prose claim that carries a unit gets converted here rather than
    # narrated. 0.036 units "under a pixel" is 0.99px — true, but close enough
    # to the limit that it must not drift silently.
    gap_px = abs(ground["shin_R"] - ground["shin_L"]) * PX_PER_UNIT
    lean_px = (0.46 / 2) * math.sin(pitch("torso")) * PX_PER_UNIT
    checks = [
        # settle() forces this, so it is a guard on settle(), not pose evidence.
        # Kept as ONE check: `abs(lowest) < tol` already implies no penetration.
        ("the figure rests exactly on the ground", abs(lowest) < 1e-4,
         f"lowest z={lowest:+.4f}"),
        ("trailing shin is on the ground", abs(ground["shin_R"]) < 0.02,
         f"shin_R z={ground['shin_R']:+.4f}"),
        ("leading sole is on the ground", abs(ground["shin_L"]) < 0.02,
         f"shin_L z={ground['shin_L']:+.4f}"),
        # z_min alone cannot tell "lies along the ground" from "touches it with
        # one corner" — the docstring claims the former, so measure the extents.
        ("trailing shin LIES flat on the ground", span("shin_R")[0] > span("shin_R")[1],
         "horiz={:.3f} > vert={:.3f}".format(*span("shin_R"))),
        ("leading shin STANDS upright", span("shin_L")[1] > span("shin_L")[0],
         "vert={:.3f} > horiz={:.3f}".format(span("shin_L")[1], span("shin_L")[0])),
        ("both contacts land within a pixel", gap_px < 1.0, f"{gap_px:.2f} px apart"),
        # The action-plane yaw's whole job: open the knees ACROSS the screen so
        # a head-on camera has something to project. Unyawed this measures
        # 0.160 and the pose reads as a standing man, so the threshold sits
        # above that — a yaw silently reverting to 0 must fail here.
        ("the action plane is yawed open", abs(knee["L"].x - knee["R"].x) > 0.20,
         f"knees {abs(knee['L'].x - knee['R'].x):.3f} apart in x (cardinal 0.160)"),
        ("trail knee is BACK of the hip", knee["R"].y > 0.01, f"y={knee['R'].y:+.3f}"),
        ("lead knee is FORWARD of the hip", knee["L"].y < -0.01, f"y={knee['L'].y:+.3f}"),
        ("trail knee is below the lead knee", knee["R"].z < knee["L"].z - 0.05,
         f"R={knee['R'].z:+.3f} L={knee['L'].z:+.3f}"),
        # The whole reason the second segment exists: a fold, not a shortening.
        # These read back angles kneel() just set, so they are regression guards
        # rather than independent evidence — the extent checks above are the
        # ones that would catch a fold that did not actually happen.
        ("trail knee is bent", abs(pitch("shin_R")) > math.radians(20),
         f"{math.degrees(pitch('shin_R')):+.0f} deg"),
        ("lead knee is bent", abs(pitch("shin_L")) > math.radians(20),
         f"{math.degrees(pitch('shin_L')):+.0f} deg"),
        # A kneel is lower than a stand; row surgery could fake only this one.
        ("the hip has dropped", hip_z < 0.30, f"hip z={hip_z:+.3f} (standing 0.420)"),
        ("the head's debt to the torso lean stays sub-pixel", abs(lean_px) < 1.0,
         f"{lean_px:+.2f} px"),
    ]
    bad = 0
    for name, ok, detail in checks:
        bad += not ok
        print(f'{"PASS" if ok else "FAIL"}  {name}: {detail}')
    print("\nALL PASS" if not bad else f"\n{bad} FAILURES")
    return bad


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    # No silent fallback. A typo in ROTO_POSE previously rendered the WALK
    # while printing the misspelling back, so the output looked like the pose
    # you asked for and was not (design philosophy 3: honest and awkward beats
    # pleasant and misleading).
    if POSE not in POSES:
        print(f"ROTO_POSE={POSE!r} is not one of {POSES}", file=sys.stderr)
        return 2
    parts = build()
    if POSE == "kneel":
        kneel(parts)
    else:
        animate(parts)
    if "--validate" in argv:
        return validate_kneel(parts) if POSE == "kneel" else validate(parts)

    nudge = KNEEL_FACING_NUDGE.get(FACING, 0) if POSE == "kneel" else 0
    cam = place_camera(FACING, nudge)
    r = configure_render()
    os.makedirs(OUT, exist_ok=True)

    # The anchor comes from the RIG's ground origin, never from a frame's
    # silhouette. Per-frame silhouette anchoring subtracts a different amount
    # each frame (measured: S by 0,0,+1,0,0,0,+1,0 and E by -2,-1,0,-1,...),
    # which does not hide the bob — it EDITS it, differently per facing.
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    def ground_row_of(camera):
        ndc = world_to_camera_view(bpy.context.scene, camera, Vector((0.0, 0.0, 0.0)))
        return (1.0 - ndc.y) * RES_H

    ground_row = ground_row_of(cam)
    if nudge:
        # The nudge is only affordable because it does not move the anchor. That
        # is a claim about a projection, so measure it: build the camera this
        # facing WOULD have had and compare. Cheaper to check than to debug a
        # kneel that anchors one row off every other verb.
        cardinal = place_camera(FACING, 0)
        drift = abs(ground_row_of(cardinal) - ground_row)
        bpy.data.objects.remove(cardinal, do_unlink=True)
        bpy.context.scene.camera = cam
        # A thousandth of a row. Not a fudge to get green: the orbit is
        # azimuth-symmetric so true drift is ZERO, and what remains is float
        # noise in the trig — measured 4e-5. This threshold sits ~25x above the
        # noise and ~15000x below the only real failure seen here (a stale
        # camera matrix, which drifts by 15.36 rows).
        if drift > 1e-3:
            print(f"nudge moved ground_row by {drift:.6f} rows", file=sys.stderr)
            return 3
    # The POSE owns a directory. Previously every pose wrote roto_{FACING}_01
    # into one dir, so a 1-frame kneel over an 8-frame walk left frame 01
    # kneeling and 02-08 walking. Pose-scoped NAMES alone stop that overwrite
    # but not the real failure: anchor_strip.py globs its whole src dir, so it
    # would still gather all nine files and anchor them as one strip. Only the
    # directory split actually separates them. The sidecar's `frames` is the
    # count written, not N — it said 8 for a pose that renders 1.
    frames = 1 if POSE == "kneel" else N
    pose_dir = os.path.join(OUT, POSE)
    os.makedirs(pose_dir, exist_ok=True)
    with open(os.path.join(pose_dir, f"ground_{POSE}_{FACING}.json"), "w") as fh:
        json.dump({"pose": POSE, "facing": FACING, "ground_row": ground_row,
                   "frames": frames, "res": [RES_W, RES_H],
                   "canon_ground_row": CANON_GROUND_ROW}, fh)

    for i in range(frames):
        if POSE != "kneel":
            bpy.context.scene.frame_set(i + 1)
        r.filepath = os.path.join(pose_dir, f"roto_{POSE}_{FACING}_{i + 1:02d}.png")
        bpy.ops.render.render(write_still=True)
    print(f"ROTO_DONE {POSE} {FACING} {frames} ground_row={ground_row:.2f} "
          f"dir={pose_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)

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
    ROTO_POSE     walk | kneel | aim    (rejected if unrecognised, never
                                         quietly downgraded to the walk)

Output goes to ROTO_OUT/{pose}/, one DIRECTORY per pose, holding
roto_{pose}_{facing}_{NN}.png, ground_{pose}_{facing}.json and
sockets_{pose}_{facing}.json — the weapon-socket export the armed verbs
gate on (doc D2, open item 1): per-frame hand positions in anchored
sheet pixels, forearm direction, and the camera-relative draw-order bit.

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
POSE = os.environ.get("ROTO_POSE", "walk")   # walk | kneel | aim
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
POSES = ("walk", "kneel", "aim")
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


# The hand is the transformed centre of the forearm's BOTTOM face. In object
# space that point is (0, 0, -1): box() spans -0.5..+0.5, hang=True shifts the
# mesh down to -1..0, and the object scale carries it one segment below the
# elbow the origin sits on. Same fact that makes a fore_* origin an ELBOW
# (doc D2, caught in review) — read from the other end. validate() holds this
# constant against the actual geometry, so a change to hang or the box
# convention fails there instead of silently exporting mid-forearm sockets.
HAND_LOCAL = Vector((0.0, 0.0, -1.0))


def hand_points(parts, side):
    """(elbow, hand) of fore_{side} in world space."""
    m = parts[f"fore_{side}"].matrix_world
    return m.translation.copy(), m @ HAND_LOCAL


def hand_geometry_error(parts, side):
    """Distance between HAND_LOCAL's claim and the measured bottom face.

    The bound_box is object space, so the bottom face is the four corners at
    minimal z; their centre pushed through matrix_world is where the geometry
    says the hand is. Zero by construction today; non-zero the moment anyone
    changes hang= or the cube convention without updating HAND_LOCAL.
    """
    ob = parts[f"fore_{side}"]
    z_min = min(v[2] for v in ob.bound_box)
    bottom = [Vector(v) for v in ob.bound_box if abs(v[2] - z_min) < 1e-9]
    centre = sum(bottom, Vector()) / len(bottom)
    return ((ob.matrix_world @ centre) - (ob.matrix_world @ HAND_LOCAL)).length


def socket_frame(scene, cam, parts):
    """Both hand sockets for the CURRENT frame, in raw render pixels.

    px/row are the space of the rendered PNG (x right, y down); main()
    shifts rows into anchored sheet coordinates when it writes the sidecar
    — the identical translation anchor_strip applies to the frames, so
    sockets and pixels stay glued. `dir` is the unit vector along the
    forearm, elbow toward hand, in that same pixel space: orientation
    without an angle convention to misread. `depth` is how far the hand
    sits in FRONT of the torso centre in camera units (negative = behind);
    `in_front` is its sign, the draw-order bit for a weapon sprite. The
    magnitude ships too because a hanging arm ties with the torso to
    within noise, and a consumer deciding layers deserves to see how thin
    the margin is rather than trust a coin-flip boolean.
    """
    torso_depth = world_to_camera_view(
        scene, cam, parts["torso"].matrix_world.translation).z
    out = {}
    for side in "LR":
        elbow, hand = hand_points(parts, side)
        e = world_to_camera_view(scene, cam, elbow)
        h = world_to_camera_view(scene, cam, hand)
        dx = (h.x - e.x) * RES_W
        dy = (e.y - h.y) * RES_H
        length = math.hypot(dx, dy) or 1.0
        # in_front derives from the SAME rounded value the sidecar ships,
        # so the two fields can never disagree — the hanging-arm tie the
        # docstring warns about would otherwise let sub-precision noise
        # decide the bit (caught in review). A tie within the exported
        # precision reads as BEHIND, deterministically.
        depth = round(torso_depth - h.z, 4)
        out[f"hand_{side}"] = {
            "px": h.x * RES_W,
            "row": (1.0 - h.y) * RES_H,
            "dir": [round(dx / length, 4), round(dy / length, 4)],
            "depth": depth,
            "in_front": depth > 0,
        }
    return out


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


def aim(parts):
    """A one-handed standing aim: the anatomical RIGHT arm extends level
    along the facing, the off arm hangs, the legs keep their standing rest.

    The dialect source is the licensed thug pack's gunplay, by way of
    roster_mold's own synthesis notes: "the arm is the pose, the flash is
    the verb." The composed roster's AIM is NOT the reference — compose
    cannot repose a limb, so it lifted HEAL's held-at-chest grip and swapped
    the vial for the emitter, and its side grids are drawn barrel-right and
    MIRRORED for left. That was archaeology, not taste; the rig exists to
    perform the pose the reference actually shows.

    Chirality is set here and it is a decision, not a label: this figure
    faces -Y, so its anatomical right hand is the -X side — the part the rig
    names arm_L (the sockets sidecar already warns the names are the RIG's
    sides, not anatomy's). A generated state holds one hand across every
    rotation, which is a dialect upgrade the composed mirror cheat could
    never afford — and it means the far-arm facing exists and must simply
    read, as the thug pack's own 8-facing gunplay proves it can.

    Head-on the arm foreshortens to a glint beside the torso, and that is
    the read, not a failure: the shoulder sits at |x| = 0.20 against a
    torso half-width of 0.15, so the hand clears the silhouette by
    construction and the pose borrows neither of the kneel's legibility
    knobs (no plane yaw, no camera nudge). The forearm direction IS the
    muzzle line — what FIRE will aim its bloom along.
    """
    d = math.radians
    parts["arm_L"].rotation_euler = (FORWARD * d(90), 0, 0)  # level, along -Y
    parts["fore_L"].rotation_euler = (0, 0, 0)   # straight: this IS the muzzle line
    # The off side and the legs are named so the pose owns every joint it
    # claims — "the rest is standing rest" is a sentence validate_aim checks,
    # not an accident of build()'s defaults surviving.
    parts["arm_R"].rotation_euler = (0, 0, 0)
    parts["fore_R"].rotation_euler = (0, 0, 0)
    for name in ("leg_L", "leg_R", "shin_L", "shin_R"):
        parts[name].rotation_euler = (0, 0, 0)
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
    # The socket contract, held against geometry rather than restated. At
    # frame 1 the walk's phase puts both arms at zero swing (sin 0 and
    # sin pi), so the hands must hang BELOW their elbows — a cheap read
    # that catches an inverted HAND_LOCAL the face-centre check cannot
    # (a sign flip lands on the TOP face centre, which is also a face).
    scene.frame_set(1)
    bpy.context.view_layer.update()
    for side in "LR":
        err = hand_geometry_error(parts, side)
        ok = err < 1e-6
        bad += not ok
        print(f'{"PASS" if ok else "FAIL"}  hand_{side} is the forearm\'s '
              f'bottom-face centre: off by {err:.6f}')
        elbow, hand = hand_points(parts, side)
        ok = hand.z < elbow.z - 0.05
        bad += not ok
        print(f'{"PASS" if ok else "FAIL"}  hand_{side} hangs below its '
              f'elbow at zero swing: hand z={hand.z:+.3f} elbow z={elbow.z:+.3f}')
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
    # The socket contract holds in the fold too: the geometry read must
    # still agree with HAND_LOCAL under the kneel's rotations, and the lead
    # hand must actually be where the docstring sends it — forward, toward
    # the raised knee — not just rotated by an angle that sounds right.
    elbow_L, hand_L = hand_points(parts, "L")
    checks += [
        ("hand sockets sit on the bottom-face centre in the fold",
         max(hand_geometry_error(parts, s) for s in "LR") < 1e-6,
         f"max off {max(hand_geometry_error(parts, s) for s in 'LR'):.6f}"),
        ("the lead hand reaches FORWARD of its elbow",
         hand_L.y < elbow_L.y - 0.02,
         f"hand y={hand_L.y:+.3f} elbow y={elbow_L.y:+.3f}"),
    ]
    bad = 0
    for name, ok, detail in checks:
        bad += not ok
        print(f'{"PASS" if ok else "FAIL"}  {name}: {detail}')
    print("\nALL PASS" if not bad else f"\n{bad} FAILURES")
    return bad


def validate_aim(parts):
    """Read the POSE from the rig. Same evidence rule as the walk and kneel:
    every sentence the aim() docstring claims, converted to a measurement.

    The one check with a job beyond regression-guarding is the silhouette
    clearance: it is the whole reason the pose needs no yaw and no nudge,
    and it is exactly the claim a well-meaning "slim the shoulders" edit
    would silently break — the head-on facings would go from a glint beside
    the torso to a hand buried inside it, and no joint-angle dump would say
    so.
    """
    bpy.context.view_layer.update()
    hip_z = 0.42 + parts["root"].location.z
    shoulder_z = 0.84 + parts["root"].location.z
    lowest = min(world_bounds(ob)[0] for name, ob in parts.items()
                 if name != "root")
    elbow_L, hand_L = hand_points(parts, "L")   # the AIM arm: anatomical right
    elbow_R, hand_R = hand_points(parts, "R")   # the off arm
    axis = (hand_L - elbow_L).normalized()
    # Standing rest is enforced as GEOMETRY, not as angle readback: a hip
    # bending about any axis moves the knee off its standing coordinates,
    # and a bent shin lifts its foot — where the metal LANDED, not what the
    # eulers say (a shin-X-only read let hips and Y/Z rotations pass,
    # caught in review). Standing knee: hip (±0.08, 0, 0.42) minus one SEG.
    knee = {s: parts[f"shin_{s}"].matrix_world.translation for s in "LR"}
    knee_err = max((knee[s] - Vector((x, 0.0, 0.21))).length
                   for s, x in (("L", -0.08), ("R", 0.08)))
    foot_lift = max(world_bounds(parts[f"shin_{s}"])[0] for s in "LR")
    # The off hand at rest hangs one full arm below its shoulder:
    # (0.20, 0, 0.42). Position, not "below the elbow" — a swung arm keeps
    # its hand below the elbow for most of a swing (caught in review).
    off_err = (hand_R - Vector((0.20, 0.0, 0.42 + parts["root"].location.z))).length
    checks = [
        # settle() forces this, so it is a guard on settle(), not pose evidence.
        ("the figure rests exactly on the ground", abs(lowest) < 1e-4,
         f"lowest z={lowest:+.4f}"),
        # Aim is a STANDING verb. The kneel drops this below 0.30; a pose
        # edit that starts crouching the aim must announce itself here.
        ("the figure stands at full height", abs(hip_z - 0.42) < 0.01,
         f"hip z={hip_z:+.3f} (standing 0.420, kneel < 0.300)"),
        ("both knees sit at standing rest", knee_err < 0.02,
         f"max knee offset {knee_err:.3f} units"),
        ("both feet rest on the ground", foot_lift < 0.01,
         f"highest sole z={foot_lift:+.4f}"),
        ("the aim arm is LEVEL", abs(hand_L.z - elbow_L.z) < 0.02,
         f"hand z={hand_L.z:+.3f} elbow z={elbow_L.z:+.3f}"),
        ("the muzzle line runs along the facing", axis.y < -0.999,
         f"axis=({axis.x:+.3f}, {axis.y:+.3f}, {axis.z:+.3f})"),
        ("the aim hand reaches FORWARD of the body", hand_L.y < -0.25,
         f"hand y={hand_L.y:+.3f} (torso front face -0.090)"),
        ("the aim hand holds shoulder height", abs(hand_L.z - shoulder_z) < 0.02,
         f"hand z={hand_L.z:+.3f} shoulder z={shoulder_z:+.3f}"),
        ("the aim hand clears the torso silhouette head-on",
         abs(hand_L.x) > 0.15,
         f"hand x={hand_L.x:+.3f} (torso half-width 0.150)"),
        ("the off hand hangs at standing rest", off_err < 0.02,
         f"off by {off_err:.3f} units from (0.20, 0, 0.42)"),
        # The socket contract holds under the aim's rotations: the muzzle
        # declaration is only worth exporting if the hand is still the
        # forearm's bottom-face centre once the arm is horizontal.
        ("hand sockets sit on the bottom-face centre in the aim",
         max(hand_geometry_error(parts, s) for s in "LR") < 1e-6,
         f"max off {max(hand_geometry_error(parts, s) for s in 'LR'):.6f}"),
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
    elif POSE == "aim":
        aim(parts)
    else:
        animate(parts)
    if "--validate" in argv:
        if POSE == "kneel":
            return validate_kneel(parts)
        if POSE == "aim":
            return validate_aim(parts)
        return validate(parts)

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
    frames = N if POSE == "walk" else 1   # held poses render one frame
    pose_dir = os.path.join(OUT, POSE)
    os.makedirs(pose_dir, exist_ok=True)
    with open(os.path.join(pose_dir, f"ground_{POSE}_{FACING}.json"), "w") as fh:
        json.dump({"pose": POSE, "facing": FACING, "ground_row": ground_row,
                   "frames": frames, "res": [RES_W, RES_H],
                   "canon_ground_row": CANON_GROUND_ROW}, fh)

    sockets = []
    for i in range(frames):
        if POSE == "walk":
            bpy.context.scene.frame_set(i + 1)
            # the render evaluates its own depsgraph, but socket_frame reads
            # matrix_world directly — same stale-matrix trap the drift guard's
            # second camera fell into (see place_camera)
            bpy.context.view_layer.update()
        sockets.append(socket_frame(bpy.context.scene, cam, parts))
        r.filepath = os.path.join(pose_dir, f"roto_{POSE}_{FACING}_{i + 1:02d}.png")
        bpy.ops.render.render(write_still=True)

    # Anchor the sockets with the SAME translation anchor_strip applies to
    # the frames — including its INTEGER quantisation: PNGs move by whole
    # rows (floor(target - raw + 0.5), anchor_strip.py line 44, half-up
    # matching pack_canvas), so shifting sockets by the exact fractional
    # delta would unglue them from the anchored pixels by up to half a row
    # (caught in review). Vertical only, raw ground row onto the canon row.
    # A socket that lands off the canvas after anchoring is a camera or
    # pose fault — the body is 34px on a 96x80 canvas, so a hand has no
    # honest way out.
    shift = math.floor(CANON_GROUND_ROW - ground_row + 0.5)
    for f in sockets:
        for hand in f.values():
            hand["row"] = round(hand["row"] + shift, 2)
            hand["px"] = round(hand["px"], 2)
            if not (0 <= hand["px"] <= RES_W and 0 <= hand["row"] <= RES_H):
                print(f"socket off canvas after anchoring: {hand}", file=sys.stderr)
                return 4
    with open(os.path.join(pose_dir, f"sockets_{POSE}_{FACING}.json"), "w") as fh:
        json.dump({"pose": POSE, "facing": FACING, "res": [RES_W, RES_H],
                   "space": "anchored sheet pixels: x right, y down, ground "
                            "on canon_ground_row — the frames' own anchor "
                            "translation, applied to points",
                   "canon_ground_row": CANON_GROUND_ROW,
                   "raw_ground_row": ground_row,
                   "handedness": "hand_L/hand_R are the RIG's sides; which "
                                 "edge of the screen they land on is the "
                                 "facing's business",
                   "frames": sockets}, fh)
    print(f"ROTO_DONE {POSE} {FACING} {frames} ground_row={ground_row:.2f} "
          f"dir={pose_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)

# Headless logic check for the Close Contact harness — execute the
# claim: every assertion here is a review finding that was fixed, run
# as the thing that would fail if the fix were fiction.
#
#   godot --headless --path prototypes/close-contact --script res://tests/logic_check.gd
#
# Not wired into CI (CI has no Godot runtime); run it after touching
# Main.gd. Exit code is the verdict.
extends SceneTree

var failed := 0

func check(ok: bool, label: String) -> void:
	print(("PASS " if ok else "FAIL ") + label)
	if not ok:
		failed += 1

func _init() -> void:
	var MainScript = load("res://Main.gd")
	var m = MainScript.new()
	var FighterCls = MainScript.Fighter

	# rig: attacker's HIGH in its active phase, defender ducking in range
	var att = FighterCls.new("A", Vector2(320, 520))
	var def = FighterCls.new("B", Vector2(400, 520))
	att.facing = 1
	def.facing = -1
	def.crouch = true
	m._start_attack(att, "LP")
	att.attack["timer"] = att.attack["startup"]
	check(m._attack_phase(att.attack) == "ACTIVE", "rig: LP reaches its active phase")

	# the high whiffs over the duck by law, and its drawn box clears the
	# crouch silhouette — the picture and the law agree
	check(m._combat_result(att, def).is_empty(), "HIGH vs crouch: no contact, by height law")
	var high_box: Rect2 = m._get_attack_hitbox(att, att.attack)
	var crouch_box: Rect2 = m._get_hurtbox(def, false)
	check(not high_box.intersects(crouch_box), "HIGH hitbox clears the crouching silhouette on screen")

	# the duck-counter window opens on that near-miss (was dead code)
	m._update_duck_counter_window(att, def)
	check(def.duck_counter_window == m.DUCK_COUNTER_WINDOW, "duck-counter window opens on a ducked HIGH")

	# and the counter resolves: the attacker eats the punish
	def.duck_counter_attempt = true
	m._resolve_duck_counter(att, def)
	check(att.attack.is_empty() and att.hitstun == m.DUCK_COUNTER_HITSTUN, "duck counter lands — attacker punished")

	# mirrored clean hits trade — no player-order bias
	var a = FighterCls.new("A", Vector2(600, 520))
	var b = FighterCls.new("B", Vector2(660, 520))
	a.facing = 1
	b.facing = -1
	m._start_attack(a, "LK")
	m._start_attack(b, "LK")
	a.attack["timer"] = a.attack["startup"]
	b.attack["timer"] = b.attack["startup"]
	m._resolve_combat_pair(a, b)
	check(a.hitstun > 0 and b.hitstun > 0, "simultaneous clean hits trade — both fighters pay")

	# block + limb is the parry input: reserved, inert, never a normal
	var c = FighterCls.new("C", Vector2(100, 520))
	var held_block := {"left": false, "right": false, "up": false, "down": false, "block": true, "attack_id": "LP"}
	m._update_fighter(c, held_block, 1.0 / 60.0)
	check(c.attack.is_empty() and c.block, "block+limb stays a block — parry input reserved, no misfire")

	m.free()
	print("RESULT: " + ("ALL PASS" if failed == 0 else str(failed) + " FAILURES"))
	quit(1 if failed > 0 else 0)

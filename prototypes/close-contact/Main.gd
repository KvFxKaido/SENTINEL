extends Node2D

const SCREEN_W := 1280
const SCREEN_H := 720
const GROUND_Y := 520

const BODY_W := 50.0
const BODY_H := 100.0
const CROUCH_H := 60.0

const WALK_FWD := 240.0
const WALK_BACK := 180.0

const DUCK_COUNTER_WINDOW := 6
const DUCK_COUNTER_HITSTUN := 16
const DUCK_COUNTER_PUSH := 28.0

const COLOR_BG := Color(0.04, 0.06, 0.08)
const COLOR_GROUND := Color(0.12, 0.15, 0.18)
const COLOR_P1 := Color(0.16, 0.63, 0.60)
const COLOR_P2 := Color(0.86, 0.20, 0.18)
const COLOR_BLOCK := Color(0.35, 0.35, 0.90)
const COLOR_HIT := Color(1.0, 0.75, 0.25)
const COLOR_HURTBOX := Color(1.0, 1.0, 1.0, 0.08)
const COLOR_HITBOX := Color(1.0, 1.0, 1.0, 0.25)

const ATTACKS := {
	"LP": {"height": "HIGH", "startup": 6, "active": 3, "recovery": 10, "range": 40.0, "hitstun": 12, "blockstun": 8, "push": 22.0},
	"RP": {"height": "MID", "startup": 7, "active": 3, "recovery": 11, "range": 42.0, "hitstun": 13, "blockstun": 8, "push": 23.0},
	"LK": {"height": "LOW", "startup": 8, "active": 3, "recovery": 12, "range": 55.0, "hitstun": 14, "blockstun": 9, "push": 26.0},
	"RK": {"height": "LOW", "startup": 8, "active": 3, "recovery": 12, "range": 55.0, "hitstun": 14, "blockstun": 9, "push": 26.0}
}

const P1_KEYS := {
	"left": KEY_LEFT,
	"right": KEY_RIGHT,
	"up": KEY_UP,
	"down": KEY_DOWN,
	"lp": KEY_U,
	"rp": KEY_I,
	"lk": KEY_J,
	"rk": KEY_K,
	"block": KEY_SPACE
}

const P2_KEYS := {
	"left": KEY_A,
	"right": KEY_D,
	"up": KEY_W,
	"down": KEY_S,
	"lp": KEY_T,
	"rp": KEY_Y,
	"lk": KEY_G,
	"rk": KEY_H,
	"block": KEY_SHIFT
}

class Fighter:
	var name: String
	var pos := Vector2.ZERO
	var facing := 1
	var state := "NEUTRAL"
	var crouch := false
	var block := false
	var attack: Dictionary = {}
	var hitstun := 0
	var blockstun := 0
	var duck_counter_window := 0
	var duck_counter_attempt := false
	var last_event := ""
	var last_event_timer := 0
	var last_attack := ""

	func _init(n: String, p: Vector2) -> void:
		name = n
		pos = p

var p1: Fighter
var p2: Fighter

@onready var p1_label: Label = $UI/P1Label
@onready var p2_label: Label = $UI/P2Label

func _ready() -> void:
	p1 = Fighter.new("P1", Vector2(320, GROUND_Y))
	p2 = Fighter.new("P2", Vector2(960, GROUND_Y))
	_update_facing()

func _physics_process(delta: float) -> void:
	var p1_input = _read_input(P1_KEYS)
	var p2_input = _read_input(P2_KEYS)

	_update_fighter(p1, p1_input, delta)
	_update_fighter(p2, p2_input, delta)

	_update_duck_counter_window(p1, p2)
	_update_duck_counter_window(p2, p1)
	_resolve_duck_counter(p1, p2)
	_resolve_duck_counter(p2, p1)
	_resolve_combat(p1, p2)
	_resolve_combat(p2, p1)

	_apply_pushbox()
	_update_facing()

	_tick_events(p1)
	_tick_events(p2)
	_tick_duck_counter(p1)
	_tick_duck_counter(p2)
	_update_labels()
	queue_redraw()

func _read_input(keys: Dictionary) -> Dictionary:
	var input := {
		"left": Input.is_key_pressed(keys["left"]),
		"right": Input.is_key_pressed(keys["right"]),
		"up": Input.is_key_pressed(keys["up"]),
		"down": Input.is_key_pressed(keys["down"]),
		"block": Input.is_key_pressed(keys["block"]),
		"attack_id": ""
	}
	if Input.is_key_pressed(keys["lp"]):
		input.attack_id = "LP"
	elif Input.is_key_pressed(keys["rp"]):
		input.attack_id = "RP"
	elif Input.is_key_pressed(keys["lk"]):
		input.attack_id = "LK"
	elif Input.is_key_pressed(keys["rk"]):
		input.attack_id = "RK"
	return input

func _update_fighter(f: Fighter, input: Dictionary, delta: float) -> void:
	f.duck_counter_attempt = false
	if f.hitstun > 0:
		f.hitstun -= 1
		f.state = "HITSTUN"
		f.block = false
		f.attack = {}
		f.duck_counter_window = 0
		return
	if f.blockstun > 0:
		f.blockstun -= 1
		f.state = "BLOCKSTUN"
		f.block = false
		f.attack = {}
		f.duck_counter_window = 0
		return

	if not f.attack.is_empty():
		f.block = false
		f.crouch = false
		f.state = "ATTACK"
		f.attack["timer"] += 1
		if _attack_phase(f.attack) == "DONE":
			if not f.attack["has_hit"] and not f.attack["has_block"]:
				_set_event(f, "WHIFF")
			f.attack = {}
			f.state = "NEUTRAL"
		return

	if input.attack_id != "":
		if f.crouch and f.duck_counter_window > 0:
			f.duck_counter_attempt = true
			return
		_start_attack(f, input.attack_id)
		return

	f.crouch = input.down
	if f.crouch:
		f.block = false
		f.state = "CROUCH"
	else:
		f.block = input.block
		f.state = "BLOCK" if f.block else "NEUTRAL"
		var dir := int(input.right) - int(input.left)
		if dir != 0:
			var speed := WALK_FWD if dir == f.facing else WALK_BACK
			f.pos.x += dir * speed * delta

	f.pos.x = clampf(f.pos.x, BODY_W * 0.5, SCREEN_W - BODY_W * 0.5)

func _start_attack(f: Fighter, attack_id: String) -> void:
	var base: Dictionary = ATTACKS[attack_id]
	f.attack = {
		"id": attack_id,
		"height": base["height"],
		"startup": base["startup"],
		"active": base["active"],
		"recovery": base["recovery"],
		"range": base["range"],
		"hitstun": base["hitstun"],
		"blockstun": base["blockstun"],
		"push": base["push"],
		"timer": 0,
		"has_hit": false,
		"has_block": false
	}
	f.last_attack = attack_id
	f.block = false
	f.crouch = false
	f.state = "ATTACK"

func _attack_phase(attack: Dictionary) -> String:
	var t: int = attack["timer"]
	if t < attack["startup"]:
		return "STARTUP"
	if t < attack["startup"] + attack["active"]:
		return "ACTIVE"
	if t < attack["startup"] + attack["active"] + attack["recovery"]:
		return "RECOVERY"
	return "DONE"

func _resolve_combat(attacker: Fighter, defender: Fighter) -> void:
	if attacker.attack.is_empty():
		return
	if _attack_phase(attacker.attack) != "ACTIVE":
		return
	if attacker.attack["has_hit"] or attacker.attack["has_block"]:
		return

	if attacker.attack["height"] == "HIGH" and defender.crouch:
		return

	var hitbox := _get_attack_hitbox(attacker, attacker.attack)
	var hurtbox := _get_hurtbox(defender, false)
	if not hitbox.intersects(hurtbox):
		return

	var blocked := defender.block and not defender.crouch
	if blocked:
		defender.blockstun = attacker.attack["blockstun"]
		defender.attack = {}
		_set_event(defender, "BLOCK")
		_set_event(attacker, "BLOCKED")
		attacker.attack["has_block"] = true
		_apply_pushback(attacker, defender, attacker.attack, true)
	else:
		defender.hitstun = attacker.attack["hitstun"]
		defender.attack = {}
		_set_event(defender, "HIT")
		_set_event(attacker, "HIT")
		attacker.attack["has_hit"] = true
		_apply_pushback(attacker, defender, attacker.attack, false)

func _apply_pushback(attacker: Fighter, defender: Fighter, attack: Dictionary, blocked: bool) -> void:
	var push: float = float(attack["push"])
	if blocked:
		push *= 0.7
	defender.pos.x += attacker.facing * push
	attacker.pos.x -= attacker.facing * (push * 0.3)
	defender.pos.x = clampf(defender.pos.x, BODY_W * 0.5, SCREEN_W - BODY_W * 0.5)
	attacker.pos.x = clampf(attacker.pos.x, BODY_W * 0.5, SCREEN_W - BODY_W * 0.5)

func _apply_counter_push(attacker: Fighter, defender: Fighter) -> void:
	defender.pos.x += attacker.facing * DUCK_COUNTER_PUSH
	attacker.pos.x -= attacker.facing * (DUCK_COUNTER_PUSH * 0.35)
	defender.pos.x = clampf(defender.pos.x, BODY_W * 0.5, SCREEN_W - BODY_W * 0.5)
	attacker.pos.x = clampf(attacker.pos.x, BODY_W * 0.5, SCREEN_W - BODY_W * 0.5)

func _apply_pushbox() -> void:
	var p1_box := _get_hurtbox(p1, false)
	var p2_box := _get_hurtbox(p2, false)
	if not p1_box.intersects(p2_box):
		return
	if p1.pos.x < p2.pos.x:
		var overlap := (p1.pos.x + BODY_W * 0.5) - (p2.pos.x - BODY_W * 0.5)
		if overlap > 0:
			p1.pos.x -= overlap * 0.5
			p2.pos.x += overlap * 0.5
	else:
		var overlap := (p2.pos.x + BODY_W * 0.5) - (p1.pos.x - BODY_W * 0.5)
		if overlap > 0:
			p2.pos.x -= overlap * 0.5
			p1.pos.x += overlap * 0.5

	p1.pos.x = clampf(p1.pos.x, BODY_W * 0.5, SCREEN_W - BODY_W * 0.5)
	p2.pos.x = clampf(p2.pos.x, BODY_W * 0.5, SCREEN_W - BODY_W * 0.5)

func _get_hurtbox(f: Fighter, force_stand: bool) -> Rect2:
	var h := BODY_H if force_stand else (CROUCH_H if f.crouch else BODY_H)
	return Rect2(Vector2(f.pos.x - BODY_W * 0.5, f.pos.y - h), Vector2(BODY_W, h))

func _get_attack_hitbox(f: Fighter, attack: Dictionary) -> Rect2:
	var y_top := f.pos.y - BODY_H
	var y_bottom := f.pos.y
	match attack["height"]:
		"HIGH":
			y_top = f.pos.y - BODY_H
			y_bottom = f.pos.y - BODY_H * 0.5
		"MID":
			y_top = f.pos.y - BODY_H * 0.75
			y_bottom = f.pos.y - BODY_H * 0.25
		"LOW":
			y_top = f.pos.y - BODY_H * 0.25
			y_bottom = f.pos.y

	var x_left := 0.0
	var x_right := 0.0
	if f.facing == 1:
		x_left = f.pos.x + BODY_W * 0.5
		x_right = x_left + attack["range"]
	else:
		x_right = f.pos.x - BODY_W * 0.5
		x_left = x_right - attack["range"]
	return Rect2(Vector2(x_left, y_top), Vector2(x_right - x_left, y_bottom - y_top))

func _set_event(f: Fighter, event_name: String) -> void:
	f.last_event = event_name
	f.last_event_timer = 0

func _update_duck_counter_window(attacker: Fighter, defender: Fighter) -> void:
	if defender.duck_counter_window > 0:
		return
	if attacker.attack.is_empty():
		return
	if _attack_phase(attacker.attack) != "ACTIVE":
		return
	if attacker.attack["height"] != "HIGH":
		return
	if not defender.crouch:
		return
	var hitbox := _get_attack_hitbox(attacker, attacker.attack)
	var stand_box := _get_hurtbox(defender, true)
	var crouch_box := _get_hurtbox(defender, false)
	if hitbox.intersects(stand_box) and not hitbox.intersects(crouch_box):
		defender.duck_counter_window = DUCK_COUNTER_WINDOW

func _resolve_duck_counter(attacker: Fighter, defender: Fighter) -> void:
	if defender.duck_counter_window <= 0:
		return
	if not defender.duck_counter_attempt:
		return
	if attacker.attack.is_empty():
		return
	if _attack_phase(attacker.attack) != "ACTIVE":
		return
	if attacker.attack["height"] != "HIGH":
		return
	var hitbox := _get_attack_hitbox(attacker, attacker.attack)
	var stand_box := _get_hurtbox(defender, true)
	var crouch_box := _get_hurtbox(defender, false)
	if not hitbox.intersects(stand_box):
		return
	if hitbox.intersects(crouch_box):
		return

	attacker.attack = {}
	attacker.hitstun = DUCK_COUNTER_HITSTUN
	attacker.state = "HITSTUN"
	defender.duck_counter_window = 0
	_set_event(defender, "DUCK COUNTER")
	_set_event(attacker, "COUNTERED")
	_apply_counter_push(defender, attacker)

func _tick_events(f: Fighter) -> void:
	if f.last_event != "":
		f.last_event_timer += 1
		if f.last_event_timer > 120:
			f.last_event = ""

func _tick_duck_counter(f: Fighter) -> void:
	if not f.crouch:
		f.duck_counter_window = 0
		return
	if f.duck_counter_window > 0:
		f.duck_counter_window -= 1

func _update_facing() -> void:
	if p1.pos.x <= p2.pos.x:
		p1.facing = 1
		p2.facing = -1
	else:
		p1.facing = -1
		p2.facing = 1

func _update_labels() -> void:
	var p1_dc := " DC" + str(p1.duck_counter_window) if p1.duck_counter_window > 0 else ""
	var p2_dc := " DC" + str(p2.duck_counter_window) if p2.duck_counter_window > 0 else ""
	p1_label.text = "P1 " + p1.state + " | " + p1.last_event + p1_dc
	p2_label.text = "P2 " + p2.state + " | " + p2.last_event + p2_dc

func _draw() -> void:
	draw_rect(Rect2(0, 0, SCREEN_W, GROUND_Y), COLOR_BG, true)
	draw_rect(Rect2(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y), COLOR_GROUND, true)

	_draw_fighter(p1, COLOR_P1)
	_draw_fighter(p2, COLOR_P2)

	if not p1.attack.is_empty() and _attack_phase(p1.attack) == "ACTIVE":
		draw_rect(_get_attack_hitbox(p1, p1.attack), COLOR_HITBOX, true)
	if not p2.attack.is_empty() and _attack_phase(p2.attack) == "ACTIVE":
		draw_rect(_get_attack_hitbox(p2, p2.attack), COLOR_HITBOX, true)

func _draw_fighter(f: Fighter, base_color: Color) -> void:
	var color := base_color
	if f.state == "HITSTUN":
		color = COLOR_HIT
	elif f.block:
		color = COLOR_BLOCK
	var rect := _get_hurtbox(f, false)
	draw_rect(rect, color, true)
	draw_rect(rect, COLOR_HURTBOX, false)

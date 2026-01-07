# SENTINEL Portrait Prompt Template

Standard prompt structure for generating NPC portraits via NanoBanana.

## Base Template

```
Portrait of a [ARCHETYPE] with [DEFINING_FEATURES], [FACTION] faction survivor.
[FACTION_GEAR]. [EXPRESSION] expression, weathered survivor features.
Dark atmospheric background with [FACTION_COLOR] accent lighting.
Comic book style with clean character lines, dramatic lighting.
Bust framing, 3/4 angle, codec portrait composition.
```

## Variables

### ARCHETYPE
Character role: scout, elder, enforcer, technician, trader, medic, operative, etc.

### DEFINING_FEATURES
1-2 distinctive physical traits that make the character memorable.

### FACTION + FACTION_COLOR
| Faction | Color Name | Hex | Gear/Aesthetic |
|---------|------------|-----|----------------|
| Nexus | Data Blue | #00A8E8 | Data visors, antenna rigs, sensor arrays, eye augments |
| Ember Colonies | Hearth Orange | #E85D04 | Salvaged leather, wool layers, fire-scarred gear |
| Lattice | Grid Yellow | #FFD000 | Work gear, tool belts, cable coils, utility harness |
| Convergence | Integration Purple | #7B2CBF | Bio-tech integration, visible augmentations, asymmetric |
| Covenant | Oath White | #E8E8E8 | Clean white/silver cloth, oath marks, formal bearing |
| Wanderers | Trail Tan | #C9A227 | Dust cloaks, travel packs, route maps, road-worn |
| Cultivators | Growth Green | #2D6A4F | Natural fibers, soil-stained, seed pouches |
| Steel Syndicate | Gunmetal | #5C677D | Armor layers, hidden pockets, sharp edges |
| Witnesses | Archive Sepia | #8B4513 | Document satchels, ink-stained fingers, record books |
| Architects | Blueprint Cyan | #0077B6 | Pre-collapse uniforms (worn), credential badges |
| Ghost Networks | Void Black | #0D0D0D | Nondescript clothing, forgettable features, shadows |

### EXPRESSION (maps to disposition)
| Disposition | Expression Description |
|-------------|----------------------|
| Hostile | Hard eyes, tight jaw, aggressive stance |
| Wary | Narrowed eyes, slight frown, guarded |
| Neutral | Even gaze, alert but calm |
| Warm | Softened eyes, hint of smile |
| Loyal | Direct eye contact, confident, open |

## Example Prompts

### Nexus Scout (Neutral)
```
Portrait of a scout with data visor and antenna headset, Nexus faction survivor.
Sleek tech fabric uniform with sensor arrays, subtle eye augments with blue data overlay.
Neutral expression, weathered survivor features.
Dark atmospheric background with blue (#00A8E8) accent lighting and faint data streams.
Comic book style with clean character lines, dramatic lighting.
Bust framing, 3/4 angle, codec portrait composition.
```

### Ember Elder (Warm)
```
Portrait of an elder with grey-streaked hair and fire-scarred hands, Ember Colonies faction survivor.
Layered wool and salvaged leather coat, warmth-worn face with kind eyes.
Warm expression, weathered survivor features.
Dark atmospheric background with orange (#E85D04) accent lighting and faint ember glow.
Comic book style with clean character lines, dramatic lighting.
Bust framing, 3/4 angle, codec portrait composition.
```

### Steel Syndicate Enforcer (Hostile)
```
Portrait of an enforcer with facial scar and cybernetic eye, Steel Syndicate faction survivor.
Heavy armor layers with hidden weapon holsters, intimidating build.
Hostile expression, weathered survivor features.
Dark atmospheric background with gunmetal (#5C677D) accent lighting and industrial haze.
Comic book style with clean character lines, dramatic lighting.
Bust framing, 3/4 angle, codec portrait composition.
```

### Ghost Networks Operative (Neutral)
```
Portrait of an operative with forgettable features and hooded cloak, Ghost Networks faction survivor.
Nondescript dark clothing, face partially shadowed, no identifying marks.
Neutral expression, weathered survivor features.
Dark atmospheric background with minimal lighting, deep shadows.
Comic book style with clean character lines, dramatic lighting.
Bust framing, 3/4 angle, codec portrait composition.
```

## Generation Command

```bash
gemini --yolo -e nanobanana "Generate a portrait image: [PROMPT]. Save the image to C:\dev\SENTINEL\assets\portraits\[faction]_[archetype].png"
```

## Style Notes

- **Keep "Comic book style with clean character lines, dramatic lighting"** - This is the core style anchor
- **Faction color in lighting, not clothing** - Let the accent lighting carry faction identity
- **Weathered survivor features** - Nobody in SENTINEL is fresh-faced; everyone has seen collapse
- **Dark atmospheric background** - Keeps focus on character, suggests post-collapse world
- **Bust framing, 3/4 angle** - Standard codec portrait composition for consistency

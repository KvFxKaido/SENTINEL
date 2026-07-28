---
name: portrait
description: Generate character portraits using the Antigravity CLI (agy) image tool. Reads from character YAML and builds explicit prompts with full guardrails.
allowed-tools: Bash, Read, Glob, Write
user-invocable: true
proactive: false
---

# Portrait Generation

Generate character portraits using the Antigravity CLI (`agy`), whose agent has
a built-in `generate_image` tool. (The previous Gemini CLI + NanoBanana path is
retired.) Reads character appearance from YAML files and builds explicit
prompts with all guardrails to prevent style drift.

**Portraits are campaign-specific** - each campaign has its own portrait set in `portraits/campaigns/{campaign_id}/`.

## Usage

```
/portrait <character_name>
/portrait cipher
/portrait elder_kara
/portrait vex --regenerate
```

## How It Works

1. **Determine current campaign ID** from bridge API or config
2. Read the character YAML from campaign-specific folder (fall back to global)
3. Build an explicit prompt with all guardrails
4. Call `agy -p "<prompt>" --add-dir <target dir> --dangerously-skip-permissions`
5. Handle the scratch-directory fallback if needed
6. Report success with the file path

## Step 0: Get Current Campaign ID

First, get the current campaign ID. Check the bridge API:

```bash
curl -s http://localhost:3333/state | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('sentinel',{}).get('campaign',{}).get('id',''))"
```

If bridge isn't running, check the config file:
```bash
cat C:/dev/SENTINEL/sentinel-agent/campaigns/.sentinel_config.json
```

The `last_campaign` field contains the campaign ID. If no campaign is loaded, ask the user to load one first.

**IMPORTANT**: Store the campaign ID - you'll need it for all paths.

## Step 1: Find and Read Character YAML

Look for the character file in this order:

1. **Campaign-specific**: `C:\dev\SENTINEL\assets\characters\campaigns\{campaign_id}\{name}.yaml`
2. **Legacy global**: `C:\dev\SENTINEL\assets\characters\{name}.yaml`

If not found in either location, ask the user if they want to create one.

## Step 2: Build the Prompt

### Required Structure

```
Cinematic portrait, photorealistic digital art style.
Modern post-apocalyptic cyberpunk aesthetic. NOT fantasy, NOT medieval, NOT anime, NOT elf, NOT blue hair.
[EXPLICIT_PERSON_DESCRIPTOR] with [BUILD] build, [HAIR_DESCRIPTION], [EYE_DESCRIPTION], [FACIAL_FEATURES], [DISTINGUISHING_MARKS], [EXPRESSION].
[FACTION] [ROLE] survivor. [FACTION_GEAR].
Dark atmospheric background with [FACTION_COLOR] accent lighting.
High detail, dramatic rim lighting, shallow depth of field.
Bust framing, 3/4 angle, looking slightly off-camera.
Use your generate_image tool. Save the file to exactly this absolute path: C:\dev\SENTINEL\sentinel-ui\public\assets\portraits\campaigns\{campaign_id}\{name}.png - do not save it anywhere else. Do not ask for confirmation.
```

**NOTE**: Always use the campaign-specific path for saving. The "exactly this
absolute path" phrasing matters — without it the agy agent saves into its own
scratch workspace instead (see Step 4).

### Person Descriptor Mapping (CRITICAL)

Build explicit descriptors to anchor generation. DO NOT use vague terms.

| Skin Tone | Gender: Masculine | Gender: Feminine | Gender: Androgynous |
|-----------|-------------------|------------------|---------------------|
| pale | pale-skinned white man | pale-skinned white woman | pale-skinned person |
| light | light-skinned white man | light-skinned white woman | light-skinned person |
| medium | olive-skinned man | olive-skinned woman | olive-skinned person |
| tan | tan Latino man | tan Latina woman | tan person |
| brown | Black man | Black woman | Black person |
| dark | dark-skinned Black man | dark-skinned Black woman | dark-skinned Black person |

For elderly characters, prepend "elderly" (e.g., "elderly olive-skinned woman").

### Faction Colors

| Faction | Color | Hex | Gear Description |
|---------|-------|-----|------------------|
| nexus | blue | #00A8E8 | Data visors, sensor arrays, sleek tech fabric |
| ember_colonies | orange | #E85D04 | Salvaged leather, wool layers, fire-scarred gear |
| lattice | yellow | #FFD000 | Work gear, tool belts, utility harness |
| convergence | purple | #7B2CBF | Bio-tech integration, visible augmentations |
| covenant | white | #E8E8E8 | Clean white/silver cloth, formal bearing |
| wanderers | tan | #C9A227 | Dust cloaks, travel packs, road-worn appearance |
| cultivators | green | #2D6A4F | Natural fibers, soil-stained hands |
| steel_syndicate | gunmetal | #5C677D | Heavy armor layers, tactical gear, intimidating |
| witnesses | sepia | #8B4513 | Document satchels, ink-stained fingers |
| architects | cyan | #0077B6 | Pre-collapse uniforms, credential badges |
| ghost_networks | black | #0D0D0D | Nondescript dark clothing, deep shadows |

### Expression Mapping

| YAML Value | Prompt Description |
|------------|-------------------|
| neutral | calm alert expression |
| wary | wary guarded expression |
| warm | warm approachable expression |
| stern | stern serious expression |
| tired | tired world-weary expression |

## Step 3: Execute Generation

First, ensure the campaign portrait directory exists:

```bash
mkdir -p "C:/dev/SENTINEL/sentinel-ui/public/assets/portraits/campaigns/{campaign_id}"
```

Then run the generation:

```bash
agy -p "[FULL_PROMPT]" --add-dir "C:/dev/SENTINEL/sentinel-ui/public/assets/portraits/campaigns/{campaign_id}" --dangerously-skip-permissions --model gemini-3.6-flash-medium
```

Use a 3-minute timeout (180000ms).

Invocation notes (each of these was learned the hard way):

- **The prompt goes immediately after `-p`; every flag comes after the
  prompt.** With flags placed before `-p`, the agent has been observed
  treating the flag text as the topic and chatting about it instead of
  working.
- **`--add-dir` with the target directory is mandatory** — it grants the
  agent write access outside its own workspace. Without it, the image lands
  in the scratch directory no matter what the prompt says.
- `--model gemini-3.6-flash-medium` is enough: the CLI model only
  orchestrates the call; `generate_image` does the actual image work.

## Step 4: Handle Output

The agy agent sometimes saves to its scratch workspace instead of the
requested path (always, if `--add-dir` was omitted).

1. Check if file exists at `sentinel-ui/public/assets/portraits/campaigns/{campaign_id}/{name}.png`
2. If not, check `C:/Users/ishaw/.gemini/antigravity-cli/scratch/` for recent PNG files
3. Move the most recent one to the correct location:
   ```bash
   mv "C:/Users/ishaw/.gemini/antigravity-cli/scratch/[filename].png" "C:/dev/SENTINEL/sentinel-ui/public/assets/portraits/campaigns/{campaign_id}/{name}.png"
   ```

## Step 5: Report Result

Show the user the generated portrait using the Read tool on the PNG file.

## Example: Full Prompt for Cipher (in campaign "cipher")

Character YAML (from `assets/characters/campaigns/cipher/cipher.yaml`):
```yaml
name: Cipher
faction: nexus
role: analyst
gender: masculine
age: adult
skin_tone: brown
build: lean
hair_color: black
hair_length: short
hair_style: dreadlocks
eye_color: augmented
facial_features: [sharp, high cheekbones]
augmentations: subtle blue data overlay in eyes, small temple implant
other_features: always wears a data visor
default_expression: neutral
```

Generated prompt:
```
Cinematic portrait, photorealistic digital art style.
Modern post-apocalyptic cyberpunk aesthetic. NOT fantasy, NOT medieval, NOT anime, NOT elf, NOT blue hair.
Black man with lean build, short black dreadlocks, cybernetic eyes with subtle blue data overlay, sharp features, high cheekbones, small temple implant, always wears a data visor, calm alert expression.
Nexus analyst survivor. Data visors, sensor arrays, sleek tech fabric.
Dark atmospheric background with blue (#00A8E8) accent lighting.
High detail, dramatic rim lighting, shallow depth of field.
Bust framing, 3/4 angle, looking slightly off-camera.
Use your generate_image tool. Save the file to exactly this absolute path: C:\dev\SENTINEL\sentinel-ui\public\assets\portraits\campaigns\cipher\cipher.png - do not save it anywhere else. Do not ask for confirmation.
```

## Error Handling

- **No campaign loaded**: Ask user to load a campaign first with `/load <name>`
- **YAML not found**: Ask user if they want to create one with `/portrait create {name}`
- **agy not available**: Report error; the CLI lives at
  `%LOCALAPPDATA%\agy\bin\agy.exe` — suggest `agy update`, or launching `agy`
  interactively once if the failure looks like expired auth
- **Generation fails**: Show error output, suggest retrying
- **Wrong style generated**: Regenerate with stronger guardrails (add more NOT constraints)

## Style Note (future)

The default style above is photorealistic-cinematic, matching the existing
`sentinel-ui` portrait set. `architecture/art_direction_gba_tactics.md` names
an alternative target for the GBA-tactics direction: *"GBA-era tactical RPG
portrait, hard cel shading, 1px outline, limited palette, quantized"*. Do not
switch styles unprompted — mixing the two in one campaign's portrait set is
worse than either. If the user asks for the GBA style, replace the first two
lines of the prompt structure with that descriptor and keep every other
guardrail.

## Creating New Characters

If the user wants to create a new character:

1. Ask for the key details (or use the table format from create_character.py)
2. Create the YAML file in `assets/characters/campaigns/{campaign_id}/{name}.yaml`
3. Generate the portrait

Or direct them to run:
```bash
python scripts/create_character.py
```

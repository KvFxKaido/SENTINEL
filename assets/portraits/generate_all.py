"""Generate all 33 SENTINEL faction portraits via Gemini + NanoBanana."""

import os
import shutil
import subprocess
from pathlib import Path

PORTRAITS_DIR = Path(__file__).parent

# All 33 portraits: (filename, prompt)
PORTRAITS = [
    # NEXUS - Data Blue #00A8E8
    ("nexus_scout", "Portrait of a scout with data visor and antenna headset, Nexus faction survivor. Sleek tech fabric uniform with sensor arrays, subtle eye augments with blue data overlay. Neutral expression, weathered survivor features. Dark atmospheric background with blue (#00A8E8) accent lighting and faint data streams. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("nexus_analyst", "Portrait of an analyst with holographic interface glasses and neural implant ports, Nexus faction survivor. Clean tech uniform with data tablet, intense focused gaze. Neutral expression, weathered survivor features. Dark atmospheric background with blue (#00A8E8) accent lighting and scrolling data. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("nexus_handler", "Portrait of a handler with command headset and authority insignia, Nexus faction survivor. Fitted tech coat with multiple screens reflected in eyes, commanding presence. Wary expression, weathered survivor features. Dark atmospheric background with blue (#00A8E8) accent lighting and network nodes. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),

    # EMBER COLONIES - Hearth Orange #E85D04
    ("ember_scout", "Portrait of a scout with thermal goggles pushed up and ash-streaked face, Ember Colonies faction survivor. Layered salvaged leather and wool, fire-resistant gear. Alert expression, weathered survivor features. Dark atmospheric background with orange (#E85D04) accent lighting and distant flames. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("ember_elder", "Portrait of an elder with grey-streaked hair and fire-scarred hands, Ember Colonies faction survivor. Layered wool and salvaged leather coat, warmth-worn face with kind eyes. Warm expression, weathered survivor features. Dark atmospheric background with orange (#E85D04) accent lighting and faint ember glow. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("ember_defender", "Portrait of a defender with burn scars and heavy protective coat, Ember Colonies faction survivor. Reinforced leather armor, fire axe slung across back, protective stance. Determined expression, weathered survivor features. Dark atmospheric background with orange (#E85D04) accent lighting and smoke wisps. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),

    # LATTICE - Grid Yellow #FFD000
    ("lattice_technician", "Portrait of a technician with safety goggles and tool belt, Lattice faction survivor. Work coveralls with cable coils, grease-stained hands, practical bearing. Neutral expression, weathered survivor features. Dark atmospheric background with yellow (#FFD000) accent lighting and electrical sparks. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("lattice_supervisor", "Portrait of a supervisor with hard hat and clipboard, Lattice faction survivor. Utility vest over work clothes, radio on shoulder, authoritative stance. Wary expression, weathered survivor features. Dark atmospheric background with yellow (#FFD000) accent lighting and power grid glow. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("lattice_engineer", "Portrait of an engineer with welding mask pushed back and circuit diagrams, Lattice faction survivor. Heavy work apron with tools, calloused hands, focused intensity. Neutral expression, weathered survivor features. Dark atmospheric background with yellow (#FFD000) accent lighting and machinery silhouettes. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),

    # CONVERGENCE - Integration Purple #7B2CBF
    ("convergence_initiate", "Portrait of an initiate with fresh bio-integration scars and eager eyes, Convergence faction survivor. Asymmetric clothing revealing partial augmentation, nervous energy. Wary expression, weathered survivor features. Dark atmospheric background with purple (#7B2CBF) accent lighting and bio-tech pulse. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("convergence_adept", "Portrait of an adept with visible cybernetic arm and glowing eye implant, Convergence faction survivor. Tech-integrated bodysuit, confident posthuman bearing. Neutral expression, weathered survivor features. Dark atmospheric background with purple (#7B2CBF) accent lighting and integration tendrils. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("convergence_recruiter", "Portrait of a recruiter with subtle enhancements and persuasive smile, Convergence faction survivor. Clean clothes hiding augmentations, charismatic presence. Warm expression, weathered survivor features. Dark atmospheric background with purple (#7B2CBF) accent lighting and soft tech glow. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),

    # COVENANT - Oath White #E8E8E8
    ("covenant_guardian", "Portrait of a guardian with ceremonial armor and oath brands on forearms, Covenant faction survivor. White and silver formal gear, protective stance, unwavering gaze. Neutral expression, weathered survivor features. Dark atmospheric background with white (#E8E8E8) accent lighting and clean geometric shapes. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("covenant_elder", "Portrait of an elder with white robes and ritual scars, Covenant faction survivor. Formal bearing with oath medallion, wise penetrating eyes. Warm expression, weathered survivor features. Dark atmospheric background with white (#E8E8E8) accent lighting and sanctuary glow. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("covenant_mediator", "Portrait of a mediator with neutral vestments and balance symbol, Covenant faction survivor. Diplomatic bearing, hands open in gesture of peace. Neutral expression, weathered survivor features. Dark atmospheric background with white (#E8E8E8) accent lighting and soft radiance. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),

    # WANDERERS - Trail Tan #C9A227
    ("wanderer_scout", "Portrait of a scout with dust cloak and road-worn boots, Wanderers faction survivor. Travel pack with route maps visible, alert traveler's eyes. Neutral expression, weathered survivor features. Dark atmospheric background with tan (#C9A227) accent lighting and distant road. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("wanderer_trader", "Portrait of a trader with caravan tokens and barter goods, Wanderers faction survivor. Layered travel clothes with many pockets, shrewd calculating gaze. Wary expression, weathered survivor features. Dark atmospheric background with tan (#C9A227) accent lighting and trade route markers. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("wanderer_elder", "Portrait of an elder with walking staff and memory beads, Wanderers faction survivor. Sun-weathered face with deep laugh lines, traveling cloak. Warm expression, weathered survivor features. Dark atmospheric background with tan (#C9A227) accent lighting and horizon glow. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),

    # CULTIVATORS - Growth Green #2D6A4F
    ("cultivator_tender", "Portrait of a tender with soil-stained hands and seed pouch, Cultivators faction survivor. Natural fiber clothing, gentle nurturing demeanor. Warm expression, weathered survivor features. Dark atmospheric background with green (#2D6A4F) accent lighting and growing plants. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("cultivator_elder", "Portrait of an elder with sun-weathered skin and harvest wreath, Cultivators faction survivor. Earth-toned robes, deep connection to land visible in bearing. Warm expression, weathered survivor features. Dark atmospheric background with green (#2D6A4F) accent lighting and fertile growth. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("cultivator_guard", "Portrait of a guard with farming tool repurposed as weapon, Cultivators faction survivor. Practical work clothes reinforced for protection, vigilant stance. Wary expression, weathered survivor features. Dark atmospheric background with green (#2D6A4F) accent lighting and field silhouettes. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),

    # STEEL SYNDICATE - Gunmetal #5C677D
    ("syndicate_dealer", "Portrait of a dealer with sharp suit and hidden weapons, Steel Syndicate faction survivor. Expensive salvaged clothes, calculating predator eyes. Wary expression, weathered survivor features. Dark atmospheric background with gunmetal (#5C677D) accent lighting and industrial shadows. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("syndicate_enforcer", "Portrait of an enforcer with facial scar and armored coat, Steel Syndicate faction survivor. Heavy build with visible weapons, intimidating presence. Hostile expression, weathered survivor features. Dark atmospheric background with gunmetal (#5C677D) accent lighting and cold steel. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("syndicate_boss", "Portrait of a boss with expensive rings and power suit, Steel Syndicate faction survivor. Commanding presence with cold authority, everything has a price in those eyes. Neutral expression, weathered survivor features. Dark atmospheric background with gunmetal (#5C677D) accent lighting and luxury shadows. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),

    # WITNESSES - Archive Sepia #8B4513
    ("witness_archivist", "Portrait of an archivist with ink-stained fingers and reading glasses, Witnesses faction survivor. Document satchel overflowing with papers, meticulous bearing. Neutral expression, weathered survivor features. Dark atmospheric background with sepia (#8B4513) accent lighting and old paper textures. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("witness_investigator", "Portrait of an investigator with notebook and suspicious gaze, Witnesses faction survivor. Practical clothes with many pockets for evidence, sharp observant eyes. Wary expression, weathered survivor features. Dark atmospheric background with sepia (#8B4513) accent lighting and record fragments. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("witness_elder", "Portrait of an elder with memory aids and truth-seeker medallion, Witnesses faction survivor. Formal archival robes, burden of knowledge in aged eyes. Neutral expression, weathered survivor features. Dark atmospheric background with sepia (#8B4513) accent lighting and ancient texts. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),

    # ARCHITECTS - Blueprint Cyan #0077B6
    ("architect_surveyor", "Portrait of a surveyor with measuring tools and blueprint tubes, Architects faction survivor. Pre-collapse uniform worn but maintained, professional bearing. Neutral expression, weathered survivor features. Dark atmospheric background with cyan (#0077B6) accent lighting and structural diagrams. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("architect_credential_officer", "Portrait of a credential officer with verification scanner and ID badges, Architects faction survivor. Formal pre-collapse attire, bureaucratic authority. Wary expression, weathered survivor features. Dark atmospheric background with cyan (#0077B6) accent lighting and credential holograms. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("architect_elder", "Portrait of an elder with master builder insignia and structural plans, Architects faction survivor. Distinguished bearing with pre-collapse medals, weight of lost civilization. Neutral expression, weathered survivor features. Dark atmospheric background with cyan (#0077B6) accent lighting and blueprint glow. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),

    # GHOST NETWORKS - Void Black #0D0D0D
    ("ghost_operative", "Portrait of an operative with forgettable features and hood shadows, Ghost Networks faction survivor. Nondescript dark clothing, face partially obscured, no identifying marks. Neutral expression, weathered survivor features. Dark atmospheric background with minimal lighting and deep shadows. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("ghost_handler", "Portrait of a handler with multiple identity tokens and encrypted device, Ghost Networks faction survivor. Plain clothes that could belong to any faction, deliberately average appearance. Wary expression, weathered survivor features. Dark atmospheric background with faint pale flicker and void darkness. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
    ("ghost_elder", "Portrait of an elder with no distinguishing features and shadow cloak, Ghost Networks faction survivor. Intentionally unmemorable face, presence that fades from memory. Neutral expression, weathered survivor features. Dark atmospheric background dominated by shadows and absence. Comic book style with clean character lines, dramatic lighting. Bust framing, 3/4 angle, codec portrait composition."),
]

# Resolve the gemini CLI portably: env override, then PATH, then the original
# dev machine's install path as a last-resort fallback. Keeps this preserved
# reference script runnable outside the machine it was authored on.
GEMINI_CMD = (
    os.environ.get("GEMINI_CMD")
    or shutil.which("gemini")
    or shutil.which("gemini.cmd")
    or r"C:\Users\ishaw\AppData\Roaming\npm\gemini.cmd"
)

def generate_portrait(filename: str, prompt: str) -> bool:
    """Generate a single portrait."""
    output_path = PORTRAITS_DIR / f"{filename}.png"

    if output_path.exists():
        print(f"  SKIP: {filename} (already exists)")
        return True

    full_prompt = f'Generate a portrait image: {prompt} Save the image to {output_path}'

    cmd = [GEMINI_CMD, "--yolo", "-e", "nanobanana", full_prompt]

    try:
        # shell=True is required to invoke the Windows .cmd shim; this script is
        # Windows-oriented as authored. On POSIX, run without shell=True.
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, shell=True)
        if output_path.exists():
            print(f"  DONE: {filename}")
            return True
        else:
            print(f"  FAIL: {filename} - file not created")
            print(f"         stdout: {result.stdout[:200] if result.stdout else 'none'}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT: {filename}")
        return False
    except Exception as e:
        print(f"  ERROR: {filename} - {e}")
        return False

def main():
    print("=" * 50)
    print("  SENTINEL Portrait Batch Generator")
    print("=" * 50)
    print(f"\nGenerating {len(PORTRAITS)} portraits...\n")

    success = 0
    failed = []

    for i, (filename, prompt) in enumerate(PORTRAITS, 1):
        faction = filename.split("_")[0].upper()
        print(f"[{i:02d}/{len(PORTRAITS)}] {faction}: {filename}")

        if generate_portrait(filename, prompt):
            success += 1
        else:
            failed.append(filename)

    print("\n" + "=" * 50)
    print(f"  Complete: {success}/{len(PORTRAITS)} portraits")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
    print("=" * 50)

if __name__ == "__main__":
    main()

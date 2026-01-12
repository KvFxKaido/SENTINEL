"""Generate Braille portraits for SENTINEL factions.

This script uses src.interface.braille.generate_portrait to create
Braille art portraits roughly corresponding to the prompts in
assets/PORTRAIT_PROMPTS.md.

Output: C:\dev\SENTINEL\assets\braille_portraits\<id>.txt
"""

from pathlib import Path

from src.interface.braille import generate_portrait


# id, archetype, expression, width
PORTRAIT_SPECS: list[tuple[str, str, str, int]] = [
    # NEXUS (Data Blue)
    ("nexus_scout", "scout", "wary", 20),
    ("nexus_analyst", "default", "wary", 20),
    ("nexus_handler", "default", "neutral", 20),

    # EMBER COLONIES (Hearth Orange)
    ("ember_scout", "scout", "friendly", 20),
    ("ember_elder", "elder", "friendly", 20),
    ("ember_defender", "soldier", "hostile", 20),

    # LATTICE (Grid Yellow)
    ("lattice_technician", "default", "neutral", 20),
    ("lattice_supervisor", "default", "wary", 20),
    ("lattice_engineer", "default", "neutral", 20),

    # CONVERGENCE (Integration Purple)
    ("convergence_initiate", "mystic", "wary", 20),
    ("convergence_adept", "mystic", "neutral", 20),
    ("convergence_recruiter", "merchant", "friendly", 20),

    # COVENANT (Oath White)
    ("covenant_guardian", "soldier", "friendly", 20),
    ("covenant_elder", "elder", "friendly", 20),
    ("covenant_mediator", "default", "neutral", 20),

    # WANDERERS (Trail Tan)
    ("wanderer_scout", "scout", "neutral", 20),
    ("wanderer_trader", "merchant", "friendly", 20),
    ("wanderer_elder", "elder", "friendly", 20),

    # CULTIVATORS (Growth Green)
    ("cultivator_tender", "default", "friendly", 20),
    ("cultivator_elder", "elder", "friendly", 20),
    ("cultivator_guard", "soldier", "wary", 20),

    # STEEL SYNDICATE (Gunmetal)
    ("syndicate_dealer", "merchant", "wary", 20),
    ("syndicate_enforcer", "soldier", "hostile", 20),
    ("syndicate_boss", "merchant", "hostile", 20),

    # WITNESSES (Archive Sepia)
    ("witness_archivist", "default", "neutral", 20),
    ("witness_investigator", "default", "wary", 20),
    ("witness_elder", "elder", "neutral", 20),

    # ARCHITECTS (Blueprint Cyan)
    ("architect_surveyor", "default", "wary", 20),
    ("architect_credential_officer", "default", "wary", 20),
    ("architect_elder", "elder", "neutral", 20),

    # GHOST NETWORKS (Void Black)
    ("ghost_operative", "hacker", "neutral", 20),
    ("ghost_handler", "hacker", "wary", 20),
    ("ghost_elder", "mystic", "neutral", 20),
]


def main() -> None:
    here = Path(__file__).resolve()
    # C:\dev\SENTINEL\sentinel-agent\scripts -> parents[1] is sentinel-agent,
    # parents[2] is repo root C:\dev\SENTINEL
    repo_root = here.parents[2]
    out_dir = repo_root / "assets" / "braille_portraits"
    out_dir.mkdir(parents=True, exist_ok=True)

    for ident, archetype, expression, width in PORTRAIT_SPECS:
        art = generate_portrait(archetype, expression, width)
        out_path = out_dir / f"{ident}.txt"
        out_path.write_text(art + "\n", encoding="utf-8")
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

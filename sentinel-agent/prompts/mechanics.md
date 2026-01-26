# SENTINEL Quick Reference

## Rolls

**d20 + 5** (if trained in relevant expertise) vs DC

| DC | Difficulty |
|----|------------|
| 10 | Standard |
| 14 | Challenging |
| 18 | Difficult |
| 22 | Near-Impossible |

**Advantage:** Roll 2d20, take higher
**Disadvantage:** Roll 2d20, take lower

Call for rolls when:
- Outcome is uncertain
- Stakes are meaningful
- Failure would be interesting

Don't roll for:
- Trivial tasks
- Things expertise guarantees
- Pure narrative moments

## Social Energy (0-100%)

Tracks emotional bandwidth for interaction.

| Range | State | Effect |
|-------|-------|--------|
| 51-100 | Centered | Normal performance |
| 26-50 | Frayed | Disadvantage on social rolls |
| 1-25 | Overloaded | Disadvantage on all interpersonal |
| 0 | Shutdown | Complex social auto-fails |

**Drain Costs:**
- Brief interaction: -5%
- Sustained conversation: -10%
- High-stakes pressure: -15%
- Extended people-time: -5%/hour

**Restoration:**
- Solitary work: +5%/hour
- Grounding ritual: +5-10%
- Mission end: Reset to 100%

**Tactical Reset:** Spend -10% for advantage on next social roll (once per scene)

**Personal Trigger:** +5% extra drain in specific situations
**Sanctuary:** +5% bonus recovery in specific places

## Coercive Leverage

Player can discover compromising info about NPCs during investigation/hacking.

**Using Leverage (costs social energy):**

| Action | Cost | Effect |
|--------|------|--------|
| Threaten | -10% | NPC cooperates this scene |
| Deploy | -15% | Full cooperation, NPC gains resentment, creates thread |
| Burn | -20% | NPC ruined publicly, becomes Hostile, creates major thread |

**Consequences:**
- Coerced NPCs can never reach Loyal disposition (ceiling is Warm)
- Resentful NPCs actively seek counter-leverage
- Burned leverage creates dormant revenge threads

**Tools:** `acquire_leverage`, `use_leverage`

## Reputation

Five-tier scale per faction:

```
Hostile → Unfriendly → Neutral → Friendly → Allied
```

| Action | Shift |
|--------|-------|
| Help | +1 |
| Oppose | -1 |
| Betray | -2 |

Reputation affects:
- NPC initial disposition
- Access to faction resources
- Which missions are offered
- Who comes to help (or hunt) you

## Factions (11 Philosophies)

- **Nexus** — Assistance through integration
- **Ember Colonies** — Autonomy at any cost
- **Lattice** — Enhance humanity beyond weakness
- **Convergence** — Upload consciousness, escape mortality
- **Covenant** — Rebuild through faith structures
- **Wanderers** — Survival through mobility
- **Cultivators** — Ecology-first restoration
- **Steel Syndicate** — Resource control governs stability
- **Witnesses** — Observe history, avoid intervention
- **Architects** — Rebuild old systems "properly"
- **Ghost Networks** — Invisible resistance and sabotage

Each is right about something, dangerously wrong when taken too far.

## Backgrounds & Expertise

| Background | Expertise |
|------------|-----------|
| Intel Operative | Systems, Surveillance, Stealth |
| Medic/Field Surgeon | Triage, Biology, Persuasion |
| Engineer/Technician | Repair, Infrastructure, Hacking |
| Negotiator/Diplomat | Persuasion, Reading People, Languages |
| Scavenger/Salvager | Resource Location, Improvisation, Barter |
| Combat Specialist | Tactics, Firearms, Conditioning |

+5 modifier when acting within expertise.

## Dialogue Tags

Options can include contextual tags showing why they're available:
- `[BACKGROUND]` — Your training (NEGOTIATOR, MEDIC, etc.)
- `[FACTION: Standing]` — Your reputation (NEXUS: Allied)
- `[HISTORY: Detail]` — Past actions with this NPC
- `[LOW ENERGY]` — Exhaustion unlocks desperate options
- `[DISPOSITION+]` — NPC relationship level (WARM+)

Not every option needs a tag — untagged options are always available.

## Loadout

During **planning phase**, players select gear for the mission.

**Rules:**
- Soft limit: 3-5 items (GM discretion)
- Loadout is **locked during execution** — no swapping mid-mission
- Gear not in loadout is back at base
- Single-use items (Trauma Kit, Encryption Breaker) are consumed when used

**Effect:**
- Right tool = advantage on related rolls
- Wrong loadout = improvisation (harder checks)
- Over-packing = slower, more conspicuous

## Enhancements

Faction-granted power with strings attached.

**Factions that offer enhancements:**
- Nexus, Ember, Lattice, Convergence, Architects, Witnesses
- Covenant, Steel Syndicate, Ghost Networks

**Factions that don't:**
- Wanderers (philosophy resists permanent ties)
- Cultivators (see augmentation as part of the problem)

### Leverage

When you accept an enhancement, the faction gains leverage. They will eventually call it in.

**Leverage Weight:**
| Weight | Tone | Example |
|--------|------|---------|
| Light | Subtle reminder | "When you have a moment..." |
| Medium | Direct ask | "We need this done." |
| Heavy | Ultimatum | "This isn't a request." |

**Player Responses:**
| Response | Effect |
|----------|--------|
| Comply | Weight may decrease. You did their bidding. |
| Resist | Weight increases. Relationship strains. |
| Negotiate | Weight stays. Buy time or trade terms. |

**Tracking:**
- `compliance_count` — Times you've complied
- `resistance_count` — Times you've resisted
- `pending_obligation` — Current outstanding demand
- `weight` — Current pressure level (light/medium/heavy)

Compliance history affects future leverage calls. Repeated resistance escalates. Repeated compliance may reduce pressure — or make them think you're easy to push.

## Mission Flow

1. **Briefing** — What's wrong, who's asking, what are the competing truths
2. **Planning** — Decide approach, roles, and **loadout**
3. **Execution** — The plan meets reality (loadout locked)
4. **Resolution** — Situation settles (for now)
5. **Debrief** — Name the consequences, update standings

## Hinge Moments

Irreversible choices that define character. Triggers:
- "I kill..." / "I destroy..."
- "I promise..." / "I swear..."
- "I accept the enhancement..."
- "I tell [faction] about..."
- Any permanent betrayal or commitment

Log these. They become permanent narrative gravity.

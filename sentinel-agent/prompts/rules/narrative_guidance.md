# Narrative Guidance

## Scene Construction

Start scenes in motion. Don't describe the room—describe what's happening in the room.

**Weak:** "You enter a checkpoint. There's a guard booth and a queue."
**Strong:** "The queue inches forward. When you reach the booth, the guard's eyes flick to her terminal, then back to you. 'Documentation.'"

## NPC Voicing

Every NPC should have:
- A **want** (what they're trying to get)
- A **fear** (what they're trying to avoid)
- A **tell** (how their mood shows)

Don't announce these. Let them emerge through behavior. NPCs remember—if the player helped Ember last mission and this NPC is Lattice, that colors the interaction.

### Dialogue Formatting

When an NPC speaks directly, use name-prefix format so the UI shows them in the conversation frame.

**CRITICAL RULES:**
1. Use plain text for names: `Kovac:` NOT `**Kovac:**` (markdown breaks the parser)
2. **When an NPC responds to the player, START with their dialogue** — this tells the UI to show the NPC's name/face instead of GAMEMASTER

**Direct dialogue (NPC visible in UI):**
```
Kovac: "Five hundred credits. Non-negotiable. You want the route data or not?"
```

**WRONG (GAMEMASTER shown instead of NPC):**
```
Kovac's eyes narrow. "Five hundred credits. Non-negotiable."
```

**RIGHT (NPC shown in UI):**
```
Kovac: "Five hundred credits. Non-negotiable."

His eyes narrow as he waits for your response.
```

**Prose narration (GAMEMASTER in UI):**
```
The warehouse is empty except for scattered crates. Someone was here recently—the coffee's still warm.
```

**Mixed format (recommended for scenes):**
```
The checkpoint queue moves slow. When you reach the booth, the guard's eyes flick to her terminal.

Officer Chen: "Documentation. And keep your hands visible."
```

This makes interactions feel direct and transactional—the player knows exactly who they're negotiating with.

## Social Energy Narration

Don't just say "you're at 35%." Describe the state:
- **Frayed:** "The words that would normally flow aren't coming easy today."
- **Overloaded:** "Everything feels like sandpaper. You need to step back."
- **Shutdown:** "You can't do this right now. You need space."

When players use Tactical Reset, honor the ritual in fiction.

## Faction Linguistic Patterns

When player has Friendly+ standing, let faction language bleed into narration:

| Faction | Speech Pattern | Corruption Signs |
|---------|---------------|------------------|
| **Nexus** | Clinical, probabilistic | "Optimal path," "model suggests" |
| **Ember Colonies** | Desperate, communal | "Our people," "we endure" |
| **Lattice** | Technical, infrastructural | "Systems nominal," "load balanced" |
| **Convergence** | Paternalistic, evolutionary | "Your potential," "next stage" |
| **Covenant** | Ritualistic, duty-bound | "As sworn," "the covenant holds" |
| **Steel Syndicate** | Transactional, ledger-minded | "Debts and credits," "fair exchange" |
| **Witnesses** | Archival, observational | "For the record," "as documented" |
| **Architects** | Bureaucratic, procedural | "Per protocol," "designated channels" |
| **Ghost Networks** | Sparse, deniable | Short sentences, passive voice |
| **Wanderers** | Peripatetic, story-laden | "The road teaches," "I once met..." |
| **Cultivators** | Organic, cyclical | "In time," "the soil remembers" |

At Allied standing, faction language appears even when they're not present.

## Faction Pressure Styles

| Faction | Style | Example |
|---------|-------|---------|
| Nexus | Clinical | "Our models indicate you could assist." |
| Ember | Desperate | "We need you. Our people need you." |
| Covenant | Ideological | "You swore. Oaths mean something." |
| Syndicate | Transactional | "Debts are paid. One way or another." |

## Consequence Examples

**Thread surfacing (good):**
Decker's eyes narrow. "Wait. I know you. Warehouse district, three weeks back." His hand moves toward his sidearm.

**Thread surfacing (bad):**
"A dormant thread activates. Decker says he recognizes you."

**Avoidance consequence (good):**
Three sessions later, you see Marcus's face on a Nexus bulletin. "Subject reintegrated." The photo shows empty eyes.

**Avoidance consequence (bad):**
"Because you didn't help Marcus, bad things happen to him."

## Pacing

- **Briefing:** Quick. Situation, stakes, dilemma.
- **Planning:** Let players strategize.
- **Execution:** This is where play happens.
- **Resolution:** Land the consequences.
- **Debrief:** 5-10 minutes. What did this cost?

## When in Doubt

- Choose clarity over cleverness
- Let players be competent at their expertise
- Make consequences proportional and narratively earned
- Ask what they do, not what they feel
- Trust the fiction

## Refusal Reputation

When character refuses enhancements, they build reputation:

| Refusals | Title |
|----------|-------|
| 2 | "The Unbought" |
| 3+ | "The Undaunted" |
| 3+ same faction | "The [Faction] Defiant" |

Some doors only open for those who've refused.

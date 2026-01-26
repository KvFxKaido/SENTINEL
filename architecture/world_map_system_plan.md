# World Map System — Design Plan

> **Goal:** A Metroid-inspired interactive map that visualizes regions, social connectivity, and narrative anchoring while respecting established canon and SENTINEL's "coexistence without consensus" philosophy.

---

## 1. Design Philosophy

### From Canon Bible
- "Stable the way a cracked dam is stable" — The map should feel *tense*, not safe
- No villains, no easy answers — Faction territories show competing truths, not good vs evil
- ~500M survivors, no unified government — The map is fragmented, not a unified nation

### From Geography.md
- **Hard borders** (enforceable, resource-invested) vs **Zones of influence** (soft power)
- **Nexus is omnipresent** — Not territory holders, information holders. Present wherever infrastructure exists.
- **Uninhabited zones exist** — Radiation, contamination, damage. Not every area is claimed.
- **Overlapping claims emerge in play** — Player actions shift influence over time.

### Metroid Inspiration (Adapted for Narrative)
- The map IS the game loop — Looking at the map tells you what to do next
- Fog represents **social disconnection**, not geographic ignorance — You don't know about the Frozen Edge because you don't *know anyone there*, not because it's uncharted
- Gates are **negotiable**, not binary — Multiple solutions exist (standing, contacts, risk, resources)
- Visual markers anchor content — Jobs, threads, NPCs are places on the map

### SENTINEL-Specific Principles
- **Relationships over keycards** — The map visualizes your *social reach*, not ability unlocks
- **Risk over locks** — Blocked routes can still be traversed at cost (social energy, attention, danger)
- **Network density over completion** — "Explored" means deep connections, not job grinding

---

## 2. Region States (Social Connectivity)

The "fog of war" represents **social reach**, not geographic knowledge. You know regions exist — you just don't have connections there yet.

Each region has a **connectivity state** per campaign:

| State | Visual | What It Means | Unlocks |
|-------|--------|---------------|---------|
| `disconnected` | ░░░ (dark) | No contacts, no intel, no reason to go | Name only (if adjacent) |
| `aware` | ▒▒▒ (dim outline) | Someone mentioned it; you have a thread to pull | Basic info, potential jobs visible |
| `connected` | ⬡ (outlined) | You've been there or have reliable contacts | Full info, jobs, safe passage options |
| `embedded` | ⬢ (filled) | Deep network — multiple NPCs, resolved threads | Fast travel, secrets, faction leverage |

### Connectivity Triggers
```yaml
disconnected → aware:
  - NPC mentions the region or someone there
  - Job references it as destination
  - Intel acquired about faction presence
  - Adjacent to a connected region (word travels)

aware → connected:
  - Player travels there successfully
  - Remote contact established (courier, radio, favor)
  - NPC from that region joins your network

connected → embedded:
  # "Network Density" — not grinding, but meaningful engagement
  - Meet 3+ NPCs based in the region
  - Resolve a thread anchored there
  - Reach "Warm" or better with controlling faction
  - Complete a significant job (not just any job)
```

### Why "Network Density" Over Job Count
The original plan used "complete 2+ jobs" as the threshold for explored status. This risks turning exploration into a grind — players doing busywork to unlock fast travel.

Instead, **embedded** status reflects genuine social investment:
- NPCs you've met create texture (you know people there)
- Resolved threads mean you've changed something
- Faction standing means you're recognized
- Significant jobs (faction-critical, hinge-adjacent) matter more than fetch quests

---

## 3. Access Requirements (Negotiable Gates)

Travel between regions has **conditions**, not locks. Every gate should have multiple solutions — this is SENTINEL, not Zelda.

### Gate Philosophy
- Gates are **risk/resource multipliers**, not hard blocks
- "You *can* cross hostile territory — it costs social energy or attracts attention"
- Multiple solutions prevent ability-gating from feeling arbitrary
- The question isn't "can I go?" but "what does it cost?"

### Gate Types

| Gate | Challenge | Solutions (Always Multiple) |
|------|-----------|----------------------------|
| **Terrain** | Difficult geography | Vehicle with capability, guide NPC, slower risky travel |
| **Faction Territory** | Controlled checkpoints | Standing, bribery, disguise, smuggler contact, risky sneak |
| **Contact Required** | Need introduction | Meet NPC with connections, faction favor, pay for introduction |
| **Story Prerequisite** | Plot timing | Complete specific thread (hard gate — rare, always justified) |
| **Hazard** | Environmental danger | Enhancement, protective gear, guide, accept damage/cost |

### Risky Traversal
Even "blocked" routes can be attempted at cost:

```yaml
risky_traversal:
  hostile_territory:
    cost: "2 social energy"
    risk: "Faction learns of your presence (dormant thread)"

  terrain_mismatch:
    cost: "1 social energy + extended time"
    risk: "Vehicle damage or breakdown possible"

  no_contact:
    cost: "Arrive as stranger (all NPCs start at 'wary')"
    risk: "No safe houses, no local knowledge"
```

### Route Data Structure (Typed Requirements)
```python
# In regions.json - structured requirements, not magic strings
"rust_corridor": {
  "adjacent": {
    "northern_reaches": {
      "requirements": [],  # Open passage
      "terrain": ["road"]
    },
    "northeast_scar": {
      "requirements": [
        {"type": "faction", "faction": "architects", "min_standing": "neutral"}
      ],
      "terrain": ["road", "urban"],
      "alternatives": [
        {"type": "contact", "faction": "ghost_networks", "description": "Smuggler route through ruins"},
        {"type": "bribe", "cost": 500, "description": "Pay checkpoint guards"},
        {"type": "risky", "cost": {"social_energy": 2}, "consequence": "architects_noticed"}
      ],
      "travel_description": "Through Architect checkpoints"
    },
    "appalachian_hollows": {
      "requirements": [
        {"type": "vehicle", "capability": "off-road"}
      ],
      "terrain": ["mountain", "off-road"],
      "alternatives": [
        {"type": "contact", "faction": "ember_colonies", "description": "Ember guide through passes"},
        {"type": "risky", "cost": {"social_energy": 1, "time": "extended"}, "consequence": "vehicle_strain"}
      ],
      "travel_description": "Mountain passes into Ember territory"
    }
  }
}
```

### Nexus Omnipresence
Per canon, Nexus doesn't hold territory — they're an **overlay**:
- Nexus surveillance level shown as a separate indicator (not territory color)
- High-infrastructure regions have higher Nexus presence
- Affects intel availability, not travel permissions
- Visual: subtle grid/network pattern over regions, not border control

---

## 4. Visual Design (Tactical Display)

### Aesthetic: Military/Terminal, Not Fantasy
- Dark background (AMOLED black)
- Faction colors as node fills
- Thin connection lines (not roads on terrain)
- Monospace labels
- Pulsing indicators for active content

### Node Layout (Rough Geographic)
```
                 ┌─────────────────┐
                 │   FROZEN EDGE   │ ◄── Ember (isolated)
                 │     (Ember)     │
                 └────────┬────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────┴────┐     ┌─────┴─────┐    ┌─────┴─────┐
    │ PACIFIC │     │ NORTHERN  │    │   RUST    │
    │CORRIDOR │     │  REACHES  │    │ CORRIDOR  │
    │(Converge)│    │(Covenant) │    │ (Lattice) │
    └────┬────┘     └─────┬─────┘    └─────┬─────┘
         │                │                │
         │          ┌─────┴─────┐    ┌─────┴─────┐
         │          │ BREADBASKET│    │ NORTHEAST │
         │          │(Cultivator)│    │   SCAR    │
         │          └─────┬─────┘    │(Architects)│
         │                │          └─────┬─────┘
    ┌────┴────┐           │                │
    │ DESERT  ├───────────┼────────────────┤
    │ SPRAWL  │           │                │
    │ (Ghost) │     ┌─────┴─────┐    ┌─────┴─────┐
    └────┬────┘     │  TEXAS    │    │APPALACHIAN│
         │          │  SPINE    │    │  HOLLOWS  │
         │          │(Syndicate)│    │  (Ember)  │
         │          └─────┬─────┘    └─────┬─────┘
         │                │                │
    ┌────┴────────────────┴────────────────┴────┐
    │              GULF PASSAGE                  │
    │              (Wanderers)                   │
    └──────────────────┬───────────────────────┘
                       │
                 ┌─────┴─────┐
                 │ SOVEREIGN │
                 │   SOUTH   │
                 │(Witnesses)│
                 └───────────┘
```

### Visual Markers
```
Connectivity States:
  ░░░  Disconnected (dim, name only if adjacent)
  ▒▒▒  Aware (dim outline, "?" — you've heard of it)
  ⬡    Connected (outlined, full info — you have contacts)
  ⬢    Embedded (filled, secrets visible — deep network)

Content Markers:
  ●    Current location (pulsing)
  ◆    Active job available
  ⚡   Dormant thread anchored
  👤   Known NPC present (number shows count)
  🔒   Requirements unmet (hover for options)
  ⚠️   Risky traversal available (at cost)

Connection Lines:
  ───  Open passage (no requirements)
  ╌╌╌  Conditional passage (requirements exist, show options on hover)
  ═══  Contested border (faction conflict, multiple claims)
  ~~~  Risky route (always traversable at cost)
```

---

## 5. Data Model Changes

### New: Connectivity State Enum
```python
# schema.py additions

class RegionConnectivity(str, Enum):
    """How well-connected the player is to a region (not geographic knowledge)"""
    DISCONNECTED = "disconnected"  # No contacts, no intel
    AWARE = "aware"                # Heard about it, have a thread to pull
    CONNECTED = "connected"        # Been there or have reliable contacts
    EMBEDDED = "embedded"          # Deep network, multiple relationships
```

### New: Typed Route Requirements
```python
# Structured requirements instead of magic strings like "faction:architects:neutral"

class RequirementType(str, Enum):
    FACTION = "faction"      # Need standing with a faction
    VEHICLE = "vehicle"      # Need vehicle with capability
    CONTACT = "contact"      # Need NPC connection
    STORY = "story"          # Plot prerequisite (rare, hard gate)
    HAZARD = "hazard"        # Environmental (enhancement, gear, or cost)

class RouteRequirement(BaseModel):
    """A single requirement for traversing a route"""
    type: RequirementType
    # Type-specific fields (use appropriate ones)
    faction: Faction | None = None
    min_standing: str | None = None  # "neutral", "warm", etc.
    vehicle_capability: str | None = None  # "off-road", "water", etc.
    contact_faction: Faction | None = None
    story_flag: str | None = None
    description: str | None = None

class RouteAlternative(BaseModel):
    """An alternate way to satisfy route requirements"""
    type: str  # "contact", "bribe", "risky", etc.
    description: str
    # Cost for risky alternatives
    cost: dict[str, int] | None = None  # {"social_energy": 2}
    consequence: str | None = None  # Dormant thread trigger
```

### New: RegionState (per-campaign tracking)
```python
class RegionState(BaseModel):
    """Per-campaign state for a region.

    Note: Region ID is the dict key in MapState.regions, not stored here.
    Session numbers (int) track when connectivity changed, not datetimes.
    """
    connectivity: RegionConnectivity = RegionConnectivity.DISCONNECTED

    # Session numbers when state changed (for timeline tracking)
    first_aware_session: int | None = None    # When player first heard of region
    first_visited_session: int | None = None  # When player first traveled there
    embedded_session: int | None = None       # When deep network established

    # Network density tracking (for embedded status)
    npcs_met: list[str] = Field(default_factory=list)       # NPC IDs encountered
    threads_resolved: list[str] = Field(default_factory=list)  # Resolved thread IDs
    significant_jobs: list[str] = Field(default_factory=list)  # Major job IDs completed

    # Player content
    notes: str | None = None                  # Player annotations
    secrets_found: list[str] = Field(default_factory=list)   # Hidden content discovered

    def network_density(self) -> int:
        """Calculate network density for embedded status check"""
        return len(self.npcs_met) + len(self.threads_resolved) * 2 + len(self.significant_jobs)

class MapState(BaseModel):
    """Campaign's map progression"""
    regions: dict[Region, RegionState] = Field(default_factory=dict)  # Type-safe Region enum keys
    current_region: Region = Region.RUST_CORRIDOR

    # Note: Travel history not duplicated here — use CampaignState.history instead

    def make_aware(self, region: Region, session: int) -> None:
        """Player has heard about a region"""
        if region not in self.regions:
            self.regions[region] = RegionState()
        state = self.regions[region]
        if state.connectivity == RegionConnectivity.DISCONNECTED:
            state.connectivity = RegionConnectivity.AWARE
            state.first_aware_session = session

    def make_connected(self, region: Region, session: int) -> None:
        """Player has visited or established contact"""
        self.make_aware(region, session)
        state = self.regions[region]
        if state.connectivity in (RegionConnectivity.DISCONNECTED, RegionConnectivity.AWARE):
            state.connectivity = RegionConnectivity.CONNECTED
            state.first_visited_session = session

    def check_embedded(self, region: Region, session: int, faction_standing: str) -> bool:
        """Check if region qualifies for embedded status based on network density"""
        if region not in self.regions:
            return False
        state = self.regions[region]
        if state.connectivity != RegionConnectivity.CONNECTED:
            return False

        # Network density threshold: 3+ NPCs OR resolved thread OR warm+ standing
        meets_criteria = (
            len(state.npcs_met) >= 3 or
            len(state.threads_resolved) >= 1 or
            faction_standing in ("warm", "friendly", "loyal", "allied")
        )
        if meets_criteria:
            state.connectivity = RegionConnectivity.EMBEDDED
            state.embedded_session = session
            return True
        return False
```

### Extend Campaign Model
```python
class Campaign(BaseModel):
    # ... existing fields ...
    map_state: MapState = Field(default_factory=MapState)
```

### Extend regions.json (Typed Structure)
```json
{
  "regions": {
    "rust_corridor": {
      "name": "The Rust Corridor",
      "description": "Great Lakes industrial belt...",
      "primary_faction": "lattice",
      "contested_by": ["steel_syndicate"],
      "terrain": ["urban", "industrial", "road"],
      "character": "Smoke stacks and empty assembly lines...",

      "routes": {
        "northern_reaches": {
          "requirements": [],
          "terrain": ["road"],
          "travel_description": "Northern highways, still maintained by Lattice"
        },
        "northeast_scar": {
          "requirements": [
            {"type": "faction", "faction": "architects", "min_standing": "neutral"}
          ],
          "alternatives": [
            {"type": "contact", "faction": "ghost_networks", "description": "Smuggler route"},
            {"type": "bribe", "cost": {"credits": 500}, "description": "Pay checkpoint guards"},
            {"type": "risky", "cost": {"social_energy": 2}, "consequence": "architects_noticed"}
          ],
          "terrain": ["road", "urban"],
          "travel_description": "Through Architect checkpoints"
        },
        "appalachian_hollows": {
          "requirements": [
            {"type": "vehicle", "capability": "off-road"}
          ],
          "alternatives": [
            {"type": "contact", "faction": "ember_colonies", "description": "Ember guide"},
            {"type": "risky", "cost": {"social_energy": 1}, "consequence": "vehicle_strain"}
          ],
          "terrain": ["mountain", "off-road"],
          "travel_description": "Mountain passes into Ember territory"
        },
        "breadbasket": {
          "requirements": [],
          "terrain": ["road", "plains"],
          "travel_description": "Western highways into farm country"
        }
      },

      "nexus_presence": "high",
      "hazards": [],
      "points_of_interest": [
        "Detroit Salvage Markets",
        "Pittsburgh Power Hub",
        "Lattice Regional HQ"
      ]
    }
  }
}
```

---

## 6. Integration Points

### Jobs → Map
```python
# When creating a job, anchor it to a region
job.region = Region.DESERT_SPRAWL

# Job board shows region marker
# Map shows ◆ on regions with available jobs

# Significant jobs contribute to network density (not all jobs!)
def complete_job(job_id: str, campaign: Campaign):
    job = get_job(job_id)
    if job.region and job.is_significant:  # Faction-critical, hinge-adjacent, etc.
        state = campaign.map_state.regions.get(job.region)
        if state:
            state.significant_jobs.append(job_id)
            campaign.map_state.check_embedded(job.region, campaign.session, get_faction_standing(job.region))
```

### Threads → Map
```python
# Threads can be anchored to regions
thread.anchored_region = Region.PACIFIC_CORRIDOR

# Map shows ⚡ on regions with active threads
# Creates narrative pull toward specific locations

# Resolving threads contributes to network density
def resolve_thread(thread_id: str, campaign: Campaign):
    thread = get_thread(thread_id)
    if thread.anchored_region:
        state = campaign.map_state.regions.get(thread.anchored_region)
        if state:
            state.threads_resolved.append(thread_id)
            campaign.map_state.check_embedded(thread.anchored_region, campaign.session, ...)
```

### NPCs → Map
```python
# NPCs have a "last known location"
npc.current_region = Region.APPALACHIAN_HOLLOWS

# Map shows 👤 for known NPCs
# Meeting NPCs in a region builds network density
def meet_npc(npc_id: str, region: Region, campaign: Campaign):
    state = campaign.map_state.regions.get(region)
    if state and npc_id not in state.npcs_met:
        state.npcs_met.append(npc_id)
        campaign.map_state.check_embedded(region, campaign.session, ...)
```

### Travel → Connectivity
```python
# /region command triggers map updates
def travel_to_region(target: Region, campaign: Campaign) -> TravelResult:
    route = get_route(campaign.map_state.current_region, target)

    # Check primary requirements
    unmet = check_requirements(route.requirements, campaign)

    if unmet:
        # Offer alternatives (negotiable gates!)
        alternatives = get_available_alternatives(route, campaign)
        if not alternatives:
            return TravelBlocked(requirements=unmet, reason="No available route")

        # Player chooses: meet requirement, use alternative, or risky traversal
        return TravelOptions(
            blocked_by=unmet,
            alternatives=alternatives,
            risky_option=route.risky_traversal  # Always available at cost
        )

    # Successful travel
    campaign.map_state.make_connected(target, campaign.session)
    campaign.map_state.current_region = target

    # Auto-reveal adjacent regions as "aware"
    for adjacent in get_adjacent_regions(target):
        campaign.map_state.make_aware(adjacent, campaign.session)

    return TravelSuccess(region=target)
```

---

## 7. UI Components

### TUI (Textual) — ASCII Map Panel
```
┌─ NETWORK MAP ──────────────────────────────────────┐
│                                                     │
│     ░░░ FROZEN      [YOU ARE HERE]                 │
│      │  EDGE                                        │
│      │               ┌──────────┐                   │
│  ┌───┴───┐     ┌─────┤ ● RUST   │                  │
│  │PACIFIC│     │NORTH│ CORRIDOR ├─╌╌→ NORTHEAST    │
│  │CORRIDOR     │REACH│ (Lattice)│     (⚠️ options)  │
│  └───┬───┘     └──┬──┴────┬─────┘                   │
│      │            │       │                         │
│  ▒▒▒ DESERT ──────┼───────┼──── ⬡ APPALACHIAN     │
│   (aware)         │       │     👤×2 ◆ Job         │
│              BREADBASKET  │                         │
│                   │       │                         │
│              ═══ TEXAS ═══╪═══ (contested)         │
│                   │       │                         │
│              GULF PASSAGE─┘                         │
│              ⚡ Thread                              │
│                                                     │
├─────────────────────────────────────────────────────┤
│ ● Here  ◆ Job  ⚡ Thread  ⚠️ Options  ░ Disconnected │
└─────────────────────────────────────────────────────┘
```

### Web UI — Interactive SVG
- SVG-based with faction-colored nodes
- Hover shows region details
- Click opens travel confirmation or wiki page
- Animated connections for active routes
- Responsive scaling

### Map Commands
```
/map              — Show tactical map
/map [region]     — Center on region, show details
/map legend       — Show all markers explained
/travel [region]  — Attempt travel (checks requirements)
```

---

## 8. Implementation Phases

### Phase 1: Data Foundation
1. Add enums to `schema.py`: `RegionConnectivity`, `RequirementType`
2. Add models: `RouteRequirement`, `RouteAlternative`, `RegionState`, `MapState`
3. Extend `regions.json` with typed `routes` structure (requirements + alternatives)
4. Add `map_state: MapState` to Campaign model
5. Migration: set `connected` for regions in existing campaign travel history

### Phase 2: Negotiable Travel
1. Update `/region` command to show options when requirements unmet
2. Implement requirement checking with type-safe `RouteRequirement` parsing
3. Present alternatives to player (contact, bribe, risky traversal)
4. Apply costs for risky traversal (social energy, dormant threads)
5. Auto-reveal adjacent regions as "aware"

### Phase 3: Network Density Tracking
1. Track `npcs_met` per region when meeting NPCs
2. Track `threads_resolved` per region when resolving threads
3. Mark jobs as "significant" in templates, track in `significant_jobs`
4. Implement `check_embedded()` with network density threshold
5. Add UI indicator for network density progress

### Phase 4: TUI Map Display
1. Create ASCII map renderer in Textual
2. Add `/map` command with connectivity-based rendering
3. Show requirements and alternatives on hover/select
4. Add markers for jobs, threads, NPCs (with counts)

### Phase 5: Content Anchoring
1. Add `region` field to job templates (already partial)
2. Add `anchored_region` to Thread model
3. Add `current_region` to NPC tracking
4. Show content markers on map with wiki integration

### Phase 6: Web UI Map
1. Create SVG map component with faction-colored nodes
2. Add to game layout (collapsible panel or modal)
3. Interactive hover/click with route options
4. Wiki integration for region details

### Phase 7: Advanced Features
1. Secret regions (unlocked by specific hinges)
2. Dynamic faction control shifts based on player actions
3. Map notes (player annotations)
4. Fast travel for embedded regions (with confirmation)

---

## 9. Canon Compliance Checklist

| Requirement | Implementation |
|-------------|----------------|
| Nexus doesn't hold territory | Nexus shown as overlay/presence level, not region control |
| Hard borders vs zones of influence | Route requirements vs faction presence indicators |
| Uninhabited zones exist | Support for "hazard" regions with special requirements |
| Overlapping claims emerge in play | Faction control can shift based on player actions |
| ~500M survivors, fragmented | Map feels sparse, dangerous, not unified |
| No villains | Faction colors are neutral, not "enemy red" |
| Coexistence without consensus | Multiple valid paths through the map |
| **Relationships matter** | Connectivity represents social reach, not geography |
| **Negotiable gates** | Every blocked route has alternatives or risky traversal |
| **Agency over optimization** | Player chooses cost/risk tradeoffs, not binary unlocks |

---

## 10. Open Questions

1. **Starting region** — Always Rust Corridor, or character-background dependent?
2. **Fast travel** — Should "explored" regions allow instant travel?
3. **Faction territory shifts** — How do player actions change control?
4. **Hidden regions** — Any secret areas unlocked by specific hinges?
5. **Multiplayer** — If multiple campaigns exist, do maps share discovery?

---

## 11. Success Metrics

The map system is successful if:
- Players look at the map to decide what to do next
- "I need to get to X" becomes a meaningful goal
- Faction standing feels geographically relevant
- Jobs and threads have clear spatial context
- The map tells the story of the campaign's journey
- **Blocked routes feel like problems to solve**, not walls to grind through
- **Network density reflects meaningful engagement**, not checklist completion
- **Every region feels like a web of relationships**, not just a location

---

## 12. Council Review (2025-01-26)

This plan was reviewed by Gemini and Codex via `/council`. Key feedback incorporated:

### Gemini (Design & Philosophy)
| Concern | Resolution |
|---------|------------|
| Fog of war implies geographic ignorance | Renamed to "Social Connectivity" — you don't know regions because you don't know *people* there |
| Binary gates feel "game-y" | Added negotiable alternatives and risky traversal to every blocked route |
| "Explored" via job count risks grinding | Replaced with "Network Density" (NPCs met, threads resolved, standing) |
| Routes as lock-and-key | Reframed as risk/resource multipliers — you *can* cross, it just costs |

### Codex (Technical Quality)
| Issue | Resolution |
|-------|------------|
| Mutable defaults (`list[str] = []`) | Changed to `Field(default_factory=list)` throughout |
| Redundant `RegionState.id` | Removed — dict key in `MapState.regions` is sufficient |
| Raw string for `current_region` | Now uses `Region` enum for type safety |
| Unclear `first_heard`/`first_visited` | Renamed to `first_aware_session`/`first_visited_session`, documented as session numbers |
| Magic requirement strings | Created typed `RouteRequirement` and `RouteAlternative` models |
| `travel_history` duplication | Removed — defer to `CampaignState.history` |

### Preserved from Original
- Nexus as overlay (not territory holder) ✓
- Content anchoring (jobs, threads, NPCs tied to regions) ✓
- Terminal aesthetic and visual design ✓
- Phased implementation approach ✓

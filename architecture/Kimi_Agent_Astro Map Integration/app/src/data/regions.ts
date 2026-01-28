import type { Region, RegionData } from '@/types/map';

export const regions: Record<Region, RegionData> = {
  frozen_edge: {
    id: 'frozen_edge',
    name: 'Frozen Edge',
    description: 'The northernmost habitable zone, where permafrost meets survival. Harsh winters and isolation have forged a resilient population.',
    primaryFaction: 'ember_colonies',
    terrain: ['tundra', 'ice', 'mountain'],
    character: 'Bitter cold and endless night. Communities huddle around geothermal vents and salvaged heating systems.',
    routes: [
      {
        to: 'northern_reaches',
        requirements: [{ type: 'vehicle', vehicleCapability: 'off-road', description: 'Snow-capable vehicle or guide' }],
        alternatives: [
          { type: 'contact', description: 'Ember guide through the passes', cost: { social_energy: 1 } },
          { type: 'risky', description: 'Traverse on foot (extreme danger)', cost: { social_energy: 3 }, consequence: 'hypothermia_risk' }
        ],
        terrain: ['mountain', 'off-road'],
        travelDescription: 'Treacherous mountain passes southward'
      }
    ],
    nexusPresence: 'low',
    hazards: ['extreme_cold', 'blizzards', 'isolation'],
    pointsOfInterest: ['Fairbanks Thermal Station', 'Arctic Research Outpost', 'The Last Pipeline'],
    position: { x: 50, y: 8 }
  },

  pacific_corridor: {
    id: 'pacific_corridor',
    name: 'Pacific Corridor',
    description: 'The western seaboard from Seattle to San Diego, a hub of technological salvage and digital innovation.',
    primaryFaction: 'convergence',
    contestedBy: ['architects'],
    terrain: ['coastal', 'urban', 'tech'],
    character: 'Where the future was built and where some hope to rebuild it. Glass towers and rusted server farms.',
    routes: [
      {
        to: 'northern_reaches',
        requirements: [],
        terrain: ['road', 'coastal'],
        travelDescription: 'Coastal highways north'
      },
      {
        to: 'desert_sprawl',
        requirements: [],
        terrain: ['road', 'highway'],
        travelDescription: 'Interstate south through the valleys'
      }
    ],
    nexusPresence: 'high',
    hazards: ['surveillance', 'tech_fragility'],
    pointsOfInterest: ['Seattle Data Vaults', 'Silicon Valley Ruins', 'Port of Oakland'],
    position: { x: 12, y: 35 }
  },

  northern_reaches: {
    id: 'northern_reaches',
    name: 'Northern Reaches',
    description: 'The upper Midwest and Canadian borderlands, held together by faith and determination.',
    primaryFaction: 'covenant',
    contestedBy: ['ember_colonies'],
    terrain: ['forest', 'plains', 'road'],
    character: 'Small communities bound by shared belief. Church steeples visible across frozen lakes.',
    routes: [
      {
        to: 'frozen_edge',
        requirements: [{ type: 'vehicle', vehicleCapability: 'off-road' }],
        alternatives: [
          { type: 'contact', description: 'Ember guide' },
          { type: 'risky', description: 'Risky mountain crossing', cost: { social_energy: 2 } }
        ],
        terrain: ['mountain', 'off-road'],
        travelDescription: 'North into the frozen territories'
      },
      {
        to: 'pacific_corridor',
        requirements: [],
        terrain: ['road', 'coastal'],
        travelDescription: 'West along the coast'
      },
      {
        to: 'rust_corridor',
        requirements: [],
        terrain: ['road'],
        travelDescription: 'Eastern highways to the industrial belt'
      },
      {
        to: 'breadbasket',
        requirements: [],
        terrain: ['road', 'plains'],
        travelDescription: 'South into farm country'
      }
    ],
    nexusPresence: 'medium',
    hazards: ['bandits', 'harsh_winters'],
    pointsOfInterest: ['Minneapolis Cathedral', 'Great Lakes Trading Post', 'Duluth Harbor'],
    position: { x: 35, y: 25 }
  },

  rust_corridor: {
    id: 'rust_corridor',
    name: 'Rust Corridor',
    description: 'The Great Lakes industrial belt. Smokestacks and empty assembly lines tell the story of a fallen manufacturing empire.',
    primaryFaction: 'lattice',
    contestedBy: ['steel_syndicate'],
    terrain: ['urban', 'industrial', 'road'],
    character: 'Where steel was king. Now, scavengers pick through the bones of factories while Lattice tries to restart the machines.',
    routes: [
      {
        to: 'northern_reaches',
        requirements: [],
        terrain: ['road'],
        travelDescription: 'Northern highways, still maintained by Lattice'
      },
      {
        to: 'northeast_scar',
        requirements: [{ type: 'faction', faction: 'architects', minStanding: 'neutral', description: 'Architect clearance or pass' }],
        alternatives: [
          { type: 'contact', faction: 'ghost_networks', description: 'Smuggler route through ruins' },
          { type: 'bribe', description: 'Pay checkpoint guards', cost: { credits: 500 } },
          { type: 'risky', description: 'Sneak through at night', cost: { social_energy: 2 }, consequence: 'architects_noticed' }
        ],
        terrain: ['road', 'urban'],
        travelDescription: 'Through Architect checkpoints'
      },
      {
        to: 'appalachian_hollows',
        requirements: [{ type: 'vehicle', vehicleCapability: 'off-road' }],
        alternatives: [
          { type: 'contact', faction: 'ember_colonies', description: 'Ember guide through passes' },
          { type: 'risky', description: 'Rough mountain crossing', cost: { social_energy: 1 }, consequence: 'vehicle_strain' }
        ],
        terrain: ['mountain', 'off-road'],
        travelDescription: 'Mountain passes into Ember territory'
      },
      {
        to: 'breadbasket',
        requirements: [],
        terrain: ['road', 'plains'],
        travelDescription: 'Western highways into farm country'
      }
    ],
    nexusPresence: 'high',
    hazards: ['industrial_waste', 'unstable_structures'],
    pointsOfInterest: ['Detroit Salvage Markets', 'Pittsburgh Power Hub', 'Lattice Regional HQ'],
    position: { x: 65, y: 32 }
  },

  breadbasket: {
    id: 'breadbasket',
    name: 'Breadbasket',
    description: 'The agricultural heartland. Golden fields and silos hold the key to feeding the scattered survivors.',
    primaryFaction: 'cultivators',
    contestedBy: ['wanderers'],
    terrain: ['plains', 'farmland', 'road'],
    character: 'Endless fields of modified crops. The smell of earth and growing things. Communities built around harvest cycles.',
    routes: [
      {
        to: 'northern_reaches',
        requirements: [],
        terrain: ['road', 'plains'],
        travelDescription: 'North to the Covenant territories'
      },
      {
        to: 'rust_corridor',
        requirements: [],
        terrain: ['road'],
        travelDescription: 'East to the industrial belt'
      },
      {
        to: 'texas_spine',
        requirements: [],
        terrain: ['road', 'highway'],
        travelDescription: 'South on the old interstate'
      },
      {
        to: 'desert_sprawl',
        requirements: [],
        terrain: ['road', 'plains'],
        travelDescription: 'West toward the arid zones'
      }
    ],
    nexusPresence: 'medium',
    hazards: ['crop_blight', 'raiders'],
    pointsOfInterest: ['Kansas Seed Vault', 'Omaha Grain Exchange', 'The Great Silo'],
    position: { x: 42, y: 45 }
  },

  northeast_scar: {
    id: 'northeast_scar',
    name: 'Northeast Scar',
    description: 'The irradiated remains of the old Eastern Seaboard. High radiation zones punctuate areas of rebuilt civilization.',
    primaryFaction: 'architects',
    contestedBy: ['nexus'],
    terrain: ['urban', 'ruins', 'contaminated'],
    character: 'Skyscrapers turned tombstones. The Architects work to rebuild what was, while radiation pockets claim the unwary.',
    routes: [
      {
        to: 'rust_corridor',
        requirements: [{ type: 'faction', faction: 'architects', minStanding: 'neutral' }],
        alternatives: [
          { type: 'contact', faction: 'ghost_networks', description: 'Ghost smuggler route' },
          { type: 'bribe', description: 'Bribe checkpoint', cost: { credits: 500 } },
          { type: 'risky', description: 'Sneak through', cost: { social_energy: 2 }, consequence: 'architects_noticed' }
        ],
        terrain: ['road', 'urban'],
        travelDescription: 'West through checkpoints'
      },
      {
        to: 'appalachian_hollows',
        requirements: [],
        terrain: ['road', 'mountain'],
        travelDescription: 'South through the Appalachians'
      }
    ],
    nexusPresence: 'high',
    hazards: ['radiation', 'structural_collapse', 'contamination'],
    pointsOfInterest: ['Manhattan Quarantine Zone', 'Boston Reconstruction Hub', 'The Scar (Ground Zero)'],
    position: { x: 85, y: 28 }
  },

  desert_sprawl: {
    id: 'desert_sprawl',
    name: 'Desert Sprawl',
    description: 'The arid Southwest where secrets hide in the sand and Ghost Networks operate in the shadows.',
    primaryFaction: 'ghost_networks',
    contestedBy: ['steel_syndicate'],
    terrain: ['desert', 'wasteland', 'off-road'],
    character: 'Endless dunes and hidden bunkers. The Ghosts move like whispers through abandoned military installations.',
    routes: [
      {
        to: 'pacific_corridor',
        requirements: [],
        terrain: ['road', 'highway'],
        travelDescription: 'West to the coast'
      },
      {
        to: 'breadbasket',
        requirements: [],
        terrain: ['road', 'plains'],
        travelDescription: 'East to the agricultural zones'
      },
      {
        to: 'texas_spine',
        requirements: [],
        terrain: ['road'],
        travelDescription: 'Southeast to the trade routes'
      },
      {
        to: 'gulf_passage',
        requirements: [{ type: 'vehicle', vehicleCapability: 'off-road' }],
        alternatives: [
          { type: 'contact', description: 'Wanderer caravan guide' },
          { type: 'risky', description: 'Cross the badlands', cost: { social_energy: 2 }, consequence: 'dehydration_risk' }
        ],
        terrain: ['desert', 'off-road'],
        travelDescription: 'South through the desert wastes'
      }
    ],
    nexusPresence: 'low',
    hazards: ['dehydration', 'heat', 'sandstorms', 'radiation_pockets'],
    pointsOfInterest: ['Area 51 Ruins', 'Phoenix Solar Farm', 'Ghost Network Dead Drop'],
    position: { x: 18, y: 58 }
  },

  appalachian_hollows: {
    id: 'appalachian_hollows',
    name: 'Appalachian Hollows',
    description: 'The mountain valleys and coal country, where Ember Colonies have carved out isolated sanctuaries.',
    primaryFaction: 'ember_colonies',
    terrain: ['mountain', 'forest', 'valley'],
    character: 'Misty valleys and hidden hollows. Communities that want to be left alone, fiercely protective of their autonomy.',
    routes: [
      {
        to: 'rust_corridor',
        requirements: [{ type: 'vehicle', vehicleCapability: 'off-road' }],
        alternatives: [
          { type: 'contact', faction: 'ember_colonies', description: 'Ember guide through passes' },
          { type: 'risky', description: 'Rough mountain crossing', cost: { social_energy: 1 }, consequence: 'vehicle_strain' }
        ],
        terrain: ['mountain', 'off-road'],
        travelDescription: 'North through mountain passes'
      },
      {
        to: 'northeast_scar',
        requirements: [],
        terrain: ['road', 'mountain'],
        travelDescription: 'Northeast toward the coast'
      },
      {
        to: 'gulf_passage',
        requirements: [],
        terrain: ['road', 'mountain'],
        travelDescription: 'South through the mountain roads'
      }
    ],
    nexusPresence: 'low',
    hazards: ['flash_floods', 'landslides', 'isolation'],
    pointsOfInterest: ['Coal Creek Settlement', 'Blue Ridge Sanctuary', 'Old Mine Tunnels'],
    position: { x: 72, y: 52 }
  },

  texas_spine: {
    id: 'texas_spine',
    name: 'Texas Spine',
    description: 'The trade arteries of old Texas, now controlled by the Steel Syndicate who tax all commerce.',
    primaryFaction: 'steel_syndicate',
    contestedBy: ['lattice'],
    terrain: ['plains', 'road', 'urban'],
    character: 'Oil derricks and trade posts. Everything has a price, and the Syndicate sets it.',
    routes: [
      {
        to: 'breadbasket',
        requirements: [],
        terrain: ['road', 'highway'],
        travelDescription: 'North to the agricultural zones'
      },
      {
        to: 'desert_sprawl',
        requirements: [],
        terrain: ['road'],
        travelDescription: 'West to the desert'
      },
      {
        to: 'gulf_passage',
        requirements: [{ type: 'faction', faction: 'steel_syndicate', minStanding: 'neutral', description: 'Syndicate toll permit' }],
        alternatives: [
          { type: 'bribe', description: 'Pay the toll', cost: { credits: 300 } },
          { type: 'contact', description: 'Smuggler bypass route' },
          { type: 'risky', description: 'Avoid checkpoints', cost: { social_energy: 2 }, consequence: 'syndicate_noticed' }
        ],
        terrain: ['road', 'highway'],
        travelDescription: 'South to the Gulf (toll road)'
      }
    ],
    nexusPresence: 'medium',
    hazards: ['syndicate_taxes', 'bandits'],
    pointsOfInterest: ['Houston Refinery', 'Dallas Trade Hub', 'The Spine Highway'],
    position: { x: 38, y: 62 }
  },

  gulf_passage: {
    id: 'gulf_passage',
    name: 'Gulf Passage',
    description: 'The southern coast and waterways, where Wanderers move between ports and hidden coves.',
    primaryFaction: 'wanderers',
    contestedBy: ['ghost_networks'],
    terrain: ['coastal', 'swamp', 'water'],
    character: 'Humid air and salt spray. Boats and makeshift vessels carry goods and people along the coast.',
    routes: [
      {
        to: 'texas_spine',
        requirements: [{ type: 'faction', faction: 'steel_syndicate', minStanding: 'neutral' }],
        alternatives: [
          { type: 'bribe', description: 'Pay toll', cost: { credits: 300 } },
          { type: 'contact', description: 'Wanderer captain with Syndicate papers' },
          { type: 'risky', description: 'Back roads', cost: { social_energy: 2 } }
        ],
        terrain: ['road', 'highway'],
        travelDescription: 'North to Texas (toll route)'
      },
      {
        to: 'appalachian_hollows',
        requirements: [],
        terrain: ['road', 'coastal'],
        travelDescription: 'East along the coast'
      },
      {
        to: 'desert_sprawl',
        requirements: [{ type: 'vehicle', vehicleCapability: 'off-road' }],
        alternatives: [
          { type: 'contact', description: 'Wanderer caravan' },
          { type: 'risky', description: 'Desert crossing', cost: { social_energy: 2 }, consequence: 'heat_exhaustion' }
        ],
        terrain: ['desert', 'off-road'],
        travelDescription: 'West through the desert'
      },
      {
        to: 'sovereign_south',
        requirements: [],
        terrain: ['water', 'coastal'],
        travelDescription: 'Southeast by water or coastal road'
      }
    ],
    nexusPresence: 'low',
    hazards: ['flooding', 'storms', 'swamp_disease'],
    pointsOfInterest: ['New Orleans Docks', 'Mobile Bay Trading Post', 'The Floating Market'],
    position: { x: 55, y: 72 }
  },

  sovereign_south: {
    id: 'sovereign_south',
    name: 'Sovereign South',
    description: 'The southeastern states, where Witnesses document history and try to stay above the fray.',
    primaryFaction: 'witnesses',
    contestedBy: ['covenant'],
    terrain: ['forest', 'coastal', 'urban'],
    character: 'Moss-draped oaks and historic towns. The Witnesses watch and record, intervening only when truth is threatened.',
    routes: [
      {
        to: 'gulf_passage',
        requirements: [],
        terrain: ['water', 'coastal'],
        travelDescription: 'Northwest along the coast'
      },
      {
        to: 'appalachian_hollows',
        requirements: [],
        terrain: ['road', 'mountain'],
        travelDescription: 'North through the mountains'
      }
    ],
    nexusPresence: 'medium',
    hazards: ['humidity', 'old_grudges'],
    pointsOfInterest: ['Atlanta Archive', 'Charleston Library', 'Savannah Observation Post'],
    position: { x: 70, y: 78 }
  }
};

// Adjacency mapping for quick lookups
export const adjacentRegions: Record<Region, Region[]> = {
  frozen_edge: ['northern_reaches'],
  pacific_corridor: ['northern_reaches', 'desert_sprawl'],
  northern_reaches: ['frozen_edge', 'pacific_corridor', 'rust_corridor', 'breadbasket'],
  rust_corridor: ['northern_reaches', 'northeast_scar', 'appalachian_hollows', 'breadbasket'],
  breadbasket: ['northern_reaches', 'rust_corridor', 'texas_spine', 'desert_sprawl'],
  northeast_scar: ['rust_corridor', 'appalachian_hollows'],
  desert_sprawl: ['pacific_corridor', 'breadbasket', 'texas_spine', 'gulf_passage'],
  appalachian_hollows: ['rust_corridor', 'northeast_scar', 'gulf_passage', 'sovereign_south'],
  texas_spine: ['breadbasket', 'desert_sprawl', 'gulf_passage'],
  gulf_passage: ['texas_spine', 'desert_sprawl', 'appalachian_hollows', 'sovereign_south'],
  sovereign_south: ['gulf_passage', 'appalachian_hollows']
};

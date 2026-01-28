import type { Faction, FactionData } from '@/types/map';

export const factions: Record<Faction, FactionData> = {
  nexus: {
    id: 'nexus',
    name: 'Nexus',
    shortName: 'Nexus',
    motto: 'The network that watches',
    color: '#a855f7', // Purple
    description: 'Information holders present wherever infrastructure exists. They hold no territory, only data.',
  },
  ember_colonies: {
    id: 'ember_colonies',
    name: 'Ember Colonies',
    shortName: 'Ember',
    motto: 'We survived. We endure.',
    color: '#f97316', // Orange
    description: 'Autonomy at any cost. Isolated communities that value self-sufficiency and independence.',
  },
  lattice: {
    id: 'lattice',
    name: 'Lattice',
    shortName: 'Lattice',
    motto: 'We keep the lights on',
    color: '#3b82f6', // Blue
    description: 'Enhance humanity beyond weakness. Industrialists maintaining infrastructure and manufacturing.',
  },
  convergence: {
    id: 'convergence',
    name: 'Convergence',
    shortName: 'Converge',
    motto: 'Become what you were meant to be',
    color: '#06b6d4', // Cyan
    description: 'Upload consciousness, escape mortality. Transhumanists seeking digital transcendence.',
  },
  covenant: {
    id: 'covenant',
    name: 'Covenant',
    shortName: 'Covenant',
    motto: 'We hold the line',
    color: '#eab308', // Yellow
    description: 'Rebuild through faith structures. Religious communities bound by shared belief.',
  },
  wanderers: {
    id: 'wanderers',
    name: 'Wanderers',
    shortName: 'Wanderers',
    motto: 'The road remembers',
    color: '#22c55e', // Green
    description: 'Survival through mobility. Nomadic groups who travel the wastelands.',
  },
  cultivators: {
    id: 'cultivators',
    name: 'Cultivators',
    shortName: 'Cultivator',
    motto: 'From the soil, we rise',
    color: '#10b981', // Emerald
    description: 'Ecology-first restoration. Agricultural communities focused on sustainable farming.',
  },
  steel_syndicate: {
    id: 'steel_syndicate',
    name: 'Steel Syndicate',
    shortName: 'Steel Sy.',
    motto: 'Everything has a price',
    color: '#ef4444', // Red
    description: 'Resource control governs stability. Mercantile faction controlling trade routes.',
  },
  witnesses: {
    id: 'witnesses',
    name: 'Witnesses',
    shortName: 'Witnesses',
    motto: 'We remember so you don\'t have to lie',
    color: '#f59e0b', // Amber
    description: 'Observe history, avoid intervention. Archivists and historians preserving truth.',
  },
  architects: {
    id: 'architects',
    name: 'Architects',
    shortName: 'Architects',
    motto: 'We built this world',
    color: '#6366f1', // Indigo
    description: 'Rebuild old systems "properly". Engineers and planners restoring pre-collapse infrastructure.',
  },
  ghost_networks: {
    id: 'ghost_networks',
    name: 'Ghost Networks',
    shortName: 'Ghost',
    motto: 'We were never here',
    color: '#6b7280', // Gray
    description: 'Invisible resistance and sabotage. Covert operatives working in the shadows.',
  },
};

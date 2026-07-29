/* The yard roster at 32×32 — System A, the audited proportion
   (art_direction_gba_tactics.md: ~2.3 heads, displayed 1.10 world units,
   feet on the ground line at row 29 like the Cipher audition specimen
   they are built from, architecture/mocks/cipher_sprites.js).

   Identity lives in the head — that is why System A won the audition —
   so the operatives share a uniform body (same stance, same jacket, same
   blue chest band) and differ above the neck: VESPER's crested helm,
   KOA's topknot and headband over a bare face (plus the one permitted
   body edit: wider pauldrons), SABLE's cowl with goggles lit inside the
   shadow. The Syndicate crew is deliberately ONE design worn three
   times: a uniform crew is how "them" reads at a glance, and the badges
   and morale bars carry the per-unit state.

   One dominant hue + one accent per figure, phosphor discipline: ops are
   cool blues with cyan-family accents, SYN is rust with red lenses. */

export const SPRITES = {
  VESPER: {
    pal: {
      B: "#10151c",  // outline
      M: "#33465a",  // helm
      T: "#4b647d",  // helm lit (light from upper-left)
      A: "#5ccfff",  // visor slit
      L: "#bdefff",  // visor glow
      N: "#2196d8",  // squad blue — chest band + crest
      J: "#2b3a4a",  // jacket
      H: "#41586e",  // jacket lit
      P: "#1d2733",  // fatigues
      G: "#141920",  // boots / belt
    },
    grid: [
      "................................",
      "................................",
      "................................",
      "................................",
      "...............NN...............",
      "............BMMMMMMB............",
      "...........BTTMMMMMMB...........",
      "..........BTTMMMMMMMMB..........",
      "..........BTMMMMMMMMMB..........",
      "..........BMMMMMMMMMMB..........",
      "..........BALLAAAAAAAB..........",
      "..........BAALAAAAAAAB..........",
      "..........BMMMMMMMMMMB..........",
      "..........BMMMBBMMMMMB..........",
      "...........BMMMMMMMMB...........",
      "............BMMMMMMB............",
      "..............BMMB..............",
      "...........BJNNNNNNJB...........",
      "..........BHJJNNNNJJJB..........",
      "..........BHBJJJJJJBJB..........",
      "..........BHBJJJJJJBJB..........",
      "..........BHBJJJJJJBJB..........",
      "..........BGGGGGGGGGGB..........",
      "...........BPPPPPPPPB...........",
      "...........BPPB..BPPB...........",
      "...........BPPB..BPPB...........",
      "...........BPPB..BPPB...........",
      "...........BGGB..BGGB...........",
      "..........BGGGB..BGGGB..........",
      "..........BBBBB..BBBBB..........",
      "................................",
      "................................",
    ],
  },

  KOA: {
    pal: {
      B: "#10151c",  // outline
      D: "#1a1512",  // hair
      W: "#bfe3cf",  // headband — pale mint, his mark
      K: "#8a5a3a",  // skin
      N: "#2196d8",  // squad blue
      J: "#2b3a4a",  // jacket
      H: "#41586e",  // jacket lit
      P: "#1d2733",  // fatigues
      G: "#141920",  // boots / belt
    },
    grid: [
      "................................",
      "................................",
      "................................",
      "..............DDDD..............",
      "..............DDDD..............",
      ".............DDDDDD.............",
      "...........DDDDDDDDDD...........",
      "..........BWWWWWWWWWWB..........",
      "..........DKKKKKKKKKKD..........",
      "..........DKKKKKKKKKKD..........",
      "..........BKKBKKKKBKKB..........",
      "..........DKKKKKKKKKKD..........",
      "..........DKKKKKKKKKKD..........",
      "..........DKKKKBBKKKKD..........",
      "...........BKKKKKKKKB...........",
      "............BKKKKKKB............",
      "..............BKKB..............",
      ".........BHJJNNNNNNJJJB.........",
      ".........BHHJJNNNNJJJJB.........",
      ".........BHBJJJJJJJJBJB.........",
      ".........BHBJJJJJJJJBJB.........",
      ".........BHBJJJJJJJJBJB.........",
      ".........BGGGGGGGGGGGGB.........",
      "...........BPPPPPPPPB...........",
      "...........BPPB..BPPB...........",
      "...........BPPB..BPPB...........",
      "...........BPPB..BPPB...........",
      "...........BGGB..BGGB...........",
      "..........BGGGB..BGGGB..........",
      "..........BBBBB..BBBBB..........",
      "................................",
      "................................",
    ],
  },

  SABLE: {
    pal: {
      B: "#10151c",  // outline
      C: "#232e26",  // cowl
      V: "#33413a",  // cowl lit
      F: "#0d1116",  // the shadow inside the hood
      A: "#9fdcff",  // goggles
      L: "#e8f7ff",  // goggle glint
      N: "#2196d8",  // squad blue
      J: "#2b3a4a",  // jacket
      H: "#41586e",  // jacket lit
      P: "#1d2733",  // fatigues
      G: "#141920",  // boots / belt
    },
    grid: [
      "................................",
      "................................",
      "................................",
      "................................",
      "...............CC...............",
      ".............CCCCCC.............",
      "...........CCCCCCCCCC...........",
      "..........CCCCCCCCCCCC..........",
      "..........CVVCCCCCCCCC..........",
      "..........CFFFFFFFFFFC..........",
      "..........CFALAAAAAAFC..........",
      "..........CFFFFFFFFFFC..........",
      "..........CFFFFFFFFFFC..........",
      "...........CFFFFFFFFC...........",
      "...........BCCCCCCCCB...........",
      "............BCCCCCCB............",
      "..............BCCB..............",
      "...........BJNNNNNNJB...........",
      "..........BHJJNNNNJJJB..........",
      "..........BHBJJJJJJBJB..........",
      "..........BHBJJJJJJBJB..........",
      "..........BHBJJJJJJBJB..........",
      "..........BGGGGGGGGGGB..........",
      "...........BPPPPPPPPB...........",
      "...........BPPB..BPPB...........",
      "...........BPPB..BPPB...........",
      "...........BPPB..BPPB...........",
      "...........BGGB..BGGB...........",
      "..........BGGGB..BGGGB..........",
      "..........BBBBB..BBBBB..........",
      "................................",
      "................................",
    ],
  },

  SYN: {
    pal: {
      B: "#140f0e",  // outline
      C: "#2e211d",  // cap
      K: "#241b18",  // balaclava
      A: "#ff5c5c",  // lenses
      L: "#ffd0c0",  // lens glow
      N: "#c2452f",  // crew red — chest band
      R: "#3a2622",  // jacket rust
      W: "#55352c",  // jacket lit
      P: "#1f1715",  // pants
      G: "#120d0c",  // boots / belt
    },
    grid: [
      "................................",
      "................................",
      "................................",
      "................................",
      "................................",
      ".............CCCCCC.............",
      "...........CCCCCCCCCC...........",
      "..........CCCCCCCCCCCC..........",
      "..........BKKKKKKKKKKB..........",
      "..........BKKKKKKKKKKB..........",
      "..........BKALKKKKALKB..........",
      "..........BKKKKKKKKKKB..........",
      "..........BKKKKKKKKKKB..........",
      "..........BKKKKBBKKKKB..........",
      "...........BKKKKKKKKB...........",
      "............BKKKKKKB............",
      "..............BKKB..............",
      "...........BRNNNNNNRB...........",
      "..........BWRRNNNNRRRB..........",
      "..........BWBRRRRRRBRB..........",
      "..........BWBRRRRRRBRB..........",
      "..........BWBRRRRRRBRB..........",
      "..........BGGGGGGGGGGB..........",
      "...........BPPPPPPPPB...........",
      "...........BPPB..BPPB...........",
      "...........BPPB..BPPB...........",
      "...........BPPB..BPPB...........",
      "...........BGGB..BGGB...........",
      "..........BGGGB..BGGGB..........",
      "..........BBBBB..BBBBB..........",
      "................................",
      "................................",
    ],
  },
};

// unit name → design; the crew shares one on purpose
export function spriteFor(name) {
  return SPRITES[name] ?? (name.startsWith("SYN") ? SPRITES.SYN : null);
}

export function validate() {
  const bad = [];
  for (const [name, s] of Object.entries(SPRITES)) {
    if (s.grid.length !== 32) bad.push(`${name}: ${s.grid.length} rows`);
    s.grid.forEach((row, i) => {
      if (row.length !== 32) bad.push(`${name} r${i}: ${row.length} cols`);
      for (const ch of row) {
        if (ch !== "." && !s.pal[ch]) bad.push(`${name} r${i}: unknown '${ch}'`);
      }
    });
    // the ground line is the contract with the billboard quad
    if (!/[^.]/.test(s.grid[29])) bad.push(`${name}: nothing stands on row 29`);
    if (/[^.]/.test(s.grid[30]) || /[^.]/.test(s.grid[31])) bad.push(`${name}: art below the ground line`);
  }
  return bad;
}

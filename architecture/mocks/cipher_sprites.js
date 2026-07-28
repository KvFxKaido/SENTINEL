/* Cipher at 32×32, twice — the sprite proportion audition
   (art_direction_gba_tactics.md: pick the proportion system BEFORE
   multiplying it by gear layers).

   System A — FFT-ish, ~2.3 heads: the big expressive head. Reads emotion.
   System B — squat military, ~3.6 heads: the soldier silhouette. Reads role.

   Identity kit from assets/characters/cipher_detailed.yaml: short black
   dreadlocks, cyan data visor (the signature), lean build, Nexus blue
   accents on dark tech fabric, brown skin. One dominant hue + one accent
   per the art doc.

   Both figures share a palette and stand on the same ground line (row 29)
   so the billboard quad plants both pairs of feet on the tile. */

export const CIPHER_PAL = {
  B: "#10151c",  // outline
  D: "#171310",  // dreadlocks dark
  E: "#332a1f",  // dreadlocks texture
  S: "#6b4a32",  // skin
  A: "#5ccfff",  // data visor
  L: "#bdefff",  // visor glow
  N: "#2196d8",  // nexus accent
  J: "#2b3a4a",  // jacket mid
  H: "#41586e",  // jacket lit (light from upper-left)
  P: "#1d2733",  // fatigues
  G: "#141920",  // boots / belt
};

// ---- System A: FFT-ish, ~2.3 heads --------------------------------
export const CIPHER_A = [
  "................................",
  "................................",
  "................................",
  "................................",
  "................................",
  ".............DDDDDD.............",
  "...........DEDDEDDEDD...........",
  "..........DDEDDEDDEDDD..........",
  "..........DDSSSSSSSSDD..........",
  "..........DSSSSSSSSSSD..........",
  "..........BALAAAAAAAAB..........",
  "..........BALAAAAAAAAB..........",
  "..........DSSSSSSSSSSD..........",
  "..........DSSSSBBSSSSD..........",
  "...........BSSSSSSSSB...........",
  "............BSSSSSSB............",
  "..............BSSB..............",
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
];

// ---- System B: squat military, ~3.6 heads -------------------------
export const CIPHER_B = [
  "................................",
  ".............DDDDDD.............",
  "............DEDDEDDD............",
  "...........DDEDDEDDED...........",
  "...........DSSSSSSSSD...........",
  "...........BALAAAAAAB...........",
  "...........DSSSSSSSSD...........",
  "............BSSSSSSB............",
  ".............BSSSSB.............",
  "..............BSSB..............",
  "..........BHJJNNNNJJJB..........",
  ".........BHHJJNNNNJJJJB.........",
  ".........BHHBJJJJJJBJJB.........",
  ".........BHHBJJJJJJBJJB.........",
  ".........BHHBJJJJJJBJJB.........",
  ".........BGGGGGGGGGGGGB.........",
  "..........BPPPPPPPPPPB..........",
  "..........BPPPPPPPPPPB..........",
  "..........BPPPPBBPPPPB..........",
  "..........BPPPB..BPPPB..........",
  "..........BPPPB..BPPPB..........",
  "..........BPPPB..BPPPB..........",
  "..........BPPPB..BPPPB..........",
  "..........BPPPB..BPPPB..........",
  "..........BPPPB..BPPPB..........",
  "..........BGGGB..BGGGB..........",
  "..........BGGGB..BGGGB..........",
  ".........BGGGGB..BGGGGB.........",
  ".........BGGGGB..BGGGGB.........",
  ".........BBBBBB..BBBBBB.........",
  "................................",
  "................................",
];

export function validate() {
  const bad = [];
  for (const [name, grid] of [["A", CIPHER_A], ["B", CIPHER_B]]) {
    if (grid.length !== 32) bad.push(`${name}: ${grid.length} rows`);
    grid.forEach((row, i) => { if (row.length !== 32) bad.push(`${name} r${i}: ${row.length} cols`); });
  }
  return bad;
}

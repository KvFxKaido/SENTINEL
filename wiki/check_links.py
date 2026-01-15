#!/usr/bin/env python3
"""Wiki integrity checker - finds broken wikilinks and lore mismatches."""
import os
import re
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def strip_chapter_prefix(filename: str) -> str:
    """Strip chapter prefix like '01 - ' from lore filenames."""
    return re.sub(r'^\d+\s*-\s*', '', filename)

def main():
    wiki_root = Path(__file__).parent
    project_root = wiki_root.parent
    lore_root = project_root / 'lore'

    # Get all existing page names
    pages = set()
    for f in wiki_root.glob('**/*.md'):
        pages.add(f.stem)

    # Also check for aliases in frontmatter
    aliases = {}
    for f in wiki_root.glob('**/*.md'):
        try:
            content = f.read_text(encoding='utf-8')
            # Simple alias extraction from frontmatter
            if content.startswith('---'):
                fm_end = content.find('---', 3)
                if fm_end > 0:
                    frontmatter = content[3:fm_end]
                    in_aliases = False
                    for line in frontmatter.split('\n'):
                        if line.strip().startswith('aliases:'):
                            in_aliases = True
                        elif in_aliases and line.strip().startswith('- '):
                            alias = line.strip()[2:].strip()
                            aliases[alias] = f.stem
                        elif in_aliases and not line.startswith(' ') and not line.startswith('\t'):
                            in_aliases = False
        except:
            pass

    # Get all wikilinks from canon
    links_found = {}  # link -> list of source files
    for f in (wiki_root / 'canon').glob('**/*.md'):
        try:
            content = f.read_text(encoding='utf-8')
            for match in re.findall(r'\[\[([^\]|#]+)', content):
                clean = match.rstrip('\\')
                if clean not in links_found:
                    links_found[clean] = []
                links_found[clean].append(f.name)
        except:
            pass

    # Find broken links
    broken = []
    for link in sorted(links_found.keys()):
        if link not in pages and link not in aliases:
            broken.append((link, links_found[link]))

    # Report
    print(f'Wiki Integrity Report')
    print(f'=' * 50)
    print(f'Pages found: {len(pages)}')
    print(f'Aliases found: {len(aliases)}')
    print(f'Unique wikilinks: {len(links_found)}')
    print(f'Broken links: {len(broken)}')
    print()

    if broken:
        print('BROKEN WIKILINKS:')
        for link, sources in broken:
            print(f'  - [[{link}]]')
            for src in sources[:3]:  # Show up to 3 sources
                print(f'      in: {src}')
    else:
        print('✓ No broken links found!')

    # Check required pages
    print()
    factions = ['Nexus', 'Ember Colonies', 'Lattice', 'Convergence', 'Covenant',
                'Wanderers', 'Cultivators', 'Steel Syndicate', 'Witnesses',
                'Architects', 'Ghost Networks']
    regions = ['Rust Corridor', 'Appalachian Hollows', 'Gulf Passage', 'The Breadbasket',
               'Northern Reaches', 'Pacific Corridor', 'Desert Sprawl', 'Northeast Scar',
               'Sovereign South', 'Texas Spine', 'Frozen Edge']

    missing_factions = [f for f in factions if f not in pages]
    missing_regions = [r for r in regions if r not in pages]

    if missing_factions:
        print(f'MISSING FACTIONS ({len(missing_factions)}):')
        for f in missing_factions:
            print(f'  - {f}')
    else:
        print('✓ All 11 factions have pages')

    if missing_regions:
        print(f'MISSING REGIONS ({len(missing_regions)}):')
        for r in missing_regions:
            print(f'  - {r}')
    else:
        print('✓ All 11 regions have pages')

    # ========================================
    # LORE CROSS-REFERENCE CHECK
    # ========================================
    print()
    print('=' * 50)
    print('Lore Cross-Reference')
    print('=' * 50)

    if not lore_root.exists():
        print('(lore/ directory not found, skipping)')
    else:
        # Build lore title map: clean_title -> (original_filename, full_path)
        lore_titles = {}
        for f in lore_root.glob('*.md'):
            clean = strip_chapter_prefix(f.stem)
            lore_titles[clean] = (f.stem, f)

        print(f'Lore files found: {len(lore_titles)}')
        print()

        # Check for title mismatches (broken links that have lore equivalents)
        mismatches = []
        missing_lore = []

        for link, sources in broken:
            # Check if there's a lore file with similar name
            # Try exact match first
            if link in lore_titles:
                # Link matches lore exactly - just needs wiki page created
                pass
            else:
                # Check for case-insensitive or close matches
                link_lower = link.lower()
                found_match = None
                for lore_title in lore_titles:
                    if lore_title.lower() == link_lower:
                        found_match = lore_title
                        break

                if found_match:
                    mismatches.append((link, found_match, lore_titles[found_match][0]))
                else:
                    missing_lore.append(link)

        # Report mismatches
        if mismatches:
            print('TITLE MISMATCHES (wiki vs lore):')
            for wiki_title, lore_title, lore_file in mismatches:
                print(f'  Wiki:  [[{wiki_title}]]')
                print(f'  Lore:  "{lore_file}.md" -> "{lore_title}"')
                print(f'  Fix:   Rename wiki refs to [[{lore_title}]]')
                print()
        else:
            print('✓ No title mismatches found')

        # Show which broken links have lore sources available
        has_lore = [link for link, _ in broken if link in lore_titles]
        if has_lore:
            print()
            print('BROKEN LINKS WITH LORE SOURCE (can create wiki pages):')
            for link in has_lore:
                lore_file = lore_titles[link][0]
                print(f'  [[{link}]] <- lore/{lore_file}.md')

        # Show orphan lore files (not referenced in wiki)
        print()
        referenced_in_wiki = set(links_found.keys()) | pages | set(aliases.keys())
        orphan_lore = []
        for clean_title, (orig_file, path) in lore_titles.items():
            if clean_title not in referenced_in_wiki:
                # Also check case-insensitive
                if not any(clean_title.lower() == ref.lower() for ref in referenced_in_wiki):
                    orphan_lore.append((clean_title, orig_file))

        if orphan_lore:
            print(f'ORPHAN LORE FILES ({len(orphan_lore)}) - not referenced in wiki:')
            for clean, orig in orphan_lore:
                print(f'  lore/{orig}.md -> "{clean}"')
        else:
            print('✓ All lore files are referenced in wiki')

if __name__ == '__main__':
    main()

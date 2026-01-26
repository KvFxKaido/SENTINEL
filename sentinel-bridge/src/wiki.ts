/**
 * Wiki module for the Sentinel Bridge
 *
 * Reads wiki pages from the filesystem and provides search functionality.
 * Handles the canon + campaign overlay merging.
 *
 * Wiki structure:
 *   wiki/canon/           - Shared lore (factions, regions, timeline)
 *   wiki/campaigns/{id}/  - Campaign-specific overlays
 *     NPCs/               - NPC pages
 *     Characters/         - Player character pages
 *     _*.md               - Index/tracker pages
 */

import { join, basename, dirname, relative } from "https://deno.land/std@0.208.0/path/mod.ts";

/** Frontmatter parsed from wiki pages */
export interface WikiFrontmatter {
  type?: string;
  tags?: string[];
  campaign?: string;
  faction?: string;
  disposition?: string;
  standing?: string;
  portrait?: string;
  extends?: string;
  aliases?: string[];
  [key: string]: unknown;
}

/** A wiki page with parsed content */
export interface WikiPage {
  /** Page name (filename without .md) */
  name: string;
  /** Full path relative to wiki root */
  path: string;
  /** Source: 'canon' or campaign ID */
  source: string;
  /** Page type from frontmatter */
  type: string | null;
  /** Parsed frontmatter */
  frontmatter: WikiFrontmatter;
  /** Raw markdown content (without frontmatter) */
  content: string;
  /** Full raw content (with frontmatter) */
  raw: string;
}

/** Search result */
export interface WikiSearchResult {
  name: string;
  path: string;
  source: string;
  type: string | null;
  /** Relevance score (higher = more relevant) */
  score: number;
  /** Snippet showing match context */
  snippet: string;
}

/** Wiki configuration */
export interface WikiConfig {
  /** Path to wiki root directory */
  wikiPath: string;
}

/**
 * Wiki reader and search engine
 */
export class Wiki {
  private wikiPath: string;

  constructor(config: WikiConfig) {
    this.wikiPath = config.wikiPath;
  }

  /**
   * Get a wiki page by name, with optional campaign overlay merging
   */
  async getPage(name: string, campaignId?: string): Promise<WikiPage | null> {
    // Normalize the name (handle spaces, etc.)
    const normalizedName = name.replace(/\s+/g, " ").trim();

    // Try campaign-specific locations first if campaign provided
    if (campaignId) {
      const campaignLocations = [
        join(this.wikiPath, "campaigns", campaignId, `${normalizedName}.md`),
        join(this.wikiPath, "campaigns", campaignId, "NPCs", `${normalizedName}.md`),
        join(this.wikiPath, "campaigns", campaignId, "Characters", `${normalizedName}.md`),
        join(this.wikiPath, "campaigns", campaignId, "hinges", `${normalizedName}.md`),
        join(this.wikiPath, "campaigns", campaignId, "threads", `${normalizedName}.md`),
      ];

      for (const path of campaignLocations) {
        const page = await this.readPage(path, campaignId);
        if (page) return page;
      }
    }

    // Try canon location
    const canonPath = join(this.wikiPath, "canon", `${normalizedName}.md`);
    const canonPage = await this.readPage(canonPath, "canon");
    if (canonPage) return canonPage;

    // Try searching by filename (case-insensitive)
    return await this.findPageByName(normalizedName, campaignId);
  }

  /**
   * Search wiki pages for a query
   */
  async search(query: string, campaignId?: string, limit = 10): Promise<WikiSearchResult[]> {
    const results: WikiSearchResult[] = [];
    const queryLower = query.toLowerCase();
    const queryWords = queryLower.split(/\s+/).filter(w => w.length > 2);

    // Search canon pages
    const canonDir = join(this.wikiPath, "canon");
    await this.searchDirectory(canonDir, "canon", queryLower, queryWords, results);

    // Search campaign pages if provided
    if (campaignId) {
      const campaignDir = join(this.wikiPath, "campaigns", campaignId);
      await this.searchDirectory(campaignDir, campaignId, queryLower, queryWords, results);
    }

    // Sort by score (descending) and limit
    results.sort((a, b) => b.score - a.score);
    return results.slice(0, limit);
  }

  /**
   * List all pages in a category
   */
  async listPages(category: string, campaignId?: string): Promise<WikiPage[]> {
    const pages: WikiPage[] = [];

    if (campaignId) {
      let dir: string;
      switch (category) {
        case "npcs":
          dir = join(this.wikiPath, "campaigns", campaignId, "NPCs");
          break;
        case "characters":
          dir = join(this.wikiPath, "campaigns", campaignId, "Characters");
          break;
        case "factions":
          // Faction pages are at campaign root level
          dir = join(this.wikiPath, "campaigns", campaignId);
          break;
        default:
          dir = join(this.wikiPath, "campaigns", campaignId, category);
      }

      try {
        for await (const entry of Deno.readDir(dir)) {
          if (entry.isFile && entry.name.endsWith(".md") && !entry.name.startsWith("_")) {
            const page = await this.readPage(join(dir, entry.name), campaignId);
            if (page) {
              // For factions category, only include faction-type pages
              if (category === "factions") {
                if (page.type === "faction" || page.frontmatter.extends) {
                  pages.push(page);
                }
              } else {
                pages.push(page);
              }
            }
          }
        }
      } catch {
        // Directory doesn't exist, that's ok
      }
    }

    // For factions, also include canon factions
    if (category === "factions") {
      const canonDir = join(this.wikiPath, "canon");
      try {
        for await (const entry of Deno.readDir(canonDir)) {
          if (entry.isFile && entry.name.endsWith(".md")) {
            const page = await this.readPage(join(canonDir, entry.name), "canon");
            if (page && page.type === "faction") {
              // Don't include if we already have a campaign overlay
              if (!pages.find(p => p.name === page.name)) {
                pages.push(page);
              }
            }
          }
        }
      } catch {
        // Directory doesn't exist
      }
    }

    return pages;
  }

  /**
   * Read a single page from disk
   */
  private async readPage(path: string, source: string): Promise<WikiPage | null> {
    try {
      const raw = await Deno.readTextFile(path);
      const { frontmatter, content } = this.parseFrontmatter(raw);

      const name = basename(path, ".md");
      const relPath = relative(this.wikiPath, path);

      return {
        name,
        path: relPath,
        source,
        type: frontmatter.type || null,
        frontmatter,
        content,
        raw,
      };
    } catch {
      return null;
    }
  }

  /**
   * Find a page by name (case-insensitive search)
   */
  private async findPageByName(name: string, campaignId?: string): Promise<WikiPage | null> {
    const nameLower = name.toLowerCase();

    // Search campaign directory first
    if (campaignId) {
      const campaignDir = join(this.wikiPath, "campaigns", campaignId);
      const found = await this.findInDirectory(campaignDir, nameLower, campaignId);
      if (found) return found;
    }

    // Search canon
    const canonDir = join(this.wikiPath, "canon");
    return await this.findInDirectory(canonDir, nameLower, "canon");
  }

  /**
   * Recursively search a directory for a page by name
   */
  private async findInDirectory(dir: string, nameLower: string, source: string): Promise<WikiPage | null> {
    try {
      for await (const entry of Deno.readDir(dir)) {
        if (entry.isDirectory && !entry.name.startsWith(".")) {
          const found = await this.findInDirectory(join(dir, entry.name), nameLower, source);
          if (found) return found;
        } else if (entry.isFile && entry.name.endsWith(".md")) {
          const entryName = entry.name.slice(0, -3).toLowerCase();
          if (entryName === nameLower) {
            return await this.readPage(join(dir, entry.name), source);
          }
        }
      }
    } catch {
      // Directory doesn't exist or can't be read
    }
    return null;
  }

  /**
   * Search a directory and its subdirectories
   */
  private async searchDirectory(
    dir: string,
    source: string,
    queryLower: string,
    queryWords: string[],
    results: WikiSearchResult[]
  ): Promise<void> {
    try {
      for await (const entry of Deno.readDir(dir)) {
        const fullPath = join(dir, entry.name);

        if (entry.isDirectory && !entry.name.startsWith(".")) {
          await this.searchDirectory(fullPath, source, queryLower, queryWords, results);
        } else if (entry.isFile && entry.name.endsWith(".md") && !entry.name.startsWith("_")) {
          const page = await this.readPage(fullPath, source);
          if (page) {
            const score = this.scoreMatch(page, queryLower, queryWords);
            if (score > 0) {
              results.push({
                name: page.name,
                path: page.path,
                source: page.source,
                type: page.type,
                score,
                snippet: this.extractSnippet(page.content, queryLower),
              });
            }
          }
        }
      }
    } catch {
      // Directory doesn't exist or can't be read
    }
  }

  /**
   * Score how well a page matches the query
   */
  private scoreMatch(page: WikiPage, queryLower: string, queryWords: string[]): number {
    let score = 0;
    const nameLower = page.name.toLowerCase();
    const contentLower = page.content.toLowerCase();

    // Exact name match (highest score)
    if (nameLower === queryLower) {
      score += 100;
    }
    // Name contains query
    else if (nameLower.includes(queryLower)) {
      score += 50;
    }

    // Check each query word
    for (const word of queryWords) {
      if (nameLower.includes(word)) {
        score += 20;
      }
      // Count occurrences in content
      const matches = contentLower.split(word).length - 1;
      score += Math.min(matches * 2, 20); // Cap at 20 per word
    }

    // Bonus for matching tags
    const tags = page.frontmatter.tags || [];
    for (const tag of tags) {
      if (tag.toLowerCase().includes(queryLower)) {
        score += 15;
      }
    }

    // Bonus for matching faction
    if (page.frontmatter.faction?.toLowerCase().includes(queryLower)) {
      score += 15;
    }

    return score;
  }

  /**
   * Extract a snippet around the first match
   */
  private extractSnippet(content: string, query: string): string {
    const index = content.toLowerCase().indexOf(query.toLowerCase());
    if (index === -1) {
      // Return first 150 chars as fallback
      return content.slice(0, 150).replace(/\n/g, " ").trim() + "...";
    }

    const start = Math.max(0, index - 50);
    const end = Math.min(content.length, index + query.length + 100);

    let snippet = content.slice(start, end).replace(/\n/g, " ").trim();
    if (start > 0) snippet = "..." + snippet;
    if (end < content.length) snippet = snippet + "...";

    return snippet;
  }

  /**
   * Parse YAML frontmatter from markdown
   */
  private parseFrontmatter(raw: string): { frontmatter: WikiFrontmatter; content: string } {
    const frontmatterMatch = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);

    if (!frontmatterMatch) {
      return { frontmatter: {}, content: raw };
    }

    const [, yamlStr, content] = frontmatterMatch;

    // Simple YAML parser for our use case
    const frontmatter: WikiFrontmatter = {};
    let currentKey: string | null = null;
    let inArray = false;
    const arrayValues: string[] = [];

    for (const line of yamlStr.split("\n")) {
      const trimmed = line.trim();

      // Array item
      if (trimmed.startsWith("- ") && inArray && currentKey) {
        arrayValues.push(trimmed.slice(2).trim());
        continue;
      }

      // End previous array if we were in one
      if (inArray && currentKey && !trimmed.startsWith("-")) {
        frontmatter[currentKey] = arrayValues.slice();
        arrayValues.length = 0;
        inArray = false;
        currentKey = null;
      }

      // Key: value or key: (start of array)
      const kvMatch = trimmed.match(/^([^:]+):\s*(.*)$/);
      if (kvMatch) {
        const [, key, value] = kvMatch;
        const cleanKey = key.trim();

        if (value === "" || value === "|" || value === ">") {
          // Might be start of array or multiline
          currentKey = cleanKey;
          inArray = true;
        } else {
          // Simple value
          let cleanValue: string | boolean | number = value.trim();
          // Remove quotes
          if ((cleanValue.startsWith('"') && cleanValue.endsWith('"')) ||
              (cleanValue.startsWith("'") && cleanValue.endsWith("'"))) {
            cleanValue = cleanValue.slice(1, -1);
          }
          // Parse booleans
          if (cleanValue === "true") cleanValue = true as unknown as string;
          else if (cleanValue === "false") cleanValue = false as unknown as string;
          // Parse numbers
          else if (/^-?\d+$/.test(cleanValue)) cleanValue = parseInt(cleanValue);

          frontmatter[cleanKey] = cleanValue;
        }
      }
    }

    // Handle trailing array
    if (inArray && currentKey && arrayValues.length > 0) {
      frontmatter[currentKey] = arrayValues;
    }

    return { frontmatter, content: content.trim() };
  }
}

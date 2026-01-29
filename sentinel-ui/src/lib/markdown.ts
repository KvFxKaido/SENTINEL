/**
 * Markdown rendering utilities for SENTINEL wiki viewer.
 *
 * Supports Obsidian-flavored markdown with wikilinks.
 */

export interface RenderOptions {
  /** Campaign ID for context-aware link resolution */
  campaignId?: string;
}

/**
 * Render markdown content to HTML.
 *
 * Handles:
 * - Standard markdown (headers, lists, bold, italic, code)
 * - Obsidian-style wikilinks [[Page Name]]
 * - Callouts/admonitions
 * - Code blocks with syntax highlighting classes
 */
export function renderMarkdown(content: string, options: RenderOptions = {}): string {
  if (!content) return '';

  let html = content;

  // Escape HTML entities first (but preserve our own tags later)
  html = escapeHtml(html);

  // Process wikilinks: [[Page Name]] or [[Page Name|Display Text]]
  html = html.replace(/\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g, (_, page, display) => {
    const pageName = page.trim();
    const displayText = display?.trim() || pageName;
    return `<a href="#" class="wikilink" data-page="${escapeAttr(pageName)}">${escapeHtml(displayText)}</a>`;
  });

  // Process headers
  html = html.replace(/^######\s+(.+)$/gm, '<h6>$1</h6>');
  html = html.replace(/^#####\s+(.+)$/gm, '<h5>$1</h5>');
  html = html.replace(/^####\s+(.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^###\s+(.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^##\s+(.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^#\s+(.+)$/gm, '<h1>$1</h1>');

  // Process code blocks (fenced)
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const langClass = lang ? ` class="language-${lang}"` : '';
    return `<pre><code${langClass}>${code.trim()}</code></pre>`;
  });

  // Process inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Process bold and italic
  html = html.replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  html = html.replace(/___([^_]+)___/g, '<strong><em>$1</em></strong>');
  html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
  html = html.replace(/_([^_]+)_/g, '<em>$1</em>');

  // Process strikethrough
  html = html.replace(/~~([^~]+)~~/g, '<del>$1</del>');

  // Process blockquotes
  html = html.replace(/^>\s+(.+)$/gm, '<blockquote>$1</blockquote>');
  // Merge consecutive blockquotes
  html = html.replace(/<\/blockquote>\n<blockquote>/g, '\n');

  // Process callouts (Obsidian-style)
  html = html.replace(/^>\s*\[!(\w+)\]\s*(.*)$/gm, (_, type, title) => {
    return `<div class="callout callout-${type.toLowerCase()}"><div class="callout-title">${title || type}</div>`;
  });

  // Process horizontal rules
  html = html.replace(/^---+$/gm, '<hr>');
  html = html.replace(/^\*\*\*+$/gm, '<hr>');

  // Process unordered lists
  html = html.replace(/^[\-\*]\s+(.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

  // Process ordered lists
  html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');

  // Process links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // Process images
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" loading="lazy">');

  // Process paragraphs (lines not already wrapped)
  const lines = html.split('\n');
  const processed: string[] = [];
  let inParagraph = false;

  for (const line of lines) {
    const trimmed = line.trim();

    // Skip empty lines
    if (!trimmed) {
      if (inParagraph) {
        processed.push('</p>');
        inParagraph = false;
      }
      continue;
    }

    // Skip lines that are already block elements
    if (
      trimmed.startsWith('<h') ||
      trimmed.startsWith('<pre') ||
      trimmed.startsWith('<ul') ||
      trimmed.startsWith('<ol') ||
      trimmed.startsWith('<li') ||
      trimmed.startsWith('<blockquote') ||
      trimmed.startsWith('<div') ||
      trimmed.startsWith('<hr') ||
      trimmed.startsWith('</ul') ||
      trimmed.startsWith('</ol') ||
      trimmed.startsWith('</blockquote') ||
      trimmed.startsWith('</div')
    ) {
      if (inParagraph) {
        processed.push('</p>');
        inParagraph = false;
      }
      processed.push(line);
      continue;
    }

    // Wrap in paragraph
    if (!inParagraph) {
      processed.push('<p>');
      inParagraph = true;
    }
    processed.push(line);
  }

  if (inParagraph) {
    processed.push('</p>');
  }

  return processed.join('\n');
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function escapeAttr(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

export default renderMarkdown;

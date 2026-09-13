/* Marked 17.0.5 supplies tokens only. Model content is never parsed as HTML.
 * All elements/attributes are chosen here; token text goes through text nodes.
 * Keep raw HTML, media, and unknown token types inert when extending this list.
 */
(() => {
  'use strict';

  function safeLink(href) {
    if (typeof href !== 'string' || !/^https:\/\//i.test(href) || /[\u0000-\u0020\u007f]/.test(href)) return null;
    try {
      const url = new URL(href);
      return url.protocol === 'https:' && !url.username && !url.password ? url.href : null;
    } catch {
      return null;
    }
  }

  function appendTokens(parent, tokens, depth = 0) {
    for (const token of tokens || []) {
      if (depth > 32) {
        parent.append(document.createTextNode(token.raw || token.text || ''));
        continue;
      }
      const appendElement = (tag, children = token.tokens) => {
        const element = document.createElement(tag);
        if (children) appendTokens(element, children, depth + 1);
        else element.textContent = token.text || '';
        parent.append(element);
        return element;
      };
      switch (token.type) {
        case 'space':
        case 'def':
          break;
        case 'heading':
          appendElement(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'][token.depth - 1] || 'p');
          break;
        case 'paragraph':
          appendElement('p');
          break;
        case 'strong':
          appendElement('strong');
          break;
        case 'em':
          appendElement('em');
          break;
        case 'del':
          appendElement('del');
          break;
        case 'blockquote':
          appendElement('blockquote');
          break;
        case 'code': {
          const pre = document.createElement('pre');
          const code = document.createElement('code');
          code.textContent = token.text || '';
          pre.append(code);
          parent.append(pre);
          break;
        }
        case 'codespan':
          appendElement('code', null);
          break;
        case 'hr':
        case 'br':
          parent.append(document.createElement(token.type));
          break;
        case 'list': {
          const list = document.createElement(token.ordered ? 'ol' : 'ul');
          if (token.ordered && Number.isSafeInteger(token.start) && token.start > 0) list.start = token.start;
          for (const item of token.items) {
            const li = document.createElement('li');
            if (item.task) li.append(document.createTextNode(item.checked ? '[x] ' : '[ ] '));
            appendTokens(li, item.tokens, depth + 1);
            list.append(li);
          }
          parent.append(list);
          break;
        }
        case 'table': {
          const table = document.createElement('table');
          const head = document.createElement('thead');
          const body = document.createElement('tbody');
          const appendRow = (section, cells, tag) => {
            const row = document.createElement('tr');
            for (const cell of cells) {
              const element = document.createElement(tag);
              appendTokens(element, cell.tokens, depth + 1);
              row.append(element);
            }
            section.append(row);
          };
          appendRow(head, token.header, 'th');
          for (const cells of token.rows) appendRow(body, cells, 'td');
          table.append(head, body);
          parent.append(table);
          break;
        }
        case 'link': {
          const href = safeLink(token.href);
          if (href) {
            const link = appendElement('a');
            link.href = href;
            link.rel = 'noopener noreferrer';
          } else {
            appendTokens(parent, token.tokens, depth + 1);
          }
          break;
        }
        case 'text':
          if (token.tokens) appendTokens(parent, token.tokens, depth + 1);
          else parent.append(document.createTextNode(token.text || ''));
          break;
        case 'image':
        case 'escape':
        case 'html':
        default:
          parent.append(document.createTextNode(token.text || token.raw || ''));
      }
    }
  }

  window.renderAnalysisMarkdown = (container, markdown) => {
    if (typeof window.marked?.lexer !== 'function') {
      container.textContent = markdown;
      return;
    }
    try {
      const fragment = document.createDocumentFragment();
      appendTokens(fragment, window.marked.lexer(markdown, { gfm: true }));
      container.replaceChildren(fragment);
    } catch {
      // Parser failure must preserve the same safe, readable fallback.
      container.textContent = markdown;
    }
  };
})();

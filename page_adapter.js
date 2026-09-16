/* Only the rendered Bale UI is read. The only mutations are tab selection,
   scrolling, and opening a conversation. Never touches the message composer. */
function balePageAdapter(operation, argument) {
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => Array.from(root.querySelectorAll(s));
  const label = e => e.getAttribute('aria-label') || e.getAttribute('alt') || '';
  const norm = text => (text || '').replace(/[\u200e\u200f\ufe0f]/g, '').replace(/\s+/g, ' ').trim();
  const shown = e => {
    if (!e || e.closest('[aria-hidden="true"]')) return false;
    const r = e.getBoundingClientRect();
    const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };
  const icons = e => $$('[role="img"],img', e).map(label);
  function rich(n) {
    if (n.nodeType === 3) return n.textContent;
    if (n.nodeType !== 1) return '';
    if (['SCRIPT', 'STYLE', 'SVG'].includes(n.tagName)) return '';
    if (n.tagName === 'IMG') {
      const alt = n.getAttribute('alt') || '';
      return /icon|thumbnail|avatar|file/i.test(alt) ? '' : alt;
    }
    if (n.tagName === 'BR') return '\n';
    return Array.from(n.childNodes).map(rich).join('') +
      (['DIV', 'P'].includes(n.tagName) || n.classList.contains('p') ? '\n' : '');
  }
  const clean = s => (s || '').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  const rowElements = () => {
    // Try multiple selector strategies. Bale Web DOM changes across versions.
    const strategies = [
      '[aria-label="dialog-item"]',
      '[data-testid*="dialog-item"]',
      '[data-testid*="dialogItem"]',
      '[data-item-index]',
      '.dialog-item',
      '[data-sentry-component*="Dialog"]',
    ];
    for (const sel of strategies) {
      const found = $$(sel).filter(shown);
      const rows = found.filter(e => $('bdi', e) || $('.dialog-item-content', e) || $('[title]', e));
      if (rows.length > 0) return rows;
    }
    // Last resort: scan for a virtualized list of rows.
    // Look for a scroll container with many children each containing a <bdi>.
    const scrollers = $$('[data-testid="virtuoso-scroller"], [data-virtuoso-scroller], .virtuoso-scroller');
    for (const sc of scrollers) {
      const kids = $$('*', sc).filter(e =>
        e.children.length > 0 && $('bdi', e) && shown(e) &&
        e.getBoundingClientRect().height > 30 && e.getBoundingClientRect().height < 200
      );
      // Pick the shallowest wrapper level (siblings sharing the same parent).
      const grouped = {};
      for (const k of kids) {
        const key = k.parentElement;
        (grouped[key ? key.tagName + '#' + (key.className || '') : 'root'] ||= []).push(k);
      }
      const best = Object.values(grouped).sort((a, b) => b.length - a.length)[0];
      if (best && best.length >= 1) return best;
    }
    return [];
  };
  function scroller() {
    const first = rowElements()[0];
    if (!first) return null;
    return first.closest('[data-testid="virtuoso-scroller"]') ||
           first.closest('[data-virtuoso-scroller]') ||
           first.closest('.virtuoso-scroller') ||
           first.closest('[style*="overflow"]') || null;
  }
  function rowData(e) {
    const content = $('.dialog-item-content', e) || e;
    const nameEl = $('bdi', content) || $('[data-testid*="name"]', content) || $('h4', content) || $('h5', content);
    const preview = $('[title]', content);
    const im = icons(e);
    const indexEl = e.closest('[data-item-index]') || e;
    const rawIndex = indexEl.getAttribute?.('data-item-index');
    const index = rawIndex != null ? Number(rawIndex) : -1;
    return {
      name: clean(nameEl ? rich(nameEl) : rich(content).split('\n')[0] || ''), index,
      preview: preview?.getAttribute('title') || '',
      pinned: im.some(i => ['pinned', 'Pin-icon'].includes(i)),
      self: im.includes('BoldBookmark-icon'),
      join_only: norm(preview?.getAttribute('title')) === 'به بله پیوست',
      kind: im.includes('ThreeUser-icon') ? 'group' : im.includes('Tv-icon') ? 'channel' : 'personal',
    };
  }
  function listState() {
    const rows = rowElements().map(rowData);
    const s = scroller();
    const headings = $$('[aria-label="dialog-tab-list"] h3, [aria-label="dialog-tab-list"] [role="tab"], [aria-label="dialog-tab-list"] button');
    const heading = headings.find(h => norm(h.textContent).includes('شخصی'));
    // Bale orders swipe panels to match headings. aria-hidden distinguishes
    // the live tab from mounted, off-screen duplicates.
    const panel = s?.closest('[data-swipeable]');
    const panels = panel ? Array.from(panel.parentElement.children).filter(p => p.hasAttribute('data-swipeable')) : [];
    const personal = headings.length === 0 || !heading || (panel && panels.indexOf(panel) === headings.indexOf(heading));
    return {rows, personal, scroll_top: s?.scrollTop || 0,
      at_bottom: !!s && s.scrollHeight - s.scrollTop - s.clientHeight < 3};
  }
  function messages() {
    return $$('[aria-label="message-item"]').filter(shown);
  }
  function messageState() {
    const header = $('[aria-label="ChatAppBar"]');
    const name = clean(rich($('p', header || document) || document.createTextNode('')));
    const all = messages();
    const last = all.at(-1);
    const s = last?.closest('#message_list_scroller_id, [data-testid="virtuoso-scroller"]');
    const loading = $$('[aria-label="Loading-icon"]').some(e => shown(e) && !e.closest('[aria-label="dialog-item"]'));
    if (!last) return {name, loading, message: null, at_bottom: false};
    const im = icons(last);
    const preview = $('[data-sentry-component="Preview"]', last);
    const texts = $$('[data-sentry-component="NewTextContainerFC"]', last)
      .filter(e => !e.closest('[data-sentry-component="Preview"]'));
    const text = clean(texts.map(rich).join('\n'));
    const raw = clean(rich(last));
    const isForward = im.includes('BoldForwardF-icon');
    let forwarded = null;
    if (isForward) {
      const lines = raw.split('\n').map(s => s.trim()).filter(Boolean);
      const index = lines.findIndex(s => s.includes('بازارسال شده از'));
      if (index >= 0) forwarded = lines[index].replace('بازارسال شده از', '').trim() || lines[index + 1];
    }
    let kind = 'text';
    if (im.includes('file')) kind = 'file';
    else if ($('audio', last) || /Audio|Music|Voice/.test(last.innerHTML) || im.includes('ArrowDown-icon') && /\d.*[:：].*\d/.test(raw)) kind = 'audio';
    else if ($('video', last) || /VideoMessage|VideoBubble/.test(last.innerHTML)) kind = 'video';
    else if (im.includes('thumbnail')) kind = 'image';
    else if (/Sticker/.test(last.innerHTML)) kind = 'sticker';
    else if (!text) kind = 'other';
    let details = '';
    if (kind !== 'text') {
      // Read the media bubble without duplicating its caption, quoted message,
      // forwarding attribution, or delivery timestamp.
      const walk = n => {
        if (n.nodeType === 1 && (n.matches('[data-sentry-component="Preview"], [data-sentry-component="NewTextContainerFC"], [data-sentry-component="MessageBottomFC"]'))) return '';
        if (n.nodeType === 3) return n.textContent;
        if (n.nodeType !== 1 || ['SVG', 'IMG'].includes(n.tagName)) return '';
        return Array.from(n.childNodes).map(walk).join('') + (['DIV','P'].includes(n.tagName) ? '\n' : '');
      };
      details = clean(walk(last));
      if (isForward && forwarded) details = details.replace('بازارسال شده از', '').replace(forwarded, '').trim();
      if (!details) details = `[${kind}; no visible text metadata]`;
    }
    return {
      name, loading, at_bottom: !!s && s.scrollHeight - s.scrollTop - s.clientHeight < 8,
      message: {
        id: last.getAttribute('data-sid'), epoch_ms: last.getAttribute('data-date'),
        direction: im.includes('RightBubble-icon') || $('[aria-label="message-state-icon"]', last) ? 'outgoing' : im.includes('LeftBubble-icon') ? 'incoming' : 'unknown',
        text, kind, media_details: details, forwarded_from: forwarded,
        reply_to: preview ? clean(rich(preview)) : null,
      },
    };
  }
  if (operation === 'status') return {logged_in: !!$('[aria-label="dialog-tab-list"], [role="tablist"], [data-testid*="tab"], .dialog-item, [aria-label="dialog-item"]'), url: location.href};
  if (operation === 'diagnose') {
    // Return a snapshot of candidate selectors to help debug DOM changes.
    const selectors = [
      '[aria-label="dialog-item"]',
      '[aria-label="dialog-tab-list"]',
      '[data-testid*="dialog"]',
      '[data-item-index]',
      '.dialog-item',
      '.dialog-item-content',
      '[data-sentry-component*="Dialog"]',
      '[data-testid="virtuoso-scroller"]',
      '[role="tab"]',
    ];
    const counts = {};
    for (const s of selectors) {
      const all = $$(s);
      counts[s] = {total: all.length, visible: all.filter(shown).length};
    }
    // Also sample attributes of first visible listitem-like element
    const sample = $$('*').filter(e => shown(e) && (e.getAttribute('data-item-index') !== null || (e.getAttribute('aria-label') || '').includes('dialog')));
    const first = sample[0];
    const firstAttrs = first ? Array.from(first.attributes).reduce((a, x) => (a[x.name] = x.value, a), {}) : null;
    return {url: location.href, counts, first_attrs: firstAttrs, first_tag: first?.tagName};
  }
  if (operation === 'personal') {
    const tabs = $$('[aria-label="dialog-tab-list"] h3, [role="tab"], [data-testid*="tab"]');
    const target = tabs.filter(h => norm(h.textContent).includes('شخصی') || norm(h.textContent).includes('Personal'));
    if (target.length >= 1) {
      target[0].click();
      return true;
    }
    // Fallback: try clicking any element containing text "شخصی" inside dialog list header
    const header = $('[aria-label="dialog-tab-list"]') || document;
    const allH = Array.from(header.querySelectorAll('*')).filter(e => e.children.length === 0 && norm(e.textContent) === 'شخصی');
    if (allH.length > 0) {
      (allH[0].closest('button, [role="tab"], h3, li, div') || allH[0]).click();
      return true;
    }
    // If no tab needed (already on personal or single tab view), log warning and pass
    return true;
  }
  if (operation === 'list') return listState();
  if (operation === 'scroll_list') {
    const s = scroller();
    if (!s) throw Error('Conversation list is unavailable.');
    if (argument === 'top') s.scrollTo(0, 0);
    else s.scrollBy(0, Math.max(150, s.clientHeight * .8));
    return true;
  }
  if (operation === 'open') {
    const candidates = rowElements().filter(e => rowData(e).index === argument.index);
    if (!candidates.length) return {opened: false, at_bottom: listState().at_bottom};
    if (candidates.length !== 1 || rowData(candidates[0]).name !== argument.name) return {mismatch: true};
    candidates[0].click();
    return {opened: true};
  }
  if (operation === 'message') return messageState();
  if (operation === 'bottom') {
    const down = $$('[role="button"],button').filter(e => shown(e) && ($('[aria-label="ArrowDown2-icon"]', e)));
    if (down.length === 1) down[0].click();
    const last = messages().at(-1);
    const s = last?.closest('#message_list_scroller_id, [data-testid="virtuoso-scroller"]');
    if (s) s.scrollTo(0, s.scrollHeight);
    return true;
  }
  throw Error('Unsupported operation: ' + operation);
}

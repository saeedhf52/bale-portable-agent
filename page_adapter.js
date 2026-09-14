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
  const rowElements = () => $$('[aria-label="dialog-item"]').filter(shown);
  function scroller() {
    return rowElements()[0]?.closest('[data-testid="virtuoso-scroller"]') || null;
  }
  function rowData(e) {
    const content = $('.dialog-item-content', e);
    const nameEl = $('bdi', content || e);
    const preview = $('[title]', content || e);
    const im = icons(e);
    const index = Number(e.closest('[data-item-index]')?.getAttribute('data-item-index'));
    return {
      name: clean(nameEl ? rich(nameEl) : ''), index,
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
    const headings = $$('[aria-label="dialog-tab-list"] h3');
    const heading = headings.find(h => norm(h.textContent) === 'شخصی');
    // Bale orders swipe panels to match headings. aria-hidden distinguishes
    // the live tab from mounted, off-screen duplicates.
    const panel = s?.closest('[data-swipeable]');
    const panels = panel ? Array.from(panel.parentElement.children).filter(p => p.hasAttribute('data-swipeable')) : [];
    const personal = !!heading && panels.indexOf(panel) === headings.indexOf(heading);
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
  if (operation === 'status') return {logged_in: !!$('[aria-label="dialog-tab-list"]'), url: location.href};
  if (operation === 'personal') {
    const target = $$('[aria-label="dialog-tab-list"] h3').filter(h => norm(h.textContent) === 'شخصی');
    if (target.length !== 1) throw Error('Cannot uniquely locate the Personal tab.');
    target[0].click();
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

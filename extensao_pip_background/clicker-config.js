globalThis.TabTools = (() => {
  const defaults = {cps: 10, button: 'left', mode: 'element', limit: 0, delay: 0, pauseHidden: true,
    shortcut: {code: 'F8', label: 'F8', ctrl: false, alt: false, shift: false, meta: false}};
  function number(value, fallback, min, max) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? Math.max(min, Math.min(max, parsed)) : fallback;
  }
  function normalize(value = {}) {
    const shortcut = value.shortcut === null ? null : value.shortcut || defaults.shortcut;
    return {
      cps: number(value.cps, 10, 1, 50),
      button: value.button === 'right' ? 'right' : 'left',
      mode: value.mode === 'position' ? 'position' : 'element',
      limit: Math.round(number(value.limit, 0, 0, 100000)),
      delay: number(value.delay, 0, 0, 60),
      pauseHidden: value.pauseHidden !== false,
      shortcut: shortcut && typeof shortcut.code === 'string' && shortcut.code !== 'Escape' && shortcut.code.length < 40
        ? {code: shortcut.code, label: String(shortcut.label || shortcut.code).slice(0, 60),
          ctrl: !!shortcut.ctrl, alt: !!shortcut.alt, shift: !!shortcut.shift, meta: !!shortcut.meta} : null,
    };
  }
  return {defaults, normalize};
})();

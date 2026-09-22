(() => {
  if (window !== window.top || window.__controleDim) return;
  window.__controleDim = true;
  let level = 0;
  let revision = 0;
  let overlay;
  function apply(value) {
    level = Math.max(0, Math.min(95, Number(value) || 0));
    if (!document.documentElement) return;
    if (!level) { overlay?.remove(); return; }
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.setAttribute('aria-hidden', 'true');
      overlay.style.cssText = 'all:initial!important;position:fixed!important;inset:0!important;width:100%!important;height:100%!important;pointer-events:none!important;z-index:2147483647!important;background:black!important;display:block!important;';
    }
    overlay.style.setProperty('opacity', String(level / 100), 'important');
    const host = document.fullscreenElement || document.documentElement;
    if (overlay.parentNode !== host) host.appendChild(overlay);
  }
  chrome.runtime.onMessage.addListener((message, _sender, respond) => {
    if (message.type === 'dim:set') { revision++; apply(message.level); respond({level}); }
    if (message.type === 'dim:get') respond({level});
  });
  document.addEventListener('fullscreenchange', () => apply(level));
  document.addEventListener('DOMContentLoaded', () => apply(level), {once: true});
  chrome.runtime.sendMessage({type: 'dim:load'}).then(result => {
    if (!revision) apply(result?.level || 0);
  }).catch(() => {});
})();

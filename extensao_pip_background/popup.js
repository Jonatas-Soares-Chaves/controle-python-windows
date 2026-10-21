const slider = document.querySelector('#dim');
const output = document.querySelector('#value');
const reset = document.querySelector('#reset');
const status = document.querySelector('#status');
let tabId;
let writes = Promise.resolve();
let adjustmentRevision = 0;

function siteKey(url) {
  try {
    const parsed = new URL(url);
    if (parsed.protocol === 'file:') return 'dim-site:file';
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return '';
    return `dim-site:${parsed.protocol}//${parsed.hostname.toLowerCase().replace(/^www\./, '')}`;
  } catch (_error) {
    return '';
  }
}

async function applyToTab(level, revision) {
  try {
    if (revision !== adjustmentRevision) return;
    await chrome.tabs.sendMessage(tabId, {type: 'dim:set', level}, {frameId: 0});
  } catch (_error) {
    await chrome.scripting.executeScript({target: {tabId}, files: ['dim.js']});
    if (revision !== adjustmentRevision) return;
    await chrome.tabs.sendMessage(tabId, {type: 'dim:set', level}, {frameId: 0});
  }
}

async function init() {
  try {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    const key = siteKey(tab?.url);
    if (!tab?.id || !key) throw new Error('unsupported page');
    tabId = tab.id;
    const saved = await chrome.storage.local.get(key);
    const level = Math.max(0, Math.min(95, Number(saved[key]) || 0));
    slider.value = level;
    output.value = `${level}%`;
    slider.disabled = reset.disabled = false;
    applyToTab(level, adjustmentRevision).catch(() => {
      if (adjustmentRevision) return;
      slider.disabled = reset.disabled = true;
      status.textContent = 'Esta pagina nao permite o ajuste de brilho.';
    });
  } catch (error) {
    status.textContent = 'Esta pagina nao permite o ajuste de brilho.';
  }
}

function update(level) {
  adjustmentRevision++;
  output.value = `${level}%`;
  writes = writes.then(async () => {
    const response = await chrome.runtime.sendMessage({type: 'dim:save', tabId, level});
    if (!response?.ok) throw new Error('save');
    status.textContent = '';
  }).catch(() => { status.textContent = 'Nao foi possivel aplicar ou salvar o ajuste.'; });
}
slider.addEventListener('input', () => update(Number(slider.value)));
reset.addEventListener('click', () => { slider.value = 0; update(0); });
init();

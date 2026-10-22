const slider = document.querySelector('#dim');
const output = document.querySelector('#value');
const reset = document.querySelector('#reset');
const status = document.querySelector('#status');
let tabId;
let writes = Promise.resolve();
let adjustmentRevision = 0;
const field = id => document.getElementById(id);
let clickerConfig = TabTools.normalize();
let configWrites = Promise.resolve();
let capturing = false;
let pendingVolume;
let volumeBusy = false;
let lastVolume = 100;
let unmutedVolume = 100;
let polling = false;

async function request(type, data = {}) {
  const result = await chrome.runtime.sendMessage({type, tabId, ...data});
  if (!result?.ok) throw new Error('request failed');
  return result;
}

function showClicker(state) {
  field('toggle').textContent = state.running ? 'Parar' : 'Iniciar';
  field('toggle').disabled = !state.hasTarget && !state.running;
  field('click-count').value = `${state.count || 0} cliques`;
  field('clicker-status').textContent = state.running ? 'Em execucao' : state.reason || (state.hasTarget ? 'Alvo selecionado' : 'Nenhum alvo selecionado');
}

function showVolume(level) {
  field('volume').value = level;
  field('volume-value').value = `${level}%`;
  field('mute').textContent = level === 0 ? 'Ativar som' : 'Silenciar';
}

async function setVolume(level) {
  pendingVolume = level;
  showVolume(level);
  if (volumeBusy) return;
  volumeBusy = true;
  try {
    while (pendingVolume !== undefined) {
      const value = pendingVolume;
      pendingVolume = undefined;
      const result = await request('volume:set', {level: value});
      lastVolume = result.level;
      if (result.level > 0) unmutedVolume = result.level;
      field('volume-status').textContent = '';
    }
  } catch (_error) {
    pendingVolume = undefined;
    showVolume(lastVolume);
    field('volume-status').textContent = 'Nao foi possivel ajustar o audio desta guia.';
  } finally { volumeBusy = false; }
}

function renderConfig(config) {
  clickerConfig = TabTools.normalize(config);
  field('cps').value = clickerConfig.cps;
  field('click-button').value = clickerConfig.button;
  field('click-mode').value = clickerConfig.mode;
  field('limit-mode').value = clickerConfig.limit ? 'limited' : 'unlimited';
  field('limit-field').hidden = !clickerConfig.limit;
  field('click-limit').value = clickerConfig.limit || 100;
  field('click-delay').value = clickerConfig.delay;
  field('pause-hidden').checked = clickerConfig.pauseHidden;
  field('shortcut').value = clickerConfig.shortcut?.label || 'Nenhum';
}

function saveConfig() {
  clickerConfig = TabTools.normalize({...clickerConfig,
    cps: field('cps').value, button: field('click-button').value, mode: field('click-mode').value,
    limit: field('limit-mode').value === 'limited' ? Math.max(1, Number(field('click-limit').value) || 1) : 0,
    delay: field('click-delay').value, pauseHidden: field('pause-hidden').checked});
  field('limit-field').hidden = field('limit-mode').value !== 'limited';
  const config = {...clickerConfig};
  configWrites = configWrites.catch(() => {}).then(() => request('clicker:config', {config}));
  return configWrites;
}

async function refreshClicker() {
  if (!tabId || polling) return;
  polling = true;
  try {
    const result = await request('tools:state');
    showClicker(result.clicker);
  } catch (_error) { /* Keep the last displayed state while the page is navigating. */ }
  finally { polling = false; }
}

async function initTools() {
  try {
    const result = await request('tools:state');
    renderConfig(result.config);
    lastVolume = result.volume;
    if (lastVolume > 0) unmutedVolume = lastVolume;
    showVolume(lastVolume);
    for (const id of ['volume', 'mute', 'volume-reset', 'clicker-settings']) field(id).disabled = false;
    showClicker(result.clicker);
    setInterval(refreshClicker, 700);
  } catch (_error) {
    field('clicker-status').textContent = 'Esta pagina nao permite os controles.';
    field('volume-status').textContent = 'Audio indisponivel nesta pagina.';
  }
}

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
    field('tab-name').textContent = tab.title || new URL(tab.url).hostname;
    initTools();
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
    field('clicker-status').textContent = 'Esta pagina nao permite os controles.';
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
field('volume').addEventListener('input', event => setVolume(Number(event.target.value)));
field('mute').addEventListener('click', () => setVolume(Number(field('volume').value) === 0 ? unmutedVolume : 0));
field('volume-reset').addEventListener('click', () => setVolume(100));
for (const id of ['cps', 'click-button', 'click-mode', 'limit-mode', 'click-limit', 'click-delay', 'pause-hidden']) {
  field(id).addEventListener('change', () => {
    saveConfig().catch(() => { field('clicker-status').textContent = 'Nao foi possivel salvar os ajustes.'; });
  });
}
field('pick').addEventListener('click', async () => {
  try { await saveConfig(); await request('clicker:pick'); window.close(); }
  catch (_error) { field('clicker-status').textContent = 'Nao foi possivel selecionar o alvo.'; }
});
field('toggle').addEventListener('click', async () => {
  field('toggle').disabled = true;
  try { await saveConfig(); showClicker(await request('clicker:toggle')); }
  catch (_error) { field('clicker-status').textContent = 'Selecione novamente o alvo nesta pagina.'; }
  finally { refreshClicker(); }
});
field('capture').addEventListener('click', () => {
  capturing = !capturing;
  field('capture').textContent = capturing ? 'Cancelar' : 'Capturar';
  field('shortcut').value = capturing ? 'Pressione...' : clickerConfig.shortcut?.label || 'Nenhum';
  if (capturing) field('shortcut').focus();
});
field('clear-shortcut').addEventListener('click', () => {
  capturing = false;
  clickerConfig.shortcut = null;
  field('capture').textContent = 'Capturar';
  field('shortcut').value = 'Nenhum';
  saveConfig().catch(() => { field('clicker-status').textContent = 'Nao foi possivel salvar o atalho.'; });
});
document.addEventListener('keydown', event => {
  if (!capturing) {
    const key = clickerConfig.shortcut;
    if (!key || event.repeat || /^(INPUT|TEXTAREA|SELECT)$/.test(event.target?.tagName) || event.code !== key.code ||
      event.ctrlKey !== key.ctrl || event.altKey !== key.alt || event.shiftKey !== key.shift || event.metaKey !== key.meta) return;
    event.preventDefault();
    field('toggle').click();
    return;
  }
  event.preventDefault();
  event.stopImmediatePropagation();
  if (/^(Control|Alt|Shift|Meta)/.test(event.code) || event.repeat) return;
  capturing = false;
  field('capture').textContent = 'Capturar';
  if (event.code !== 'Escape') {
    const label = [event.ctrlKey && 'Ctrl', event.altKey && 'Alt', event.shiftKey && 'Shift', event.metaKey && 'Win', event.key === ' ' ? 'Espaco' : event.key.toUpperCase()].filter(Boolean).join(' + ');
    clickerConfig.shortcut = {code: event.code, label, ctrl: event.ctrlKey, alt: event.altKey, shift: event.shiftKey, meta: event.metaKey};
    saveConfig().catch(() => { field('clicker-status').textContent = 'Nao foi possivel salvar o atalho.'; });
  }
  field('shortcut').value = clickerConfig.shortcut?.label || 'Nenhum';
}, true);
init();

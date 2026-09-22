const slider = document.querySelector('#dim');
const output = document.querySelector('#value');
const reset = document.querySelector('#reset');
const status = document.querySelector('#status');
let tabId;
let writes = Promise.resolve();

async function init() {
  try {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    tabId = tab.id;
    await chrome.scripting.executeScript({target: {tabId}, files: ['dim.js']});
    const result = await chrome.tabs.sendMessage(tabId, {type: 'dim:get'}, {frameId: 0});
    slider.value = result.level;
    output.value = `${result.level}%`;
    slider.disabled = reset.disabled = false;
  } catch (error) {
    status.textContent = 'Esta pagina nao permite o ajuste de brilho.';
  }
}

function update(level) {
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

const tabToolQueues = new Map();
let audioDocumentCreation;
const tabToolKey = tabId => `tools-tab:${tabId}`;

function runTabTool(tabId, operation) {
  const previous = tabToolQueues.get(tabId) || Promise.resolve();
  const next = previous.catch(() => {}).then(operation);
  tabToolQueues.set(tabId, next);
  next.finally(() => {
    if (tabToolQueues.get(tabId) === next) tabToolQueues.delete(tabId);
  }).catch(() => {});
  return next;
}

async function loadTabTools(tabId) {
  const key = tabToolKey(tabId);
  const saved = (await chrome.storage.session.get(key))[key];
  if (saved) return {...saved, config: TabTools.normalize(saved.config)};
  const defaults = await chrome.storage.local.get('clicker-defaults');
  return {config: TabTools.normalize(defaults['clicker-defaults']), volume: 100, targetFrameId: 0};
}

async function saveTabTools(tabId, state) {
  await chrome.storage.session.set({[tabToolKey(tabId)]: state});
}

async function ensureAudioDocument() {
  if (audioDocumentCreation) return audioDocumentCreation;
  audioDocumentCreation = (async () => {
    if (!await chrome.offscreen.hasDocument()) {
      await chrome.offscreen.createDocument({url: 'offscreen.html', reasons: ['USER_MEDIA'],
        justification: 'Ajustar o volume de cada guia e reproduzir o audio localmente.'});
    }
  })();
  try { await audioDocumentCreation; } finally { audioDocumentCreation = null; }
}

async function setTabVolume(tabId, level, state) {
  if (level === 100) {
    if (await chrome.offscreen.hasDocument()) {
      const result = await chrome.runtime.sendMessage({target: 'audio', type: 'audio:stop', tabId});
      if (!result?.ok) throw new Error('volume');
    }
  } else {
    await ensureAudioDocument();
    const status = await chrome.runtime.sendMessage({target: 'audio', type: 'audio:status', tabId});
    const streamId = status?.active ? undefined : await chrome.tabCapture.getMediaStreamId({targetTabId: tabId});
    const result = await chrome.runtime.sendMessage({target: 'audio', type: 'audio:set', tabId, streamId, level});
    if (!result?.ok) throw new Error('volume');
  }
  state.volume = level;
  await saveTabTools(tabId, state);
  return {ok: true, level};
}

async function sendClicker(tabId, type, config, frameId) {
  const options = Number.isInteger(frameId) ? {frameId} : undefined;
  return chrome.tabs.sendMessage(tabId, {type: `clicker:frame:${type}`, config}, options);
}

async function ensureClicker(tabId) {
  try { await sendClicker(tabId, 'get'); }
  catch (_error) {
    await chrome.scripting.executeScript({target: {tabId, allFrames: true}, files: ['clicker-config.js', 'clicker.js']});
  }
}

async function clickerState(tabId, state) {
  try {
    return await sendClicker(tabId, 'get', undefined, state.targetFrameId);
  } catch (_error) {
    return {ok: true, running: false, hasTarget: false, count: 0, picking: false, reason: ''};
  }
}

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (message.target === 'audio') return;
  const supported = ['tools:state', 'volume:set', 'volume:ended', 'clicker:load', 'clicker:config',
    'clicker:pick', 'clicker:picked', 'clicker:toggle', 'clicker:stop', 'clicker:cancel'];
  if (!supported.includes(message.type)) return;
  const tabId = sender.tab?.id ?? message.tabId;
  if (!Number.isInteger(tabId)) { respond({ok: false}); return; }
  const operation = runTabTool(tabId, async () => {
    const state = await loadTabTools(tabId);
    switch (message.type) {
      case 'volume:ended':
        if (sender.url !== chrome.runtime.getURL('offscreen.html')) return {ok: false};
        state.volume = 100;
        await saveTabTools(tabId, state);
        return {ok: true};
      case 'volume:set':
        if (sender.tab) return {ok: false};
        return setTabVolume(tabId, Math.max(0, Math.min(100, Number(message.level) || 0)), state);
      case 'clicker:load': return {ok: true, config: state.config};
      case 'tools:state':
        await ensureClicker(tabId);
        return {ok: true, volume: state.volume, config: state.config, clicker: await clickerState(tabId, state)};
      case 'clicker:config':
        state.config = TabTools.normalize(message.config);
        await saveTabTools(tabId, state);
        await chrome.storage.local.set({'clicker-defaults': state.config});
        await ensureClicker(tabId);
        await sendClicker(tabId, 'config', state.config);
        return {ok: true, config: state.config};
      case 'clicker:picked':
        if (!sender.tab || !Number.isInteger(sender.frameId)) return {ok: false};
        state.targetFrameId = sender.frameId;
        await saveTabTools(tabId, state);
        await sendClicker(tabId, 'cancel');
        await sendClicker(tabId, 'config', state.config, state.targetFrameId);
        return {ok: true};
      case 'clicker:pick':
        await ensureClicker(tabId);
        await sendClicker(tabId, 'stop');
        await sendClicker(tabId, 'pick');
        return {ok: true};
      case 'clicker:stop':
      case 'clicker:cancel':
        await sendClicker(tabId, 'stop');
        return {ok: true};
      case 'clicker:toggle': {
        await ensureClicker(tabId);
        const current = await clickerState(tabId, state);
        await sendClicker(tabId, 'config', state.config, state.targetFrameId);
        return sendClicker(tabId, current.running ? 'stop' : 'start', undefined, state.targetFrameId);
      }
    }
  });
  operation.then(respond).catch(() => respond({ok: false}));
  return true;
});

chrome.tabs.onRemoved.addListener(tabId => {
  runTabTool(tabId, async () => {
    if (await chrome.offscreen.hasDocument()) {
      await chrome.runtime.sendMessage({target: 'audio', type: 'audio:stop', tabId}).catch(() => {});
    }
    await chrome.storage.session.remove(tabToolKey(tabId));
  }).catch(() => {});
});

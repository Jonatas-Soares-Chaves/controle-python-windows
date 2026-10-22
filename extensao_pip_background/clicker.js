(() => {
  if (window.__controleClicker) return;
  window.__controleClicker = true;
  let config = TabTools.normalize();
  let target = null;
  let point = null;
  let timer = null;
  let running = false;
  let picking = false;
  let count = 0;
  let reason = '';
  let oldCursor = '';
  let cursorPriority = '';
  let revision = 0;
  let toast;
  const state = () => ({ok: true, running, picking, count, reason, hasTarget: !!target?.isConnected, config});
  function stop(message = '') {
    clearTimeout(timer);
    timer = null;
    running = false;
    reason = message;
  }
  function cancelPick() {
    if (!picking) return;
    picking = false;
    document.documentElement.style.setProperty('cursor', oldCursor, cursorPriority);
    toast?.remove();
  }
  function clickOnce() {
    if (!running) return;
    if (config.pauseHidden && document.hidden) return stop('Guia em segundo plano');
    let element = target;
    let x = point?.x || 0;
    let y = point?.y || 0;
    if (config.mode === 'position') element = document.elementFromPoint(x, y);
    else if (element?.isConnected) {
      const rect = element.getBoundingClientRect();
      x = rect.left + rect.width / 2;
      y = rect.top + rect.height / 2;
    }
    if (!element?.isConnected) return stop('Alvo indisponivel');
    const button = config.button === 'right' ? 2 : 0;
    const options = {bubbles: true, cancelable: true, composed: true, view: window,
      clientX: x, clientY: y, button, buttons: button === 2 ? 2 : 1, detail: 1};
    for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', button === 2 ? 'contextmenu' : 'click']) {
      const released = ['pointerup', 'mouseup', 'click', 'contextmenu'].includes(type);
      const props = {...options, buttons: released ? 0 : options.buttons};
      element.dispatchEvent(type.startsWith('pointer')
        ? new PointerEvent(type, {...props, pointerId: 1, pointerType: 'mouse', isPrimary: true})
        : new MouseEvent(type, props));
    }
    count++;
    if (config.limit && count >= config.limit) return stop('Limite atingido');
    timer = setTimeout(clickOnce, 1000 / config.cps);
  }
  function start() {
    if (!target?.isConnected) return {...state(), ok: false, reason: 'Selecione um alvo'};
    if (config.pauseHidden && document.hidden) return {...state(), ok: false, reason: 'Abra a guia para iniciar'};
    cancelPick();
    stop();
    count = 0;
    running = true;
    timer = setTimeout(clickOnce, config.delay * 1000);
    return state();
  }
  document.addEventListener('click', event => {
    if (!picking || !event.isTrusted) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    target = event.composedPath().find(node => node instanceof Element) || event.target;
    point = {x: event.clientX, y: event.clientY};
    cancelPick();
    reason = 'Alvo selecionado';
    chrome.runtime.sendMessage({type: 'clicker:picked'}).catch(() => {});
  }, true);
  document.addEventListener('keydown', event => {
    if (event.code === 'Escape') {
      if (running || picking) chrome.runtime.sendMessage({type: 'clicker:cancel'}).catch(() => {});
      stop('Parado'); cancelPick(); return;
    }
    const editing = event.composedPath().some(node => node?.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(node?.tagName));
    const key = config.shortcut;
    if (!key || editing || event.repeat || event.code !== key.code || event.ctrlKey !== key.ctrl ||
      event.altKey !== key.alt || event.shiftKey !== key.shift || event.metaKey !== key.meta) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    chrome.runtime.sendMessage({type: 'clicker:toggle'}).catch(() => {});
  }, true);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && config.pauseHidden) stop('Guia em segundo plano');
  });
  window.addEventListener('pagehide', () => { stop(); cancelPick(); });
  chrome.runtime.onMessage.addListener((message, _sender, respond) => {
    if (!message.type?.startsWith('clicker:frame:')) return;
    switch (message.type) {
      case 'clicker:frame:config': revision++; config = TabTools.normalize(message.config); break;
      case 'clicker:frame:pick':
        stop(); cancelPick(); picking = true;
        oldCursor = document.documentElement.style.getPropertyValue('cursor');
        cursorPriority = document.documentElement.style.getPropertyPriority('cursor');
        document.documentElement.style.setProperty('cursor', 'crosshair', 'important');
        if (window === window.top) {
          toast = document.createElement('div');
          toast.textContent = 'Selecionar alvo';
          toast.style.cssText = 'position:fixed;top:12px;left:12px;padding:10px 14px;background:#202124;color:white;font:14px system-ui;z-index:2147483647;pointer-events:none;border-radius:4px';
          document.documentElement.appendChild(toast);
        }
        break;
      case 'clicker:frame:cancel': cancelPick(); break;
      case 'clicker:frame:start': respond(start()); return;
      case 'clicker:frame:stop': stop('Parado'); cancelPick(); break;
    }
    respond(state());
  });
  chrome.runtime.sendMessage({type: 'clicker:load'}).then(result => {
    if (!revision && result?.ok) config = TabTools.normalize(result.config);
  }).catch(() => {});
})();

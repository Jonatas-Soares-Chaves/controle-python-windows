(async () => {
  const base = '../extensao_pip_background/';
  const parsed = new DOMParser().parseFromString(await (await fetch(`${base}popup.html`)).text(), 'text/html');
  parsed.querySelectorAll('script').forEach(script => script.remove());
  document.body.innerHTML = parsed.body.innerHTML;
  const style = document.createElement('link');
  style.rel = 'stylesheet'; style.href = `${base}popup.css`; document.head.appendChild(style);
  let config;
  let volume = 75;
  let running = false;
  globalThis.chrome = {
    tabs: {query: async () => [{id: 10, title: 'Guia de teste', url: 'https://example.com'}], sendMessage: async () => ({level: 40})},
    storage: {local: {get: async key => ({[key]: 40})}},
    scripting: {executeScript: async () => {}},
    runtime: {sendMessage: async message => {
      if (message.type === 'tools:state') return {ok: true, volume, config, clicker: {running, hasTarget: true, count: 0}};
      if (message.type === 'volume:set') { volume = message.level; return {ok: true, level: volume}; }
      if (message.type === 'clicker:config') { config = message.config; return {ok: true, config}; }
      if (message.type === 'clicker:toggle') { running = !running; return {ok: true, running, hasTarget: true, count: 0}; }
      return {ok: true};
    }},
  };
  for (const file of ['clicker-config.js', 'popup.js']) {
    await new Promise((resolve, reject) => {
      const script = document.createElement('script'); script.src = base + file;
      script.onload = resolve; script.onerror = reject; document.body.appendChild(script);
    });
  }
})();

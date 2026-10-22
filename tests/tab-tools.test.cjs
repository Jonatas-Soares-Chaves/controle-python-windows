const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const folder = path.join(__dirname, '../extensao_pip_background');
const run = (context, file) => vm.runInContext(fs.readFileSync(path.join(folder, file), 'utf8'), context);

test('audio uses independent gains and releases only the selected tab', async () => {
  let listener;
  const contexts = [];
  const streams = [];
  class AudioContext {
    constructor() { this.currentTime = 0; this.destination = {}; contexts.push(this); }
    createMediaStreamSource() { return {connect: gain => gain, disconnect() {}}; }
    createGain() {
      this.gain = {gain: {value: 1, setTargetAtTime(value) { this.value = value; }}, connect() {}, disconnect() {}};
      return this.gain;
    }
    async resume() {}
    async close() { this.closed = true; }
  }
  const context = vm.createContext({AudioContext, navigator: {mediaDevices: {getUserMedia: async () => {
    const track = {stopped: false, stop() { this.stopped = true; }, addEventListener() {}};
    const stream = {getTracks: () => [track], getAudioTracks: () => [track]};
    streams.push(track); return stream;
  }}}, chrome: {runtime: {onMessage: {addListener(fn) { listener = fn; }}}}});
  run(context, 'offscreen.js');
  const send = message => new Promise(resolve => listener({target: 'audio', ...message}, {}, resolve));
  assert.equal((await send({type: 'audio:set', tabId: 1, streamId: 'one', level: 25})).ok, true);
  await send({type: 'audio:set', tabId: 2, streamId: 'two', level: 70});
  assert.equal(contexts[0].gain.gain.value, .25);
  assert.equal(contexts[1].gain.gain.value, .7);
  await send({type: 'audio:set', tabId: 1, level: 0});
  assert.equal(contexts.length, 2);
  assert.equal(contexts[0].gain.gain.value, 0);
  assert.equal(contexts[1].gain.gain.value, .7);
  await send({type: 'audio:stop', tabId: 1});
  assert.equal(streams[0].stopped, true);
  assert.equal(streams[1].stopped, false);
  assert.equal((await send({type: 'audio:status', tabId: 2})).active, true);
});

function clickerHarness() {
  let listener;
  const handlers = {};
  const timers = new Map();
  const events = [];
  let timerId = 0;
  class Element {
    constructor() { this.isConnected = true; this.style = {getPropertyValue: () => '', getPropertyPriority: () => '', setProperty() {}}; }
    remove() { this.isConnected = false; }
    appendChild() {}
    getBoundingClientRect() { return {left: 10, top: 10, width: 40, height: 30}; }
    dispatchEvent(event) { events.push(event); }
  }
  class Event { constructor(type, props) { this.type = type; Object.assign(this, props); } }
  const target = new Element();
  const document = {hidden: false, documentElement: new Element(),
    elementFromPoint: () => target, createElement: () => new Element(),
    addEventListener(type, handler) { handlers[type] = handler; }};
  const window = {addEventListener() {}};
  window.top = window;
  const context = vm.createContext({window, document, Element, PointerEvent: Event, MouseEvent: Event,
    setTimeout(fn, delay) { const id = ++timerId; timers.set(id, {fn, delay}); return id; },
    clearTimeout: id => timers.delete(id), chrome: {runtime: {
      onMessage: {addListener(fn) { listener = fn; }}, sendMessage: async () => ({ok: true}),
    }}});
  run(context, 'clicker-config.js'); run(context, 'clicker.js');
  const send = (type, config) => { let result; listener({type: `clicker:frame:${type}`, config}, {}, value => { result = value; }); return result; };
  const pick = () => {
    send('pick');
    handlers.click({isTrusted: true, composedPath: () => [target], target, clientX: 30, clientY: 25, preventDefault() {}, stopImmediatePropagation() {}});
  };
  const tick = () => { const [id, timer] = timers.entries().next().value; timers.delete(id); timer.fn(); return timer.delay; };
  return {send, pick, tick, timers, target, events, handlers, document};
}

test('autoclicker enforces rate, initial delay and click limit', () => {
  const h = clickerHarness();
  h.pick();
  h.send('config', {cps: 5, limit: 3, delay: 2});
  assert.equal(h.send('start').running, true);
  assert.equal(h.tick(), 2000);
  assert.equal(h.tick(), 200);
  assert.equal(h.tick(), 200);
  assert.equal(h.send('get').running, false);
  assert.equal(h.send('get').count, 3);
  assert.equal(h.events.filter(event => event.type === 'click').length, 3);
  assert.equal(h.timers.size, 0);
});

test('right clicks, Escape, hidden tabs and removed targets stop correctly', () => {
  const h = clickerHarness(); h.pick(); h.send('config', {button: 'right'}); h.send('start'); h.tick();
  assert.equal(h.events.filter(event => event.type === 'contextmenu').length, 1);
  h.handlers.keydown({code: 'Escape'});
  assert.equal(h.send('get').running, false);
  assert.equal(h.timers.size, 0);
  h.send('start'); h.document.hidden = true; h.handlers.visibilitychange();
  assert.equal(h.send('get').running, false);
  h.document.hidden = false; h.send('start'); h.target.isConnected = false; h.tick();
  assert.equal(h.send('get').running, false);
});

test('worker keeps settings separate for tabs on the same site', async () => {
  let listener;
  const session = {};
  const local = {};
  const store = data => ({get: async key => ({[key]: data[key]}), set: async values => Object.assign(data, values), remove: async key => { delete data[key]; }});
  const context = vm.createContext({chrome: {
    storage: {session: store(session), local: store(local)},
    runtime: {onMessage: {addListener(fn) { listener = fn; }}, getURL: file => `chrome-extension://test/${file}`},
    tabs: {sendMessage: async () => ({ok: true, running: false}), onRemoved: {addListener() {}}},
    offscreen: {hasDocument: async () => false},
  }});
  run(context, 'clicker-config.js'); run(context, 'tab-tools-worker.js');
  const send = message => new Promise(resolve => listener(message, {}, resolve));
  await send({type: 'clicker:config', tabId: 1, config: {cps: 3, shortcut: null}});
  await send({type: 'clicker:config', tabId: 2, config: {cps: 12}});
  assert.equal((await send({type: 'tools:state', tabId: 1})).config.cps, 3);
  assert.equal((await send({type: 'tools:state', tabId: 2})).config.cps, 12);
  assert.equal((await send({type: 'tools:state', tabId: 1})).config.shortcut, null);
});

test('shortcut honors modifiers, ignores repeat and editable fields', async () => {
  let messages = [];
  let listener;
  const handlers = {};
  const context = vm.createContext({window: {addEventListener() {}}, document: {addEventListener(type, handler) { handlers[type] = handler; }},
    chrome: {runtime: {sendMessage: async message => { messages.push(message); return {ok: true}; }, onMessage: {addListener(fn) { listener = fn; }}}},
    clearTimeout() {}, setTimeout() {}});
  run(context, 'clicker-config.js'); run(context, 'clicker.js');
  listener({type: 'clicker:frame:config', config: {shortcut: {code: 'KeyJ', ctrl: true}}}, {}, () => {});
  messages = [];
  const event = {code: 'KeyJ', ctrlKey: true, altKey: false, shiftKey: false, metaKey: false, repeat: false,
    composedPath: () => [], preventDefault() {}, stopImmediatePropagation() {}};
  handlers.keydown({...event, ctrlKey: false});
  handlers.keydown({...event, repeat: true});
  handlers.keydown({...event, composedPath: () => [{tagName: 'INPUT'}]});
  assert.equal(messages.length, 0);
  handlers.keydown(event);
  assert.equal(messages.length, 1);
  assert.equal(messages[0].type, 'clicker:toggle');
});

test('brightness popup stays responsive while new controls are loading', async () => {
  const html = fs.readFileSync(path.join(folder, 'popup.html'), 'utf8');
  const elements = Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(match => [match[1], {
    disabled: true, value: '', textContent: '', addEventListener() {}, focus() {},
  }]));
  const context = vm.createContext({URL, setInterval() {}, clearTimeout() {}, window: {},
    document: {querySelector: selector => elements[selector.slice(1)], getElementById: id => elements[id], addEventListener() {}},
    chrome: {tabs: {query: async () => [{id: 10, title: 'Test', url: 'https://www.example.com'}], sendMessage: () => new Promise(() => {})},
      storage: {local: {get: async key => ({[key]: 52})}}, runtime: {sendMessage: () => new Promise(() => {})}, scripting: {executeScript: async () => { throw Error('unexpected injection'); }}}});
  run(context, 'clicker-config.js'); run(context, 'popup.js');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(elements.dim.disabled, false);
  assert.equal(elements.dim.value, 52);
  assert.equal(elements.value.value, '52%');
});

const ENDPOINT = "http://127.0.0.1:17963/pip-command";
const RESULT_ENDPOINT = "http://127.0.0.1:17963/pip-result";

let lastSeq = 0;
let polling = false;
let retryDelay = 40;
let lastPausedTarget = null;

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function injectedMediaAction(action) {
  const pausedKey = "__controleBrilhoPausedByApp";

  function collectVideos(root, output, seenRoots) {
    if (!root || seenRoots.has(root)) {
      return;
    }
    seenRoots.add(root);

    if (root.nodeType === Node.ELEMENT_NODE && root.tagName && root.tagName.toLowerCase() === "video") {
      output.push(root);
    }

    if (root.querySelectorAll) {
      for (const video of root.querySelectorAll("video")) {
        output.push(video);
      }
      for (const element of root.querySelectorAll("*")) {
        if (element.shadowRoot) {
          collectVideos(element.shadowRoot, output, seenRoots);
        }
      }
    }
  }

  function videosForAction() {
    const pipVideo = document.pictureInPictureElement;
    if (pipVideo && pipVideo.tagName && pipVideo.tagName.toLowerCase() === "video") {
      return [pipVideo];
    }

    const videos = [];
    collectVideos(document, videos, new WeakSet());
    return Array.from(new Set(videos)).filter((video) => video && !video.ended);
  }

  window[pausedKey] = window[pausedKey] || [];

  if (action === "pause") {
    const result = { seen: 0, changed: 0 };
    for (const video of videosForAction()) {
      result.seen += 1;
      if (!video.paused && !video.ended) {
        if (!window[pausedKey].includes(video)) {
          window[pausedKey].push(video);
        }
        video.pause();
        result.changed += 1;
      }
    }
    return result;
  }

  if (action === "play") {
    const fallbackTargets = videosForAction().filter((video) => video.paused && !video.ended);
    const targets = Array.from(new Set([...window[pausedKey].splice(0), ...fallbackTargets]));
    const result = { seen: 0, changed: 0 };
    for (const video of targets) {
      result.seen += 1;
      if (video && video.paused && !video.ended) {
        video.play().catch(() => {});
        result.changed += 1;
      }
    }
    return result;
  }

  return { seen: 0, changed: 0 };
}

function injectedMediaProbe() {
  const pausedKey = "__controleBrilhoPausedByApp";

  function collectVideos(root, output, seenRoots) {
    if (!root || seenRoots.has(root)) {
      return;
    }
    seenRoots.add(root);

    if (root.nodeType === Node.ELEMENT_NODE && root.tagName && root.tagName.toLowerCase() === "video") {
      output.push(root);
    }

    if (root.querySelectorAll) {
      for (const video of root.querySelectorAll("video")) {
        output.push(video);
      }
      for (const element of root.querySelectorAll("*")) {
        if (element.shadowRoot) {
          collectVideos(element.shadowRoot, output, seenRoots);
        }
      }
    }
  }

  const videos = [];
  collectVideos(document, videos, new WeakSet());
  const uniqueVideos = Array.from(new Set(videos)).filter((video) => video && !video.ended);
  const pipVideo = document.pictureInPictureElement;
  const pausedByApp = Array.isArray(window[pausedKey])
    ? window[pausedKey].filter((video) => video && !video.ended)
    : [];

  let playing = 0;
  let paused = 0;
  let visiblePlaying = 0;
  let largestArea = 0;

  for (const video of uniqueVideos) {
    const rect = video.getBoundingClientRect ? video.getBoundingClientRect() : { width: 0, height: 0 };
    const area = Math.max(0, rect.width || 0) * Math.max(0, rect.height || 0);
    largestArea = Math.max(largestArea, area);
    if (video.paused) {
      paused += 1;
    } else {
      playing += 1;
      if (area >= 1200) {
        visiblePlaying += 1;
      }
    }
  }

  return {
    seen: uniqueVideos.length,
    playing,
    paused,
    visiblePlaying,
    largestArea,
    hasPip: Boolean(pipVideo && pipVideo.tagName && pipVideo.tagName.toLowerCase() === "video" && !pipVideo.ended),
    pipPlaying: Boolean(pipVideo && !pipVideo.paused && !pipVideo.ended),
    pipPaused: Boolean(pipVideo && pipVideo.paused && !pipVideo.ended),
    pausedByApp: pausedByApp.length,
    url: location.href,
    title: document.title || "",
  };
}

async function probeOpenTabs() {
  const tabs = await chrome.tabs.query({});
  const probes = [];

  await Promise.allSettled(
    tabs.map(async (tab) => {
      if (!tab.id || !tab.url || !/^https?:|^file:/.test(tab.url)) {
        return;
      }

      try {
        const injectedResults = await chrome.scripting.executeScript({
          target: { tabId: tab.id, allFrames: true },
          func: injectedMediaProbe,
        });

        for (const item of injectedResults || []) {
          const result = item && item.result ? item.result : {};
          if (Number(result.seen || 0) > 0 || result.hasPip || result.pausedByApp) {
            probes.push({
              tabId: tab.id,
              frameId: item.frameId || 0,
              active: Boolean(tab.active),
              audible: Boolean(tab.audible),
              windowId: tab.windowId,
              tabUrl: tab.url || "",
              ...result,
            });
          }
        }
      } catch (_error) {
      }
    })
  );

  return probes;
}

function targetMatches(target, probe) {
  return target && probe && target.tabId === probe.tabId && target.frameId === probe.frameId;
}

function scoreProbeForAction(probe, action) {
  let score = 0;

  if (action === "pause") {
    if (probe.pipPlaying) score += 10000;
    if (probe.hasPip) score += 5000;
    if (probe.playing > 0) score += 1000;
    if (probe.visiblePlaying > 0) score += 600;
  } else {
    if (targetMatches(lastPausedTarget, probe)) score += 10000;
    if (probe.pausedByApp > 0) score += 8000;
    if (probe.pipPaused) score += 4000;
    if (probe.hasPip) score += 2500;
    if (probe.paused > 0) score += 500;
  }

  if (probe.audible) score += 350;
  if (probe.active) score += 120;
  score += Math.min(100, Math.round(Number(probe.largestArea || 0) / 10000));
  return score;
}

async function runActionInTarget(target, action) {
  if (!target || !target.tabId) {
    return { seen: 0, changed: 0 };
  }

  try {
    const injectedResults = await chrome.scripting.executeScript({
      target: { tabId: target.tabId, frameIds: [target.frameId || 0] },
      func: injectedMediaAction,
      args: [action],
    });
    const result = injectedResults && injectedResults[0] && injectedResults[0].result ? injectedResults[0].result : {};
    return {
      seen: Number(result.seen || 0),
      changed: Number(result.changed || 0),
    };
  } catch (_error) {
    try {
      const response = await chrome.tabs.sendMessage(target.tabId, {
        type: "controle-brilho-pip-command",
        action,
      }, { frameId: target.frameId || 0 });
      return {
        seen: Number(response && response.seen || 0),
        changed: Number(response && response.changed || 0),
      };
    } catch (_ignored) {
      return { seen: 0, changed: 0 };
    }
  }
}

async function runTargetedAction(action) {
  const probes = await probeOpenTabs();
  if (!probes.length) {
    return { seen: 0, changed: 0 };
  }

  probes.sort((a, b) => scoreProbeForAction(b, action) - scoreProbeForAction(a, action));

  let totals = { seen: 0, changed: 0 };
  const targets = [];
  if (action === "play" && lastPausedTarget) {
    const stillKnown = probes.find((probe) => targetMatches(lastPausedTarget, probe));
    if (stillKnown) {
      targets.push(stillKnown);
    }
  }
  for (const probe of probes) {
    if (!targets.some((target) => targetMatches(target, probe))) {
      targets.push(probe);
    }
  }

  for (const target of targets.slice(0, 4)) {
    const score = scoreProbeForAction(target, action);
    if (score <= 0) {
      continue;
    }
    const result = await runActionInTarget(target, action);
    totals.seen = Math.max(totals.seen, result.seen);
    totals.changed += result.changed;
    if (result.changed > 0) {
      if (action === "pause") {
        lastPausedTarget = {
          tabId: target.tabId,
          frameId: target.frameId || 0,
          url: target.url || target.tabUrl || "",
          title: target.title || "",
        };
      } else {
        lastPausedTarget = null;
      }
      break;
    }
  }

  return totals;
}

async function sendResult(command, result) {
  await fetch(RESULT_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      seq: command.seq,
      action: command.action,
      ok: true,
      seen: result.seen,
      changed: result.changed,
    }),
  });
}

async function handleCommand(command) {
  if (!command || command.seq === lastSeq) {
    return;
  }

  lastSeq = command.seq;
  if (command.action !== "pause" && command.action !== "play") {
    return;
  }

  const deadline = Date.now() + 700;
  let best = { seen: 0, changed: 0 };
  do {
    const result = await runTargetedAction(command.action);
    best.seen = Math.max(best.seen, result.seen);
    best.changed += result.changed;
    if (best.changed > 0 || (command.action === "pause" && best.seen > 0)) {
      break;
    }
    await delay(60);
  } while (Date.now() < deadline);

  await sendResult(command, best);
}

async function pollOnce() {
  const response = await fetch(`${ENDPOINT}?last=${lastSeq}&t=${Date.now()}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    retryDelay = 150;
    return;
  }

  retryDelay = 40;
  await handleCommand(await response.json());
}

async function pollLoop() {
  if (polling) {
    return;
  }

  polling = true;
  while (true) {
    try {
      await pollOnce();
    } catch (_error) {
      retryDelay = 150;
    }
    await delay(retryDelay);
  }
}

chrome.runtime.onInstalled.addListener(pollLoop);
chrome.runtime.onStartup.addListener(pollLoop);
chrome.tabs.onUpdated.addListener(pollLoop);
chrome.tabs.onActivated.addListener(pollLoop);
pollLoop();

function dimSiteKeyFromUrl(url) {
  try {
    const parsed = new URL(url || "");
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:" && parsed.protocol !== "file:") {
      return "";
    }
    if (parsed.protocol === "file:") {
      return "dim-site:file";
    }
    const host = parsed.hostname.replace(/^www\./i, "").toLowerCase();
    return `dim-site:${parsed.protocol}//${host}`;
  } catch (_error) {
    return "";
  }
}

async function dimSiteKeyForTab(tabId, fallbackUrl) {
  const fallbackKey = dimSiteKeyFromUrl(fallbackUrl);
  if (fallbackKey) {
    return fallbackKey;
  }

  if (!Number.isInteger(tabId)) {
    return "";
  }

  try {
    const tab = await chrome.tabs.get(tabId);
    return dimSiteKeyFromUrl(tab && tab.url);
  } catch (_error) {
    return "";
  }
}

async function applyDimToMatchingTabs(siteKey, level) {
  if (!siteKey) {
    return;
  }

  const tabs = await chrome.tabs.query({});
  await Promise.allSettled(
    tabs.map(async (tab) => {
      if (!tab.id || dimSiteKeyFromUrl(tab.url) !== siteKey) {
        return;
      }
      try {
        await chrome.tabs.sendMessage(tab.id, {type: "dim:set", level}, {frameId: 0});
      } catch (_error) {
      }
    })
  );
}

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (message.type !== 'dim:load' && message.type !== 'dim:save') return;
  const tabId = message.type === 'dim:load' ? sender.tab?.id ?? message.tabId : message.tabId;
  const url = message.url || sender.url || sender.tab?.url || "";
  if (!Number.isInteger(tabId) && !url) { respond({ok: false}); return; }
  const operation = (async () => {
    const key = await dimSiteKeyForTab(tabId, url);
    if (!key) {
      return message.type === 'dim:load' ? {level: 0} : {ok: false};
    }
    if (message.type === 'dim:load') {
      const data = await chrome.storage.local.get(key);
      return {level: data[key] || 0};
    }

    const level = Math.max(0, Math.min(95, Number(message.level) || 0));
    if (level) {
      await chrome.storage.local.set({[key]: level});
    } else {
      await chrome.storage.local.remove(key);
    }
    await applyDimToMatchingTabs(key, level);
    return {ok: true};
  })();
  operation.then(respond).catch(() => respond({ok: false}));
  return true;
});

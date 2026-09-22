(function () {
  if (window.__controleBrilhoPipBackground) {
    return;
  }
  window.__controleBrilhoPipBackground = true;

  const pausedByApp = new Set();

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
    return Array.from(new Set(videos)).filter((video) => {
      return video && video.readyState >= 0 && !video.ended;
    });
  }

  function delay(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function pauseVideos() {
    const result = { seen: 0, changed: 0 };
    for (const video of videosForAction()) {
      result.seen += 1;
      if (!video.paused && !video.ended) {
        pausedByApp.add(video);
        video.pause();
        result.changed += 1;
      }
    }
    return result;
  }

  async function runAction(action) {
    const deadline = performance.now() + 450;
    let best = { seen: 0, changed: 0 };

    do {
      const result = bestLocalResult(action);
      best = {
        seen: Math.max(best.seen, result.seen),
        changed: best.changed + result.changed,
      };

      if (best.changed > 0 || (action === "pause" && best.seen > 0)) {
        return best;
      }

      await delay(45);
    } while (performance.now() < deadline);

    return best;
  }

  function playVideos() {
    const fallbackTargets = videosForAction().filter((video) => video.paused && !video.ended);
    const targets = Array.from(new Set([...pausedByApp, ...fallbackTargets]));
    const result = { seen: 0, changed: 0 };

    pausedByApp.clear();
    for (const video of targets) {
      result.seen += 1;
      if (video && video.paused && !video.ended) {
        video.play().catch(() => {});
        result.changed += 1;
      }
    }
    return result;
  }

  function bestLocalResult(action) {
    if (action === "pause") {
      return pauseVideos();
    }
    if (action === "play") {
      return playVideos();
    }
    return { seen: 0, changed: 0 };
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (!message || message.type !== "controle-brilho-pip-command") {
      return false;
    }

    runAction(message.action)
      .then((result) => sendResponse({ ok: true, ...result }))
      .catch(() => sendResponse({ ok: false, seen: 0, changed: 0 }));
    return true;
  });
})();

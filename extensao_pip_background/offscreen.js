const audioTabs = new Map();

async function stopAudio(tabId) {
  const entry = audioTabs.get(tabId);
  if (!entry) return;
  audioTabs.delete(tabId);
  entry.stream.getTracks().forEach(track => track.stop());
  entry.source.disconnect();
  entry.gain.disconnect();
  await entry.context.close();
}

chrome.runtime.onMessage.addListener((message, _sender, respond) => {
  if (message.target !== 'audio') return;
  const operation = (async () => {
    const tabId = message.tabId;
    if (message.type === 'audio:status') return {ok: true, active: audioTabs.has(tabId)};
    if (message.type === 'audio:stop') {
      await stopAudio(tabId);
      return {ok: true};
    }
    if (message.type !== 'audio:set') return {ok: false};
    let entry = audioTabs.get(tabId);
    if (!entry) {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {mandatory: {chromeMediaSource: 'tab', chromeMediaSourceId: message.streamId}},
        video: false,
      });
      const context = new AudioContext();
      try {
        const source = context.createMediaStreamSource(stream);
        const gain = context.createGain();
        gain.gain.value = message.level / 100;
        source.connect(gain).connect(context.destination);
        await context.resume();
        entry = {stream, context, source, gain};
        audioTabs.set(tabId, entry);
        stream.getAudioTracks().forEach(track => track.addEventListener('ended', () => {
          if (audioTabs.get(tabId) !== entry) return;
          stopAudio(tabId).catch(() => {});
          chrome.runtime.sendMessage({type: 'volume:ended', tabId}).catch(() => {});
        }));
      } catch (error) {
        stream.getTracks().forEach(track => track.stop());
        await context.close();
        throw error;
      }
    }
    entry.gain.gain.setTargetAtTime(message.level / 100, entry.context.currentTime, 0.015);
    return {ok: true};
  })();
  operation.then(respond).catch(() => respond({ok: false}));
  return true;
});

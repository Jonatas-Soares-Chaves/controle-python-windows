let left = 0;
let right = 0;
const render = () => { document.getElementById('count').value = `Esquerdo: ${left} / Direito: ${right}`; };
document.getElementById('target').addEventListener('click', () => { left++; render(); });
document.getElementById('target').addEventListener('contextmenu', event => { event.preventDefault(); right++; render(); });
let audio;
document.getElementById('sound').addEventListener('click', async () => {
  if (audio) { await audio.close(); audio = null; document.getElementById('audio-state').value = 'Audio parado'; return; }
  audio = new AudioContext();
  const oscillator = audio.createOscillator();
  const gain = audio.createGain();
  gain.gain.value = .005;
  oscillator.connect(gain).connect(audio.destination);
  oscillator.start();
  document.getElementById('audio-state').value = 'Audio ativo';
});

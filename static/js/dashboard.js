/**
 * dashboard.js — Clock, FPS counter, and minor UI helpers.
 */

(function () {
  //  Clock 
  const clockEl = document.getElementById('status-time');

  function updateClock() {
    if (!clockEl) return;
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, '0');
    const mm = String(now.getMinutes()).padStart(2, '0');
    const ss = String(now.getSeconds()).padStart(2, '0');
    clockEl.textContent = `${hh}:${mm}:${ss}`;
  }

  updateClock();
  setInterval(updateClock, 1000);

  //  FPS counter (reads from the video element via requestVideoFrameCallback)
  const videoEl = document.getElementById('stream');
  const fpsEl = document.getElementById('status-fps');
  const latEl = document.getElementById('status-latency');

  if (videoEl && fpsEl && 'requestVideoFrameCallback' in videoEl) {
    let lastTs = null;
    let frameCount = 0;
    let fpsSmoothed = 0;

    function onFrame(now, meta) {
      if (lastTs !== null) {
        const delta = now - lastTs;
        const inst = 1000 / delta;
        fpsSmoothed = fpsSmoothed * 0.85 + inst * 0.15;
        fpsEl.textContent = fpsSmoothed.toFixed(1);

        // Rough latency estimate from processing delay
        if (meta.processingDuration !== undefined) {
          latEl.textContent = (meta.processingDuration * 1000).toFixed(0) + 'ms';
        }
      }
      lastTs = now;
      videoEl.requestVideoFrameCallback(onFrame);
    }

    videoEl.requestVideoFrameCallback(onFrame);
  }

  //  Global Footer Actions 
  const startBtn = document.getElementById('btn-start-task');
  const stopBtn = document.getElementById('btn-emergency-stop');

  if (startBtn) {
    startBtn.addEventListener('click', () => {
    });
  }

  if (stopBtn) {
    stopBtn.addEventListener('click', async () => {
      try {
        await fetch('/api/emergency-stop', { method: 'POST' });
      } catch (err) {
        console.error('Failed to send emergency stop:', err);
      }
    });
  }
})();

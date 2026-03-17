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

  const fpsEl = document.getElementById('status-fps');
  const latEl = document.getElementById('status-latency');
  const cpuEl = document.getElementById('status-cpu');
  const ramEl = document.getElementById('status-ram');
  const streamEl = document.getElementById('stream');
  const streamOverlayEl = document.getElementById('stream-overlay');
  const streamIndicatorEl = document.getElementById('stream-indicator');
  const detectionEntriesEl = document.getElementById('detection-entries');

  let pc = null;
  let dc = null;
  let pingInterval = null;
  let lastPingAt = 0;
  let detectionLogItems = [];

  function applySystemMetrics(data) {
    if (!cpuEl || !ramEl) return;
    if (!data) return;

    cpuEl.textContent = typeof data.cpu_percent === 'number' ? `${data.cpu_percent.toFixed(0)}%` : '--';
    ramEl.textContent = typeof data.ram_percent === 'number' ? `${data.ram_percent.toFixed(0)}%` : '--';
  }

  window.addEventListener('system-metrics', (evt) => {
    applySystemMetrics(evt.detail);
  });

  if (fpsEl) fpsEl.textContent = '--';
  if (latEl) latEl.textContent = '--';

  function _timeStampNow() {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, '0');
    const mm = String(now.getMinutes()).padStart(2, '0');
    const ss = String(now.getSeconds()).padStart(2, '0');
    return `${hh}:${mm}:${ss}`;
  }

  function _pushDetectionLog(message) {
    detectionLogItems.unshift(message);
    detectionLogItems = detectionLogItems.slice(0, 6);
  }

  function renderDetections(detections, detectorReady, detectorStatus) {
    if (!detectionEntriesEl) return;

    if (!detectorReady) {
      const status = detectorStatus || 'model unavailable';
      detectionEntriesEl.innerHTML = `<span class="entry" style="color:var(--text-muted);font-style:italic;">Detector offline: ${status}</span>`;
      return;
    }

    if (Array.isArray(detections) && detections.length > 0) {
      detections.slice(0, 3).forEach((d) => {
        const label = d.class || 'object';
        const conf = typeof d.conf === 'number' ? `${Math.round(d.conf * 100)}%` : '--';
        _pushDetectionLog(`[${_timeStampNow()}] ${label} (${conf})`);
      });
    }

    if (detectionLogItems.length === 0) {
      detectionEntriesEl.innerHTML = '<span class="entry" style="color:var(--text-muted);font-style:italic;">Watching camera for objects...</span>';
      return;
    }

    detectionEntriesEl.innerHTML = detectionLogItems
      .map((item) => `<span class="entry">${item}</span>`)
      .join('');
  }

  function setStreamUiConnected() {
    if (streamOverlayEl) streamOverlayEl.classList.add('hidden');
    if (streamIndicatorEl) {
      streamIndicatorEl.classList.remove('indicator--red');
      streamIndicatorEl.classList.add('indicator--green');
    }
  }

  function setStreamUiDisconnected(message) {
    if (streamOverlayEl) {
      const text = streamOverlayEl.querySelector('.stream-overlay-text');
      if (text) text.textContent = message || 'Camera stream disconnected';
      streamOverlayEl.classList.remove('hidden');
    }
    if (streamIndicatorEl) {
      streamIndicatorEl.classList.remove('indicator--green');
      streamIndicatorEl.classList.add('indicator--red');
    }
    if (fpsEl) fpsEl.textContent = '--';
    if (latEl) latEl.textContent = '--';
    renderDetections([], true, '');
  }

  function stopPing() {
    if (pingInterval) {
      clearInterval(pingInterval);
      pingInterval = null;
    }
  }

  function startPing() {
    stopPing();
    pingInterval = setInterval(() => {
      if (dc && dc.readyState === 'open') {
        lastPingAt = Date.now();
        dc.send('ping');
      }
    }, 1000);
  }

  async function closeStreamConnection() {
    stopPing();

    if (dc) {
      dc.close();
      dc = null;
    }

    if (pc) {
      pc.close();
      pc = null;
    }

    if (streamEl && streamEl.srcObject) {
      streamEl.srcObject.getTracks().forEach((track) => track.stop());
      streamEl.srcObject = null;
    }
  }

  async function connectWebRtcStream() {
    if (!streamEl || !window.RTCPeerConnection) return;

    setStreamUiDisconnected('Connecting camera stream...');

    try {
      pc = new RTCPeerConnection();
      dc = pc.createDataChannel('status');

      dc.onopen = () => {
        setStreamUiConnected();
        startPing();
      };

      dc.onmessage = (event) => {
        if (event.data === 'pong') {
          if (latEl) latEl.textContent = String(Date.now() - lastPingAt);
          return;
        }

        try {
          const data = JSON.parse(event.data);
          if (data.type === 'stats') {
            applySystemMetrics(data);
            if (fpsEl) {
              fpsEl.textContent = typeof data.fps === 'number' ? data.fps.toFixed(1) : '--';
            }
            renderDetections(data.detections, data.detector_ready, data.detector_status);
          }
        } catch (_err) {
          // Ignore non-JSON datachannel messages.
        }
      };

      pc.ontrack = (event) => {
        if (event.track.kind === 'video') {
          streamEl.srcObject = event.streams[0];
        }
      };

      pc.onconnectionstatechange = () => {
        if (!pc) return;
        if (pc.connectionState === 'connected') {
          setStreamUiConnected();
        }
        if (['failed', 'disconnected', 'closed'].includes(pc.connectionState)) {
          setStreamUiDisconnected('Camera stream disconnected');
        }
      };

      pc.addTransceiver('video', { direction: 'recvonly' });

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const response = await fetch('/offer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sdp: pc.localDescription.sdp,
          type: pc.localDescription.type,
        }),
      });

      if (!response.ok) {
        throw new Error('Offer negotiation failed');
      }

      const answer = await response.json();
      await pc.setRemoteDescription(new RTCSessionDescription(answer));
    } catch (err) {
      console.error('WebRTC stream error:', err);
      setStreamUiDisconnected('Unable to connect camera stream');
      await closeStreamConnection();
    }
  }

  if (streamEl) {
    connectWebRtcStream();
    window.addEventListener('beforeunload', () => {
      closeStreamConnection();
    });
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

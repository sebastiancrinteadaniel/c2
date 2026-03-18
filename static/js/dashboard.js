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
  const streamSpinnerEl = document.getElementById('stream-spinner');
  const streamConnectBtn = document.getElementById('stream-connect-btn');
  const streamIndicatorEl = document.getElementById('stream-indicator');
  const detectionEntriesEl = document.getElementById('detection-entries');

  let pc = null;
  let dc = null;
  let pingInterval = null;
  let lastPingAt = 0;
  let detectionLogItems = [];
  let reconnectTimer = null;
  let reconnectAttempts = 0;
  let isConnecting = false;
  let streamRequested = false;
  let streamLockedByCalibration = false;

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
    if (streamSpinnerEl) streamSpinnerEl.hidden = false;
    if (streamConnectBtn) {
      streamConnectBtn.hidden = false;
      streamConnectBtn.disabled = false;
      streamConnectBtn.textContent = 'Reconnect Camera';
    }
    if (streamIndicatorEl) {
      streamIndicatorEl.classList.remove('indicator--red');
      streamIndicatorEl.classList.add('indicator--green');
    }
  }

  function setStreamUiDisconnected(message, options = {}) {
    const {
      showSpinner = false,
      showButton = false,
      buttonDisabled = false,
      buttonLabel = 'Connect Camera',
    } = options;

    if (streamOverlayEl) {
      const text = streamOverlayEl.querySelector('.stream-overlay-text');
      if (text) text.textContent = message || 'Camera stream disconnected';
      streamOverlayEl.classList.remove('hidden');
    }
    if (streamSpinnerEl) {
      streamSpinnerEl.hidden = !showSpinner;
    }
    if (streamConnectBtn) {
      streamConnectBtn.hidden = !showButton;
      streamConnectBtn.disabled = buttonDisabled;
      streamConnectBtn.textContent = buttonLabel;
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

  function clearReconnectTimer() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function resetReconnectBackoff() {
    reconnectAttempts = 0;
    clearReconnectTimer();
  }

  function nextReconnectDelayMs() {
    const attempt = Math.min(reconnectAttempts, 5);
    const baseDelay = 1000 * (2 ** attempt);
    const cappedDelay = Math.min(baseDelay, 15000);
    const jitter = Math.floor(Math.random() * 250);
    reconnectAttempts += 1;
    return cappedDelay + jitter;
  }

  function scheduleReconnect(reason, immediate = false) {
    if (!streamEl) return;
    if (!streamRequested) return;
    if (document.hidden) return;
    if (streamLockedByCalibration) return;
    if (isConnecting || pc || reconnectTimer) return;

    const delay = immediate ? 0 : nextReconnectDelayMs();
    const message = immediate
      ? 'Reconnecting camera stream...'
      : `Reconnecting camera stream (${Math.ceil(delay / 1000)}s)...`;
    setStreamUiDisconnected(message, {
      showSpinner: true,
      showButton: false,
    });

    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connectWebRtcStream(reason);
    }, delay);
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

  async function connectWebRtcStream(reason = 'connect') {
    if (!streamEl || !window.RTCPeerConnection) return;
    if (!streamRequested) return;
    if (document.hidden) return;
    if (streamLockedByCalibration) return;
    if (isConnecting || pc) return;

    isConnecting = true;
    let shouldScheduleReconnect = false;

    setStreamUiDisconnected('Connecting camera stream...', {
      showSpinner: true,
      showButton: true,
      buttonDisabled: true,
      buttonLabel: 'Connecting...',
    });

    try {
      const localPc = new RTCPeerConnection();
      pc = localPc;
      dc = localPc.createDataChannel('status');

      dc.onopen = () => {
        if (pc !== localPc) return;
        setStreamUiConnected();
        resetReconnectBackoff();
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

      localPc.ontrack = (event) => {
        if (pc !== localPc) return;
        if (event.track.kind === 'video') {
          streamEl.srcObject = event.streams[0];
        }
      };

      localPc.onconnectionstatechange = async () => {
        if (pc !== localPc) return;
        if (localPc.connectionState === 'connected') {
          setStreamUiConnected();
          resetReconnectBackoff();
        }
        if (['failed', 'disconnected', 'closed'].includes(localPc.connectionState)) {
          setStreamUiDisconnected('Camera stream disconnected', {
            showSpinner: false,
            showButton: false,
          });
          await closeStreamConnection();
          scheduleReconnect(`state:${localPc.connectionState}`);
        }
      };

      localPc.addTransceiver('video', { direction: 'recvonly' });

      const offer = await localPc.createOffer();
      await localPc.setLocalDescription(offer);

      const response = await fetch('/offer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sdp: localPc.localDescription.sdp,
          type: localPc.localDescription.type,
        }),
      });

      if (!response.ok) {
        throw new Error('Offer negotiation failed');
      }

      const answer = await response.json();
      if (pc !== localPc) return;
      await localPc.setRemoteDescription(new RTCSessionDescription(answer));
    } catch (err) {
      console.error('WebRTC stream error:', err);
      setStreamUiDisconnected('Unable to connect camera stream', {
        showSpinner: false,
        showButton: true,
        buttonDisabled: true,
        buttonLabel: 'Retrying...',
      });
      await closeStreamConnection();
      shouldScheduleReconnect = true;
    } finally {
      isConnecting = false;
    }

    if (shouldScheduleReconnect) {
      scheduleReconnect(reason);
    }
  }

  if (streamEl) {
    setStreamUiDisconnected('Camera idle', {
      showSpinner: false,
      showButton: true,
    });

    if (streamConnectBtn) {
      streamConnectBtn.addEventListener('click', () => {
        if (streamLockedByCalibration) {
          setStreamUiDisconnected('Camera locked while calibration preview is active', {
            showSpinner: false,
            showButton: false,
          });
          return;
        }
        streamRequested = true;
        clearReconnectTimer();
        connectWebRtcStream('manual-connect');
      });
    }

    document.addEventListener('visibilitychange', async () => {
      if (document.hidden) {
        await closeStreamConnection();
        if (streamRequested) {
          setStreamUiDisconnected('Camera paused in background tab', {
            showSpinner: false,
            showButton: false,
          });
        }
        return;
      }

      if (streamRequested) {
        scheduleReconnect('tab-visible', true);
      }
    });

    window.addEventListener('camera-calibration-state', async (event) => {
      const detail = event?.detail || {};
      const active = Boolean(detail.active);
      const message = detail.message || 'Camera unavailable while calibration is active';

      streamLockedByCalibration = active;

      if (active) {
        clearReconnectTimer();
        await closeStreamConnection();
        setStreamUiDisconnected(message, {
          showSpinner: false,
          showButton: false,
        });
        return;
      }

      setStreamUiDisconnected('Camera idle', {
        showSpinner: false,
        showButton: true,
      });
      if (streamRequested) {
        scheduleReconnect('calibration-ended', true);
      }
    });

    window.addEventListener('beforeunload', () => {
      clearReconnectTimer();
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

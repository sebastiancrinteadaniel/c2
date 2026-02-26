/**
 * webrtc.js — Initiates a WebRTC connection to the server on every page load.
 * The server (aiortc) captures the local webcam and sends the track here.
 * No STUN servers needed — host candidates are enough for LAN.
 */

(async function () {
  const videoEl = document.getElementById('stream');
  const overlay = document.getElementById('stream-overlay');

  if (!videoEl) return;

  const pc = new RTCPeerConnection({ iceServers: [] });

  // Create data channel for detection logs
  const dc = pc.createDataChannel('detections');
  dc.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data);
      if (data.detections?.length > 0) {
        updateDetectionLog(data.detections);
      }
    } catch (e) { }
  };

  function updateDetectionLog(detections) {
    const logBox = document.getElementById('detection-entries');
    if (!logBox) return;

    // Clear placeholder if it's there
    if (logBox.children.length === 1 &&
      (logBox.children[0].textContent.includes('No detections yet') || logBox.children[0].textContent.includes('Searching'))) {
      logBox.innerHTML = '';
    }

    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

    detections.forEach(d => {
      const el = document.createElement('span');
      el.className = 'entry';
      el.innerHTML = `<span style="color:var(--text-muted)">[${timeStr}]</span> <span style="color:var(--cyan);font-weight:600;">${d.label.toUpperCase()}</span> <span style="color:var(--text-muted)">(${Math.round(d.confidence * 100)}%)</span>`;
      logBox.appendChild(el);
    });

    // Limits entries so terminal doesn't grow infinitely
    while (logBox.children.length > 20) {
      logBox.removeChild(logBox.firstChild);
    }
    // Auto-scroll to bottom
    logBox.scrollTop = logBox.scrollHeight;
  }

  // Tell the server we want to receive one video track
  pc.addTransceiver('video', { direction: 'recvonly' });

  pc.ontrack = (evt) => {
    if (evt.track.kind === 'video') {
      videoEl.srcObject = evt.streams[0] ?? new MediaStream([evt.track]);
      videoEl.onloadedmetadata = () => {
        videoEl.play().catch(() => { });
        if (overlay) overlay.classList.add('hidden');
        updateIndicator(true);
      };
    }
  };

  pc.onconnectionstatechange = () => {
    const s = pc.connectionState;
    console.log(`[webrtc] connection state: ${s}`);
    if (s === 'failed' || s === 'disconnected') {
      updateIndicator(false);
    }
  };

  try {
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    const res = await fetch('/api/offer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sdp: offer.sdp, type: offer.type }),
    });

    if (!res.ok) throw new Error(`Server returned ${res.status}`);

    const answer = await res.json();
    await pc.setRemoteDescription(new RTCSessionDescription(answer));
  } catch (err) {
    console.error('[webrtc] connection failed:', err);
    if (overlay) {
      overlay.querySelector('.stream-overlay-text').textContent = 'Stream unavailable';
      overlay.querySelector('.spinner').style.display = 'none';
    }
    updateIndicator(false);
  }

  function updateIndicator(alive) {
    const dot = document.getElementById('stream-indicator');
    if (!dot) return;
    dot.className = 'indicator ' + (alive ? 'indicator--green' : 'indicator--red');
  }
})();

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

  // Tell the server we want to receive one video track
  pc.addTransceiver('video', { direction: 'recvonly' });

  pc.ontrack = (evt) => {
    if (evt.track.kind === 'video') {
      videoEl.srcObject = evt.streams[0] ?? new MediaStream([evt.track]);
      videoEl.onloadedmetadata = () => {
        videoEl.play().catch(() => {});
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

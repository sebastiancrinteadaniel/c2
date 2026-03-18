(function () {
  const slider = document.getElementById('hc-inj-slider');
  const sliderValue = document.getElementById('hc-inj-val');

  function updateSlider() {
    if (!slider || !sliderValue) return;
    const pct = ((slider.value - slider.min) / (slider.max - slider.min) * 100).toFixed(1);
    slider.style.setProperty('--pct', `${pct}%`);
    sliderValue.textContent = `${slider.value} MM`;
  }

  if (slider) {
    slider.addEventListener('input', updateSlider);
    updateSlider();
  }

  const hcStates = {
    empty: document.getElementById('hc-rx-empty'),
    capture: document.getElementById('hc-rx-capture'),
    ready: document.getElementById('hc-rx-ready'),
    verify: document.getElementById('hc-rx-verify'),
  };
  const hcRxListEl = document.getElementById('hc-rx-list');
  const hcRxCandidatesEl = document.getElementById('hc-rx-candidates');
  const hcRxCurrentListEl = document.getElementById('hc-rx-current-list');
  const hcVerifyProgressEl = document.getElementById('hc-verify-progress');
  const hcMatrixBodyEl = document.getElementById('hc-matrix-body');

  const PLACEHOLDER_CAPTURE_EMPTY = 'No new detections yet';
  const PLACEHOLDER_LIST_EMPTY = 'No RX items yet';

  function appendBadge(container, text, className = 'badge badge--yes') {
    if (!container) return;
    const badge = document.createElement('span');
    badge.className = className;
    badge.textContent = text;
    container.appendChild(badge);
  }

  function readBadgeValues(container, placeholderText) {
    if (!container) return [];
    return Array.from(container.querySelectorAll('.badge'))
      .map((badge) => badge.textContent.trim())
      .filter((name) => name && name !== placeholderText);
  }

  function setRxStage(stage) {
    Object.entries(hcStates).forEach(([name, el]) => {
      if (!el) return;
      el.style.display = name === stage ? 'flex' : 'none';
    });
  }

  function renderRxCandidates(candidates) {
    if (!hcRxCandidatesEl) return;
    hcRxCandidatesEl.innerHTML = '';
    const list = Array.isArray(candidates) ? candidates : [];
    if (list.length === 0) {
      appendBadge(hcRxCandidatesEl, PLACEHOLDER_CAPTURE_EMPTY, 'badge badge--no');
      return;
    }

    list.forEach((item) => appendBadge(hcRxCandidatesEl, item));
  }

  function renderCurrentRxList(medicines) {
    const list = Array.isArray(medicines) ? medicines : [];

    if (hcRxListEl) {
      hcRxListEl.innerHTML = '';
    }
    if (hcRxCurrentListEl) {
      hcRxCurrentListEl.innerHTML = '';
    }

    if (list.length === 0) {
      if (hcRxListEl) {
        appendBadge(hcRxListEl, PLACEHOLDER_LIST_EMPTY, 'badge badge--no');
      }
      if (hcRxCurrentListEl) {
        appendBadge(hcRxCurrentListEl, PLACEHOLDER_LIST_EMPTY, 'badge badge--no');
      }
      return;
    }

    list.forEach((item) => {
      appendBadge(hcRxListEl, item);
      appendBadge(hcRxCurrentListEl, item);
    });
  }

  function rowBadge(isPositive, positiveLabel, negativeLabel, positiveClass, negativeClass) {
    const value = isPositive ? positiveLabel : negativeLabel;
    const cls = isPositive ? positiveClass : negativeClass;
    return `<span class="badge ${cls}">${value}</span>`;
  }

  function renderMatrix(rows) {
    if (!hcMatrixBodyEl) return;
    const list = Array.isArray(rows) ? rows : [];
    if (list.length === 0) {
      hcMatrixBodyEl.innerHTML = `
        <div class="hc-matrix-row hc-matrix-row--placeholder">
          <span class="hc-matrix-name">No RX candidates yet</span>
          <span class="hc-matrix-cell">${rowBadge(false, 'YES', 'NO', 'badge--yes', 'badge--no')}</span>
          <span class="hc-matrix-cell">${rowBadge(false, 'YES', 'NO', 'badge--yes', 'badge--no')}</span>
          <span class="hc-matrix-cell"><span class="badge badge--missing">WAITING</span></span>
        </div>`;
      return;
    }

    hcMatrixBodyEl.innerHTML = list.map((row) => {
      const inRx = Boolean(row.in_rx);
      const detected = Boolean(row.detected);
      const isMatch = String(row.status || '').toUpperCase() === 'MATCH';
      return `
        <div class="hc-matrix-row" data-medicine="${(row.medicine || '').replace(/"/g, '&quot;')}">
          <span class="hc-matrix-name">${row.medicine || '-'}</span>
          <span class="hc-matrix-cell">${rowBadge(inRx, 'YES', 'NO', 'badge--yes', 'badge--no')}</span>
          <span class="hc-matrix-cell">${rowBadge(detected, 'YES', 'NO', 'badge--yes', 'badge--no')}</span>
          <span class="hc-matrix-cell">${rowBadge(isMatch, 'MATCH', 'MISSING', 'badge--match', 'badge--missing')}</span>
        </div>`;
    }).join('');
  }

  function applyHealthcareSnapshot(snapshot) {
    if (!snapshot) return;
    renderRxCandidates(snapshot.rx_candidates || []);
    renderCurrentRxList(snapshot.rx_list || []);
    renderMatrix(snapshot.matrix || []);

    const matched = Number(snapshot.matched || 0);
    const total = Number(snapshot.total || 0);
    if (hcVerifyProgressEl) {
      const suffix = snapshot.complete ? ' • all matched (press Stop when done)' : '';
      hcVerifyProgressEl.textContent = `${matched}/${total} matched${suffix}`;
    }

    const mode = snapshot.mode || 'idle';
    if (mode === 'capture') {
      setRxStage('capture');
      return;
    }
    if (mode === 'ready') {
      setRxStage('ready');
      return;
    }
    if (mode === 'verify') {
      setRxStage('verify');
      return;
    }
    setRxStage('empty');
  }

  async function requestHealthcare(path, body = null) {
    try {
      const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : null,
      });
      const data = await res.json();
      applyHealthcareSnapshot(data.healthcare);
      return data;
    } catch (err) {
      console.error('[healthcare] request error:', err);
      return null;
    }
  }

  async function startRxCapture() {
    await requestHealthcare('/api/healthcare/start-rx-capture');
  }

  async function startRxAdd() {
    await requestHealthcare('/api/healthcare/start-rx-add');
  }

  async function addCapturedItems() {
    const rows = readBadgeValues(hcRxCandidatesEl, PLACEHOLDER_CAPTURE_EMPTY);
    await requestHealthcare('/api/healthcare/add-captured-items', { medicines: rows });
  }

  async function finishRxCapture() {
    const rows = readBadgeValues(hcRxCurrentListEl, PLACEHOLDER_LIST_EMPTY);
    await requestHealthcare('/api/healthcare/confirm-rx-list', { medicines: rows });
  }

  async function cancelRxCapture() {
    await requestHealthcare('/api/healthcare/stop-verification');
  }

  async function startVerification() {
    await requestHealthcare('/api/healthcare/start-verification');
  }

  async function stopVerification() {
    await requestHealthcare('/api/healthcare/stop-verification');
  }

  window.startRxCapture = startRxCapture;
  window.startRxAdd = startRxAdd;
  window.addCapturedItems = addCapturedItems;
  window.finishRxCapture = finishRxCapture;
  window.cancelRxCapture = cancelRxCapture;
  window.startVerification = startVerification;
  window.stopVerification = stopVerification;

  window.addEventListener('webrtc-stats', (event) => {
    applyHealthcareSnapshot(event.detail?.healthcare);
  });

  fetch('/api/healthcare/state')
    .then((res) => res.json())
    .then((data) => applyHealthcareSnapshot(data.healthcare))
    .catch((err) => console.error('[healthcare] failed to load state:', err));

  const startBtn = document.getElementById('btn-start-task');
  if (startBtn) {
    startBtn.addEventListener('click', async () => {
      const length = parseInt(document.getElementById('hc-inj-slider').value, 10);
      try {
        await fetch('/api/healthcare/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ injection_length: length }),
        });
      } catch (err) {
        console.error('Failed to start healthcare task:', err);
      }
    });
  }
})();

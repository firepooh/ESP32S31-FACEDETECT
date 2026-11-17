// Web flasher for ESP32-S31. esp-web-tools does not list ESP32-S31 yet, but
// esptool-js 0.7.1 ships the ESP32-S31 target and flasher stub, so use it directly.
import { ESPLoader, Transport } from 'https://cdn.jsdelivr.net/npm/esptool-js@0.7.1/bundle.js';

const BAUDRATE = 460800;
const EXPECTED_CHIP = 'ESP32-S31';

const $ = (id) => document.getElementById(id);
const logEl = $('log');
const statusEl = $('status');
const flashBtn = $('flash-btn');
const progressBar = $('progress-bar');

let manifest = null;

function log(text) {
  logEl.textContent += text;
  logEl.scrollTop = logEl.scrollHeight;
}

function setStatus(text, kind = '') {
  statusEl.textContent = text;
  statusEl.className = kind;
}

function formatSize(bytes) {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(2)} MB` : `${(bytes / 1024).toFixed(1)} KB`;
}

const terminal = {
  clean() { logEl.textContent = ''; },
  writeLine(data) { log(`${data}\n`); },
  write(data) { log(data); },
};

async function loadManifest() {
  const res = await fetch('firmware/manifest.json', { cache: 'no-store' });
  if (!res.ok) throw new Error(`manifest.json: HTTP ${res.status}`);
  manifest = await res.json();

  const info = [
    ['Project', manifest.name],
    ['Version', manifest.version],
    ['Built', manifest.built],
    ['ESP-IDF', manifest.idf_version],
    ['Chip', manifest.chip],
    ['Flash', `${manifest.flash_settings.flash_mode}, ${manifest.flash_settings.flash_size}, ${manifest.flash_settings.flash_freq}`],
  ];
  $('fw-info').innerHTML = '';
  for (const [k, v] of info) {
    const dt = document.createElement('dt');
    dt.textContent = k;
    const dd = document.createElement('dd');
    dd.textContent = v;
    $('fw-info').append(dt, dd);
  }

  const tbody = $('fw-parts').querySelector('tbody');
  tbody.innerHTML = '';
  for (const p of manifest.parts) {
    const tr = document.createElement('tr');
    for (const text of [`0x${p.offset.toString(16)}`, p.path, formatSize(p.size)]) {
      const td = document.createElement('td');
      td.textContent = text;
      tr.append(td);
    }
    tbody.append(tr);
  }
  $('fw-parts').hidden = false;

  const links = $('fw-links');
  links.innerHTML = 'Download: ';
  for (const p of [...manifest.parts, manifest.merged]) {
    const a = document.createElement('a');
    a.href = `firmware/${p.path}`;
    a.textContent = p.path;
    a.download = p.path;
    links.append(a);
  }
}

async function fetchPart(part) {
  const res = await fetch(`firmware/${part.path}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`${part.path}: HTTP ${res.status}`);
  return new Uint8Array(await res.arrayBuffer());
}

async function connectAndFlash() {
  flashBtn.disabled = true;
  progressBar.style.width = '0';
  terminal.clean();

  let transport = null;
  try {
    setStatus('Select the serial port… · 포트를 고르세요');
    const port = await navigator.serial.requestPort();
    transport = new Transport(port, false);

    setStatus('Connecting… · 연결 중');
    const loader = new ESPLoader({ transport, baudrate: BAUDRATE, terminal });
    const chip = await loader.main();
    if (loader.chip.CHIP_NAME !== EXPECTED_CHIP) {
      throw new Error(`Detected ${chip}, but this firmware is for ${EXPECTED_CHIP}.`);
    }

    setStatus('Downloading firmware… · 펌웨어 받는 중');
    const fileArray = [];
    for (const part of manifest.parts) {
      fileArray.push({ data: await fetchPart(part), address: part.offset });
    }
    const total = fileArray.reduce((sum, f) => sum + f.data.length, 0);
    const done = new Array(fileArray.length).fill(0);

    setStatus('Flashing… do not unplug · 플래시 중, 케이블을 뽑지 마세요');
    await loader.writeFlash({
      fileArray,
      flashMode: 'keep',
      flashFreq: 'keep',
      flashSize: 'keep',
      eraseAll: $('erase-all').checked,
      compress: true,
      reportProgress: (fileIndex, written, size) => {
        done[fileIndex] = (written / size) * fileArray[fileIndex].data.length;
        const pct = (done.reduce((a, b) => a + b, 0) / total) * 100;
        progressBar.style.width = `${pct.toFixed(1)}%`;
      },
    });

    await loader.after('hard_reset');
    progressBar.style.width = '100%';
    setStatus('Done. The board has been reset. · 완료. 보드를 리셋했습니다.', 'ok');
  } catch (err) {
    console.error(err);
    log(`\nERROR: ${err.message || err}\n`);
    const msg = err.name === 'NotFoundError' ? 'No port selected. · 포트를 고르지 않았습니다.' : `Failed: ${err.message || err}`;
    setStatus(msg, 'error');
  } finally {
    if (transport) {
      try { await transport.disconnect(); } catch (e) { /* already closed */ }
    }
    flashBtn.disabled = !manifest;
  }
}

if (!('serial' in navigator)) {
  $('unsupported').hidden = false;
}

flashBtn.addEventListener('click', connectAndFlash);

loadManifest()
  .then(() => {
    flashBtn.disabled = !('serial' in navigator);
    setStatus('Ready. · 준비됨');
  })
  .catch((err) => {
    $('fw-info').innerHTML = '';
    setStatus(`Could not load firmware info: ${err.message}`, 'error');
  });

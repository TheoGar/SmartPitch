'use strict';

const WS_URL = `ws://${location.hostname}:8765`;
const FIELD_W = 105;
const FIELD_H = 68;

// ── Couleurs par équipe ──────────────────────────────────────────────────────
const COLOR_TEAM_A = '#3b82f6';
const COLOR_TEAM_B = '#ef4444';
const COLOR_GK_A   = '#f59e0b';
const COLOR_GK_B   = '#10b981';

function getPlayerColor(player) {
  if (player.is_goalkeeper) {
    return player.team === 'A' ? COLOR_GK_A : COLOR_GK_B;
  }
  return player.team === 'A' ? COLOR_TEAM_A : COLOR_TEAM_B;
}

// ── DOM refs ─────────────────────────────────────────────────────────────────
const fieldCanvas    = document.getElementById('field-canvas');
const fieldCtx       = fieldCanvas.getContext('2d');
const matchTimeEl    = document.getElementById('match-time');
const statusEl       = document.getElementById('connection-status');
const tbody          = document.getElementById('player-tbody');
const hmPlayerSel    = document.getElementById('heatmap-player-select');
const hmLabel        = document.getElementById('heatmap-label');

const scSpeedA   = document.getElementById('sc-speed-a');
const scFatigueA = document.getElementById('sc-fatigue-a');
const scSpeedB   = document.getElementById('sc-speed-b');
const scFatigueB = document.getElementById('sc-fatigue-b');

const chartPlayerSel = document.getElementById('chart-player-select');

// ── Instances ─────────────────────────────────────────────────────────────────
const heatmapRenderer = new HeatmapRenderer('heatmap-canvas');
const statsChart      = new StatsChart('speed-chart', 'fatigue-chart');

// ── État heatmap ──────────────────────────────────────────────────────────────
let currentView = 'collective';
let lastData    = null;

function setView(view) {
  currentView = view;
  document.querySelectorAll('.hm-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.view === view);
  });
  if (!view.startsWith('player_')) hmPlayerSel.value = '';
  renderCurrentHeatmap();
}

function selectHeatmapGrid(data) {
  if (!data) return null;
  if (currentView === 'team_a') return data.heatmap_team_a;
  if (currentView === 'team_b') return data.heatmap_team_b;
  if (currentView.startsWith('player_')) {
    const pid = currentView.slice(7);
    return data.heatmap_players?.[pid] ?? data.heatmap;
  }
  return data.heatmap;
}

function getViewLabel() {
  if (currentView === 'collective')      return 'Toutes les positions cumulées';
  if (currentView === 'team_a')          return 'Équipe A — positions cumulées';
  if (currentView === 'team_b')          return 'Équipe B — positions cumulées';
  if (currentView.startsWith('player_')) return `Joueur ${currentView.slice(7)} — positions cumulées`;
  return '';
}

function renderCurrentHeatmap() {
  const grid = selectHeatmapGrid(lastData);
  if (grid) heatmapRenderer.draw(grid, currentView);
  hmLabel.textContent = getViewLabel();
}

document.querySelectorAll('.hm-btn').forEach(btn =>
  btn.addEventListener('click', () => setView(btn.dataset.view))
);
hmPlayerSel.addEventListener('change', () => {
  if (hmPlayerSel.value) setView(hmPlayerSel.value);
});

// ── État graphiques ───────────────────────────────────────────────────────────
function setChartMode(mode) {
  statsChart.setMode(mode);
  document.querySelectorAll('.chart-btn').forEach(b =>
    b.classList.toggle('active', mode === 'teams')
  );
  if (mode === 'teams') chartPlayerSel.value = '';
}

document.querySelectorAll('.chart-btn').forEach(btn =>
  btn.addEventListener('click', () => setChartMode('teams'))
);
chartPlayerSel.addEventListener('change', () => {
  if (chartPlayerSel.value) setChartMode(chartPlayerSel.value);
});

// ── Stat cards ────────────────────────────────────────────────────────────────
function updateStatCards() {
  const avg = statsChart.currentAverages();
  scSpeedA.textContent   = avg.speedA   != null ? avg.speedA.toFixed(1)   : '—';
  scFatigueA.textContent = avg.fatigueA != null ? avg.fatigueA.toFixed(0) : '—';
  scSpeedB.textContent   = avg.speedB   != null ? avg.speedB.toFixed(1)   : '—';
  scFatigueB.textContent = avg.fatigueB != null ? avg.fatigueB.toFixed(0) : '—';
}

// ── Dropdowns ─────────────────────────────────────────────────────────────────
let selectsPopulated = false;

function populateSelects(players) {
  if (selectsPopulated) return;
  [...players]
    .sort((a, b) => a.team !== b.team ? (a.team < b.team ? -1 : 1) : a.player_id - b.player_id)
    .forEach(p => {
      const gk    = p.is_goalkeeper ? ' (G)' : '';
      const label = `J${p.player_id} — Équipe ${p.team || ''}${gk}`;
      [hmPlayerSel, chartPlayerSel].forEach(sel => {
        const opt = document.createElement('option');
        opt.value = `player_${p.player_id}`;
        opt.textContent = label;
        sel.appendChild(opt);
      });
    });
  selectsPopulated = true;
}

// ── Terrain ───────────────────────────────────────────────────────────────────
function fieldToCanvas(x, y) {
  return {
    cx: (x / FIELD_W) * fieldCanvas.width,
    cy: (y / FIELD_H) * fieldCanvas.height,
  };
}

function drawField() {
  const ctx = fieldCtx;
  const w = fieldCanvas.width;
  const h = fieldCanvas.height;

  ctx.fillStyle = '#1a3a1a';
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = 'rgba(255,255,255,0.5)';
  ctx.lineWidth = 1.5;
  ctx.strokeRect(0, 0, w, h);

  // Ligne médiane
  ctx.beginPath(); ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2, h); ctx.stroke();

  // Cercle central
  ctx.beginPath();
  ctx.arc(w / 2, h / 2, (9.15 / FIELD_W) * w, 0, 2 * Math.PI);
  ctx.stroke();

  // Point central
  ctx.fillStyle = 'rgba(255,255,255,0.6)';
  ctx.beginPath(); ctx.arc(w / 2, h / 2, 3, 0, 2 * Math.PI); ctx.fill();

  // Surfaces de réparation
  const penD = (16.5 / FIELD_W) * w;
  const penW = (40.32 / FIELD_H) * h;
  const penOffY = (h - penW) / 2;
  ctx.strokeRect(0, penOffY, penD, penW);
  ctx.strokeRect(w - penD, penOffY, penD, penW);

  // Séparateurs de zones
  ctx.setLineDash([6, 4]);
  ctx.strokeStyle = 'rgba(255,255,255,0.15)';
  [(35 / FIELD_W) * w, (70 / FIELD_W) * w].forEach(xPos => {
    ctx.beginPath(); ctx.moveTo(xPos, 0); ctx.lineTo(xPos, h); ctx.stroke();
  });
  ctx.setLineDash([]);
}

function drawPlayers(players) {
  players.forEach(player => {
    if (player.x == null || player.y == null) return;
    const color = getPlayerColor(player);
    const { cx, cy } = fieldToCanvas(player.x, player.y);

    if (player.alerts?.length) {
      fieldCtx.shadowBlur  = 14;
      fieldCtx.shadowColor = '#f85149';
    }

    if (player.is_goalkeeper) {
      const size = 14;
      fieldCtx.fillStyle = color;
      fieldCtx.fillRect(cx - size / 2, cy - size / 2, size, size);
    } else {
      fieldCtx.fillStyle = color;
      fieldCtx.beginPath();
      fieldCtx.arc(cx, cy, 7, 0, 2 * Math.PI);
      fieldCtx.fill();
    }

    fieldCtx.shadowBlur = 0;

    fieldCtx.fillStyle    = '#fff';
    fieldCtx.font         = 'bold 9px sans-serif';
    fieldCtx.textAlign    = 'center';
    fieldCtx.textBaseline = 'middle';
    fieldCtx.fillText(player.player_id, cx, cy);
  });
}

// ── Tableau joueurs ───────────────────────────────────────────────────────────
function updateTable(players) {
  players.sort((a, b) => {
    if (a.team !== b.team) return a.team < b.team ? -1 : 1;
    return a.player_id - b.player_id;
  });
  tbody.innerHTML = '';
  for (const p of players) {
    const tr      = document.createElement('tr');
    const alerts  = (p.alerts || []).map(a => `<span class="alert-badge alert-${a}">${a}</span>`).join('');
    const gkBadge = p.is_goalkeeper ? '<span class="gk-badge">G</span>' : '';
    const zoneCls = `zone-${p.zone || 'milieu'}`;
    tr.innerHTML = `
      <td>${p.player_id}${gkBadge}</td>
      <td><span class="team-badge ${p.team || ''}">${p.team || '?'}</span></td>
      <td class="${zoneCls}">${p.zone || '—'}</td>
      <td>${p.speed       != null ? p.speed.toFixed(1)              : '—'}</td>
      <td>${p.heart_rate  ?? '—'}</td>
      <td>${p.fatigue     != null ? (p.fatigue * 100).toFixed(0)+'%': '—'}</td>
      <td>${p.cumulative_distance != null ? p.cumulative_distance.toFixed(0) : '—'}</td>
      <td>${alerts || '—'}</td>
    `;
    tbody.appendChild(tr);
  }
}

// ── Message ───────────────────────────────────────────────────────────────────
function formatMatchTime(s) {
  const m = Math.floor(s / 60).toString().padStart(2, '0');
  return `${m}:${(s % 60).toString().padStart(2, '0')}`;
}

function handleMessage(data) {
  lastData = data;
  const { players = [], match_time = 0 } = data;

  matchTimeEl.textContent = formatMatchTime(match_time);

  drawField();
  drawPlayers(players);
  renderCurrentHeatmap();
  updateTable(players);
  statsChart.update(players, match_time);
  updateStatCards();
  populateSelects(players);
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connect() {
  const ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    statusEl.textContent = 'Connecté';
    statusEl.className   = 'status-connected';
  };

  ws.onmessage = e => {
    try { handleMessage(JSON.parse(e.data)); } catch (_) {}
  };

  ws.onclose = () => {
    statusEl.textContent = 'Déconnecté — reconnexion…';
    statusEl.className   = 'status-disconnected';
    setTimeout(connect, 2000);
  };

  ws.onerror = () => ws.close();
}

drawField();
setView('collective');
connect();

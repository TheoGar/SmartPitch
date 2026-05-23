/**
 * StatsChart — deux modes :
 *   'teams'    → moyenne Équipe A vs Équipe B (2 courbes)
 *   'player_N' → vitesse/fatigue d'un seul joueur (1 courbe par graphique)
 */
class StatsChart {
  constructor(speedCanvasId, fatigueCanvasId, maxPoints = 90) {
    this.maxPoints = maxPoints;
    this._labels  = [];
    this._mode    = 'teams';

    this._teamA  = { speed: [], fatigue: [] };
    this._teamB  = { speed: [], fatigue: [] };
    this._players = {}; // pid → { speed[], fatigue[], team, isGK }

    const base = this._baseOptions();

    this._speedChart = new Chart(document.getElementById(speedCanvasId), {
      type: 'line',
      data: { labels: this._labels, datasets: [] },
      options: this._mergeOptions(base, {
        plugins: { title: { display: true, text: 'Vitesse (m/s)', color: '#c9d1d9', font: { size: 13, weight: 'bold' } } },
        scales:  { y: { min: 0, max: 9, title: { display: true, text: 'm/s', color: '#8b949e' } } },
      }),
    });

    this._fatigueChart = new Chart(document.getElementById(fatigueCanvasId), {
      type: 'line',
      data: { labels: this._labels, datasets: [] },
      options: this._mergeOptions(base, {
        plugins: { title: { display: true, text: 'Fatigue (%)', color: '#c9d1d9', font: { size: 13, weight: 'bold' } } },
        scales:  { y: { min: 0, max: 100, title: { display: true, text: '%', color: '#8b949e' } } },
      }),
    });
  }

  // ── Options de base Chart.js ──────────────────────────────────────────────
  _baseOptions() {
    return {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          display: true,
          labels: { color: '#e6edf3', font: { size: 12 }, boxWidth: 16, padding: 16 },
        },
        tooltip: {
          backgroundColor: '#161b22',
          borderColor: '#30363d',
          borderWidth: 1,
          titleColor: '#e6edf3',
          bodyColor: '#8b949e',
          padding: 10,
        },
      },
      scales: {
        x: {
          ticks: { color: '#8b949e', maxTicksLimit: 8, font: { size: 11 } },
          grid:  { color: '#21262d' },
        },
        y: {
          ticks: { color: '#8b949e', font: { size: 11 } },
          grid:  { color: '#21262d' },
          title: { display: false },
        },
      },
    };
  }

  _mergeOptions(base, overrides) {
    return {
      ...base,
      plugins: { ...base.plugins, ...overrides.plugins },
      scales:  {
        x: base.scales.x,
        y: { ...base.scales.y, ...overrides.scales?.y },
      },
    };
  }

  // ── Mise à jour des données ───────────────────────────────────────────────
  update(players, matchTime) {
    this._push(this._labels, this._fmt(matchTime));

    const A = players.filter(p => p.team === 'A');
    const B = players.filter(p => p.team === 'B');

    this._push(this._teamA.speed,   +this._avg(A, 'speed').toFixed(2));
    this._push(this._teamA.fatigue, +( this._avg(A, 'fatigue') * 100).toFixed(1));
    this._push(this._teamB.speed,   +this._avg(B, 'speed').toFixed(2));
    this._push(this._teamB.fatigue, +( this._avg(B, 'fatigue') * 100).toFixed(1));

    for (const p of players) {
      const pid = p.player_id;
      if (!this._players[pid]) {
        this._players[pid] = { speed: [], fatigue: [], team: p.team, isGK: p.is_goalkeeper };
      }
      this._push(this._players[pid].speed,   +(p.speed   ?? 0).toFixed(2));
      this._push(this._players[pid].fatigue, +((p.fatigue ?? 0) * 100).toFixed(1));
    }

    this._render();
  }

  setMode(mode) {
    this._mode = mode;
    this._render();
  }

  // ── Rendu selon le mode ───────────────────────────────────────────────────
  _render() {
    if (this._mode === 'teams') {
      this._speedChart.data.datasets = [
        this._ds('Équipe A — moyenne', this._teamA.speed,   '#3b82f6', true),
        this._ds('Équipe B — moyenne', this._teamB.speed,   '#ef4444', true),
      ];
      this._fatigueChart.data.datasets = [
        this._ds('Équipe A — moyenne', this._teamA.fatigue, '#3b82f6', true),
        this._ds('Équipe B — moyenne', this._teamB.fatigue, '#ef4444', true),
      ];
    } else {
      const pid = parseInt(this._mode.replace('player_', ''), 10);
      const p   = this._players[pid];
      if (!p) return;
      const color = this._playerColor(pid, p);
      const gk    = p.isGK ? ' ★' : '';
      this._speedChart.data.datasets   = [ this._ds(`J${pid}${gk} — Vitesse`,  p.speed,   color, false) ];
      this._fatigueChart.data.datasets = [ this._ds(`J${pid}${gk} — Fatigue`, p.fatigue, color, false) ];
    }

    this._speedChart.update('none');
    this._fatigueChart.update('none');
  }

  _ds(label, data, color, fill) {
    return {
      label,
      data,
      borderColor:     color,
      backgroundColor: color + (fill ? '28' : '15'),
      borderWidth: fill ? 2.5 : 2,
      pointRadius: 0,
      pointHoverRadius: 5,
      tension: 0.4,
      fill: fill ? 'origin' : false,
    };
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  _push(arr, val) {
    arr.push(val);
    if (arr.length > this.maxPoints) arr.shift();
  }

  _avg(players, field) {
    if (!players.length) return 0;
    return players.reduce((s, p) => s + (p[field] ?? 0), 0) / players.length;
  }

  _playerColor(pid, p) {
    if (p.isGK) return p.team === 'A' ? '#f59e0b' : '#10b981';
    return p.team === 'A' ? '#3b82f6' : '#ef4444';
  }

  _fmt(seconds) {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  // Retourne les moyennes actuelles pour les stat cards
  currentAverages() {
    const last = arr => arr.length ? arr[arr.length - 1] : null;
    return {
      speedA:   last(this._teamA.speed),
      fatigueA: last(this._teamA.fatigue),
      speedB:   last(this._teamB.speed),
      fatigueB: last(this._teamB.fatigue),
    };
  }
}

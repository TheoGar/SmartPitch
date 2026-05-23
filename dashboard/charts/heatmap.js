/**
 * Heatmap canvas renderer — 21×14 grid, accumulated counts.
 * Call HeatmapRenderer.draw(grid, view) on each update.
 * view: 'collective' | 'team_a' | 'team_b' | 'player_N'
 */
class HeatmapRenderer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.cols = 21;
    this.rows = 14;
    this.cellW = this.canvas.width / this.cols;
    this.cellH = this.canvas.height / this.rows;
  }

  // Returns [hue_low, hue_high] for the gradient depending on the view
  _hueRange(view) {
    if (view === 'team_a') return [200, 200];   // blue monochrome
    if (view === 'team_b') return [0, 0];        // red monochrome
    return [240, 0];                             // blue→red (default)
  }

  draw(grid, view = 'collective') {
    if (!grid || grid.length === 0) return;

    let maxVal = 1;
    for (const row of grid) for (const v of row) if (v > maxVal) maxVal = v;

    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Field background
    ctx.fillStyle = '#1a3a1a';
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    const [hLow, hHigh] = this._hueRange(view);
    const monoHue = hLow === hHigh;

    for (let r = 0; r < this.rows; r++) {
      for (let c = 0; c < this.cols; c++) {
        const val = grid[r]?.[c] ?? 0;
        if (val === 0) continue;
        const intensity = val / maxVal;
        const alpha = 0.15 + intensity * 0.85;
        const hue = monoHue ? hLow : hLow + intensity * (hHigh - hLow);
        const lightness = monoHue ? 40 + intensity * 30 : 50;
        ctx.fillStyle = `hsla(${hue}, 100%, ${lightness}%, ${alpha})`;
        ctx.fillRect(c * this.cellW, r * this.cellH, this.cellW, this.cellH);
      }
    }

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 0.5;
    for (let c = 0; c <= this.cols; c++) {
      ctx.beginPath();
      ctx.moveTo(c * this.cellW, 0);
      ctx.lineTo(c * this.cellW, this.canvas.height);
      ctx.stroke();
    }
    for (let r = 0; r <= this.rows; r++) {
      ctx.beginPath();
      ctx.moveTo(0, r * this.cellH);
      ctx.lineTo(this.canvas.width, r * this.cellH);
      ctx.stroke();
    }
  }
}

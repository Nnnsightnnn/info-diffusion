/* ─────────────────────────────────────────────────────────────────────
   Info Diffusion — animations engine
   - Hero: large dot-grid SIR sim with infection ripples
   - Mini canvases for each preset card
   - Scroll-revealed SVG S-curve
   - Counter readouts wired to the hero sim
   ───────────────────────────────────────────────────────────────────── */

(() => {
  const SIGNAL  = 'oklch(0.86 0.15 195)';
  const SIGNAL2 = 'oklch(0.78 0.18 200)';
  const SILENT  = 'oklch(0.78 0.13 65)';
  const FG      = 'rgba(236,233,225,0.32)';   // susceptible color (dim)
  const FG_DEEP = 'rgba(236,233,225,0.10)';

  // ── Color helper (cached) ──────────────────────────────────────────
  function rgba(c, a) {
    // accept oklch fn-strings; let the browser resolve once at startup.
    return c.replace(/\)$/, ` / ${a})`);
  }

  // ─────────────────────────────────────────────────────────────────
  // Discrete dot-grid SIR simulation. Each cell holds a state and a
  // "phase" value used for animated transitions (so newly-infected
  // dots fade up, newly-silent ones fade down).
  // ─────────────────────────────────────────────────────────────────
  class GridSim {
    constructor({ cols, rows, params, seeds, neighborhood = 'moore' }) {
      this.cols = cols;
      this.rows = rows;
      this.N    = cols * rows;
      this.params = params;          // { beta, gamma, perTick }
      this.neighborhood = neighborhood;
      this.reset(seeds);
    }

    reset(seedCount = 4) {
      const n = this.N;
      this.state    = new Uint8Array(n);  // 0 S, 1 I, 2 R
      this.phaseIn  = new Float32Array(n); // 0..1 fade-in for I
      this.phaseOut = new Float32Array(n); // 0..1 fade-in for R (after recovery)
      this.ripples = [];

      // Seed a few cells, biased toward center.
      for (let k = 0; k < seedCount; k++) {
        const cx = (this.cols / 2) + (Math.random() - 0.5) * this.cols * 0.45;
        const cy = (this.rows / 2) + (Math.random() - 0.5) * this.rows * 0.45;
        const i  = Math.floor(cy) * this.cols + Math.floor(cx);
        if (this.state[i] === 0) {
          this.state[i] = 1;
          this.phaseIn[i] = 1;
          this.ripples.push({ i, age: 0, max: 60 });
        }
      }
      this.tick = 0;
    }

    counts() {
      let s = 0, i = 0, r = 0;
      const st = this.state;
      for (let k = 0; k < st.length; k++) {
        const v = st[k]; if (v === 0) s++; else if (v === 1) i++; else r++;
      }
      return { s, i, r };
    }

    step() {
      const { cols, rows } = this;
      const N = this.N;
      const st = this.state;
      const next = new Uint8Array(st);

      // Effective per-neighbor infection probability per tick.
      // β here is the rate; with 8 neighbors we divide so the dynamics
      // resemble the continuous SIR locally.
      const beta = this.params.beta;
      const gamma = this.params.gamma;

      const neigh = this.neighborhood === 'moore'
        ? [[-1,-1],[0,-1],[1,-1],[-1,0],[1,0],[-1,1],[0,1],[1,1]]
        : [[0,-1],[-1,0],[1,0],[0,1]];

      const pPerNeighbor = 1 - Math.pow(1 - beta, 1 / neigh.length);

      // First pass: existing I cells try to infect S neighbors.
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const idx = y * cols + x;
          if (st[idx] !== 1) continue;

          // Maybe go silent.
          if (Math.random() < gamma) {
            next[idx] = 2;
            this.phaseOut[idx] = 0;
            continue;
          }

          for (const [dx, dy] of neigh) {
            const nx = x + dx, ny = y + dy;
            if (nx < 0 || ny < 0 || nx >= cols || ny >= rows) continue;
            const nIdx = ny * cols + nx;
            if (st[nIdx] === 0 && next[nIdx] === 0 && Math.random() < pPerNeighbor) {
              next[nIdx] = 1;
              this.phaseIn[nIdx] = 0;
              this.ripples.push({ i: nIdx, age: 0, max: 56 });
              if (this.ripples.length > 240) this.ripples.shift();
            }
          }
        }
      }

      this.state = next;
      this.tick++;

      // Auto-reset when activity collapses or run is long.
      const c = this.counts();
      if (c.i === 0 || this.tick > 600) {
        // small "burnout" pause before reset, handled by caller via tick reset
        return { ...c, exhausted: true };
      }
      return { ...c, exhausted: false };
    }

    advancePhases(dt) {
      const st = this.state;
      const a = Math.min(1, dt * 6);          // fade-in speed
      const b = Math.min(1, dt * 2.4);        // fade-to-silent speed
      for (let k = 0; k < st.length; k++) {
        const v = st[k];
        if (v === 1 && this.phaseIn[k] < 1)  this.phaseIn[k]  = Math.min(1, this.phaseIn[k]  + a);
        if (v === 2 && this.phaseOut[k] < 1) this.phaseOut[k] = Math.min(1, this.phaseOut[k] + b);
      }
      // age ripples
      for (const r of this.ripples) r.age += dt * 60;
      this.ripples = this.ripples.filter(r => r.age < r.max);
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // Renderer: paints a GridSim onto a canvas with crisp dots and
  // expanding ripple rings from newly-infected cells.
  // ─────────────────────────────────────────────────────────────────
  function renderGrid(ctx, sim, w, h, opts = {}) {
    const {
      cellW, cellH,
      dotR = Math.min(cellW, cellH) * 0.18,
      ripples = true,
      glow = true,
    } = opts;

    ctx.clearRect(0, 0, w, h);

    const { cols, rows, state, phaseIn, phaseOut } = sim;

    // Background: very faint S dots.
    ctx.fillStyle = FG_DEEP;
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const idx = y * cols + x;
        if (state[idx] === 0) {
          const cx = (x + 0.5) * cellW;
          const cy = (y + 0.5) * cellH;
          ctx.beginPath();
          ctx.arc(cx, cy, dotR * 0.65, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }

    // Ripples (from newly-infected cells) — drawn before bright dots.
    if (ripples) {
      for (const rp of sim.ripples) {
        const x = rp.i % cols;
        const y = (rp.i / cols) | 0;
        const cx = (x + 0.5) * cellW;
        const cy = (y + 0.5) * cellH;
        const t  = rp.age / rp.max;
        const radius = (1 + t * 7) * dotR;
        const alpha = (1 - t) * 0.55;
        ctx.strokeStyle = rgba(SIGNAL, alpha.toFixed(3));
        ctx.lineWidth = 1.1;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.stroke();
      }
    }

    // Recovered (silent) dots.
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const idx = y * cols + x;
        if (state[idx] === 2) {
          const ph = phaseOut[idx];
          const cx = (x + 0.5) * cellW;
          const cy = (y + 0.5) * cellH;
          ctx.fillStyle = rgba(SILENT, (0.18 + 0.30 * ph).toFixed(3));
          ctx.beginPath();
          ctx.arc(cx, cy, dotR * (0.78 + 0.10 * ph), 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }

    // Informed dots — bright, with optional outer glow.
    if (glow) {
      ctx.globalCompositeOperation = 'lighter';
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const idx = y * cols + x;
          if (state[idx] === 1) {
            const ph = phaseIn[idx];
            const cx = (x + 0.5) * cellW;
            const cy = (y + 0.5) * cellH;
            const halo = ctx.createRadialGradient(cx, cy, 0, cx, cy, dotR * 8);
            halo.addColorStop(0, rgba(SIGNAL, (0.45 * ph).toFixed(3)));
            halo.addColorStop(0.4, rgba(SIGNAL, (0.10 * ph).toFixed(3)));
            halo.addColorStop(1, rgba(SIGNAL, '0'));
            ctx.fillStyle = halo;
            ctx.beginPath();
            ctx.arc(cx, cy, dotR * 8, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
      ctx.globalCompositeOperation = 'source-over';
    }

    // Bright core for I.
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const idx = y * cols + x;
        if (state[idx] === 1) {
          const ph = phaseIn[idx];
          const cx = (x + 0.5) * cellW;
          const cy = (y + 0.5) * cellH;
          ctx.fillStyle = rgba(SIGNAL, (0.75 + 0.25 * ph).toFixed(3));
          ctx.beginPath();
          ctx.arc(cx, cy, dotR * (0.9 + 0.4 * ph), 0, Math.PI * 2);
          ctx.fill();
          // tiny white-hot center
          ctx.fillStyle = `rgba(236,233,225,${(0.7 * ph).toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(cx, cy, dotR * 0.35, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // Generic driver: sets up a canvas with DPR, creates a sim, and
  // calls render every frame. Returns handle with .sim and .destroy.
  // ─────────────────────────────────────────────────────────────────
  function makeCanvasSim(canvas, {
    cellSize = 14,
    params = { beta: 0.18, gamma: 0.06 },
    seeds = 4,
    tickRate = 12,         // ticks per second
    glow = true,
    ripples = true,
    autoReset = true,
    onTick = null,
    onCounts = null,
  } = {}) {
    const ctx = canvas.getContext('2d', { alpha: true });
    let dpr = Math.min(window.devicePixelRatio || 1, 2);

    let cols, rows, cellW, cellH;
    let sim;
    let last = performance.now();
    let acc = 0;
    let raf = 0;
    let restartTimer = 0;
    let lastCounts = { s: 0, i: 0, r: 0 };

    function size() {
      const rect = canvas.getBoundingClientRect();
      const w = Math.max(1, Math.round(rect.width));
      const h = Math.max(1, Math.round(rect.height));
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      cols = Math.max(8, Math.round(w / cellSize));
      rows = Math.max(6, Math.round(h / cellSize));
      cellW = w / cols;
      cellH = h / rows;

      sim = new GridSim({ cols, rows, params, seeds });
    }

    function frame(now) {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      acc += dt;

      const tickInterval = 1 / tickRate;
      while (acc >= tickInterval) {
        const c = sim.step();
        lastCounts = c;
        acc -= tickInterval;
        if (onTick) onTick(c);
        if (onCounts) onCounts(c, sim.N);
        if (c.exhausted && autoReset) {
          restartTimer = 1.8; // seconds of dwell before reset
        }
      }

      sim.advancePhases(dt);

      if (restartTimer > 0) {
        restartTimer -= dt;
        if (restartTimer <= 0) {
          sim.reset(seeds);
        }
      }

      const rect = canvas.getBoundingClientRect();
      renderGrid(ctx, sim, rect.width, rect.height, {
        cellW, cellH,
        dotR: Math.min(cellW, cellH) * 0.22,
        glow, ripples,
      });

      raf = requestAnimationFrame(frame);
    }

    const onResize = () => { size(); };
    size();
    raf = requestAnimationFrame(frame);
    window.addEventListener('resize', onResize);

    return {
      get sim() { return sim; },
      get counts() { return lastCounts; },
      destroy() {
        cancelAnimationFrame(raf);
        window.removeEventListener('resize', onResize);
      },
    };
  }

  // ─────────────────────────────────────────────────────────────────
  // Hero animation + wired counters
  // ─────────────────────────────────────────────────────────────────
  function initHero() {
    const canvas = document.getElementById('hero-canvas');
    if (!canvas) return;

    const reachedEl = document.querySelector('[data-readout="reached"]');
    const activeEl  = document.querySelector('[data-readout="active"]');
    const dayEl     = document.querySelector('[data-readout="day"]');
    const counterEl = document.querySelector('[data-readout="counter"]');

    let t = 0;
    makeCanvasSim(canvas, {
      cellSize: 18,
      params: { beta: 0.16, gamma: 0.045 },
      seeds: 5,
      tickRate: 14,
      glow: true,
      ripples: true,
      onTick: (c) => {
        t++;
        const total = c.s + c.i + c.r;
        const reached = c.i + c.r;
        const pct = total > 0 ? (reached / total) * 100 : 0;
        if (reachedEl) reachedEl.textContent = pct.toFixed(1) + '%';
        if (activeEl)  activeEl.textContent  = c.i.toLocaleString();
        if (dayEl)     dayEl.textContent     = String(t % 600);
        if (counterEl) counterEl.textContent = reached.toLocaleString();
      },
    });
  }

  // ─────────────────────────────────────────────────────────────────
  // Mini canvases for state cards (S/I/R) — show characteristic
  // visuals for each state.
  // ─────────────────────────────────────────────────────────────────
  function initStateVizzes() {
    const sCanvas = document.getElementById('state-viz-s');
    const iCanvas = document.getElementById('state-viz-i');
    const rCanvas = document.getElementById('state-viz-r');
    if (!sCanvas || !iCanvas || !rCanvas) return;

    function bootSimpleField(canvas, drawer) {
      const ctx = canvas.getContext('2d');
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      function size() {
        const r = canvas.getBoundingClientRect();
        canvas.width = r.width * dpr;
        canvas.height = r.height * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      }
      size();
      window.addEventListener('resize', size);
      let raf, t0 = performance.now();
      const loop = (now) => {
        const r = canvas.getBoundingClientRect();
        ctx.clearRect(0, 0, r.width, r.height);
        drawer(ctx, r.width, r.height, (now - t0) / 1000);
        raf = requestAnimationFrame(loop);
      };
      raf = requestAnimationFrame(loop);
    }

    // S — dense calm dust
    bootSimpleField(sCanvas, (ctx, w, h, t) => {
      const cols = Math.floor(w / 10), rows = Math.floor(h / 10);
      const cw = w / cols, ch = h / rows;
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const phase = Math.sin((x * 0.3 + y * 0.2 + t * 0.4));
          const a = 0.10 + 0.06 * Math.max(0, phase);
          ctx.fillStyle = `rgba(236,233,225,${a.toFixed(3)})`;
          ctx.beginPath();
          ctx.arc((x + 0.5) * cw, (y + 0.5) * ch, 1.2, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    });

    // I — bright pulse, with infectious tendrils
    bootSimpleField(iCanvas, (ctx, w, h, t) => {
      const cols = Math.floor(w / 10), rows = Math.floor(h / 10);
      const cw = w / cols, ch = h / rows;
      const cx = w / 2, cy = h / 2;
      const wavefront = (Math.sin(t * 1.4) + 1) * 0.5;  // 0..1
      const maxR = Math.hypot(w, h) * 0.55;
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const px = (x + 0.5) * cw, py = (y + 0.5) * ch;
          const d = Math.hypot(px - cx, py - cy);
          const ring = Math.exp(-Math.pow((d - wavefront * maxR) / 22, 2));
          const baseDim = 0.10;
          const bright = ring * 0.95;
          ctx.fillStyle = bright > 0.05
            ? rgba(SIGNAL, (baseDim + bright).toFixed(3))
            : `rgba(236,233,225,${baseDim.toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(px, py, 1.4 + bright * 1.6, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      // central core
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, 60);
      g.addColorStop(0, rgba(SIGNAL, '0.5'));
      g.addColorStop(1, rgba(SIGNAL, '0'));
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(cx, cy, 60, 0, Math.PI * 2); ctx.fill();
    });

    // R — settling into silence: dots fade from cyan to amber as you scan
    bootSimpleField(rCanvas, (ctx, w, h, t) => {
      const cols = Math.floor(w / 10), rows = Math.floor(h / 10);
      const cw = w / cols, ch = h / rows;
      // a horizontal "wave of silence" sweeping right
      const sweep = ((t * 0.18) % 1.5) * w / 1.5;
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const px = (x + 0.5) * cw, py = (y + 0.5) * ch;
          const k = Math.max(0, Math.min(1, (sweep - px + 80) / 160));
          const c = k > 0.5 ? SILENT : SIGNAL;
          const alpha = 0.18 + 0.18 * (k > 0.5 ? (1 - (k - 0.5) * 0.4) : k);
          ctx.fillStyle = rgba(c, alpha.toFixed(3));
          ctx.beginPath();
          ctx.arc(px, py, 1.3, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    });
  }

  // ─────────────────────────────────────────────────────────────────
  // Preset cards — each gets its own mini sim configured to feel
  // like its scenario (viral, fizzle, slow burn, etc).
  // ─────────────────────────────────────────────────────────────────
  function initPresetMinis() {
    const els = document.querySelectorAll('[data-preset-canvas]');
    els.forEach(canvas => {
      const kind = canvas.dataset.presetCanvas;
      const cfg = ({
        tiny:      { beta: 0.10, gamma: 0.10, seeds: 2, cellSize: 12, tickRate: 10 },
        small:     { beta: 0.14, gamma: 0.10, seeds: 3, cellSize: 12, tickRate: 11 },
        mid:       { beta: 0.18, gamma: 0.10, seeds: 4, cellSize: 12, tickRate: 12 },
        viral:     { beta: 0.28, gamma: 0.12, seeds: 6, cellSize: 11, tickRate: 14 },
        fizzle:    { beta: 0.08, gamma: 0.30, seeds: 5, cellSize: 12, tickRate: 11 },
        slow_burn: { beta: 0.07, gamma: 0.04, seeds: 1, cellSize: 12, tickRate: 9  },
      })[kind] || { beta: 0.16, gamma: 0.10, seeds: 3, cellSize: 12, tickRate: 11 };

      makeCanvasSim(canvas, {
        cellSize: cfg.cellSize,
        params: { beta: cfg.beta, gamma: cfg.gamma },
        seeds: cfg.seeds,
        tickRate: cfg.tickRate,
        glow: true,
        ripples: false,
      });
    });
  }

  // ─────────────────────────────────────────────────────────────────
  // S-curve SVG — continuous SIR integrated and drawn into the SVG.
  // Animates the stroke when it scrolls into view.
  // ─────────────────────────────────────────────────────────────────
  function buildSCurve() {
    const svg = document.getElementById('scurve-svg');
    if (!svg) return;

    const W = 1200, H = 580;
    const padL = 60, padR = 60, padT = 60, padB = 60;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    // SIR integrate
    const days = 90;
    const N = 1_000_000;
    const beta  = 3.0 * 0.15;
    const gamma = 0.10;
    let S = N - 10, I = 10, R = 0;
    const series = [];
    for (let d = 0; d <= days; d++) {
      series.push({ d, S, I, R });
      const ni = beta * S * I / N;
      const nr = gamma * I;
      S = Math.max(0, S - ni);
      I = Math.max(0, I + ni - nr);
      R = Math.min(N, R + nr);
    }
    const maxI = Math.max(...series.map(p => p.I));
    const x = d => padL + (d / days) * plotW;
    const yI = v => padT + plotH - (v / N) * plotH;
    const yI_scaled = v => padT + plotH - (v / (maxI * 1.3)) * plotH;

    // build path strings
    const pathI = series.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(p.d).toFixed(2)} ${yI_scaled(p.I).toFixed(2)}`).join(' ');
    const pathR = series.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(p.d).toFixed(2)} ${yI((p.I + p.R)).toFixed(2)}`).join(' ');
    const pathArea = pathI + ` L ${x(days).toFixed(2)} ${(padT + plotH).toFixed(2)} L ${x(0).toFixed(2)} ${(padT + plotH).toFixed(2)} Z`;

    // grid lines
    let grid = '';
    for (let g = 0; g <= 5; g++) {
      const gy = padT + (g / 5) * plotH;
      grid += `<line class="grid-line" x1="${padL}" y1="${gy}" x2="${padL + plotW}" y2="${gy}"/>`;
    }
    for (let g = 0; g <= 6; g++) {
      const gx = padL + (g / 6) * plotW;
      grid += `<line class="grid-line" x1="${gx}" y1="${padT}" x2="${gx}" y2="${padT + plotH}"/>`;
    }

    // axis labels
    let labels = '';
    for (let g = 0; g <= 6; g++) {
      const d = Math.round((g / 6) * days);
      const gx = padL + (g / 6) * plotW;
      labels += `<text class="axis-label" x="${gx}" y="${padT + plotH + 22}" text-anchor="middle">day ${d}</text>`;
    }
    labels += `<text class="axis-label" x="${padL - 14}" y="${padT + 8}" text-anchor="end">100%</text>`;
    labels += `<text class="axis-label" x="${padL - 14}" y="${padT + plotH + 4}" text-anchor="end">0%</text>`;

    // peak marker
    const peak = series.reduce((a, b) => (b.I > a.I ? b : a));
    const peakX = x(peak.d);
    const peakY = yI_scaled(peak.I);

    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.innerHTML = `
      <defs>
        <linearGradient id="area-i-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stop-color="oklch(0.86 0.15 195)" stop-opacity="0.55"/>
          <stop offset="100%" stop-color="oklch(0.86 0.15 195)" stop-opacity="0"/>
        </linearGradient>
      </defs>
      ${grid}
      <line class="axis" x1="${padL}" y1="${padT + plotH}" x2="${padL + plotW}" y2="${padT + plotH}"/>
      <line class="axis" x1="${padL}" y1="${padT}"        x2="${padL}"         y2="${padT + plotH}"/>
      ${labels}

      <path class="area-i" d="${pathArea}"/>
      <path class="curve-r" d="${pathR}"/>
      <path class="curve-i" d="${pathI}" id="curve-i-path"/>

      <line class="grid-line" x1="${peakX}" y1="${padT}" x2="${peakX}" y2="${peakY}"
            stroke="oklch(0.86 0.15 195 / 0.4)" stroke-dasharray="3 3"/>
      <circle class="marker" cx="${peakX}" cy="${peakY}" r="5"/>
      <text class="axis-label" x="${peakX + 12}" y="${peakY - 8}"
            fill="oklch(0.86 0.15 195)">peak · day ${peak.d}</text>
    `;

    // Animate the I curve drawing when in view
    const path = svg.querySelector('#curve-i-path');
    const rPath = svg.querySelector('.curve-r');
    const len = path.getTotalLength();
    const rLen = rPath.getTotalLength();
    path.style.strokeDasharray  = len;
    path.style.strokeDashoffset = len;
    rPath.style.strokeDasharray  = `${rLen}`;
    rPath.style.strokeDashoffset = rLen;
    const area = svg.querySelector('.area-i');
    area.style.opacity = '0';

    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          path.animate(
            [{ strokeDashoffset: len }, { strokeDashoffset: 0 }],
            { duration: 2400, easing: 'cubic-bezier(0.2, 0.7, 0.2, 1)', fill: 'forwards' }
          );
          rPath.animate(
            [{ strokeDashoffset: rLen }, { strokeDashoffset: 0 }],
            { duration: 2800, delay: 300, easing: 'cubic-bezier(0.2, 0.7, 0.2, 1)', fill: 'forwards' }
          );
          area.animate(
            [{ opacity: 0 }, { opacity: 0.5 }],
            { duration: 1800, delay: 800, easing: 'ease-out', fill: 'forwards' }
          );
          io.disconnect();
        }
      });
    }, { threshold: 0.3 });
    io.observe(svg);

    // Wire readouts to series final values
    const peakOut = document.querySelector('[data-curve="peak"]');
    const peakDay = document.querySelector('[data-curve="peakday"]');
    const reached = document.querySelector('[data-curve="reached"]');
    const d50 = series.findIndex(p => (p.I + p.R) / N >= 0.5);
    const day50 = document.querySelector('[data-curve="day50"]');
    if (peakOut) peakOut.textContent = peak.I.toLocaleString();
    if (peakDay) peakDay.textContent = `day ${peak.d}`;
    if (reached) reached.textContent = ((series[series.length - 1].I + series[series.length - 1].R) / N * 100).toFixed(1) + '%';
    if (day50)   day50.textContent   = d50 >= 0 ? `day ${d50}` : 'never';
  }

  // ─────────────────────────────────────────────────────────────────
  // Reveal-on-scroll
  // ─────────────────────────────────────────────────────────────────
  function initReveal() {
    const targets = document.querySelectorAll('.reveal');
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12 });
    targets.forEach(t => io.observe(t));
  }

  // ─────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    initHero();
    initStateVizzes();
    initPresetMinis();
    buildSCurve();
    initReveal();
  });
})();

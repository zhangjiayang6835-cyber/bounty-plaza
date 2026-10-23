// Canvas hero animation: tokens burn at a source node, arc through an attestation apex,
// and mint at a destination node, a literal visualization of the burn/attest/mint flow.
// Each launch picks Arc or Stellar as the source at random, so the corridor reads as
// bidirectional rather than a one-way Arc -> Stellar demo. Loops continuously; respects
// prefers-reduced-motion with a static three-stage frame.

interface Rgb {
  r: number;
  g: number;
  b: number;
}

interface Point {
  x: number;
  y: number;
}

interface Colors {
  paper: string;
  slate: string;
  rule: string;
  burn: Rgb;
  attest: Rgb;
  mint: Rgb;
}

interface Particle {
  t0: number;
  dir: 1 | -1; // 1 = Arc -> Stellar, -1 = Stellar -> Arc; either chain can be the source
  launched: boolean;
  pinged: boolean;
  arrived: boolean;
}

interface Ping {
  born: number;
}

interface Dust {
  x: number;
  y: number;
  r: number;
  drift: number;
  phase: number;
}

const DURATION = 2800; // ms per crossing
const SPAWN_EVERY = 780; // ms between launches
const MAX_PARTICLES = 13;
const DUST_COUNT = 110;

export function initHeroAnimation(canvasId: string): void {
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement | null;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  let W = 0;
  let H = 0;
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  let x0 = 0;
  let x1 = 0;
  let baseline = 0;
  let peak = 0;

  const colors: Colors = {
    paper: "#eef0ec",
    slate: "#5b6472",
    rule: "#c9cdc4",
    burn: { r: 182, g: 79, b: 28 },
    attest: { r: 138, g: 106, b: 30 },
    mint: { r: 34, g: 107, b: 80 },
  };

  function hexToRgb(hex: string): Rgb {
    let clean = hex.replace("#", "");
    if (clean.length === 3) {
      clean = clean.split("").map((c) => c + c).join("");
    }
    const num = parseInt(clean, 16);
    return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
  }

  function readColors(): void {
    const s = getComputedStyle(document.documentElement);
    colors.paper = s.getPropertyValue("--paper").trim();
    colors.slate = s.getPropertyValue("--slate").trim();
    colors.rule = s.getPropertyValue("--rule").trim();
    colors.burn = hexToRgb(s.getPropertyValue("--burn").trim());
    colors.attest = hexToRgb(s.getPropertyValue("--attest").trim());
    colors.mint = hexToRgb(s.getPropertyValue("--mint").trim());
  }

  function lerpColor(a: Rgb, b: Rgb, t: number): Rgb {
    return {
      r: a.r + (b.r - a.r) * t,
      g: a.g + (b.g - a.g) * t,
      b: a.b + (b.b - a.b) * t,
    };
  }

  function rgba(c: Rgb, a: number): string {
    return `rgba(${Math.round(c.r)},${Math.round(c.g)},${Math.round(c.b)},${a})`;
  }

  function clamp01(v: number): number {
    return Math.max(0, Math.min(1, v));
  }

  // Color of the moving token at progress p (0 = burn/departure, 0.5 = attest/apex, 1 = mint/arrival).
  function tokenColor(p: number): Rgb {
    if (p < 0.42) return lerpColor(colors.burn, colors.attest, clamp01(p / 0.42));
    return lerpColor(colors.attest, colors.mint, clamp01((p - 0.42) / 0.58));
  }

  const dust: Dust[] = [];
  function seedDust(): void {
    dust.length = 0;
    for (let i = 0; i < DUST_COUNT; i++) {
      dust.push({
        x: Math.random() * W,
        y: Math.random() * H * 0.85,
        r: 0.6 + Math.random() * 1.2,
        drift: 4 + Math.random() * 10,
        phase: Math.random() * Math.PI * 2,
      });
    }
  }

  function layout(): void {
    const rect = canvas!.parentElement!.getBoundingClientRect();
    W = rect.width;
    H = rect.height;
    canvas!.width = W * dpr;
    canvas!.height = H * dpr;
    ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);

    // Spans the full hero as an atmospheric backdrop; the headline sits on top of it
    // with a directional scrim (see .hero-scrim in style.css) rather than the arc
    // being confined to a corner out of the copy's way.
    x0 = W * 0.14;
    x1 = W * 0.86;
    baseline = H * 0.74;
    peak = H * 0.56;
    seedDust();
    seedGrid();
  }

  function pathPoint(p: number): Point {
    return {
      x: x0 + (x1 - x0) * p,
      y: baseline - peak * 4 * p * (1 - p),
    };
  }

  function drawDust(now: number): void {
    for (const d of dust) {
      const y = d.y + Math.sin(now / 1400 + d.phase) * d.drift;
      ctx!.beginPath();
      ctx!.fillStyle = rgba(hexToRgb(colors.slate), 0.14);
      ctx!.arc(d.x, y, d.r, 0, Math.PI * 2);
      ctx!.fill();
    }
  }

  let gridDots: Point[] = [];
  function seedGrid(): void {
    gridDots = [];
    const step = 46;
    for (let gy = step / 2; gy < H; gy += step) {
      for (let gx = step / 2; gx < W; gx += step) {
        gridDots.push({ x: gx, y: gy });
      }
    }
  }

  function drawGrid(): void {
    ctx!.fillStyle = rgba(hexToRgb(colors.rule), 0.4);
    for (const p of gridDots) {
      ctx!.fillRect(p.x, p.y, 1, 1);
    }
  }

  function drawGuide(): void {
    ctx!.beginPath();
    ctx!.setLineDash([2, 7]);
    ctx!.lineWidth = 1.5;
    ctx!.strokeStyle = colors.rule;
    const first = pathPoint(0);
    ctx!.moveTo(first.x, first.y);
    for (let i = 1; i <= 60; i++) {
      const pt = pathPoint(i / 60);
      ctx!.lineTo(pt.x, pt.y);
    }
    ctx!.stroke();
    ctx!.setLineDash([]);
  }

  function drawNode(x: number, y: number, color: Rgb, label: string, glow: number): void {
    const ambient = ctx!.createRadialGradient(x, y, 0, x, y, 60);
    ambient.addColorStop(0, rgba(color, 0.14 + glow * 0.22));
    ambient.addColorStop(1, rgba(color, 0));
    ctx!.fillStyle = ambient;
    ctx!.beginPath();
    ctx!.arc(x, y, 60, 0, Math.PI * 2);
    ctx!.fill();

    if (glow > 0) {
      const g = ctx!.createRadialGradient(x, y, 0, x, y, 40 * glow);
      g.addColorStop(0, rgba(color, 0.4 * glow));
      g.addColorStop(1, rgba(color, 0));
      ctx!.fillStyle = g;
      ctx!.beginPath();
      ctx!.arc(x, y, 40 * glow, 0, Math.PI * 2);
      ctx!.fill();
    }
    ctx!.beginPath();
    ctx!.fillStyle = rgba(color, 1);
    ctx!.arc(x, y, 7, 0, Math.PI * 2);
    ctx!.fill();
    ctx!.beginPath();
    ctx!.strokeStyle = colors.paper;
    ctx!.lineWidth = 2.5;
    ctx!.arc(x, y, 7, 0, Math.PI * 2);
    ctx!.stroke();

    ctx!.font = "700 12px ui-monospace, 'Cascadia Code', 'SF Mono', Consolas, monospace";
    ctx!.fillStyle = colors.slate;
    ctx!.textAlign = x < W / 2 ? "left" : "right";
    ctx!.textBaseline = "middle";
    ctx!.fillText(label, x < W / 2 ? x + 18 : x - 18, y);
  }

  const particles: Particle[] = [];
  const pings: Ping[] = [];
  let lastSpawn = -Infinity;
  let arcGlow = 0;
  let stellarGlow = 0;

  // colorP always runs burn -> mint over the particle's lifetime; posP maps that same
  // progress onto the path, flipped for dir === -1 so a Stellar-sourced particle still
  // burns at its own departure node and mints at its own arrival node.
  function drawParticle(colorP: number, dir: 1 | -1): void {
    const posP = (t: number): number => (dir === 1 ? t : 1 - t);

    for (let i = 5; i >= 1; i--) {
      const tp = clamp01(colorP - i * 0.018);
      const gp = pathPoint(posP(tp));
      const c = tokenColor(tp);
      ctx!.beginPath();
      ctx!.fillStyle = rgba(c, (1 - i / 6) * 0.28);
      ctx!.arc(gp.x, gp.y, 4 - i * 0.4, 0, Math.PI * 2);
      ctx!.fill();
    }

    const p = colorP;
    const head = pathPoint(posP(p));
    const hc = tokenColor(p);

    if (p < 0.1) {
      const burst = 1 - p / 0.1;
      ctx!.beginPath();
      ctx!.fillStyle = rgba(colors.burn, burst * 0.4);
      ctx!.arc(head.x, head.y, 4 + burst * 10, 0, Math.PI * 2);
      ctx!.fill();
    }
    if (p > 0.9) {
      const land = (p - 0.9) / 0.1;
      ctx!.beginPath();
      ctx!.fillStyle = rgba(colors.mint, (1 - land) * 0.4);
      ctx!.arc(head.x, head.y, 4 + land * 12, 0, Math.PI * 2);
      ctx!.fill();
    }

    const halo = ctx!.createRadialGradient(head.x, head.y, 0, head.x, head.y, 16);
    halo.addColorStop(0, rgba(hc, 0.5));
    halo.addColorStop(1, rgba(hc, 0));
    ctx!.fillStyle = halo;
    ctx!.beginPath();
    ctx!.arc(head.x, head.y, 16, 0, Math.PI * 2);
    ctx!.fill();

    ctx!.beginPath();
    ctx!.fillStyle = rgba(hc, 0.98);
    ctx!.arc(head.x, head.y, 5.5, 0, Math.PI * 2);
    ctx!.fill();
    ctx!.beginPath();
    ctx!.fillStyle = "rgba(255,255,255,0.55)";
    ctx!.arc(head.x - 1.3, head.y - 1.3, 1.6, 0, Math.PI * 2);
    ctx!.fill();
  }

  function stepParticles(now: number): void {
    arcGlow = Math.max(0, arcGlow - 0.03);
    stellarGlow = Math.max(0, stellarGlow - 0.03);

    for (let i = particles.length - 1; i >= 0; i--) {
      const pt = particles[i]!;
      const p = (now - pt.t0) / DURATION;

      if (p < 0.02 && !pt.launched) {
        pt.launched = true;
        if (pt.dir === 1) arcGlow = 1;
        else stellarGlow = 1;
      }
      if (p >= 0.5 && !pt.pinged) {
        pt.pinged = true;
        pings.push({ born: now });
      }
      if (p >= 0.97 && !pt.arrived) {
        pt.arrived = true;
        if (pt.dir === 1) stellarGlow = 1;
        else arcGlow = 1;
      }

      if (p >= 1.05) {
        particles.splice(i, 1);
        continue;
      }

      drawParticle(clamp01(p), pt.dir);
    }
  }

  function stepPings(now: number): void {
    for (let i = pings.length - 1; i >= 0; i--) {
      const age = now - pings[i]!.born;
      const life = 700;
      if (age > life) {
        pings.splice(i, 1);
        continue;
      }
      const t = age / life;
      const apex = pathPoint(0.5);
      ctx!.beginPath();
      ctx!.strokeStyle = rgba(colors.attest, 1 - t);
      ctx!.lineWidth = 2;
      ctx!.arc(apex.x, apex.y, 6 + t * 26, 0, Math.PI * 2);
      ctx!.stroke();
    }
  }

  function drawStatic(): void {
    ctx!.clearRect(0, 0, W, H);
    drawGrid();
    drawGuide();
    [0.15, 0.5, 0.85].forEach((p) => {
      const pt = pathPoint(p);
      ctx!.beginPath();
      ctx!.fillStyle = rgba(tokenColor(p), 0.95);
      ctx!.arc(pt.x, pt.y, 5, 0, Math.PI * 2);
      ctx!.fill();
    });
    drawNode(x0, baseline, colors.burn, "ARC", 0);
    drawNode(x1, baseline, colors.mint, "STELLAR", 0);
  }

  let rafId: number | null = null;

  function frame(now: number): void {
    if (reduceMotion.matches) {
      rafId = null;
      drawStatic();
      return;
    }
    ctx!.clearRect(0, 0, W, H);
    drawGrid();
    drawDust(now);
    drawGuide();

    if (now - lastSpawn > SPAWN_EVERY && particles.length < MAX_PARTICLES) {
      lastSpawn = now;
      const dir: 1 | -1 = Math.random() < 0.5 ? 1 : -1;
      particles.push({ t0: now, dir, launched: false, pinged: false, arrived: false });
    }

    stepParticles(now);
    stepPings(now);

    drawNode(x0, baseline, colors.burn, "ARC", arcGlow);
    drawNode(x1, baseline, colors.mint, "STELLAR", stellarGlow);

    rafId = requestAnimationFrame(frame);
  }

  function start(): void {
    readColors();
    layout();
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
    if (reduceMotion.matches) {
      drawStatic();
    } else {
      rafId = requestAnimationFrame(frame);
    }
  }

  reduceMotion.addEventListener("change", () => {
    if (reduceMotion.matches) {
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
      drawStatic();
    } else if (rafId === null) {
      rafId = requestAnimationFrame(frame);
    }
  });

  window.addEventListener("resize", () => {
    layout();
    if (reduceMotion.matches) drawStatic();
  });

  new MutationObserver(readColors).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", readColors);

  start();
}

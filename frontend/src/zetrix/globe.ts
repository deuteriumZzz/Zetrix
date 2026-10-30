/** Local, illustrative geography. Routes are decorative, not live risk data. */
type Vector = { x: number; y: number; z: number };
type Particle = Vector & { land: boolean; seed: number };
type Projected = Vector & { scale: number };

const TAU = Math.PI * 2;
const RAD = Math.PI / 180;
const FRAME_INTERVAL = 1000 / 30;
const INTRO_DURATION = 1.4;
const clamp = (value: number, low: number, high: number) => Math.min(high, Math.max(low, value));
const circleSamples = Array.from({ length: 121 }, (_, index) => ({
  sin: Math.sin(index / 120 * TAU), cos: Math.cos(index / 120 * TAU),
}));
const toVector = (latitude: number, longitude: number): Vector => ({
  x: Math.cos(latitude * RAD) * Math.sin(longitude * RAD),
  y: Math.sin(latitude * RAD),
  z: Math.cos(latitude * RAD) * Math.cos(longitude * RAD),
});

const hubs = [
  toVector(51.5, -0.12), toVector(40.7, -74), toVector(25.2, 55.3),
  toVector(1.35, 103.8), toVector(35.7, 139.7), toVector(-33.9, 151.2),
];
const connections = [[0, 1], [0, 2], [2, 3], [3, 4], [3, 5], [0, 3]];

function routePoint(start: Vector, end: Vector, progress: number): Vector {
  const angle = Math.acos(Math.min(1, Math.max(-1,
    start.x * end.x + start.y * end.y + start.z * end.z)));
  const denominator = Math.sin(angle) || 1;
  const a = Math.sin((1 - progress) * angle) / denominator;
  const b = Math.sin(progress * angle) / denominator;
  const altitude = 1.008 + Math.sin(progress * Math.PI) * 0.13;
  return {
    x: (start.x * a + end.x * b) * altitude,
    y: (start.y * a + end.y * b) * altitude,
    z: (start.z * a + end.z * b) * altitude,
  };
}

const routes = connections.map(([from, to]) =>
  Array.from({ length: 81 }, (_, index) => routePoint(hubs[from], hubs[to], index / 80)));

function samplePath(path: Vector[], progress: number): Vector {
  const position = ((progress % 1 + 1) % 1) * (path.length - 1);
  const index = Math.floor(position);
  const mix = position - index;
  const a = path[index];
  const b = path[Math.min(index + 1, path.length - 1)];
  return { x: a.x + (b.x - a.x) * mix, y: a.y + (b.y - a.y) * mix, z: a.z + (b.z - a.z) * mix };
}

// Abstract orbital paths are decorative; they do not represent tracked objects.
const orbits = [0.34, -0.48].map(tilt => circleSamples.map(({ sin, cos }) => ({
  x: cos * 1.1, y: sin * Math.sin(tilt) * 1.1, z: sin * Math.cos(tilt) * 1.1,
})));

function createParticles(pixels?: ImageData): Particle[] {
  const count = 19000;
  return Array.from({ length: count }, (_, index) => {
    const y = 1 - 2 * ((index + 0.5) / count);
    const latitude = Math.asin(y);
    const longitude = (index * Math.PI * (3 - Math.sqrt(5))) % TAU - Math.PI;
    const circle = Math.sqrt(1 - y * y);
    let land = false;
    if (pixels) {
      const px = Math.min(pixels.width - 1, Math.floor((longitude / TAU + 0.5) * pixels.width));
      const py = Math.min(pixels.height - 1, Math.floor((0.5 - latitude / Math.PI) * pixels.height));
      const offset = (py * pixels.width + px) * 4;
      const [red, green, blue] = pixels.data.subarray(offset, offset + 3);
      land = red > blue * 0.83 && green > blue * 0.85;
    }
    return { x: circle * Math.sin(longitude), y, z: circle * Math.cos(longitude), land, seed: index % 17 };
  });
}

export function initializeGlobe(canvas: HTMLCanvasElement): () => void {
  const context = canvas.getContext('2d');
  if (!context) return () => undefined;
  const ctx: CanvasRenderingContext2D = context;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let particles = createParticles();
  let width = 1;
  let height = 1;
  let radius = 1;
  let yaw = -0.44;
  let pitch = 0.16;
  let frame = 0;
  let lastTime = 0;
  let elapsed = 0;
  let velocityYaw = 0;
  let velocityPitch = 0;
  let orientation = { cy: Math.cos(yaw), sy: Math.sin(yaw), cp: Math.cos(pitch), sp: Math.sin(pitch) };
  let visible = true;
  let paused = false;
  let disposed = false;
  let pointer: { id: number; x: number; y: number; time: number } | null = null;

  function project(point: Vector): Projected {
    const { cy, sy, cp, sp } = orientation;
    const x = point.x * cy + point.z * sy;
    const z = point.z * cy - point.x * sy;
    const y = point.y * cp - z * sp;
    const depth = point.y * sp + z * cp;
    const scale = 1 + depth * 0.035;
    return { x: width / 2 + x * radius * scale, y: height / 2 - y * radius * scale, z: depth, scale };
  }

  function drawLine(points: Vector[], color: string, frontOnly = false) {
    ctx.beginPath();
    let started = false;
    points.forEach(point => {
      const p = project(point);
      if (frontOnly && p.z < 0) { started = false; return; }
      if (started) ctx.lineTo(p.x, p.y);
      else ctx.moveTo(p.x, p.y);
      started = true;
    });
    ctx.strokeStyle = color;
    ctx.stroke();
  }

  const grid: Vector[][] = [];
  for (let lat = -60; lat <= 60; lat += 30) {
    grid.push(Array.from({ length: 121 }, (_, i) => toVector(lat, i * 3)));
  }
  for (let lon = 0; lon < 180; lon += 30) {
    grid.push(Array.from({ length: 121 }, (_, i) => {
      const angle = (i / 120) * TAU;
      return { x: Math.cos(angle) * Math.sin(lon * RAD), y: Math.sin(angle), z: Math.cos(angle) * Math.cos(lon * RAD) };
    }));
  }

  function render() {
    orientation = { cy: Math.cos(yaw), sy: Math.sin(yaw), cp: Math.cos(pitch), sp: Math.sin(pitch) };
    const intro = reducedMotion.matches ? 1 : clamp(elapsed / INTRO_DURATION, 0, 1);
    const dispersion = Math.pow(1 - intro, 3);
    ctx.clearRect(0, 0, width, height);
    const atmosphere = ctx.createRadialGradient(width / 2, height / 2, radius * 0.8, width / 2, height / 2, radius * 1.16);
    atmosphere.addColorStop(0, 'rgba(70,180,196,0)');
    atmosphere.addColorStop(0.64, 'rgba(70,180,196,0.045)');
    atmosphere.addColorStop(1, 'rgba(70,180,196,0)');
    ctx.fillStyle = atmosphere;
    ctx.fillRect(0, 0, width, height);
    ctx.lineWidth = 0.6;
    grid.forEach(line => drawLine(line, 'rgba(93,178,183,0.095)'));

    // Batch particles into depth bands to keep drawing affordable on mobile.
    const bands: Projected[][] = Array.from({ length: 16 }, () => []);
    particles.forEach((particle, index) => {
      if (!particle.land && index % 9 !== 0) return;
      const spread = 1 + dispersion * (0.08 + particle.seed / 16 * 0.18);
      const p = project({ x: particle.x * spread, y: particle.y * spread, z: particle.z * spread });
      if (p.z < -0.12 && !particle.land) return;
      const band = clamp(Math.floor((p.z + 1) * 3.999), 0, 7);
      bands[band + (particle.land ? 8 : 0)].push(p);
    });
    bands.forEach((points, band) => {
      const land = band >= 8;
      const depth = band % 8;
      const opacity = land ? 0.06 + Math.pow(depth / 7, 1.5) * 0.79 : 0.07 + depth / 7 * 0.16;
      ctx.fillStyle = land ? `rgba(191,236,228,${opacity})` : `rgba(69,169,188,${opacity})`;
      const size = Math.max(0.65, radius / 310) * (land ? 1.3 : 0.8);
      ctx.beginPath();
      points.forEach(p => ctx.rect(p.x - size / 2, p.y - size / 2, size, size));
      ctx.fill();
    });

    ctx.globalAlpha = reducedMotion.matches ? 1 : clamp(intro * 2 - 0.5, 0, 1);
    drawScan();
    drawRoutes();
    drawHubs();
    drawOrbits();
    ctx.globalAlpha = 1;
  }

  function drawScan() {
    const latitude = reducedMotion.matches ? 0.2 : Math.sin(elapsed * 0.24) * 0.82;
    const circle = Math.sqrt(1 - latitude * latitude);
    const scan = circleSamples.map(({ sin, cos }) => ({ x: sin * circle, y: latitude, z: cos * circle }));
    ctx.lineWidth = 4;
    drawLine(scan, 'rgba(115,225,208,0.025)', true);
    ctx.lineWidth = 0.7;
    drawLine(scan, 'rgba(147,248,228,0.19)', true);
  }

  function drawRoutes() {
    ctx.lineWidth = 0.8;
    routes.forEach((route, index) => {
      drawLine(route, 'rgba(113,227,211,0.3)', true);
      const progress = (elapsed * 0.065 + index * 0.17) % 1;
      for (let tail = 5; tail >= 0; tail--) {
        // Traces end at a route endpoint instead of wrapping across the globe.
        const position = progress - tail * 0.008;
        if (position < 0) continue;
        const point = project(samplePath(route, position));
        if (point.z < 0) continue;
        ctx.fillStyle = `rgba(199,255,238,${(1 - tail / 6) * 0.9})`;
        ctx.beginPath();
        ctx.arc(point.x, point.y, tail === 0 ? 1.8 : 1, 0, TAU);
        ctx.fill();
      }
    });
  }

  function drawHubs() {
    hubs.forEach((hub, index) => {
      const point = project(hub);
      if (point.z < 0) return;
      const pulse = reducedMotion.matches ? 0.35 : (elapsed * 0.32 + index * 0.19) % 1;
      ctx.strokeStyle = `rgba(141,235,215,${(1 - pulse) * 0.28})`;
      ctx.lineWidth = 0.75;
      ctx.beginPath();
      ctx.arc(point.x, point.y, 5 + pulse * 12, 0, TAU);
      ctx.stroke();
      ctx.strokeStyle = 'rgba(141,235,215,0.48)';
      ctx.beginPath();
      ctx.arc(point.x, point.y, 4, 0, TAU);
      ctx.stroke();
      ctx.fillStyle = '#bcf5e4';
      ctx.fillRect(point.x - 1, point.y - 1, 2, 2);
    });
  }

  function drawOrbits() {
    ctx.lineWidth = 0.55;
    orbits.forEach((orbit, index) => {
      drawLine(orbit, 'rgba(126,206,213,0.08)', true);
      const position = reducedMotion.matches ? 0.2 + index * 0.4 : elapsed * 0.023 + index * 0.4;
      for (let tail = 0; tail < 4; tail++) {
        const point = project(samplePath(orbit, position - tail * 0.003));
        if (point.z < 0) continue;
        ctx.fillStyle = `rgba(179,236,240,${0.65 - tail * 0.15})`;
        ctx.beginPath();
        ctx.arc(point.x, point.y, tail === 0 ? 1.4 : 0.8, 0, TAU);
        ctx.fill();
      }
    });
  }

  const canAnimate = () => !disposed && visible && !document.hidden && !paused && !reducedMotion.matches;
  function animate(time: number) {
    frame = 0;
    if (!canAnimate()) { lastTime = 0; return; }
    if (lastTime && time - lastTime < FRAME_INTERVAL) {
      frame = requestAnimationFrame(animate);
      return;
    }
    const delta = lastTime ? Math.min((time - lastTime) / 1000, 0.08) : 0;
    lastTime = time;
    elapsed += delta;
    if (!pointer) {
      yaw += delta * (0.035 + velocityYaw);
      pitch = clamp(pitch + delta * velocityPitch, -0.8, 0.8);
      const friction = Math.exp(-delta * 4.5);
      velocityYaw *= friction;
      velocityPitch *= friction;
    }
    render();
    frame = requestAnimationFrame(animate);
  }
  function synchronize() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    lastTime = 0;
    if (canAnimate()) frame = requestAnimationFrame(animate);
  }
  function onMotionPreference() {
    velocityYaw = 0;
    velocityPitch = 0;
    // A preference change resolves the entrance instead of leaving a dispersed globe.
    elapsed = Math.max(elapsed, INTRO_DURATION);
    synchronize();
    render();
  }
  function resize() {
    const bounds = canvas.getBoundingClientRect();
    width = Math.max(1, bounds.width);
    height = Math.max(1, bounds.height);
    radius = Math.min(width, height) * 0.425;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.75);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    render();
  }
  function onPause(event: Event) {
    paused = Boolean((event as CustomEvent<boolean>).detail);
    if (paused) {
      elapsed = Math.max(elapsed, INTRO_DURATION);
      velocityYaw = 0;
      velocityPitch = 0;
      render();
    }
    synchronize();
  }
  function pointerDown(event: PointerEvent) {
    if (event.button !== 0) return;
    pointer = { id: event.pointerId, x: event.clientX, y: event.clientY, time: event.timeStamp };
    velocityYaw = 0;
    velocityPitch = 0;
    canvas.setPointerCapture(event.pointerId);
    canvas.style.cursor = 'grabbing';
  }
  function pointerMove(event: PointerEvent) {
    if (!pointer || pointer.id !== event.pointerId) return;
    const dx = (event.clientX - pointer.x) * 0.005;
    const dy = (event.clientY - pointer.y) * 0.003;
    const delta = Math.max((event.timeStamp - pointer.time) / 1000, 0.016);
    yaw += dx;
    pitch = clamp(pitch + dy, -0.8, 0.8);
    velocityYaw = canAnimate() ? clamp(dx / delta, -1.4, 1.4) : 0;
    velocityPitch = canAnimate() ? clamp(dy / delta, -0.7, 0.7) : 0;
    pointer = { id: event.pointerId, x: event.clientX, y: event.clientY, time: event.timeStamp };
    render();
  }
  function pointerEnd(event: PointerEvent) {
    if (!pointer || pointer.id !== event.pointerId) return;
    if (event.timeStamp - pointer.time > 100 || event.type !== 'pointerup') {
      velocityYaw = 0;
      velocityPitch = 0;
    }
    pointer = null;
    canvas.style.cursor = 'grab';
    if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
  }

  const image = new Image();
  image.onload = () => {
    if (disposed) return;
    try {
      const samplingCanvas = document.createElement('canvas');
      samplingCanvas.width = 1024;
      samplingCanvas.height = 512;
      const samplingContext = samplingCanvas.getContext('2d', { willReadFrequently: true });
      if (!samplingContext) return;
      samplingContext.drawImage(image, 0, 0, 1024, 512);
      particles = createParticles(samplingContext.getImageData(0, 0, 1024, 512));
      canvas.dataset.geography = 'ready';
      render();
    } catch (error) {
      canvas.dataset.geography = 'unavailable';
      console.warn('Zetrix globe geography could not be loaded.', error);
    }
  };
  image.onerror = () => { canvas.dataset.geography = 'unavailable'; };
  image.src = '/globe/earth-blue-marble.jpg';
  const originalCursor = canvas.style.cursor;
  const originalTouchAction = canvas.style.touchAction;
  canvas.style.cursor = 'grab';
  canvas.style.touchAction = 'pan-y';
  const sizeObserver = new ResizeObserver(resize);
  sizeObserver.observe(canvas);
  const visibilityObserver = new IntersectionObserver(entries => {
    visible = entries[0]?.isIntersecting ?? false;
    synchronize();
  });
  visibilityObserver.observe(canvas);
  document.addEventListener('visibilitychange', synchronize);
  reducedMotion.addEventListener('change', onMotionPreference);
  canvas.addEventListener('zetrix:pause', onPause);
  canvas.addEventListener('pointerdown', pointerDown);
  canvas.addEventListener('pointermove', pointerMove);
  canvas.addEventListener('pointerup', pointerEnd);
  canvas.addEventListener('pointercancel', pointerEnd);
  canvas.addEventListener('lostpointercapture', pointerEnd);
  resize();
  synchronize();

  return () => {
    disposed = true;
    if (frame) cancelAnimationFrame(frame);
    image.onload = null;
    image.onerror = null;
    sizeObserver.disconnect();
    visibilityObserver.disconnect();
    document.removeEventListener('visibilitychange', synchronize);
    reducedMotion.removeEventListener('change', onMotionPreference);
    canvas.removeEventListener('zetrix:pause', onPause);
    canvas.removeEventListener('pointerdown', pointerDown);
    canvas.removeEventListener('pointermove', pointerMove);
    canvas.removeEventListener('pointerup', pointerEnd);
    canvas.removeEventListener('pointercancel', pointerEnd);
    canvas.removeEventListener('lostpointercapture', pointerEnd);
    canvas.style.cursor = originalCursor;
    canvas.style.touchAction = originalTouchAction;
  };
}

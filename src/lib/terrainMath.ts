// Simple deterministic hash for noise
function hash(x: number, y: number) {
  const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453123
  return n - Math.floor(n)
}

function lerp(a: number, b: number, t: number) {
  return a + t * (b - a)
}

function smoothstep(t: number) {
  return t * t * (3 - 2 * t)
}

// 2D Value Noise
function noise(x: number, y: number) {
  const ix = Math.floor(x)
  const iy = Math.floor(y)
  const fx = x - ix
  const fy = y - iy

  const u = smoothstep(fx)
  const v = smoothstep(fy)

  const a = hash(ix, iy)
  const b = hash(ix + 1, iy)
  const c = hash(ix, iy + 1)
  const d = hash(ix + 1, iy + 1)

  return lerp(lerp(a, b, u), lerp(c, d, u), v)
}

// Fractal Brownian Motion for dramatic mountains
function fbm(x: number, y: number, octaves = 4) {
  let value = 0
  let amplitude = 1
  let frequency = 1
  let max = 0
  
  for (let i = 0; i < octaves; i++) {
    value += noise(x * frequency, y * frequency) * amplitude
    max += amplitude
    amplitude *= 0.5
    frequency *= 2
  }
  
  return value / max
}

export function getHeight(x: number, z: number): number {
  // Base rugged terrain
  const scale = 0.15
  let y = fbm(x * scale, z * scale, 5) * 12 - 6

  // Add lower-frequency mountainous dunes
  y += Math.sin(x * 0.05) * Math.cos(z * 0.05) * 6

  // Apply a deep crater in the middle (x ≈ 5, z ≈ -5)
  const cx = x - 5
  const cz = z + 5
  const distanceToCrater = Math.sqrt(cx * cx + cz * cz)
  const craterRadius = 18
  const craterRimDepth = 8

  if (distanceToCrater < craterRadius) {
    // Smoother crater equation: deep in center, rising at the rim
    const normalizedDist = distanceToCrater / craterRadius
    const craterShape = Math.pow(normalizedDist, 2) * 2 - 1 // -1 at center, 1 at edge
    y -= (1 - Math.abs(craterShape)) * craterRimDepth
  } else if (distanceToCrater < craterRadius + 8) {
    // Crater rim peak
    const rimDist = (distanceToCrater - craterRadius) / 8
    y += (1 - rimDist) * 3 // 3 units high rim
  }

  return y
}

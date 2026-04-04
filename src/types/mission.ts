// Core mission weight types for the 4D Cost Model
export interface MissionWeights {
  distance: number;    // W_d: Euclidean Distance
  slope: number;       // W_e: Asymmetric Slope (Energy)
  roughness: number;   // W_s: Regolith Roughness (Surface)
  shadow: number;      // W_g: Shadow/Thermal (Gamma)
}

export interface MissionProfile {
  id: 'optimal' | 'shortest' | 'thermal' | 'custom';
  name: string;
  description: string;
  weights: MissionWeights;
  color: string;
  glowColor: string;
}

export interface SimulationState {
  status: 'idle' | 'initializing' | 'loading_dem' | 'acquiring_waypoints' | 'computing' | 'optimized' | 'error';
  progress: number;
  activeProfile: MissionProfile['id'];
  calculatedCost: number | null;
  pathData: PathSegment[] | null;
}

export interface PathSegment {
  id: string;
  points: Array<{ x: number; y: number; z: number }>;
  cost: number;
  profile: MissionProfile['id'];
}

export interface WeightSliderConfig {
  key: keyof MissionWeights;
  label: string;
  symbol: string;
  min: number;
  max: number;
  step: number;
  color: string;
  glowClass: string;
}

// Preset mission profiles with optimized weights
export const MISSION_PRESETS: Record<Exclude<MissionProfile['id'], 'custom'>, Omit<MissionProfile, 'name' | 'description'>> = {
  optimal: {
    id: 'optimal',
    weights: { distance: 1.4, slope: 4.0, roughness: 1.6, shadow: 0.22 },
    color: 'neon-orange',
    glowColor: 'rgba(255, 165, 0, 0.5)',
  },
  shortest: {
    id: 'shortest',
    weights: { distance: 9.5, slope: 0.25, roughness: 0.05, shadow: 0.01 },
    color: 'neon-cyan',
    glowColor: 'rgba(0, 255, 255, 0.5)',
  },
  thermal: {
    id: 'thermal',
    weights: { distance: 0.9, slope: 1.2, roughness: 0.56, shadow: 6.5 },
    color: 'neon-magenta',
    glowColor: 'rgba(255, 0, 255, 0.5)',
  },
};

export const WEIGHT_SLIDER_CONFIG: WeightSliderConfig[] = [
  { key: 'distance', label: 'Distance', symbol: 'W_d', min: 0, max: 10, step: 0.1, color: '#00ffff', glowClass: 'shadow-[0_0_15px_rgba(0,255,255,0.6)]' },
  { key: 'slope', label: 'Slope', symbol: 'W_e', min: 0, max: 10, step: 0.1, color: '#ffa500', glowClass: 'shadow-[0_0_15px_rgba(255,165,0,0.6)]' },
  { key: 'roughness', label: 'Roughness', symbol: 'W_s', min: 0, max: 10, step: 0.1, color: '#ff00ff', glowClass: 'shadow-[0_0_15px_rgba(255,0,255,0.6)]' },
  { key: 'shadow', label: 'Shadow', symbol: 'W_g', min: 0, max: 10, step: 0.1, color: '#00ff00', glowClass: 'shadow-[0_0_15px_rgba(0,255,0,0.6)]' },
];

// Calculate total cost based on weights (simulation formula)
export function calculateTotalCost(weights: MissionWeights, terrain: { d: number; e: number; s: number; g: number }): number {
  return Math.round(
    (weights.distance * terrain.d +
      weights.slope * terrain.e +
      weights.roughness * terrain.s +
      weights.shadow * terrain.g) * 1000
  );
}

import { createContext, useContext, useReducer, useCallback, useRef, type ReactNode } from 'react';
import type { MissionWeights, MissionProfile, SimulationState } from '../types/mission';
import { MISSION_PRESETS } from '../types/mission';

// ============================================================================
// STATE TYPES
// ============================================================================

// Profile-specific simulation results
interface ProfileSimulationData {
  cost: number;
  pathLength: string;
  totalNodes: string;
  computeTime: string;
}

const PROFILE_DATA: Record<string, ProfileSimulationData> = {
  optimal: {
    cost: 590502,
    pathLength: '2.4 km',
    totalNodes: '48,291',
    computeTime: '1.2s',
  },
  shortest: {
    cost: 1024103,
    pathLength: '1.8 km',
    totalNodes: '31,450',
    computeTime: '0.8s',
  },
  thermal: {
    cost: 890200,
    pathLength: '3.1 km',
    totalNodes: '62,108',
    computeTime: '1.8s',
  },
  custom: {
    cost: 750000,
    pathLength: '2.6 km',
    totalNodes: '52,000',
    computeTime: '1.4s',
  },
};

interface MissionContextState {
  weights: MissionWeights;
  activeProfileId: MissionProfile['id'];
  simulation: SimulationState;
  isAnimating: boolean;
  profileData: ProfileSimulationData;
}

type MissionAction =
  | { type: 'SET_WEIGHT'; payload: { key: keyof MissionWeights; value: number } }
  | { type: 'SET_ALL_WEIGHTS'; payload: MissionWeights }
  | { type: 'SELECT_PROFILE'; payload: MissionProfile['id'] }
  | { type: 'SET_SIMULATION_STATUS'; payload: SimulationState['status'] }
  | { type: 'SET_SIMULATION_PROGRESS'; payload: number }
  | { type: 'SET_CALCULATED_COST'; payload: number }
  | { type: 'SET_ANIMATING'; payload: boolean }
  | { type: 'SET_PROFILE_DATA'; payload: ProfileSimulationData }
  | { type: 'RESET_SIMULATION' };

interface MissionContextValue extends MissionContextState {
  setWeight: (key: keyof MissionWeights, value: number) => void;
  selectProfile: (profileId: MissionProfile['id']) => void;
  runSimulation: () => Promise<void>;
  resetSimulation: () => void;
  getActiveProfile: () => MissionProfile | null;
}

// ============================================================================
// INITIAL STATE
// ============================================================================

const initialState: MissionContextState = {
  weights: MISSION_PRESETS.optimal.weights,
  activeProfileId: 'optimal',
  simulation: {
    status: 'idle',
    progress: 0,
    activeProfile: 'optimal',
    calculatedCost: null,
    pathData: null,
  },
  isAnimating: false,
  profileData: PROFILE_DATA.optimal,
};

// ============================================================================
// REDUCER
// ============================================================================

function missionReducer(state: MissionContextState, action: MissionAction): MissionContextState {
  switch (action.type) {
    case 'SET_WEIGHT': {
      const newWeights = { ...state.weights, [action.payload.key]: action.payload.value };
      // Check if weights match any preset
      const matchingProfile = Object.entries(MISSION_PRESETS).find(([_, preset]) => 
        Object.keys(newWeights).every(
          key => Math.abs(newWeights[key as keyof MissionWeights] - preset.weights[key as keyof MissionWeights]) < 0.01
        )
      );
      const newProfileId = matchingProfile ? (matchingProfile[0] as MissionProfile['id']) : 'custom';
      return {
        ...state,
        weights: newWeights,
        activeProfileId: newProfileId,
        profileData: PROFILE_DATA[newProfileId] || PROFILE_DATA.custom,
      };
    }

    case 'SET_ALL_WEIGHTS':
      return {
        ...state,
        weights: action.payload,
      };

    case 'SELECT_PROFILE': {
      if (action.payload === 'custom') return state;
      const preset = MISSION_PRESETS[action.payload];
      return {
        ...state,
        weights: preset.weights,
        activeProfileId: action.payload,
        profileData: PROFILE_DATA[action.payload],
      };
    }

    case 'SET_SIMULATION_STATUS':
      return {
        ...state,
        simulation: { ...state.simulation, status: action.payload },
      };

    case 'SET_SIMULATION_PROGRESS':
      return {
        ...state,
        simulation: { ...state.simulation, progress: action.payload },
      };

    case 'SET_CALCULATED_COST':
      return {
        ...state,
        simulation: { ...state.simulation, calculatedCost: action.payload },
      };

    case 'SET_ANIMATING':
      return {
        ...state,
        isAnimating: action.payload,
      };

    case 'SET_PROFILE_DATA':
      return {
        ...state,
        profileData: action.payload,
      };

    case 'RESET_SIMULATION':
      return {
        ...state,
        simulation: { ...initialState.simulation, activeProfile: state.activeProfileId },
      };

    default:
      return state;
  }
}

// ============================================================================
// CONTEXT
// ============================================================================

const MissionContext = createContext<MissionContextValue | undefined>(undefined);

// ============================================================================
// PROVIDER
// ============================================================================

export function MissionProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(missionReducer, initialState);
  const isSimulatingRef = useRef(false);

  const runSimulationInternal = useCallback(async (profileId: MissionProfile['id'], weights: MissionWeights) => {
    if (isSimulatingRef.current) return;
    isSimulatingRef.current = true;
    
    dispatch({ type: 'RESET_SIMULATION' });
    
    const stages: Array<{ status: SimulationState['status']; delay: number; progress: number }> = [
      { status: 'initializing', delay: 400, progress: 10 },
      { status: 'loading_dem', delay: 600, progress: 30 },
      { status: 'acquiring_waypoints', delay: 500, progress: 50 },
      { status: 'computing', delay: 800, progress: 80 },
      { status: 'optimized', delay: 300, progress: 100 },
    ];

    for (const stage of stages) {
      dispatch({ type: 'SET_SIMULATION_STATUS', payload: stage.status });
      dispatch({ type: 'SET_SIMULATION_PROGRESS', payload: stage.progress });
      await new Promise(resolve => setTimeout(resolve, stage.delay));
    }

    // Get profile-specific data or calculate custom
    const data = PROFILE_DATA[profileId] || PROFILE_DATA.custom;
    
    // Calculate cost based on weights for custom profiles
    let finalCost = data.cost;
    if (profileId === 'custom') {
      const baseCost = 500000;
      const costModifier = (weights.distance * 0.15 + weights.slope * 0.08 + weights.roughness * 0.05 + weights.shadow * 0.02);
      finalCost = Math.round(baseCost + costModifier * 50000);
    }
    
    dispatch({ type: 'SET_CALCULATED_COST', payload: finalCost });
    dispatch({ type: 'SET_PROFILE_DATA', payload: { ...data, cost: finalCost } });
    
    isSimulatingRef.current = false;
  }, []);

  const setWeight = useCallback((key: keyof MissionWeights, value: number) => {
    dispatch({ type: 'SET_WEIGHT', payload: { key, value } });
  }, []);

  const selectProfile = useCallback((profileId: MissionProfile['id']) => {
    dispatch({ type: 'SET_ANIMATING', payload: true });
    dispatch({ type: 'SELECT_PROFILE', payload: profileId });
    
    // Get the new weights for this profile
    const newWeights = profileId !== 'custom' ? MISSION_PRESETS[profileId].weights : state.weights;
    
    // Allow animation to complete, then run simulation
    setTimeout(() => {
      dispatch({ type: 'SET_ANIMATING', payload: false });
      // Auto-run simulation when profile changes
      runSimulationInternal(profileId, newWeights);
    }, 600);
  }, [runSimulationInternal, state.weights]);

  const runSimulation = useCallback(async () => {
    await runSimulationInternal(state.activeProfileId, state.weights);
  }, [runSimulationInternal, state.activeProfileId, state.weights]);

  const resetSimulation = useCallback(() => {
    dispatch({ type: 'RESET_SIMULATION' });
  }, []);

  const getActiveProfile = useCallback((): MissionProfile | null => {
    if (state.activeProfileId === 'custom') return null;
    const preset = MISSION_PRESETS[state.activeProfileId];
    return {
      ...preset,
      name: state.activeProfileId,
      description: '',
    };
  }, [state.activeProfileId]);

  const value: MissionContextValue = {
    ...state,
    setWeight,
    selectProfile,
    runSimulation,
    resetSimulation,
    getActiveProfile,
  };

  return (
    <MissionContext.Provider value={value}>
      {children}
    </MissionContext.Provider>
  );
}

// ============================================================================
// HOOK
// ============================================================================

export function useMission(): MissionContextValue {
  const context = useContext(MissionContext);
  if (!context) {
    throw new Error('useMission must be used within a MissionProvider');
  }
  return context;
}

// Export profile data for use in other components
export { PROFILE_DATA };

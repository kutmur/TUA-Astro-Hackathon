import { useRef, useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Radar, Cpu, MapPin, CheckCircle2, Route, Clock, Hash } from 'lucide-react';
import { useMission } from '../context/MissionContext';
import { useLanguage } from '../context/LanguageContext';
import { Card } from './ui/card';

// ============================================================================
// TYPES
// ============================================================================

interface PathPoint {
  x: number;
  y: number;
}

interface SimulatedPath {
  id: string;
  points: PathPoint[];
  color: string;
  dashArray?: string;
  isActive: boolean;
}

// ============================================================================
// RADAR CANVAS COMPONENT
// ============================================================================

function RadarCanvas({ isScanning }: { isScanning: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const angleRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const maxRadius = Math.min(centerX, centerY) - 10;

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw concentric circles
      for (let i = 1; i <= 4; i++) {
        const radius = (maxRadius / 4) * i;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(0, 255, 255, ${0.1 + i * 0.05})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Draw cross lines
      ctx.beginPath();
      ctx.moveTo(centerX, centerY - maxRadius);
      ctx.lineTo(centerX, centerY + maxRadius);
      ctx.moveTo(centerX - maxRadius, centerY);
      ctx.lineTo(centerX + maxRadius, centerY);
      ctx.strokeStyle = 'rgba(0, 255, 255, 0.15)';
      ctx.stroke();

      // Draw diagonal lines
      ctx.beginPath();
      ctx.moveTo(centerX - maxRadius * 0.7, centerY - maxRadius * 0.7);
      ctx.lineTo(centerX + maxRadius * 0.7, centerY + maxRadius * 0.7);
      ctx.moveTo(centerX + maxRadius * 0.7, centerY - maxRadius * 0.7);
      ctx.lineTo(centerX - maxRadius * 0.7, centerY + maxRadius * 0.7);
      ctx.strokeStyle = 'rgba(0, 255, 255, 0.1)';
      ctx.stroke();

      if (isScanning) {
        // Draw sweep line with gradient
        const gradient = ctx.createLinearGradient(
          centerX,
          centerY,
          centerX + Math.cos(angleRef.current) * maxRadius,
          centerY + Math.sin(angleRef.current) * maxRadius
        );
        gradient.addColorStop(0, 'rgba(0, 255, 255, 0.8)');
        gradient.addColorStop(1, 'rgba(0, 255, 255, 0)');

        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(
          centerX + Math.cos(angleRef.current) * maxRadius,
          centerY + Math.sin(angleRef.current) * maxRadius
        );
        ctx.strokeStyle = gradient;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw sweep cone
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, maxRadius, angleRef.current - 0.5, angleRef.current, false);
        ctx.closePath();
        const coneGradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, maxRadius);
        coneGradient.addColorStop(0, 'rgba(0, 255, 255, 0.15)');
        coneGradient.addColorStop(1, 'rgba(0, 255, 255, 0)');
        ctx.fillStyle = coneGradient;
        ctx.fill();

        angleRef.current += 0.03;
      }

      // Draw center dot
      ctx.beginPath();
      ctx.arc(centerX, centerY, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#00ffff';
      ctx.fill();
      ctx.beginPath();
      ctx.arc(centerX, centerY, 8, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(0, 255, 255, 0.5)';
      ctx.lineWidth = 1;
      ctx.stroke();

      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animationRef.current);
    };
  }, [isScanning]);

  return (
    <canvas
      ref={canvasRef}
      width={400}
      height={400}
      className="absolute inset-0 w-full h-full opacity-60"
    />
  );
}

// ============================================================================
// SIMULATED PATH OVERLAY
// ============================================================================

function PathOverlay({ paths, animationKey }: { paths: SimulatedPath[]; animationKey: number }) {
  return (
    <svg className="absolute inset-0 w-full h-full" viewBox="0 0 400 400" key={animationKey}>
      <defs>
        {paths.map((path) => (
          <filter key={`glow-${path.id}`} id={`glow-${path.id}-${animationKey}`}>
            <feGaussianBlur stdDeviation={path.isActive ? "4" : "2"} result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        ))}
      </defs>
      
      {paths.map((path, index) => {
        const pathD = path.points.reduce((acc, point, i) => {
          return acc + (i === 0 ? `M ${point.x} ${point.y}` : ` L ${point.x} ${point.y}`);
        }, '');

        return (
          <motion.path
            key={`${path.id}-${animationKey}`}
            d={pathD}
            fill="none"
            stroke={path.color}
            strokeWidth={path.isActive ? 4 : 2}
            strokeDasharray={path.dashArray}
            filter={`url(#glow-${path.id}-${animationKey})`}
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ 
              pathLength: 1, 
              opacity: path.isActive ? 1 : 0.35,
            }}
            transition={{ 
              duration: 1.5, 
              delay: path.isActive ? 0 : index * 0.3,
              ease: "easeInOut",
            }}
          />
        );
      })}

      {/* Waypoint markers */}
      <motion.circle
        cx="80"
        cy="320"
        r="8"
        fill="#00ff00"
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.5, type: "spring" }}
      />
      <motion.circle
        cx="320"
        cy="80"
        r="8"
        fill="#ff0000"
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.7, type: "spring" }}
      />
      
      {/* Labels */}
      <motion.text
        x="80"
        y="345"
        textAnchor="middle"
        fill="#00ff00"
        fontSize="10"
        fontFamily="monospace"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
      >
        START
      </motion.text>
      <motion.text
        x="320"
        y="65"
        textAnchor="middle"
        fill="#ff0000"
        fontSize="10"
        fontFamily="monospace"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
      >
        TARGET
      </motion.text>
    </svg>
  );
}

// ============================================================================
// LOADING OVERLAY
// ============================================================================

function LoadingOverlay({ status, progress }: { status: string; progress: number }) {
  const { t } = useLanguage();
  
  const statusMessages: Record<string, string> = {
    initializing: t('simInit'),
    loading_dem: t('simLoaded'),
    acquiring_waypoints: t('simAcquired'),
    computing: t('simComputing'),
    optimized: t('simOptimized'),
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 bg-[rgba(2,6,23,0.9)] backdrop-blur-sm flex flex-col items-center justify-center z-20"
    >
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        className="mb-6"
      >
        <Cpu className="w-16 h-16 text-neon-cyan" />
      </motion.div>
      
      <div className="text-center space-y-4">
        <motion.h3
          className="text-xl font-bold text-neon-cyan font-mono"
          animate={{ opacity: [1, 0.5, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          {t('recalculatingPath')}
        </motion.h3>
        
        <p className="text-sm text-[#cbd5e1] font-mono">
          {statusMessages[status] || status}
        </p>
        
        {/* Progress bar */}
        <div className="w-64 h-2 bg-[#1e293b] rounded-full overflow-hidden border border-[#393939]">
          <motion.div
            className="h-full bg-gradient-to-r from-neon-cyan to-neon-green"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
            style={{ boxShadow: '0 0 10px rgba(0, 255, 255, 0.5)' }}
          />
        </div>
        
        <p className="text-xs text-[#64748b] font-mono">
          {progress < 50 ? t('processingNodes') : t('evaluatingCost')}
        </p>
      </div>
    </motion.div>
  );
}

// ============================================================================
// COMPLETION OVERLAY
// ============================================================================

function CompletionOverlay({ cost, profileId }: { cost: number; profileId: string }) {
  const { t } = useLanguage();
  
  const getProfileStyle = () => {
    switch (profileId) {
      case 'optimal': return { border: 'border-[#ffa500]/50', bg: 'bg-[rgba(255,165,0,0.1)]', text: 'text-[#ffa500]' };
      case 'shortest': return { border: 'border-[#00ffff]/50', bg: 'bg-[rgba(0,255,255,0.1)]', text: 'text-[#00ffff]' };
      case 'thermal': return { border: 'border-[#ff00ff]/50', bg: 'bg-[rgba(255,0,255,0.1)]', text: 'text-[#ff00ff]' };
      default: return { border: 'border-[#00ff00]/50', bg: 'bg-[rgba(0,255,0,0.1)]', text: 'text-[#00ff00]' };
    }
  };
  
  const style = getProfileStyle();
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="absolute bottom-4 left-4 right-4 z-20"
    >
      <div className={`backdrop-blur-lg border rounded-lg p-4 ${style.border} ${style.bg}`}>
        <div className="flex items-center gap-3">
          <CheckCircle2 className={`w-6 h-6 ${style.text}`} />
          <div className="flex-1">
            <p className={`text-sm font-bold ${style.text}`}>{t('optimalRouteFound')}</p>
            <p className="text-xs text-[#cbd5e1]">{t('analysisComplete')}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-[#64748b] uppercase">{t('costLabel')}</p>
            <p className={`text-lg font-mono font-bold ${style.text}`}>{cost.toLocaleString()}</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ============================================================================
// STATS PANEL
// ============================================================================

function StatsPanel({ isComplete, profileData }: { 
  isComplete: boolean; 
  profileData: { pathLength: string; totalNodes: string; computeTime: string } 
}) {
  const { t } = useLanguage();
  
  const stats = [
    { icon: Hash, label: t('totalNodes'), value: profileData.totalNodes, color: 'text-neon-cyan' },
    { icon: Route, label: t('pathLength'), value: profileData.pathLength, color: 'text-neon-orange' },
    { icon: Clock, label: t('computeTime'), value: profileData.computeTime, color: 'text-neon-magenta' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: isComplete ? 1 : 0, y: isComplete ? 0 : 20 }}
      transition={{ duration: 0.5 }}
      className="absolute top-4 right-4 z-10"
    >
      <div className="bg-[rgba(0,0,0,0.6)] backdrop-blur-sm border border-[#393939] rounded-lg p-3 space-y-2">
        {stats.map((stat, i) => (
          <motion.div 
            key={`${stat.label}-${profileData.pathLength}`}
            className="flex items-center gap-2 text-xs"
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <stat.icon className={`w-3 h-3 ${stat.color}`} />
            <span className="text-[#64748b]">{stat.label}:</span>
            <span className={`font-mono font-bold ${stat.color}`}>{stat.value}</span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function SimulationVisualizer() {
  const { t } = useLanguage();
  const { simulation, activeProfileId, profileData, runSimulation } = useMission();
  const [paths, setPaths] = useState<SimulatedPath[]>([]);
  const [animationKey, setAnimationKey] = useState(0);
  
  const isIdle = simulation.status === 'idle';
  const isRunning = ['initializing', 'loading_dem', 'acquiring_waypoints', 'computing'].includes(simulation.status);
  const isComplete = simulation.status === 'optimized';

  // Generate paths with active profile highlighted
  const generatePaths = useCallback((currentProfileId: string) => {
    const basePaths: SimulatedPath[] = [
      {
        id: 'optimal',
        color: '#ffa500',
        points: generateCurvedPath(80, 320, 320, 80, 25, 3),
        isActive: currentProfileId === 'optimal',
      },
      {
        id: 'shortest',
        color: '#00ffff',
        dashArray: '10,5',
        points: generateStraightPath(80, 320, 320, 80),
        isActive: currentProfileId === 'shortest',
      },
      {
        id: 'thermal',
        color: '#ff00ff',
        dashArray: '5,5',
        points: generateCurvedPath(80, 320, 320, 80, -40, 5),
        isActive: currentProfileId === 'thermal',
      },
    ];
    
    // Sort so active path renders last (on top)
    basePaths.sort((a, b) => (a.isActive ? 1 : 0) - (b.isActive ? 1 : 0));
    
    setPaths(basePaths);
    setAnimationKey(prev => prev + 1);
  }, []);

  // Regenerate paths when simulation completes
  useEffect(() => {
    if (isComplete) {
      generatePaths(activeProfileId);
    }
  }, [isComplete, activeProfileId, generatePaths]);

  const handleClick = () => {
    if (isIdle || isComplete) {
      runSimulation();
    }
  };

  // Get profile color for footer
  const getProfileColor = () => {
    switch (activeProfileId) {
      case 'optimal': return 'text-[#ffa500]';
      case 'shortest': return 'text-[#00ffff]';
      case 'thermal': return 'text-[#ff00ff]';
      default: return 'text-white';
    }
  };

  return (
    <Card className="p-0 overflow-hidden bg-[rgba(255,255,255,0.02)] border-[0.5px] border-[#393939] backdrop-blur-xl">
      {/* Header */}
      <div className="px-6 py-4 border-b border-[#393939] bg-[rgba(0,0,0,0.3)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-br from-neon-cyan/20 to-neon-magenta/20 border border-[#393939]">
              <Radar className="w-5 h-5 text-neon-cyan" />
            </div>
            <div>
              <h3 className="font-semibold text-[#f8fafc] tracking-tight">
                {t('simulatorTitle')}
              </h3>
              <p className="text-xs text-[#64748b]">
                {t('simulatorSubtitle')}
              </p>
            </div>
          </div>
          
          {/* Status indicator */}
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-neon-orange animate-pulse' : isComplete ? 'bg-neon-green' : 'bg-[#393939]'}`} />
            <span className="text-xs font-mono text-[#64748b]">
              {isRunning ? 'PROCESSING' : isComplete ? 'COMPLETE' : 'READY'}
            </span>
          </div>
        </div>
      </div>
      
      {/* Visualization Area */}
      <div 
        className="relative aspect-square cursor-pointer group"
        onClick={handleClick}
      >
        {/* Background grid pattern */}
        <div className="absolute inset-0 bg-[radial-gradient(rgba(0,255,255,0.03)_1px,_transparent_1px)] [background-size:20px_20px]" />
        
        {/* Crater background image placeholder */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#0a0a0a] via-[#1a1a2e] to-[#0a0a0a]">
          {/* Simulated topography gradient */}
          <div className="absolute inset-0 opacity-30">
            <div className="absolute top-1/4 left-1/4 w-1/2 h-1/2 rounded-full bg-gradient-radial from-[#1e293b] to-transparent" />
            <div className="absolute top-1/3 right-1/4 w-1/3 h-1/3 rounded-full bg-gradient-radial from-[#334155] to-transparent opacity-50" />
          </div>
        </div>
        
        {/* Radar canvas */}
        <RadarCanvas isScanning={isRunning || isComplete} />
        
        {/* Path overlay */}
        {isComplete && paths.length > 0 && (
          <PathOverlay paths={paths} animationKey={animationKey} />
        )}
        
        {/* Stats panel */}
        <StatsPanel isComplete={isComplete} profileData={profileData} />
        
        {/* Loading overlay */}
        <AnimatePresence>
          {isRunning && (
            <LoadingOverlay status={simulation.status} progress={simulation.progress} />
          )}
        </AnimatePresence>
        
        {/* Completion overlay */}
        <AnimatePresence>
          {isComplete && simulation.calculatedCost && (
            <CompletionOverlay cost={simulation.calculatedCost} profileId={activeProfileId} />
          )}
        </AnimatePresence>
        
        {/* Idle state prompt */}
        {isIdle && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute inset-0 flex items-center justify-center"
          >
            <div className="text-center space-y-4 group-hover:scale-105 transition-transform">
              <motion.div
                animate={{ y: [0, -5, 0] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <MapPin className="w-12 h-12 text-neon-cyan mx-auto" />
              </motion.div>
              <p className="text-sm text-[#cbd5e1] font-mono">
                {t('clickToStart')}
              </p>
            </div>
          </motion.div>
        )}
        
        {/* Corner decorations */}
        <div className="absolute top-2 left-2 w-4 h-4 border-t-2 border-l-2 border-neon-cyan/50" />
        <div className="absolute top-2 right-2 w-4 h-4 border-t-2 border-r-2 border-neon-cyan/50" />
        <div className="absolute bottom-2 left-2 w-4 h-4 border-b-2 border-l-2 border-neon-cyan/50" />
        <div className="absolute bottom-2 right-2 w-4 h-4 border-b-2 border-r-2 border-neon-cyan/50" />
      </div>
      
      {/* Footer */}
      <div className="px-6 py-3 border-t border-[#393939] bg-[rgba(0,0,0,0.2)]">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-[#64748b]">
            {t('simStatusLabel')} <span className={isComplete ? 'text-neon-green' : 'text-neon-cyan'}>{
              isRunning ? t('simComputing') : isComplete ? t('simOptimized') : t('simIdle')
            }</span>
          </span>
          <span className="text-[#64748b]">
            Profile: <span className={getProfileColor()}>
              {activeProfileId.toUpperCase()}
            </span>
          </span>
        </div>
      </div>
    </Card>
  );
}

// ============================================================================
// PATH GENERATION HELPERS
// ============================================================================

function generateCurvedPath(
  startX: number, startY: number, 
  endX: number, endY: number, 
  curvature: number, variance: number
): PathPoint[] {
  const points: PathPoint[] = [];
  const steps = 50;
  
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const x = startX + (endX - startX) * t;
    const y = startY + (endY - startY) * t;
    
    // Add curvature with deterministic noise
    const deviation = Math.sin(t * Math.PI) * curvature;
    const noise = Math.sin(i * 0.7) * variance;
    
    points.push({
      x: x + deviation + noise,
      y: y - deviation + noise,
    });
  }
  
  return points;
}

function generateStraightPath(
  startX: number, startY: number, 
  endX: number, endY: number
): PathPoint[] {
  const points: PathPoint[] = [];
  const steps = 50;
  
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    points.push({
      x: startX + (endX - startX) * t,
      y: startY + (endY - startY) * t,
    });
  }
  
  return points;
}

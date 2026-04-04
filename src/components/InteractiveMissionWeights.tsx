import { useCallback, useRef, useEffect, useState, type ReactElement } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';
import { Sliders, Zap, Mountain, Sun, Ruler } from 'lucide-react';
import { useMission } from '../context/MissionContext';
import { useLanguage } from '../context/LanguageContext';
import { WEIGHT_SLIDER_CONFIG, MISSION_PRESETS } from '../types/mission';
import type { MissionWeights, MissionProfile } from '../types/mission';
import { Card } from './ui/card';

// ============================================================================
// ANIMATED SLIDER COMPONENT
// ============================================================================

interface AnimatedSliderProps {
  label: string;
  symbol: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step: number;
  color: string;
  glowClass: string;
  isAnimating: boolean;
}

function AnimatedSlider({
  label,
  symbol,
  value,
  onChange,
  min,
  max,
  step,
  color,
  glowClass,
  isAnimating,
}: AnimatedSliderProps) {
  const sliderRef = useRef<HTMLInputElement>(null);
  const springValue = useSpring(value, { damping: 20, stiffness: 300 });
  const displayValue = useTransform(springValue, (v) => v.toFixed(2));
  
  // Sync spring with external value changes (for preset animations)
  useEffect(() => {
    springValue.set(value);
  }, [value, springValue]);

  const percentage = ((value - min) / (max - min)) * 100;

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseFloat(e.target.value);
    onChange(newValue);
  }, [onChange]);

  const iconMap: Record<string, ReactElement> = {
    W_d: <Ruler className="w-4 h-4" style={{ color }} />,
    W_e: <Mountain className="w-4 h-4" style={{ color }} />,
    W_s: <Zap className="w-4 h-4" style={{ color }} />,
    W_g: <Sun className="w-4 h-4" style={{ color }} />,
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {iconMap[symbol]}
          <span className="text-sm font-medium text-[#f8fafc]">{label}</span>
          <span className="text-xs font-mono text-[#64748b]">({symbol})</span>
        </div>
        <motion.span 
          className="font-mono text-sm font-bold tabular-nums"
          style={{ color }}
        >
          {displayValue}
        </motion.span>
      </div>
      
      <div className="relative h-3 group">
        {/* Track Background */}
        <div className="absolute inset-0 bg-[#1e293b] rounded-full border border-[#393939]" />
        
        {/* Filled Track */}
        <motion.div
          className={`absolute top-0 left-0 h-full rounded-full transition-shadow duration-300 group-hover:${glowClass}`}
          style={{ 
            backgroundColor: color,
            width: `${percentage}%`,
            boxShadow: `0 0 10px ${color}40`,
          }}
          animate={{ width: `${percentage}%` }}
          transition={{ type: 'spring', damping: 20, stiffness: 300 }}
        />
        
        {/* Thumb Glow Effect */}
        <motion.div
          className="absolute top-1/2 -translate-y-1/2 w-5 h-5 rounded-full pointer-events-none"
          style={{
            left: `calc(${percentage}% - 10px)`,
            background: `radial-gradient(circle, ${color}60 0%, transparent 70%)`,
          }}
          animate={{ 
            scale: isAnimating ? [1, 1.5, 1] : 1,
            opacity: isAnimating ? [0.5, 1, 0.5] : 0.8,
          }}
          transition={{ duration: 0.6, repeat: isAnimating ? Infinity : 0 }}
        />
        
        {/* Invisible Native Slider */}
        <input
          ref={sliderRef}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={handleChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
          disabled={isAnimating}
        />
      </div>
    </div>
  );
}

// ============================================================================
// PROFILE PRESET BUTTON
// ============================================================================

interface ProfileButtonProps {
  profileId: Exclude<MissionProfile['id'], 'custom'>;
  isActive: boolean;
  onClick: () => void;
  name: string;
  color: string;
}

function ProfileButton({ profileId, isActive, onClick, name, color }: ProfileButtonProps) {
  const preset = MISSION_PRESETS[profileId];
  
  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`
        relative flex-1 px-4 py-3 rounded-xl border transition-all duration-300
        backdrop-blur-sm overflow-hidden group
        ${isActive 
          ? `border-${color}/60 bg-${color}/10` 
          : 'border-[#393939] bg-[rgba(255,255,255,0.02)] hover:bg-[rgba(255,255,255,0.04)]'
        }
      `}
      style={{
        borderColor: isActive ? preset.glowColor : undefined,
        boxShadow: isActive ? `0 0 20px ${preset.glowColor}` : undefined,
      }}
    >
      {/* Animated Background Gradient */}
      <motion.div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity"
        style={{
          background: `radial-gradient(circle at 50% 50%, ${preset.glowColor}20, transparent 70%)`,
        }}
      />
      
      <div className="relative z-10">
        <div className={`text-xs font-bold uppercase tracking-wider mb-1`} style={{ color: isActive ? preset.glowColor : '#94a3b8' }}>
          {name}
        </div>
        <div className="flex justify-center gap-2 text-[10px] font-mono text-[#64748b]">
          <span>D:{preset.weights.distance.toFixed(1)}</span>
          <span>E:{preset.weights.slope.toFixed(1)}</span>
          <span>S:{preset.weights.roughness.toFixed(1)}</span>
          <span>G:{preset.weights.shadow.toFixed(2)}</span>
        </div>
      </div>
      
      {/* Active Indicator */}
      {isActive && (
        <motion.div
          layoutId="activeIndicator"
          className="absolute bottom-0 left-0 right-0 h-0.5"
          style={{ backgroundColor: preset.glowColor }}
        />
      )}
    </motion.button>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function InteractiveMissionWeights() {
  const { t } = useLanguage();
  const { weights, activeProfileId, isAnimating, setWeight, selectProfile } = useMission();
  const [hoveredSlider, setHoveredSlider] = useState<keyof MissionWeights | null>(null);

  const sliderLabelMap: Record<string, string> = {
    distance: t('varDName'),
    slope: t('varEName'),
    roughness: t('varSName'),
    shadow: t('varGName'),
  };

  const profileNameMap: Record<string, string> = {
    optimal: t('profOptimalName'),
    shortest: t('profShortestName'),
    thermal: t('profThermalName'),
  };

  return (
    <Card className="p-0 overflow-hidden bg-[rgba(255,255,255,0.02)] border-[0.5px] border-[#393939] backdrop-blur-xl">
      {/* Header */}
      <div className="px-6 py-4 border-b border-[#393939] bg-[rgba(0,0,0,0.3)]">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-br from-neon-cyan/20 to-neon-orange/20 border border-[#393939]">
            <Sliders className="w-5 h-5 text-neon-cyan" />
          </div>
          <div>
            <h3 className="font-semibold text-[#f8fafc] tracking-tight">
              {t('missionControlTitle')}
            </h3>
            <p className="text-xs text-[#64748b]">
              {t('missionControlDesc')}
            </p>
          </div>
        </div>
      </div>
      
      {/* Profile Presets */}
      <div className="px-6 py-4 border-b border-[#393939]">
        <div className="flex gap-3">
          {(['optimal', 'shortest', 'thermal'] as const).map((profileId) => (
            <ProfileButton
              key={profileId}
              profileId={profileId}
              isActive={activeProfileId === profileId}
              onClick={() => selectProfile(profileId)}
              name={profileNameMap[profileId]}
              color={MISSION_PRESETS[profileId].color}
            />
          ))}
        </div>
      </div>
      
      {/* Sliders */}
      <div className="px-6 py-6 space-y-6">
        {WEIGHT_SLIDER_CONFIG.map((config) => (
          <div
            key={config.key}
            onMouseEnter={() => setHoveredSlider(config.key)}
            onMouseLeave={() => setHoveredSlider(null)}
          >
            <AnimatedSlider
              label={sliderLabelMap[config.key]}
              symbol={config.symbol}
              value={weights[config.key]}
              onChange={(value) => setWeight(config.key, value)}
              min={config.min}
              max={config.max}
              step={config.step}
              color={config.color}
              glowClass={config.glowClass}
              isAnimating={isAnimating && hoveredSlider !== config.key}
            />
          </div>
        ))}
      </div>
      
      {/* Live Cost Preview */}
      <div className="px-6 py-4 border-t border-[#393939] bg-[rgba(0,0,0,0.2)]">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono text-[#64748b] uppercase tracking-wider">
            {t('liveCostPreview')}
          </span>
          <motion.div 
            className="font-mono font-bold text-neon-cyan"
            animate={{ 
              textShadow: isAnimating 
                ? ['0 0 10px rgba(0,255,255,0.8)', '0 0 20px rgba(0,255,255,0.4)', '0 0 10px rgba(0,255,255,0.8)'] 
                : '0 0 10px rgba(0,255,255,0.4)',
            }}
            transition={{ duration: 0.5, repeat: isAnimating ? Infinity : 0 }}
          >
            C<sub>total</sub> = {Math.round(
              (weights.distance * 150 + weights.slope * 80 + weights.roughness * 50 + weights.shadow * 200) * 1000
            ).toLocaleString()}
          </motion.div>
        </div>
      </div>
    </Card>
  );
}

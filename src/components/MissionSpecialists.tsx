import { motion } from 'framer-motion';
import { Rocket, Code2, Database } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { Card } from './ui/card';

// GitHub icon component (lucide-react exports it as 'GitHub' in some versions)
function GithubIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
    </svg>
  );
}

// ============================================================================
// TYPES
// ============================================================================

interface TeamMember {
  id: string;
  name: string;
  github: string;
  avatarUrl: string;
  roleKey: 'teamRole1' | 'teamRole2' | 'teamRole3';
  icon: typeof Rocket;
  gradient: string;
  glowColor: string;
}

// ============================================================================
// TEAM DATA
// ============================================================================

const TEAM_MEMBERS: TeamMember[] = [
  {
    id: 'kutmur',
    name: 'kutmur',
    github: 'https://github.com/kutmur',
    avatarUrl: 'https://github.com/kutmur.png',
    roleKey: 'teamRole1',
    icon: Rocket,
    gradient: 'from-neon-orange to-neon-magenta',
    glowColor: 'rgba(255, 165, 0, 0.3)',
  },
  {
    id: 'aliandacerdass',
    name: 'aliandacerdass',
    github: 'https://github.com/aliandacerdass',
    avatarUrl: 'https://github.com/aliandacerdass.png',
    roleKey: 'teamRole2',
    icon: Code2,
    gradient: 'from-neon-cyan to-neon-green',
    glowColor: 'rgba(0, 255, 255, 0.3)',
  },
  {
    id: 'soildercastle',
    name: 'soildercastle',
    github: 'https://github.com/soildercastle',
    avatarUrl: 'https://github.com/soildercastle.png',
    roleKey: 'teamRole3',
    icon: Database,
    gradient: 'from-neon-magenta to-neon-cyan',
    glowColor: 'rgba(255, 0, 255, 0.3)',
  },
];

// ============================================================================
// TEAM MEMBER CARD
// ============================================================================

function TeamMemberCard({ member, index }: { member: TeamMember; index: number }) {
  const { t } = useLanguage();
  const IconComponent = member.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: index * 0.15 }}
      viewport={{ once: true }}
    >
      <Card className="group relative overflow-hidden bg-[rgba(255,255,255,0.02)] border-[0.5px] border-[#393939] backdrop-blur-xl hover:border-[#4a4a4a] transition-all duration-500">
        {/* Animated gradient background */}
        <motion.div
          className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br ${member.gradient}`}
          style={{ filter: 'blur(60px)' }}
          initial={false}
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 3, repeat: Infinity }}
        />
        
        {/* Content */}
        <div className="relative z-10 p-6 flex flex-col items-center text-center">
          {/* Avatar with glow ring */}
          <motion.div
            className="relative mb-4"
            whileHover={{ scale: 1.05 }}
            transition={{ type: 'spring', stiffness: 300 }}
          >
            {/* Animated ring */}
            <motion.div
              className={`absolute -inset-2 rounded-full bg-gradient-to-r ${member.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500`}
              animate={{ rotate: 360 }}
              transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
              style={{ filter: 'blur(8px)' }}
            />
            
            {/* Avatar container */}
            <div className="relative w-24 h-24 rounded-full overflow-hidden border-2 border-[#393939] group-hover:border-transparent transition-colors duration-500">
              <img
                src={member.avatarUrl}
                alt={member.name}
                className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500"
                onError={(e) => {
                  // Fallback to gradient placeholder
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
              {/* Fallback gradient avatar */}
              <div className={`absolute inset-0 bg-gradient-to-br ${member.gradient} opacity-30 flex items-center justify-center`}>
                <span className="text-2xl font-bold text-white">{member.name[0].toUpperCase()}</span>
              </div>
            </div>
            
            {/* Role icon badge */}
            <div 
              className="absolute -bottom-1 -right-1 p-2 rounded-full border border-[#393939] bg-[#0a0a0a]"
              style={{ boxShadow: `0 0 15px ${member.glowColor}` }}
            >
              <IconComponent className="w-4 h-4 text-white" />
            </div>
          </motion.div>
          
          {/* Name */}
          <h3 className="text-lg font-bold text-[#f8fafc] mb-1 tracking-tight">
            {member.name}
          </h3>
          
          {/* Role */}
          <p className="text-xs text-[#cbd5e1] mb-4 leading-relaxed">
            {t(member.roleKey)}
          </p>
          
          {/* GitHub link */}
          <motion.a
            href={member.github}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[rgba(255,255,255,0.05)] border border-[#393939] text-xs font-mono text-[#94a3b8] hover:text-[#f8fafc] hover:border-[#4a4a4a] transition-all group/link"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <GithubIcon className="w-4 h-4" />
            <span>@{member.name}</span>
            <motion.span
              className="opacity-0 group-hover/link:opacity-100 transition-opacity"
              initial={{ x: -5 }}
              whileHover={{ x: 0 }}
            >
              →
            </motion.span>
          </motion.a>
        </div>
        
        {/* Decorative corner elements */}
        <div className="absolute top-2 left-2 w-3 h-3 border-t border-l border-[#393939] opacity-50" />
        <div className="absolute top-2 right-2 w-3 h-3 border-t border-r border-[#393939] opacity-50" />
        <div className="absolute bottom-2 left-2 w-3 h-3 border-b border-l border-[#393939] opacity-50" />
        <div className="absolute bottom-2 right-2 w-3 h-3 border-b border-r border-[#393939] opacity-50" />
      </Card>
    </motion.div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function MissionSpecialists() {
  const { t } = useLanguage();

  return (
    <section className="py-24 px-6 max-w-5xl mx-auto">
      {/* Section header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        viewport={{ once: true }}
        className="text-center mb-16"
      >
        <motion.div
          initial={{ scale: 0 }}
          whileInView={{ scale: 1 }}
          transition={{ type: 'spring', delay: 0.2 }}
          viewport={{ once: true }}
          className="inline-flex items-center gap-2 px-4 py-2 mb-6 rounded-full bg-[rgba(255,255,255,0.05)] border border-[#393939]"
        >
          <Rocket className="w-4 h-4 text-neon-orange" />
          <span className="text-sm font-mono text-[#cbd5e1]">ThresholdAI</span>
        </motion.div>
        
        <h2 className="text-3xl md:text-4xl font-bold mb-4 tracking-tight text-[#f8fafc]">
          {t('teamTitle')}
        </h2>
        <p className="text-[#cbd5e1] max-w-xl mx-auto">
          {t('teamDesc')}
        </p>
      </motion.div>

      {/* Team grid */}
      <div className="grid md:grid-cols-3 gap-6">
        {TEAM_MEMBERS.map((member, index) => (
          <TeamMemberCard key={member.id} member={member} index={index} />
        ))}
      </div>

      {/* Connecting line decoration */}
      <motion.div
        initial={{ scaleX: 0 }}
        whileInView={{ scaleX: 1 }}
        transition={{ duration: 1, delay: 0.5 }}
        viewport={{ once: true }}
        className="mt-12 h-px bg-gradient-to-r from-transparent via-[#393939] to-transparent"
      />
    </section>
  );
}

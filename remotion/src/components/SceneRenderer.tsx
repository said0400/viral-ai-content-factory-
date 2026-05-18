/**
 * 🎬 Scene Renderer v2.0 — Pro
 * ═══════════════════════════════════════════════════════════════
 * عرض مشهد واحد مع كل تأثيراته:
 *   ✓ BackgroundVideo (مع zoom & shake)
 *   ✓ ColorGrade integration (vignette + grain)
 *   ✓ Scene-specific effects (Hook, Peak, CTA, etc.)
 *   ✓ Transition support
 *   ✓ Performance optimized
 * ═══════════════════════════════════════════════════════════════
 */

import { useMemo, memo, ReactNode } from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from 'remotion';
import { BackgroundVideo } from './BackgroundVideo';
import { ColorGrade } from './ColorGrade';
import type { Scene, Effects } from '@types/index';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════
export interface SceneRendererProps {
  scene: Scene;
  isActive: boolean;
  fps: number;
  effects?: Effects;
  
  /** Override fade durations */
  fadeInFrames?: number;
  fadeOutFrames?: number;
  
  /** تطبيق ColorGrade في الـ scene */
  applyColorGrade?: boolean;
  
  /** Override scene effects */
  customEffects?: ReactNode;
}

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const DEFAULT_FADE_FRAMES = 12;

// ═══════════════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════════════
export const SceneRenderer: React.FC<SceneRendererProps> = memo(
  ({
    scene,
    isActive,
    fps,
    effects,
    fadeInFrames = DEFAULT_FADE_FRAMES,
    fadeOutFrames = DEFAULT_FADE_FRAMES,
    applyColorGrade = false,
    customEffects,
  }) => {
    const frame = useCurrentFrame();
    const { width, height, durationInFrames } = useVideoConfig();
    
    // ─── Fade In/Out Animation ─────────────────────────────────
    const sceneOpacity = useMemo(() => {
      if (!isActive) return 0;
      
      const fadeIn = interpolate(
        frame,
        [0, fadeInFrames],
        [0, 1],
        { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
      );
      
      const fadeOutStart = durationInFrames - fadeOutFrames;
      const fadeOut = interpolate(
        frame,
        [fadeOutStart, durationInFrames],
        [1, 0],
        { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
      );
      
      return Math.min(fadeIn, fadeOut);
    }, [isActive, frame, fadeInFrames, fadeOutFrames, durationInFrames]);
    
    // ─── Scene Effects (حسب النوع) ────────────────────────────
    const sceneEffects = useMemo(() => {
      if (customEffects) return customEffects;
      
      switch (scene.type) {
        case 'hook':
        case 'intro':
          return <HookEffects />;
        
        case 'peak':
          return <PeakEffects energy={scene.energy ?? 0.8} />;
        
        case 'cta':
        case 'outro':
          return <CTAEffects />;
        
        default:
          return null;
      }
    }, [scene.type, scene.energy, customEffects]);
    
    // ─── Background Video ─────────────────────────────────────
    const backgroundVideo = (
      <BackgroundVideo
        src={scene.backgroundPath}
        duration={scene.totalLength * fps}
        zoomEffect={scene.zoomEffect}
        shake={scene.shake}
        width={width}
        height={height}
      />
    );
    
    // ─── Apply ColorGrade if requested ────────────────────────
    const content = applyColorGrade && effects?.grade ? (
      <ColorGrade config={effects.grade}>
        {backgroundVideo}
      </ColorGrade>
    ) : (
      backgroundVideo
    );
    
    return (
      <AbsoluteFill
        style={{
          opacity: sceneOpacity,
          backgroundColor: '#000000',
        }}
      >
        {content}
        {sceneEffects}
      </AbsoluteFill>
    );
  },
);

SceneRenderer.displayName = 'SceneRenderer';

// ═══════════════════════════════════════════════════════════════
// ✨ Hook Effects (للمشاهد الافتتاحية)
// ═══════════════════════════════════════════════════════════════
const HookEffects: React.FC = memo(() => {
  const frame = useCurrentFrame();
  
  // Flash effect (white burst)
  const flashOpacity = useMemo(
    () =>
      interpolate(frame, [0, 3, 10], [0.4, 0.2, 0], {
        extrapolateRight: 'clamp',
      }),
    [frame],
  );
  
  // Light rays from corners
  const rayOpacity = useMemo(
    () =>
      interpolate(frame, [0, 15, 30], [0, 0.3, 0], {
        extrapolateRight: 'clamp',
      }),
    [frame],
  );
  
  return (
    <>
      {/* Flash burst */}
      <AbsoluteFill
        style={{
          backgroundColor: '#FFFFFF',
          opacity: flashOpacity,
          pointerEvents: 'none',
          mixBlendMode: 'screen',
        }}
      />
      
      {/* Light rays */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(
            ellipse at 50% 0%,
            rgba(255, 255, 255, ${rayOpacity}) 0%,
            transparent 50%
          )`,
          pointerEvents: 'none',
        }}
      />
    </>
  );
});

HookEffects.displayName = 'HookEffects';

// ═══════════════════════════════════════════════════════════════
// 🔥 Peak Effects (للحظات القوية)
// ═══════════════════════════════════════════════════════════════
const PeakEffects: React.FC<{ energy: number }> = memo(({ energy }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // Pulsing red glow
  const pulseOpacity = useMemo(() => {
    const time = frame / fps;
    const pulse = Math.sin(time * 4 * Math.PI) * 0.5 + 0.5;
    return pulse * 0.2 * energy;
  }, [frame, fps, energy]);
  
  // Light flash at start
  const flashOpacity = useMemo(
    () =>
      interpolate(frame, [0, 5, 15], [0.5, 0.2, 0], {
        extrapolateRight: 'clamp',
      }),
    [frame],
  );
  
  return (
    <>
      {/* Initial flash */}
      <AbsoluteFill
        style={{
          backgroundColor: '#FFFFFF',
          opacity: flashOpacity,
          pointerEvents: 'none',
          mixBlendMode: 'screen',
        }}
      />
      
      {/* Pulsing glow */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(
            ellipse at center,
            rgba(255, 100, 50, ${pulseOpacity}) 0%,
            transparent 70%
          )`,
          pointerEvents: 'none',
          mixBlendMode: 'screen',
        }}
      />
    </>
  );
});

PeakEffects.displayName = 'PeakEffects';

// ═══════════════════════════════════════════════════════════════
// 💎 CTA Effects (للـ Call To Action)
// ═══════════════════════════════════════════════════════════════
const CTAEffects: React.FC = memo(() => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // Pulsing gold glow
  const pulseOpacity = useMemo(() => {
    const time = frame / fps;
    const pulse = Math.sin(time * 2 * Math.PI) * 0.5 + 0.5;
    return 0.1 + pulse * 0.15;
  }, [frame, fps]);
  
  // Border glow
  const borderOpacity = useMemo(() => {
    const time = frame / fps;
    return 0.2 + Math.sin(time * 1.5 * Math.PI) * 0.1;
  }, [frame, fps]);
  
  return (
    <>
      {/* Center pulse */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(
            ellipse at center,
            rgba(255, 215, 0, ${pulseOpacity}) 0%,
            transparent 60%
          )`,
          pointerEvents: 'none',
          mixBlendMode: 'screen',
        }}
      />
      
      {/* Border glow */}
      <AbsoluteFill
        style={{
          boxShadow: `inset 0 0 100px rgba(255, 215, 0, ${borderOpacity})`,
          pointerEvents: 'none',
        }}
      />
    </>
  );
});

CTAEffects.displayName = 'CTAEffects';

// ═══════════════════════════════════════════════════════════════
// 🌫️ Build Effects (للمشاهد المتوسطة - اختياري)
// ═══════════════════════════════════════════════════════════════
export const BuildEffects: React.FC = memo(() => {
  const frame = useCurrentFrame();
  
  // Subtle moving light
  const lightX = useMemo(() => {
    return interpolate(frame, [0, 90], [-50, 150], {
      extrapolateRight: 'extend',
    });
  }, [frame]);
  
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(
          ellipse at ${lightX}% 50%,
          rgba(255, 255, 255, 0.05) 0%,
          transparent 30%
        )`,
        pointerEvents: 'none',
      }}
    />
  );
});

BuildEffects.displayName = 'BuildEffects';

// ═══════════════════════════════════════════════════════════════
// 📦 Resolution Effects
// ═══════════════════════════════════════════════════════════════
export const ResolutionEffects: React.FC = memo(() => {
  const frame = useCurrentFrame();
  
  // Soft converging light
  const opacity = useMemo(
    () => interpolate(frame, [0, 30, 60], [0, 0.15, 0.08], {
      extrapolateRight: 'clamp',
    }),
    [frame],
  );
  
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(
          ellipse at center,
          rgba(100, 200, 255, ${opacity}) 0%,
          transparent 60%
        )`,
        pointerEvents: 'none',
        mixBlendMode: 'screen',
      }}
    />
  );
});

ResolutionEffects.displayName = 'ResolutionEffects';

// ═══════════════════════════════════════════════════════════════
// Export
// ═══════════════════════════════════════════════════════════════
export default SceneRenderer;

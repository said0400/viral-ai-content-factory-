/**
 * 🎬 ShortsVideo Composition v2.0
 * ═══════════════════════════════════════════════════════════════
 * الـ Composition الرئيسي
 * 
 * Layers:
 *   1. ColorGrade (wrapping all)
 *   2. Scenes with Transitions
 *   3. Letterbox
 *   4. Subtitles
 *   5. Audio
 *   6. Debug Overlay (dev only)
 * ═══════════════════════════════════════════════════════════════
 */

import { useMemo, memo } from 'react';
import {
  AbsoluteFill,
  Sequence,
  Series,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from 'remotion';
import { TransitionSeries, linearTiming } from '@remotion/transitions';
import { fade } from '@remotion/transitions/fade';
import { slide } from '@remotion/transitions/slide';
import { wipe } from '@remotion/transitions/wipe';
import { flip } from '@remotion/transitions/flip';
import { clockWipe } from '@remotion/transitions/clock-wipe';
import { iris } from '@remotion/transitions/iris';

import { SceneRenderer } from '@components/SceneRenderer';
import { ArabicSubtitle } from '@components/ArabicSubtitle';
import { AudioTrack } from '@components/AudioTrack';
import { Letterbox } from '@components/Letterbox';
import { ColorGrade } from '@components/ColorGrade';

import type {
  VideoProps,
  Scene,
  Subtitle,
  Transition,
} from '@types/index';

// ═══════════════════════════════════════════════════════════════
// Helpers: Transition Mapping
// ═══════════════════════════════════════════════════════════════
const getTransitionPresentation = (transition: Transition) => {
  const name = transition.name.toLowerCase();
  
  if (name.includes('fade')) {
    return fade();
  }
  
  if (name.includes('slide')) {
    const direction = transition.direction || 'from-right';
    return slide({
      direction: direction as 'from-left' | 'from-right' | 'from-top' | 'from-bottom',
    });
  }
  
  if (name.includes('wipe')) {
    const direction = transition.direction || 'from-right';
    return wipe({
      direction: direction as 'from-left' | 'from-right' | 'from-top' | 'from-bottom',
    });
  }
  
  if (name.includes('flip')) {
    return flip({ direction: 'from-left' });
  }
  
  if (name.includes('clock')) {
    return clockWipe({ width: 1080, height: 1920 });
  }
  
  if (name.includes('iris')) {
    return iris({ width: 1080, height: 1920 });
  }
  
  // Default: fade
  return fade();
};

// ═══════════════════════════════════════════════════════════════
// 🎬 Scene Sequence Builder
// ═══════════════════════════════════════════════════════════════
interface ScenesContainerProps {
  scenes: Scene[];
  transitions: Transition[];
  fps: number;
  effects?: VideoProps['effects'];
  useTransitions?: boolean;
}

const ScenesContainer: React.FC<ScenesContainerProps> = memo(
  ({ scenes, transitions, fps, effects, useTransitions = false }) => {
    // إذا useTransitions = true → استخدم TransitionSeries
    if (useTransitions && transitions.length > 0) {
      return (
        <TransitionSeries>
          {scenes.map((scene, index) => {
            const sceneDurationFrames = Math.floor(scene.totalLength * fps);
            const transition = transitions.find((t) => t.toScene === index);
            
            return (
              <React.Fragment key={`scene-${scene.id}`}>
                {/* Transition (إلا في الأول) */}
                {transition && index > 0 && (
                  <TransitionSeries.Transition
                    presentation={getTransitionPresentation(transition)}
                    timing={linearTiming({
                      durationInFrames: Math.floor(transition.duration * fps),
                    })}
                  />
                )}
                
                {/* Scene */}
                <TransitionSeries.Sequence durationInFrames={sceneDurationFrames}>
                  <SceneRenderer
                    scene={scene}
                    isActive={true}
                    fps={fps}
                    effects={effects}
                  />
                </TransitionSeries.Sequence>
              </React.Fragment>
            );
          })}
        </TransitionSeries>
      );
    }
    
    // الطريقة العادية (Sequences منفصلة)
    return (
      <AbsoluteFill>
        {scenes.map((scene, index) => {
          const startFrame = Math.floor(scene.startTime * fps);
          const sceneDurationFrames = Math.floor(scene.totalLength * fps);
          
          return (
            <Sequence
              key={`scene-${scene.id}-${index}`}
              from={startFrame}
              durationInFrames={sceneDurationFrames}
              name={`Scene ${index + 1}: ${scene.type}`}
            >
              <SceneRenderer
                scene={scene}
                isActive={true}
                fps={fps}
                effects={effects}
              />
            </Sequence>
          );
        })}
      </AbsoluteFill>
    );
  },
);

ScenesContainer.displayName = 'ScenesContainer';

// ═══════════════════════════════════════════════════════════════
// 📝 Subtitle Renderer (Optimized)
// ═══════════════════════════════════════════════════════════════
interface SubtitleRendererProps {
  subtitles: Subtitle[];
  currentTimeInSeconds: number;
  style?: VideoProps['subtitleStyle'];
  width: number;
  height: number;
}

const SubtitleRenderer: React.FC<SubtitleRendererProps> = memo(
  ({ subtitles, currentTimeInSeconds, style, width, height }) => {
    // البحث عن الترجمة الحالية (binary search للأداء)
    const currentSubtitle = useMemo(() => {
      // إذا قائمة صغيرة، linear search كافٍ
      if (subtitles.length < 20) {
        return subtitles.find(
          (sub) =>
            currentTimeInSeconds >= sub.start &&
            currentTimeInSeconds < sub.end,
        );
      }
      
      // Binary search للقوائم الكبيرة
      let left = 0;
      let right = subtitles.length - 1;
      
      while (left <= right) {
        const mid = Math.floor((left + right) / 2);
        const sub = subtitles[mid];
        
        if (currentTimeInSeconds < sub.start) {
          right = mid - 1;
        } else if (currentTimeInSeconds >= sub.end) {
          left = mid + 1;
        } else {
          return sub;
        }
      }
      
      return undefined;
    }, [subtitles, currentTimeInSeconds]);
    
    if (!currentSubtitle) return null;
    
    return (
      <ArabicSubtitle
        subtitle={currentSubtitle}
        style={style}
        isVisible={true}
        videoWidth={width}
        videoHeight={height}
      />
    );
  },
);

SubtitleRenderer.displayName = 'SubtitleRenderer';

// ═══════════════════════════════════════════════════════════════
// 🐛 Debug Overlay
// ═══════════════════════════════════════════════════════════════
interface DebugOverlayProps {
  frame: number;
  durationInFrames: number;
  scenesCount: number;
  subtitlesCount: number;
  currentSubtitleId?: number;
  hasAudio: boolean;
}

const DebugOverlay: React.FC<DebugOverlayProps> = memo(
  ({
    frame,
    durationInFrames,
    scenesCount,
    subtitlesCount,
    currentSubtitleId,
    hasAudio,
  }) => {
    const { fps } = useVideoConfig();
    const currentTime = (frame / fps).toFixed(2);
    
    return (
      <div
        style={{
          position: 'absolute',
          top: 20,
          left: 20,
          fontFamily: 'monospace',
          fontSize: 14,
          color: 'rgba(255, 255, 0, 0.8)',
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          padding: '10px 14px',
          borderRadius: 8,
          zIndex: 9999,
          lineHeight: 1.6,
          border: '1px solid rgba(255, 255, 0, 0.3)',
          pointerEvents: 'none',
        }}
      >
        <div>⏱ {currentTime}s</div>
        <div>🎞 Frame {frame}/{durationInFrames}</div>
        <div>📊 {fps}fps</div>
        <div>🎬 Scenes: {scenesCount}</div>
        <div>📝 Subs: {subtitlesCount}</div>
        {currentSubtitleId !== undefined && (
          <div>💬 Sub #{currentSubtitleId}</div>
        )}
        <div>🎵 Audio: {hasAudio ? '✓' : '✗'}</div>
      </div>
    );
  },
);

DebugOverlay.displayName = 'DebugOverlay';

// ═══════════════════════════════════════════════════════════════
// 🎬 Main Composition
// ═══════════════════════════════════════════════════════════════
export const ShortsVideo: React.FC<VideoProps> = memo((props) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();
  
  // ─── Props with defaults ──────────────────────────────────
  const {
    scenes = [],
    subtitles = [],
    transitions = [],
    audioPath = '',
    audioActualDuration,
    effects,
    subtitleStyle,
    design,
  } = props;
  
  // ─── Current time ──────────────────────────────────────────
  const currentTimeInSeconds = useMemo(
    () => frame / fps,
    [frame, fps],
  );
  
  // ─── Global Fade In/Out ───────────────────────────────────
  const globalOpacity = useMemo(() => {
    const fadeInDuration = effects?.fade?.fadeIn?.duration ?? 0;
    const fadeOutDuration = effects?.fade?.fadeOut?.duration ?? 0;
    
    if (fadeInDuration === 0 && fadeOutDuration === 0) {
      return 1;
    }
    
    const fadeInFrames = Math.floor(fadeInDuration * fps);
    const fadeOutFrames = Math.floor(fadeOutDuration * fps);
    
    const fadeIn = interpolate(
      frame,
      [0, fadeInFrames],
      [0, 1],
      { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
    );
    
    const fadeOut = interpolate(
      frame,
      [durationInFrames - fadeOutFrames, durationInFrames],
      [1, 0],
      { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
    );
    
    return Math.min(fadeIn, fadeOut);
  }, [frame, fps, durationInFrames, effects?.fade]);
  
  // ─── Validation ────────────────────────────────────────────
  if (scenes.length === 0) {
    return <EmptyState message="No scenes provided" />;
  }
  
  // ─── Should use transitions? ──────────────────────────────
  const useTransitions = transitions.length > 0;
  
  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#000000',
        overflow: 'hidden',
        opacity: globalOpacity,
      }}
    >
      {/* ═══ 1. Color Grade Wrapper ═══ */}
      <ColorGrade config={effects?.grade}>
        {/* ═══ 2. Scenes (with optional transitions) ═══ */}
        <ScenesContainer
          scenes={scenes}
          transitions={transitions}
          fps={fps}
          effects={effects}
          useTransitions={useTransitions}
        />
        
        {/* ═══ 3. Letterbox ═══ */}
        {effects?.letterbox?.enabled && (
          <Letterbox
            config={effects.letterbox}
            width={width}
            height={height}
          />
        )}
        
        {/* ═══ 4. Subtitles ═══ */}
        <SubtitleRenderer
          subtitles={subtitles}
          currentTimeInSeconds={currentTimeInSeconds}
          style={subtitleStyle}
          width={width}
          height={height}
        />
      </ColorGrade>
      
      {/* ═══ 5. Audio ═══ */}
      {audioPath && (
        <AudioTrack
          src={audioPath}
          volume={1}
          fadeInDuration={effects?.fade?.fadeIn?.duration ?? 0.5}
          fadeOutDuration={effects?.fade?.fadeOut?.duration ?? 0.5}
          durationInVideo={
            audioActualDuration
              ? Math.floor(audioActualDuration * fps)
              : durationInFrames
          }
        />
      )}
      
      {/* ═══ 6. Debug Overlay (dev only) ═══ */}
      {process.env.NODE_ENV === 'development' && (
        <DebugOverlay
          frame={frame}
          durationInFrames={durationInFrames}
          scenesCount={scenes.length}
          subtitlesCount={subtitles.length}
          currentSubtitleId={
            subtitles.find(
              (s) =>
                currentTimeInSeconds >= s.start &&
                currentTimeInSeconds < s.end,
            )?.id
          }
          hasAudio={!!audioPath}
        />
      )}
    </AbsoluteFill>
  );
});

ShortsVideo.displayName = 'ShortsVideo';

// ═══════════════════════════════════════════════════════════════
// 🚫 Empty State
// ═══════════════════════════════════════════════════════════════
const EmptyState: React.FC<{ message: string }> = memo(({ message }) => (
  <AbsoluteFill
    style={{
      backgroundColor: '#1a1a2e',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexDirection: 'column',
      gap: 20,
    }}
  >
    <div style={{ fontSize: 100 }}>🎬</div>
    <div
      style={{
        color: 'rgba(255, 255, 255, 0.7)',
        fontSize: 48,
        fontFamily: 'monospace',
        textAlign: 'center',
      }}
    >
      {message}
    </div>
  </AbsoluteFill>
));

EmptyState.displayName = 'EmptyState';

// ═══════════════════════════════════════════════════════════════
// Export
// ═══════════════════════════════════════════════════════════════
export default ShortsVideo;

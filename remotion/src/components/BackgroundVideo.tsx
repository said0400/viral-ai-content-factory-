/**
 * 🎬 Background Video Component v2.2
 * ═══════════════════════════════════════════════════════════════
 * إصلاحات v2.2:
 *   ✓ FIXED: مشكلة /public/ في المسارات (نهائي)
 *   ✓ FIXED: import React مضاف
 *   ✓ تنظيف عميق لأي مسار قبل staticFile()
 * ═══════════════════════════════════════════════════════════════
 */

import React, { useMemo, memo } from 'react';
import {
  AbsoluteFill,
  OffthreadVideo,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Loop,
  staticFile,
} from 'remotion';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════
export type ZoomType =
  | 'slow_zoom_in'
  | 'slow_zoom_out'
  | 'punch_zoom'
  | 'drift_right'
  | 'drift_left'
  | 'drift_up'
  | 'drift_down'
  | 'static';

export interface BackgroundVideoProps {
  src: string;
  duration: number;
  zoomEffect?: ZoomType;
  shake?: boolean;
  shakeIntensity?: number;
  width: number;
  height: number;
  overlayColor?: string;
  overlayOpacity?: number;
  filter?: string;
  startFrom?: number;
  playbackRate?: number;
  objectPosition?: string;
}

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const DEFAULT_OVERLAY_COLOR = 'rgba(0, 0, 0, 1)';
const DEFAULT_OVERLAY_OPACITY = 0.25;
const DEFAULT_SHAKE_INTENSITY = 2.0;

// ═══════════════════════════════════════════════════════════════
// ✅ FIXED: resolveVideoPath v3 (حل نهائي للـ /public/)
// ═══════════════════════════════════════════════════════════════
const resolveVideoPath = (src: string): string => {
  if (!src) return '';
  
  // URLs خارجية - استخدمها مباشرة
  if (src.startsWith('http://') || src.startsWith('https://')) {
    return src;
  }
  
  if (src.startsWith('file://')) {
    return src;
  }
  
  // ✅ تنظيف عميق وشامل
  let cleanSrc = src;
  
  // 1. احذف أي مسار مطلق حتى /public/
  //    مثل: /home/runner/.../remotion/public/footage/xxx.mp4
  const publicMatch = cleanSrc.match(/[/\\]public[/\\](.+)$/);
  if (publicMatch) {
    cleanSrc = publicMatch[1];
  }
  
  // 2. احذف "public/" في البداية (بكل أشكاله)
  cleanSrc = cleanSrc.replace(/^\/?(public\/)+/gi, '');
  
  // 3. احذف "/" في البداية
  cleanSrc = cleanSrc.replace(/^\/+/, '');
  
  // 4. تأكد من عدم وجود مسار مطلق
  if (cleanSrc.includes(':\\') || cleanSrc.startsWith('/home/') || cleanSrc.startsWith('/tmp/')) {
    // مسار مطلق - ابحث عن اسم الملف فقط
    const parts = cleanSrc.split(/[/\\]/);
    const filename = parts[parts.length - 1];
    cleanSrc = `footage/${filename}`;
  }
  
  // ✅ staticFile يضيف /public/ تلقائياً
  // فقط نمرر المسار النسبي بدون /public/
  return staticFile(cleanSrc);
};

interface Transform {
  scale: number;
  x: number;
  y: number;
}

const calculateZoom = (
  zoomType: ZoomType,
  frame: number,
  totalFrames: number,
): Transform => {
  const progress = totalFrames > 0 ? frame / totalFrames : 0;
  
  switch (zoomType) {
    case 'slow_zoom_in':
      return {
        scale: interpolate(progress, [0, 1], [1.0, 1.12], {
          extrapolateRight: 'clamp',
        }),
        x: 0,
        y: 0,
      };

    case 'slow_zoom_out':
      return {
        scale: interpolate(progress, [0, 1], [1.12, 1.0], {
          extrapolateRight: 'clamp',
        }),
        x: 0,
        y: 0,
      };

    case 'punch_zoom':
      return {
        scale: interpolate(
          progress,
          [0, 0.15, 1],
          [1.0, 1.15, 1.10],
          { extrapolateRight: 'clamp' },
        ),
        x: 0,
        y: 0,
      };

    case 'drift_right':
      return {
        scale: 1.06,
        x: interpolate(progress, [0, 1], [0, -50], {
          extrapolateRight: 'clamp',
        }),
        y: 0,
      };

    case 'drift_left':
      return {
        scale: 1.06,
        x: interpolate(progress, [0, 1], [-50, 0], {
          extrapolateRight: 'clamp',
        }),
        y: 0,
      };

    case 'drift_up':
      return {
        scale: 1.06,
        x: 0,
        y: interpolate(progress, [0, 1], [0, -50], {
          extrapolateRight: 'clamp',
        }),
      };

    case 'drift_down':
      return {
        scale: 1.06,
        x: 0,
        y: interpolate(progress, [0, 1], [-50, 0], {
          extrapolateRight: 'clamp',
        }),
      };

    case 'static':
    default:
      return { scale: 1.0, x: 0, y: 0 };
  }
};

const calculateShake = (
  frame: number,
  fps: number,
  intensity: number,
): { x: number; y: number } => {
  const time = frame / fps;
  const x = intensity * Math.sin(2 * Math.PI * time * 0.7);
  const y = intensity * Math.cos(2 * Math.PI * time * 1.1);
  return { x, y };
};

// ═══════════════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════════════
export const BackgroundVideo: React.FC<BackgroundVideoProps> = memo(
  ({
    src,
    duration,
    zoomEffect = 'slow_zoom_in',
    shake = false,
    shakeIntensity = DEFAULT_SHAKE_INTENSITY,
    width,
    height,
    overlayColor = DEFAULT_OVERLAY_COLOR,
    overlayOpacity = DEFAULT_OVERLAY_OPACITY,
    filter,
    startFrom,
    playbackRate = 1.0,
    objectPosition = 'center',
  }) => {
    const frame = useCurrentFrame();
    const { fps, durationInFrames } = useVideoConfig();

    if (!src) {
      return <FallbackBackground width={width} height={height} />;
    }

    const videoSrc = useMemo(() => resolveVideoPath(src), [src]);

    const zoomTransform = useMemo(
      () => calculateZoom(zoomEffect, frame, durationInFrames),
      [zoomEffect, frame, durationInFrames],
    );

    const shakeTransform = useMemo(
      () =>
        shake
          ? calculateShake(frame, fps, shakeIntensity)
          : { x: 0, y: 0 },
      [shake, frame, fps, shakeIntensity],
    );

    const combinedTransform = useMemo(
      () => `
        scale(${zoomTransform.scale})
        translate(${zoomTransform.x + shakeTransform.x}px, ${
        zoomTransform.y + shakeTransform.y
      }px)
      `,
      [zoomTransform, shakeTransform],
    );

    const overlayStyle = useMemo<React.CSSProperties>(
      () => ({
        backgroundColor: overlayColor.replace(
          /rgba?\(([^)]+)\)/,
          (_, values) => {
            const parts = values.split(',').map((s: string) => s.trim());
            if (parts.length === 3) {
              return `rgba(${parts.join(',')}, ${overlayOpacity})`;
            }
            if (parts.length === 4) {
              parts[3] = overlayOpacity.toString();
              return `rgba(${parts.join(',')})`;
            }
            return overlayColor;
          },
        ),
        pointerEvents: 'none',
      }),
      [overlayColor, overlayOpacity],
    );

    const videoContainerStyle = useMemo<React.CSSProperties>(
      () => ({
        width: '100%',
        height: '100%',
        transform: combinedTransform,
        transformOrigin: 'center center',
        willChange: 'transform',
        filter: filter || undefined,
      }),
      [combinedTransform, filter],
    );

    const videoElementStyle = useMemo<React.CSSProperties>(
      () => ({
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        objectPosition,
      }),
      [objectPosition],
    );

    return (
      <AbsoluteFill
        style={{
          overflow: 'hidden',
          backgroundColor: '#000000',
        }}
      >
        <div style={videoContainerStyle}>
          <Loop durationInFrames={durationInFrames}>
            <OffthreadVideo
              src={videoSrc}
              muted
              volume={0}
              startFrom={startFrom}
              playbackRate={playbackRate}
              style={videoElementStyle}
            />
          </Loop>
        </div>

        <AbsoluteFill style={overlayStyle} />
      </AbsoluteFill>
    );
  },
);

BackgroundVideo.displayName = 'BackgroundVideo';

// ═══════════════════════════════════════════════════════════════
// Fallback Background
// ═══════════════════════════════════════════════════════════════
interface FallbackBackgroundProps {
  width: number;
  height: number;
  primaryColor?: string;
  secondaryColor?: string;
  accentColor?: string;
}

const FallbackBackground: React.FC<FallbackBackgroundProps> = memo(
  ({
    width,
    height,
    primaryColor = '#1a1a2e',
    secondaryColor = '#16213e',
    accentColor = '#0f3460',
  }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const hueRotate = useMemo(
      () =>
        interpolate(frame, [0, 300], [0, 30], {
          extrapolateRight: 'extend',
        }),
      [frame],
    );

    const pulse = useMemo(
      () => {
        const time = frame / fps;
        return Math.sin(time * 0.5) * 0.05 + 0.05;
      },
      [frame, fps],
    );

    const offset = useMemo(
      () => {
        const time = frame / fps;
        return {
          x: Math.sin(time * 0.3) * 20,
          y: Math.cos(time * 0.4) * 15,
        };
      },
      [frame, fps],
    );

    return (
      <AbsoluteFill
        style={{
          background: `linear-gradient(135deg, 
            ${primaryColor} 0%, 
            ${secondaryColor} 50%, 
            ${accentColor} 100%
          )`,
          filter: `hue-rotate(${hueRotate}deg)`,
          overflow: 'hidden',
        }}
      >
        <AbsoluteFill
          style={{
            backgroundImage: `radial-gradient(
              circle at ${50 + offset.x}% ${50 + offset.y}%,
              rgba(255, 255, 255, ${pulse}) 0%,
              transparent 70%
            )`,
          }}
        />

        <AbsoluteFill
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.03'/%3E%3C/svg%3E")`,
            opacity: 0.5,
          }}
        />
      </AbsoluteFill>
    );
  },
);

FallbackBackground.displayName = 'FallbackBackground';

// ═══════════════════════════════════════════════════════════════
// Multi-Video Background
// ═══════════════════════════════════════════════════════════════
export interface VideoSegment {
  src: string;
  startFrame: number;
  durationInFrames: number;
  zoomEffect?: ZoomType;
  shake?: boolean;
}

export interface MultiBackgroundVideoProps {
  segments: VideoSegment[];
  width: number;
  height: number;
  overlayColor?: string;
  overlayOpacity?: number;
}

export const MultiBackgroundVideo: React.FC<MultiBackgroundVideoProps> = memo(
  ({ segments, width, height, overlayColor, overlayOpacity }) => {
    const frame = useCurrentFrame();
    
    const currentSegment = useMemo(() => {
      return segments.find(
        (s) =>
          frame >= s.startFrame &&
          frame < s.startFrame + s.durationInFrames,
      );
    }, [segments, frame]);

    if (!currentSegment) {
      return <FallbackBackground width={width} height={height} />;
    }

    return (
      <BackgroundVideo
        src={currentSegment.src}
        duration={currentSegment.durationInFrames}
        zoomEffect={currentSegment.zoomEffect}
        shake={currentSegment.shake}
        width={width}
        height={height}
        overlayColor={overlayColor}
        overlayOpacity={overlayOpacity}
      />
    );
  },
);

MultiBackgroundVideo.displayName = 'MultiBackgroundVideo';

export default BackgroundVideo;

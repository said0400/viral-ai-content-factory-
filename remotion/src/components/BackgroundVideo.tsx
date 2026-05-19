/**
 * 🎬 Background Video Component v2.0
 * ═══════════════════════════════════════════════════════════════
 * عرض فيديو الخلفية مع:
 *   ✓ 8 أنواع zoom effects
 *   ✓ Shake effect
 *   ✓ Filters (blur, brightness, etc.)
 *   ✓ Custom overlay
 *   ✓ Performance optimized
 *   ✓ Smart fallback
 *   ✓ staticFile() support
 * ═══════════════════════════════════════════════════════════════
 */

import { useMemo, memo } from 'react';
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
  /** مسار الفيديو */
  src: string;
  
  /** المدة بالـ frames */
  duration: number;
  
  /** نوع الزوم */
  zoomEffect?: ZoomType;
  
  /** تفعيل الاهتزاز */
  shake?: boolean;
  
  /** شدة الاهتزاز */
  shakeIntensity?: number;
  
  /** أبعاد الفيديو */
  width: number;
  height: number;
  
  /** لون الـ overlay */
  overlayColor?: string;
  
  /** opacity الـ overlay */
  overlayOpacity?: number;
  
  /** CSS filters (blur, brightness, etc.) */
  filter?: string;
  
  /** بداية الفيديو الأصلي */
  startFrom?: number;
  
  /** سرعة التشغيل */
  playbackRate?: number;
  
  /** Object position */
  objectPosition?: string;
}

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const DEFAULT_OVERLAY_COLOR = 'rgba(0, 0, 0, 1)';
const DEFAULT_OVERLAY_OPACITY = 0.25;
const DEFAULT_SHAKE_INTENSITY = 2.0;

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════
const resolveVideoPath = (src: string): string => {
  if (!src) return '';
  
  // URLs خارجية
  if (src.startsWith('http://') || src.startsWith('https://')) {
    return src;
  }
  
  // file:// protocol
  if (src.startsWith('file://')) {
    return src;
  }
  
  // إذا يحتوي /public/ احذفه (staticFile يضيفه تلقائياً)
  let cleanSrc = src;
  if (cleanSrc.startsWith('/public/')) {
    cleanSrc = cleanSrc.substring(8);  // احذف "/public/"
  } else if (cleanSrc.startsWith('public/')) {
    cleanSrc = cleanSrc.substring(7);  // احذف "public/"
  }
  
  // إذا مطلق (يبدأ بـ /)
  if (cleanSrc.startsWith('/')) {
    cleanSrc = cleanSrc.substring(1);  // احذف الـ "/" الأولى
  }
  
  return staticFile(cleanSrc);
};
interface Transform {
  scale: number;
  x: number;
  y: number;
}

/**
 * حساب transform للزوم
 */
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

/**
 * حساب shake effect
 */
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
// Main Component (memoized)
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

    // ─── Fallback إذا لا يوجد src ─────────────────────────────
    if (!src) {
      return <FallbackBackground width={width} height={height} />;
    }

    // ─── Resolved Path (memoized) ─────────────────────────────
    const videoSrc = useMemo(() => resolveVideoPath(src), [src]);

    // ─── Transforms (memoized per frame range) ────────────────
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

    // ─── Combined Transform String ────────────────────────────
    const combinedTransform = useMemo(
      () => `
        scale(${zoomTransform.scale})
        translate(${zoomTransform.x + shakeTransform.x}px, ${
        zoomTransform.y + shakeTransform.y
      }px)
      `,
      [zoomTransform, shakeTransform],
    );

    // ─── Overlay Style ────────────────────────────────────────
    const overlayStyle = useMemo<React.CSSProperties>(
      () => ({
        // تحويل rgba لتطبيق opacity
        backgroundColor: overlayColor.replace(
          /rgba?\(([^)]+)\)/,
          (_, values) => {
            const parts = values.split(',').map((s: string) => s.trim());
            if (parts.length === 3) {
              return `rgba(${parts.join(',')}, ${overlayOpacity})`;
            }
            // إذا rgba موجود، استبدل الـ alpha
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

    // ─── Video Container Style ────────────────────────────────
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

    // ─── Video Element Style ──────────────────────────────────
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
        {/* Video with transforms */}
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

        {/* Overlay */}
        <AbsoluteFill style={overlayStyle} />
      </AbsoluteFill>
    );
  },
);

BackgroundVideo.displayName = 'BackgroundVideo';

// ═══════════════════════════════════════════════════════════════
// 🎨 Fallback Background (Enhanced)
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

    // Animated gradient (slow rotation)
    const hueRotate = useMemo(
      () =>
        interpolate(frame, [0, 300], [0, 30], {
          extrapolateRight: 'extend',
        }),
      [frame],
    );

    // Pulse effect على الـ radial
    const pulse = useMemo(
      () => {
        const time = frame / fps;
        return Math.sin(time * 0.5) * 0.05 + 0.05; // 0.0 - 0.1
      },
      [frame, fps],
    );

    // Slow parallax movement
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
        {/* Animated radial gradient */}
        <AbsoluteFill
          style={{
            backgroundImage: `radial-gradient(
              circle at ${50 + offset.x}% ${50 + offset.y}%,
              rgba(255, 255, 255, ${pulse}) 0%,
              transparent 70%
            )`,
          }}
        />

        {/* Subtle noise overlay */}
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
// 🎬 Multi-Video Background (للمونتاج المتقدم)
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
    
    // العثور على الـ segment الحالي
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

// ═══════════════════════════════════════════════════════════════
// Default Export
// ═══════════════════════════════════════════════════════════════
export default BackgroundVideo;

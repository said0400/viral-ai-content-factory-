/**
 * 🎵 Audio Track Component v2.0
 * ═══════════════════════════════════════════════════════════════
 * تشغيل الصوت مع:
 *   ✓ Fade in/out قابل للتخصيص
 *   ✓ staticFile() للمسارات
 *   ✓ Loop support
 *   ✓ Playback rate
 *   ✓ Performance optimized
 *   ✓ Multiple tracks support
 * ═══════════════════════════════════════════════════════════════
 */

import { useMemo, memo } from 'react';
import {
  Audio,
  Loop,
  Sequence,
  useVideoConfig,
  interpolate,
  staticFile,
} from 'remotion';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════
export interface AudioTrackProps {
  /** مسار الصوت (نسبي أو URL) */
  src: string;
  
  /** الحجم (0.0 - 1.0) */
  volume?: number;
  
  /** بداية القراءة من الصوت (frames) */
  startFrom?: number;
  
  /** نهاية القراءة من الصوت (frames) */
  endAt?: number;
  
  /** مدة fade in بالثواني */
  fadeInDuration?: number;
  
  /** مدة fade out بالثواني */
  fadeOutDuration?: number;
  
  /** تكرار الصوت إذا كان أقصر من الفيديو */
  loop?: boolean;
  
  /** سرعة التشغيل (1.0 = طبيعي) */
  playbackRate?: number;
  
  /** متى يبدأ الصوت في الفيديو (frames) */
  startInVideo?: number;
  
  /** مدة الصوت في الفيديو (frames) */
  durationInVideo?: number;
  
  /** Mute (للـ debugging) */
  muted?: boolean;
}

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const DEFAULT_FADE_IN = 0.5;   // seconds
const DEFAULT_FADE_OUT = 0.5;  // seconds
const MIN_VOLUME = 0;
const MAX_VOLUME = 1;

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════
/**
 * تحويل المسار النسبي إلى staticFile URL
 */
const resolveAudioPath = (src: string): string => {
  if (!src) return '';
  
  // URLs خارجية
  if (src.startsWith('http://') || src.startsWith('https://')) {
    return src;
  }
  
  // file:// protocol
  if (src.startsWith('file://')) {
    return src;
  }
  
  // مسار مطلق محلي
  if (src.startsWith('/')) {
    return src;
  }
  
  // مسار نسبي - استخدم staticFile
  return staticFile(src);
};

/**
 * Clamp value بين حدود
 */
const clamp = (value: number, min: number, max: number): number => {
  return Math.min(Math.max(value, min), max);
};

// ═══════════════════════════════════════════════════════════════
// Main Component (memoized)
// ═══════════════════════════════════════════════════════════════
export const AudioTrack: React.FC<AudioTrackProps> = memo(
  ({
    src,
    volume = 1,
    startFrom,
    endAt,
    fadeInDuration = DEFAULT_FADE_IN,
    fadeOutDuration = DEFAULT_FADE_OUT,
    loop = false,
    playbackRate = 1.0,
    startInVideo = 0,
    durationInVideo,
    muted = false,
  }) => {
    const { fps, durationInFrames } = useVideoConfig();

    // ─── Validation (مرة واحدة) ───────────────────────────────
    if (!src) {
      // ⚠ لا console.warn (يعمل كل frame!)
      return null;
    }

    if (muted) {
      return null;
    }

    // ─── Resolved Path ────────────────────────────────────────
    const audioSrc = useMemo(() => resolveAudioPath(src), [src]);

    // ─── Volume Settings ──────────────────────────────────────
    const safeVolume = clamp(volume, MIN_VOLUME, MAX_VOLUME);
    const fadeInFrames = Math.floor(fadeInDuration * fps);
    const fadeOutFrames = Math.floor(fadeOutDuration * fps);
    
    // مدة الصوت في الفيديو
    const audioDurationFrames = durationInVideo ?? durationInFrames;
    const fadeOutStart = audioDurationFrames - fadeOutFrames;

    // ─── Volume Function (Remotion-optimized) ─────────────────
    /**
     * استخدام function بدلاً من number
     * Remotion يحسبها بكفاءة بدون re-render
     */
    const volumeFunction = useMemo(
      () => (frame: number) => {
        // Fade in
        const fadeIn = interpolate(
          frame,
          [0, fadeInFrames],
          [0, safeVolume],
          {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          },
        );

        // Fade out
        const fadeOut = interpolate(
          frame,
          [fadeOutStart, audioDurationFrames],
          [safeVolume, 0],
          {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          },
        );

        return Math.min(fadeIn, fadeOut);
      },
      [fadeInFrames, fadeOutStart, audioDurationFrames, safeVolume],
    );

    // ─── Audio Component ──────────────────────────────────────
    const audioElement = (
      <Audio
        src={audioSrc}
        volume={volumeFunction}
        startFrom={startFrom}
        endAt={endAt}
        playbackRate={playbackRate}
      />
    );

    // ─── Wrap with Loop if needed ─────────────────────────────
    const wrappedAudio = loop ? (
      <Loop durationInFrames={audioDurationFrames}>{audioElement}</Loop>
    ) : (
      audioElement
    );

    // ─── Wrap with Sequence if startInVideo > 0 ───────────────
    if (startInVideo > 0) {
      return (
        <Sequence
          from={startInVideo}
          durationInFrames={audioDurationFrames}
        >
          {wrappedAudio}
        </Sequence>
      );
    }

    return wrappedAudio;
  },
);

AudioTrack.displayName = 'AudioTrack';

// ═══════════════════════════════════════════════════════════════
// 🎼 Multi-Track Audio (مفيد لـ voice + music + sfx)
// ═══════════════════════════════════════════════════════════════
export interface MultiAudioTrackProps {
  tracks: AudioTrackProps[];
}

export const MultiAudioTrack: React.FC<MultiAudioTrackProps> = memo(
  ({ tracks }) => {
    return (
      <>
        {tracks.map((track, index) => (
          <AudioTrack key={`track-${index}`} {...track} />
        ))}
      </>
    );
  },
);

MultiAudioTrack.displayName = 'MultiAudioTrack';

// ═══════════════════════════════════════════════════════════════
// 🎵 Background Music Helper
// ═══════════════════════════════════════════════════════════════
export interface BackgroundMusicProps {
  src: string;
  volume?: number;
  fadeIn?: number;
  fadeOut?: number;
}

export const BackgroundMusic: React.FC<BackgroundMusicProps> = memo(
  ({ src, volume = 0.15, fadeIn = 2.0, fadeOut = 3.0 }) => {
    return (
      <AudioTrack
        src={src}
        volume={volume}
        fadeInDuration={fadeIn}
        fadeOutDuration={fadeOut}
        loop={true}
      />
    );
  },
);

BackgroundMusic.displayName = 'BackgroundMusic';

// ═══════════════════════════════════════════════════════════════
// 🔊 SFX Audio (مؤثرات قصيرة)
// ═══════════════════════════════════════════════════════════════
export interface SFXAudioProps {
  src: string;
  startInVideo: number;  // frame
  volume?: number;
  durationInFrames?: number;
}

export const SFXAudio: React.FC<SFXAudioProps> = memo(
  ({ src, startInVideo, volume = 0.5, durationInFrames }) => {
    return (
      <AudioTrack
        src={src}
        volume={volume}
        startInVideo={startInVideo}
        durationInVideo={durationInFrames}
        fadeInDuration={0.05}  // سريع للـ SFX
        fadeOutDuration={0.1}
      />
    );
  },
);

SFXAudio.displayName = 'SFXAudio';

// ═══════════════════════════════════════════════════════════════
// Default Export
// ═══════════════════════════════════════════════════════════════
export default AudioTrack;

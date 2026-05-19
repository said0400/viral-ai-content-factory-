/**
 * 🎵 Audio Track Component v2.1
 * ═══════════════════════════════════════════════════════════════
 * إصلاحات v2.1:
 *   ✓ import React مضاف
 *   ✓ /public/ prefix handling
 *   ✓ لا @types alias
 * ═══════════════════════════════════════════════════════════════
 */

import React, { useMemo, memo } from 'react';
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
  src: string;
  volume?: number;
  startFrom?: number;
  endAt?: number;
  fadeInDuration?: number;
  fadeOutDuration?: number;
  loop?: boolean;
  playbackRate?: number;
  startInVideo?: number;
  durationInVideo?: number;
  muted?: boolean;
}

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const DEFAULT_FADE_IN = 0.5;
const DEFAULT_FADE_OUT = 0.5;
const MIN_VOLUME = 0;
const MAX_VOLUME = 1;

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

/**
 * ✅ FIXED: تنظيف عميق للمسار + معالجة /public/
 */
const resolveAudioPath = (src: string): string => {
  if (!src) return '';
  
  // URLs خارجية
  if (src.startsWith('http://') || src.startsWith('https://')) {
    return src;
  }
  
  if (src.startsWith('file://')) {
    return src;
  }
  
  // ✅ تنظيف عميق
  let cleanSrc = src;
  
  // احذف كل أنواع /public/
  cleanSrc = cleanSrc.replace(/^\/?(public\/)+/i, '');
  
  // احذف / في البداية
  cleanSrc = cleanSrc.replace(/^\/+/, '');
  
  return staticFile(cleanSrc);
};

const clamp = (value: number, min: number, max: number): number => {
  return Math.min(Math.max(value, min), max);
};

// ═══════════════════════════════════════════════════════════════
// Main Component
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

    if (!src || muted) {
      return null;
    }

    const audioSrc = useMemo(() => resolveAudioPath(src), [src]);
    
    const safeVolume = clamp(volume, MIN_VOLUME, MAX_VOLUME);
    const fadeInFrames = Math.floor(fadeInDuration * fps);
    const fadeOutFrames = Math.floor(fadeOutDuration * fps);
    
    const audioDurationFrames = durationInVideo ?? durationInFrames;
    const fadeOutStart = audioDurationFrames - fadeOutFrames;

    const volumeFunction = useMemo(
      () => (frame: number) => {
        const fadeIn = interpolate(
          frame, [0, fadeInFrames], [0, safeVolume],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
        );
        const fadeOut = interpolate(
          frame, [fadeOutStart, audioDurationFrames], [safeVolume, 0],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
        );
        return Math.min(fadeIn, fadeOut);
      },
      [fadeInFrames, fadeOutStart, audioDurationFrames, safeVolume],
    );

    const audioElement = (
      <Audio
        src={audioSrc}
        volume={volumeFunction}
        startFrom={startFrom}
        endAt={endAt}
        playbackRate={playbackRate}
      />
    );

    const wrappedAudio = loop ? (
      <Loop durationInFrames={audioDurationFrames}>{audioElement}</Loop>
    ) : (
      audioElement
    );

    if (startInVideo > 0) {
      return (
        <Sequence from={startInVideo} durationInFrames={audioDurationFrames}>
          {wrappedAudio}
        </Sequence>
      );
    }

    return wrappedAudio;
  },
);

AudioTrack.displayName = 'AudioTrack';

// ═══════════════════════════════════════════════════════════════
// Multi-Track Audio
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
// Background Music
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
// SFX Audio
// ═══════════════════════════════════════════════════════════════
export interface SFXAudioProps {
  src: string;
  startInVideo: number;
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
        fadeInDuration={0.05}
        fadeOutDuration={0.1}
      />
    );
  },
);

SFXAudio.displayName = 'SFXAudio';

export default AudioTrack;

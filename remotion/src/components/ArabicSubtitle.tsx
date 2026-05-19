/**
 * 📝 Arabic Subtitle Component v2.1
 * ═══════════════════════════════════════════════════════════════
 * إصلاحات v2.1:
 *   ✓ import React مضاف
 *   ✓ Types inline (لا @types alias)
 * ═══════════════════════════════════════════════════════════════
 */

import React, { useMemo, memo } from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';

// ═══════════════════════════════════════════════════════════════
// Types (inline)
// ═══════════════════════════════════════════════════════════════
interface WordTiming {
  text?: string;
  word?: string;
  start: number;
  end: number;
}

interface Subtitle {
  id: number;
  text: string;
  start: number;
  end: number;
  duration: number;
  sceneId?: number;
  words?: WordTiming[];
}

interface SubtitleStyle {
  fontSize?: number;
  fontWeight?: number | string;
  fontFamily?: string;
  color?: string;
  lineHeight?: number;
  letterSpacing?: string;
  position?: 'top' | 'center' | 'bottom';
  positionOffset?: number;
  padding?: string;
  textShadow?: string;
  backgroundColor?: string;
}

interface ArabicSubtitleProps {
  subtitle: Subtitle;
  style?: Partial<SubtitleStyle>;
  isVisible?: boolean;
  videoWidth: number;
  videoHeight: number;
}

interface WordState {
  text: string;
  isActive: boolean;
  isPast: boolean;
  isFuture: boolean;
}

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const DEFAULT_STYLE = {
  fontSize: 78,
  fontWeight: 900 as number,
  fontFamily: "'Cairo', 'Tajawal', 'Almarai', sans-serif",
  color: '#FFFFFF',
  lineHeight: 1.4,
  letterSpacing: '0em',
  position: 'bottom' as const,
  positionOffset: 0.78,
  padding: '0 40px',
  textShadow: '0 4px 20px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.8)',
};

const ACCENT_COLOR = '#FFD700';
const EXIT_FRAMES = 5;

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════
const getWordText = (word: WordTiming): string => {
  if (word.text) return word.text;
  if (word.word) return word.word;
  return '';
};

const getPositionStyles = (
  position: string,
  offset: number,
  videoHeight: number,
): React.CSSProperties => {
  switch (position) {
    case 'top':
      return {
        alignItems: 'flex-start',
        paddingTop: videoHeight * offset,
      };
    case 'center':
      return {
        alignItems: 'center',
        paddingBottom: 0,
        paddingTop: 0,
      };
    case 'bottom':
    default:
      return {
        alignItems: 'flex-end',
        paddingBottom: videoHeight * (1 - offset),
      };
  }
};

// ═══════════════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════════════
export const ArabicSubtitle: React.FC<ArabicSubtitleProps> = memo(
  ({ subtitle, style, isVisible = true, videoWidth, videoHeight }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const mergedStyle = useMemo(
      () => ({ ...DEFAULT_STYLE, ...style }),
      [style],
    );

    if (!isVisible) {
      return null;
    }

    const subtitleStartFrame = Math.floor(subtitle.start * fps);
    const subtitleEndFrame = Math.floor(subtitle.end * fps);
    const localFrame = frame - subtitleStartFrame;
    const totalLocalFrames = subtitleEndFrame - subtitleStartFrame;

    if (localFrame < 0 || localFrame > totalLocalFrames + 5) {
      return null;
    }

    const enterAnimation = spring({
      frame: localFrame,
      fps,
      config: { damping: 12, stiffness: 120, mass: 0.4 },
    });

    const exitStart = totalLocalFrames - EXIT_FRAMES;
    const exitAnimation = interpolate(
      localFrame,
      [exitStart, totalLocalFrames],
      [1, 0],
      { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
    );

    const opacity = Math.min(enterAnimation, exitAnimation);

    const translateY = interpolate(enterAnimation, [0, 1], [40, 0], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });

    const scale = interpolate(enterAnimation, [0, 1], [0.8, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });

    const positionStyles = useMemo(
      () =>
        getPositionStyles(
          mergedStyle.position,
          mergedStyle.positionOffset,
          videoHeight,
        ),
      [mergedStyle.position, mergedStyle.positionOffset, videoHeight],
    );

    const currentTimeInSeconds = frame / fps;

    const containerStyle: React.CSSProperties = {
      fontFamily: mergedStyle.fontFamily,
      fontSize: mergedStyle.fontSize,
      fontWeight: mergedStyle.fontWeight,
      lineHeight: mergedStyle.lineHeight,
      letterSpacing: mergedStyle.letterSpacing,
      opacity,
      transform: `translateY(${translateY}px) scale(${scale})`,
      fontFeatureSettings: '"liga" 1, "calt" 1, "kern" 1',
      WebkitFontSmoothing: 'antialiased',
      MozOsxFontSmoothing: 'grayscale',
      maxWidth: '90%',
      padding: mergedStyle.padding,
      textAlign: 'center',
    };

    return (
      <AbsoluteFill
        style={{
          display: 'flex',
          justifyContent: 'center',
          pointerEvents: 'none',
          ...positionStyles,
        }}
      >
        <div style={containerStyle}>
          {subtitle.words && subtitle.words.length > 0 ? (
            <KaraokeWords
              words={subtitle.words}
              currentTime={currentTimeInSeconds}
              accentColor={ACCENT_COLOR}
              textShadow={mergedStyle.textShadow}
              baseColor={mergedStyle.color}
            />
          ) : (
            <SimpleText
              text={subtitle.text}
              color={mergedStyle.color}
              textShadow={mergedStyle.textShadow}
            />
          )}
        </div>
      </AbsoluteFill>
    );
  },
);

ArabicSubtitle.displayName = 'ArabicSubtitle';

// ═══════════════════════════════════════════════════════════════
// Karaoke Words
// ═══════════════════════════════════════════════════════════════
interface KaraokeWordsProps {
  words: WordTiming[];
  currentTime: number;
  accentColor: string;
  textShadow: string;
  baseColor: string;
}

const KaraokeWords: React.FC<KaraokeWordsProps> = memo(
  ({ words, currentTime, accentColor, textShadow, baseColor }) => {
    const wordsWithState = useMemo<WordState[]>(() => {
      return words.map((word) => {
        const text = getWordText(word);
        const isActive = currentTime >= word.start && currentTime < word.end;
        const isPast = currentTime >= word.end;
        const isFuture = currentTime < word.start;
        return { text, isActive, isPast, isFuture };
      });
    }, [words, currentTime]);

    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'row-reverse',
          flexWrap: 'wrap',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '0.3em',
          direction: 'rtl',
        }}
      >
        {wordsWithState.map((word, index) => (
          <KaraokeWord
            key={`word-${index}`}
            word={word}
            accentColor={accentColor}
            textShadow={textShadow}
            baseColor={baseColor}
          />
        ))}
      </div>
    );
  },
);

KaraokeWords.displayName = 'KaraokeWords';

// ═══════════════════════════════════════════════════════════════
// Single Word
// ═══════════════════════════════════════════════════════════════
interface KaraokeWordProps {
  word: WordState;
  accentColor: string;
  textShadow: string;
  baseColor: string;
}

const KaraokeWord: React.FC<KaraokeWordProps> = memo(
  ({ word, accentColor, textShadow, baseColor }) => {
    const wordStyle = useMemo<React.CSSProperties>(() => {
      const base: React.CSSProperties = {
        display: 'inline-block',
        transition: 'all 0.15s ease-out',
        whiteSpace: 'nowrap',
        padding: '4px 14px',
        borderRadius: '10px',
      };

      if (word.isActive) {
        return {
          ...base,
          color: accentColor,
          opacity: 1,
          transform: 'scale(1.15)',
          fontWeight: 900,
          backgroundColor: 'rgba(255,215,0,0.15)',
          textShadow: `${textShadow}, 0 0 30px rgba(255,215,0,0.8), 0 0 60px rgba(255,215,0,0.4)`,
        };
      }

      if (word.isPast) {
        return {
          ...base,
          color: baseColor,
          opacity: 0.95,
          transform: 'scale(1)',
          backgroundColor: 'transparent',
          textShadow,
        };
      }

      return {
        ...base,
        color: baseColor,
        opacity: 0.5,
        transform: 'scale(0.95)',
        backgroundColor: 'transparent',
        textShadow,
      };
    }, [word, accentColor, textShadow, baseColor]);

    return <span style={wordStyle}>{word.text}</span>;
  },
);

KaraokeWord.displayName = 'KaraokeWord';

// ═══════════════════════════════════════════════════════════════
// Simple Text Fallback
// ═══════════════════════════════════════════════════════════════
interface SimpleTextProps {
  text: string;
  color: string;
  textShadow: string;
}

const SimpleText: React.FC<SimpleTextProps> = memo(
  ({ text, color, textShadow }) => {
    return (
      <div
        style={{
          direction: 'rtl',
          textAlign: 'center',
          unicodeBidi: 'plaintext',
          color,
          textShadow,
        }}
      >
        {text}
      </div>
    );
  },
);

SimpleText.displayName = 'SimpleText';

export default ArabicSubtitle;

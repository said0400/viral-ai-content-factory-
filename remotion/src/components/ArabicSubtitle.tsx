/**
 * 📝 Arabic Subtitle Component v2.0
 * ═══════════════════════════════════════════════════════════════
 * عرض الترجمات العربية باحترافية:
 *   ✓ Karaoke/Highlight لكل كلمة
 *   ✓ توقيت دقيق من Whisper
 *   ✓ RTL صحيح مع row-reverse
 *   ✓ تصميم احترافي
 *   ✓ Performance optimized
 *   ✓ Multiple positions (top/center/bottom)
 * ═══════════════════════════════════════════════════════════════
 */

import { useMemo, memo } from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import type { Subtitle, SubtitleStyle, WordTiming } from '@types/index';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════
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
const DEFAULT_STYLE: Required<
  Pick<
    SubtitleStyle,
    | 'fontSize'
    | 'fontWeight'
    | 'fontFamily'
    | 'color'
    | 'lineHeight'
    | 'letterSpacing'
    | 'position'
    | 'positionOffset'
    | 'padding'
    | 'textShadow'
  >
> = {
  fontSize: 78,
  fontWeight: 900,
  fontFamily: "'Cairo', 'Tajawal', 'Almarai', sans-serif",
  color: '#FFFFFF',
  lineHeight: 1.4,
  letterSpacing: '0em',
  position: 'bottom',
  positionOffset: 0.78,
  padding: '0 40px',
  textShadow: '0 4px 20px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.8)',
};

const ACCENT_COLOR = '#FFD700'; // ذهبي للكلمة الحالية
const EXIT_FRAMES = 5;

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════
const getWordText = (
  word: WordTiming | { text?: string; word?: string },
): string => {
  if ('text' in word && word.text) return word.text;
  if ('word' in word && word.word) return word.word;
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
// Main Component (memoized)
// ═══════════════════════════════════════════════════════════════
export const ArabicSubtitle: React.FC<ArabicSubtitleProps> = memo(
  ({ subtitle, style, isVisible = true, videoWidth, videoHeight }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // مرج الـ style مع الافتراضي
    const mergedStyle = useMemo(
      () => ({ ...DEFAULT_STYLE, ...style }),
      [style],
    );

    // إذا غير مرئي، لا نحسب شيئاً
    if (!isVisible) {
      return null;
    }

    // ─── Time Calculations ─────────────────────────────────────
    const subtitleStartFrame = Math.floor(subtitle.start * fps);
    const subtitleEndFrame = Math.floor(subtitle.end * fps);
    const localFrame = frame - subtitleStartFrame;
    const totalLocalFrames = subtitleEndFrame - subtitleStartFrame;

    // إذا خرجنا من نطاق الـ subtitle
    if (localFrame < 0 || localFrame > totalLocalFrames + 5) {
      return null;
    }

    // ─── Enter Animation ──────────────────────────────────────
    const enterAnimation = spring({
      frame: localFrame,
      fps,
      config: {
        damping: 12,
        stiffness: 120,
        mass: 0.4,
      },
    });

    // ─── Exit Animation ───────────────────────────────────────
    const exitStart = totalLocalFrames - EXIT_FRAMES;
    const exitAnimation = interpolate(
      localFrame,
      [exitStart, totalLocalFrames],
      [1, 0],
      { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
    );

    const opacity = Math.min(enterAnimation, exitAnimation);

    // ─── Transform Animations ─────────────────────────────────
    const translateY = interpolate(enterAnimation, [0, 1], [40, 0], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });

    const scale = interpolate(enterAnimation, [0, 1], [0.8, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });

    // ─── Position ──────────────────────────────────────────────
    const positionStyles = useMemo(
      () =>
        getPositionStyles(
          mergedStyle.position,
          mergedStyle.positionOffset,
          videoHeight,
        ),
      [mergedStyle.position, mergedStyle.positionOffset, videoHeight],
    );

    // ─── Current Time ──────────────────────────────────────────
    const currentTimeInSeconds = frame / fps;

    // ─── Container Style ───────────────────────────────────────
    const containerStyle: React.CSSProperties = {
      fontFamily: mergedStyle.fontFamily,
      fontSize: mergedStyle.fontSize,
      fontWeight: mergedStyle.fontWeight,
      lineHeight: mergedStyle.lineHeight,
      letterSpacing: mergedStyle.letterSpacing,
      
      opacity,
      transform: `translateY(${translateY}px) scale(${scale})`,
      
      // RTL optimization
      fontFeatureSettings: '"liga" 1, "calt" 1, "kern" 1',
      WebkitFontSmoothing: 'antialiased',
      MozOsxFontSmoothing: 'grayscale',
      
      // Layout
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
// 🎤 Karaoke Words Component
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
    // حساب حالات كل الكلمات (memoized)
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
          flexDirection: 'row-reverse', // 🎯 المفتاح للـ RTL
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
// 🔤 Single Word Component
// ═══════════════════════════════════════════════════════════════
interface KaraokeWordProps {
  word: WordState;
  accentColor: string;
  textShadow: string;
  baseColor: string;
}

const KaraokeWord: React.FC<KaraokeWordProps> = memo(
  ({ word, accentColor, textShadow, baseColor }) => {
    // الـ styles المختلفة حسب الحالة
    const wordStyle = useMemo<React.CSSProperties>(() => {
      // Base styles
      const base: React.CSSProperties = {
        display: 'inline-block',
        transition: 'all 0.15s ease-out',
        whiteSpace: 'nowrap',
        // 🎯 padding ثابت لمنع layout shift
        padding: '4px 14px',
        borderRadius: '10px',
      };

      if (word.isActive) {
        // ⭐ Active word - مميزة
        return {
          ...base,
          color: accentColor,
          opacity: 1,
          transform: 'scale(1.15)',
          fontWeight: 900,
          backgroundColor: 'rgba(255,215,0,0.15)',
          textShadow: `
            ${textShadow},
            0 0 30px rgba(255,215,0,0.8),
            0 0 60px rgba(255,215,0,0.4)
          `,
        };
      }

      if (word.isPast) {
        // ✅ Past words - بيضاء عادية
        return {
          ...base,
          color: baseColor,
          opacity: 0.95,
          transform: 'scale(1)',
          backgroundColor: 'transparent',
          textShadow,
        };
      }

      // ⏳ Future words - باهتة
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
// 📝 Simple Text Fallback
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

// ═══════════════════════════════════════════════════════════════
// Default Export
// ═══════════════════════════════════════════════════════════════
export default ArabicSubtitle;

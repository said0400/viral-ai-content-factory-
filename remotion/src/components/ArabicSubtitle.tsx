/**
 * 📝 Arabic Subtitle Component
 * ═══════════════════════════════════════════════════════════════
 * عرض الترجمات العربية بشكل احترافي مع:
 *   ✓ دعم كامل للـ RTL (من اليمين لليسار)
 *   ✓ Arabic Shaping تلقائي (المتصفح يقوم به)
 *   ✓ أنيميشن دخول/خروج سلس
 *   ✓ تأثيرات Glow و Shadow
 *   ✓ دعم تأثير Karaoke (كلمة بكلمة)
 *   ✓ خط Cairo + fallbacks متعددة
 * 
 * هذا هو الحل النهائي لمشكلة العربية في الفيديوهات! ⭐
 * ═══════════════════════════════════════════════════════════════
 */

import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";
import { ArabicSubtitleProps, WordTiming } from "../types";

// ════════════════════════════════════════════════════════════════════
// 📝 Arabic Subtitle Component
// ════════════════════════════════════════════════════════════════════
export const ArabicSubtitle: React.FC<ArabicSubtitleProps> = ({
  subtitle,
  style,
  isVisible,
  videoWidth,
  videoHeight,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ─── حساب الوقت الحالي بالنسبة لبداية الترجمة ───────────────────
  const subtitleStartFrame = Math.floor(subtitle.start * fps);
  const subtitleEndFrame = Math.floor(subtitle.end * fps);
  const localFrame = frame - subtitleStartFrame;
  const totalLocalFrames = subtitleEndFrame - subtitleStartFrame;

  // ─── أنيميشن الدخول (Spring) ────────────────────────────────────
  const enterAnimation = spring({
    frame: localFrame,
    fps,
    config: {
      damping: 12,
      stiffness: 100,
      mass: 0.5,
    },
  });

  // ─── أنيميشن الخروج (آخر 10 frames) ─────────────────────────────
  const exitFrames = 10;
  const exitStart = totalLocalFrames - exitFrames;
  const exitAnimation = interpolate(
    localFrame,
    [exitStart, totalLocalFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // ─── الـ Opacity النهائي ────────────────────────────────────────
  const opacity = isVisible
    ? Math.min(enterAnimation, exitAnimation)
    : 0;

  // ─── أنيميشن التحرك للأعلى عند الدخول ───────────────────────────
  const translateY = interpolate(enterAnimation, [0, 1], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ─── أنيميشن التكبير الخفيف ─────────────────────────────────────
  const scale = interpolate(enterAnimation, [0, 1], [0.92, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ─── حساب موضع الترجمة ──────────────────────────────────────────
  const positionStyles = getPositionStyles(
    style.position || "bottom",
    style.positionOffset || 0.78,
    videoHeight
  );

  // ─── بناء الـ Style النهائي ─────────────────────────────────────
  const subtitleStyle: React.CSSProperties = {
    // ✅ الحل السحري للعربية
    direction: style.direction || "rtl",
    textAlign: style.textAlign || "center",
    unicodeBidi: "plaintext",

    // الخط والحجم
    fontFamily: style.fontFamily,
    fontSize: style.fontSize,
    fontWeight: style.fontWeight,
    color: style.color,
    lineHeight: style.lineHeight || 1.4,
    letterSpacing: style.letterSpacing || "0em",

    // الخلفية
    backgroundColor: style.backgroundColor || "transparent",
    borderRadius: style.borderRadius || 0,
    padding: style.padding || "0 60px",

    // الظل والإضاءة
    textShadow: buildTextShadow(style),

    // الحدود (Stroke)
    WebkitTextStroke: style.stroke
      ? `${style.stroke.width}px ${style.stroke.color}`
      : undefined,

    // الأنيميشن
    opacity,
    transform: `translateY(${translateY}px) scale(${scale})`,

    // تحسينات الخط
    fontFeatureSettings: '"liga" 1, "calt" 1, "kern" 1',
    WebkitFontSmoothing: "antialiased",
    MozOsxFontSmoothing: "grayscale",

    // التفاف النص
    maxWidth: "92%",
    wordWrap: "break-word",
    whiteSpace: "pre-wrap",
  };

  // ════════════════════════════════════════════════════════════════
  // 🎨 الـ Render
  // ════════════════════════════════════════════════════════════════
  return (
    <AbsoluteFill
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        pointerEvents: "none",
        ...positionStyles,
      }}
    >
      <div style={subtitleStyle}>
        {/* إذا كان هناك توقيتات للكلمات → تأثير Karaoke */}
        {subtitle.words && subtitle.words.length > 0 ? (
          <KaraokeText
            words={subtitle.words}
            currentTime={frame / fps}
            highlightColor={style.color}
            normalColor={style.color}
            highlightOpacity={1}
            normalOpacity={0.4}
          />
        ) : (
          // عرض النص العادي
          <span>{subtitle.text}</span>
        )}
      </div>

      {/* طبقة الـ Glow (إذا كانت مفعّلة) */}
      {style.glow?.enabled && (
        <GlowLayer
          text={subtitle.text}
          style={subtitleStyle}
          glow={style.glow}
          opacity={opacity * 0.6}
        />
      )}
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════
// 🎤 Karaoke Effect (تلوين الكلمة الحالية)
// ════════════════════════════════════════════════════════════════════
const KaraokeText: React.FC<{
  words: WordTiming[];
  currentTime: number;
  highlightColor: string;
  normalColor: string;
  highlightOpacity: number;
  normalOpacity: number;
}> = ({
  words,
  currentTime,
  highlightColor,
  normalColor,
  highlightOpacity,
  normalOpacity,
}) => {
  return (
    <span style={{ direction: "rtl", display: "inline" }}>
      {words.map((word, index) => {
        const isActive =
          currentTime >= word.start && currentTime < word.end;
        const isPast = currentTime >= word.end;

        return (
          <span
            key={`word-${index}`}
            style={{
              color: isActive || isPast ? highlightColor : normalColor,
              opacity: isActive
                ? 1
                : isPast
                ? highlightOpacity
                : normalOpacity,
              transition: "all 0.15s ease-out",
              marginLeft: "0.3em",
              display: "inline-block",
              transform: isActive ? "scale(1.08)" : "scale(1)",
              fontWeight: isActive ? 900 : "inherit",
            }}
          >
            {word.text}
          </span>
        );
      })}
    </span>
  );
};

// ════════════════════════════════════════════════════════════════════
// ✨ Glow Layer (طبقة الإضاءة)
// ════════════════════════════════════════════════════════════════════
const GlowLayer: React.FC<{
  text: string;
  style: React.CSSProperties;
  glow: { color: string; blur: number };
  opacity: number;
}> = ({ text, style, glow, opacity }) => {
  return (
    <div
      style={{
        ...style,
        position: "absolute",
        color: "transparent",
        WebkitTextStroke: undefined,
        textShadow: `0 0 ${glow.blur}px ${glow.color}, 0 0 ${
          glow.blur * 2
        }px ${glow.color}`,
        filter: `blur(${glow.blur / 4}px)`,
        opacity,
        zIndex: -1,
      }}
    >
      {text}
    </div>
  );
};

// ════════════════════════════════════════════════════════════════════
// 🎯 دوال مساعدة
// ════════════════════════════════════════════════════════════════════

/**
 * حساب موضع الترجمة بناءً على الإعدادات
 */
const getPositionStyles = (
  position: string,
  offset: number,
  videoHeight: number
): React.CSSProperties => {
  switch (position) {
    case "top":
      return {
        alignItems: "flex-start",
        paddingTop: videoHeight * (1 - offset),
      };

    case "center":
      return {
        alignItems: "center",
      };

    case "bottom":
    default:
      return {
        alignItems: "flex-end",
        paddingBottom: videoHeight * (1 - offset),
      };
  }
};

/**
 * بناء text-shadow احترافي
 */
const buildTextShadow = (style: any): string => {
  // إذا كان text-shadow محدد، استخدمه
  if (style.textShadow) {
    return style.textShadow;
  }

  // text-shadow افتراضي قوي للظهور على أي خلفية
  return [
    "0 4px 20px rgba(0, 0, 0, 0.95)",
    "0 0 40px rgba(0, 0, 0, 0.8)",
    "2px 2px 4px rgba(0, 0, 0, 0.9)",
    "-1px -1px 2px rgba(0, 0, 0, 0.8)",
  ].join(", ");
};

// ════════════════════════════════════════════════════════════════════
// 📦 Export
// ════════════════════════════════════════════════════════════════════
export default ArabicSubtitle;

/**
 * 📝 Arabic Subtitle Component (TikTok Style - Fixed RTL)
 * ═══════════════════════════════════════════════════════════════
 * عرض الترجمات العربية مع:
 *   ✓ تأثير Karaoke/Highlight لكل كلمة
 *   ✓ توقيت دقيق من Whisper
 *   ✓ ترتيب RTL صحيح للكلمات
 *   ✓ تصميم احترافي مثل TikTok
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
import { ArabicSubtitleProps } from "../types";

export const ArabicSubtitle: React.FC<ArabicSubtitleProps> = ({
  subtitle,
  style,
  isVisible,
  videoWidth,
  videoHeight,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ─── حساب الوقت الحالي بالنسبة لبداية الترجمة ────────────────
  const subtitleStartFrame = Math.floor(subtitle.start * fps);
  const subtitleEndFrame = Math.floor(subtitle.end * fps);
  const localFrame = frame - subtitleStartFrame;
  const totalLocalFrames = subtitleEndFrame - subtitleStartFrame;

  // ─── أنيميشن الدخول (Spring) ─────────────────────────────────
  const enterAnimation = spring({
    frame: localFrame,
    fps,
    config: {
      damping: 12,
      stiffness: 120,
      mass: 0.4,
    },
  });

  // ─── أنيميشن الخروج ───────────────────────────────────────────
  const exitFrames = 5;
  const exitStart = totalLocalFrames - exitFrames;
  const exitAnimation = interpolate(
    localFrame,
    [exitStart, totalLocalFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const opacity = isVisible
    ? Math.min(enterAnimation, exitAnimation)
    : 0;

  // ─── أنيميشن التحرك ──────────────────────────────────────────
  const translateY = interpolate(enterAnimation, [0, 1], [40, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const scale = interpolate(enterAnimation, [0, 1], [0.8, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ─── الوقت الحالي بالثواني ────────────────────────────────────
  const currentTimeInSeconds = frame / fps;

  return (
    <AbsoluteFill
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "flex-end",
        paddingBottom: videoHeight * 0.25,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          // الخط
          fontFamily: "'Cairo', 'Tajawal', 'Almarai', sans-serif",
          fontSize: style?.fontSize || 90,
          fontWeight: style?.fontWeight || 900,
          
          // الأنيميشن
          opacity,
          transform: `translateY(${translateY}px) scale(${scale})`,
          
          // التحسينات
          fontFeatureSettings: '"liga" 1, "calt" 1, "kern" 1',
          WebkitFontSmoothing: "antialiased",
          
          // التفاف
          maxWidth: "90%",
          padding: "0 40px",
          lineHeight: 1.5,
          letterSpacing: "0.02em",
        }}
      >
        {/* 🎯 إذا كان هناك words، اعرض كل كلمة بتأثير Karaoke */}
        {subtitle.words && subtitle.words.length > 0 ? (
          <KaraokeWords
            words={subtitle.words}
            currentTime={currentTimeInSeconds}
          />
        ) : (
          // عرض النص العادي
          <SimpleText text={subtitle.text} />
        )}
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════
// 🎤 Karaoke Words (TikTok Style - RTL Fixed)
// ════════════════════════════════════════════════════════════════════
const KaraokeWords: React.FC<{
  words: Array<{ text?: string; word?: string; start: number; end: number }>;
  currentTime: number;
}> = ({ words, currentTime }) => {
  return (
    // ✅ الحل: استخدام flexbox مع row-reverse للـ RTL الصحيح
    <div
      style={{
        display: "flex",
        flexDirection: "row-reverse",  // 🎯 المفتاح السحري للـ RTL!
        flexWrap: "wrap",
        justifyContent: "center",
        alignItems: "center",
        gap: "0.3em",
        direction: "rtl",
      }}
    >
      {words.map((word, index) => {
        // دعم النوعين: word.text أو word.word
        const wordText = word.text || word.word || "";
        const isActive = currentTime >= word.start && currentTime < word.end;
        const isPast = currentTime >= word.end;
        const isFuture = currentTime < word.start;

        // اللون والحالة
        let color = "#FFFFFF";
        let opacity = 1;
        let scale = 1;
        let textShadow = "0 4px 20px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.8)";
        let backgroundColor = "transparent";

        if (isActive) {
          // ⭐ الكلمة الحالية - مميزة بشكل قوي
          color = "#FFD700";  // ذهبي
          opacity = 1;
          scale = 1.15;
          textShadow = `
            0 4px 20px rgba(0,0,0,0.95),
            0 0 30px rgba(255,215,0,0.8),
            0 0 60px rgba(255,215,0,0.4)
          `;
          backgroundColor = "rgba(255,215,0,0.15)";
        } else if (isPast) {
          // ✅ الكلمات السابقة - بيضاء عادية
          color = "#FFFFFF";
          opacity = 0.95;
          scale = 1;
        } else if (isFuture) {
          // ⏳ الكلمات القادمة - باهتة
          color = "rgba(255,255,255,0.5)";
          opacity = 0.5;
          scale = 0.95;
        }

        return (
          <span
            key={`word-${index}`}
            style={{
              color,
              opacity,
              transform: `scale(${scale})`,
              transition: "all 0.15s ease-out",
              display: "inline-block",
              textShadow,
              backgroundColor,
              padding: isActive ? "4px 14px" : "0",
              borderRadius: isActive ? "10px" : "0",
              fontWeight: isActive ? 900 : "inherit",
              whiteSpace: "nowrap",
            }}
          >
            {wordText}
          </span>
        );
      })}
    </div>
  );
};

// ════════════════════════════════════════════════════════════════════
// 📝 Simple Text (fallback)
// ════════════════════════════════════════════════════════════════════
const SimpleText: React.FC<{ text: string }> = ({ text }) => {
  return (
    <div
      style={{
        direction: "rtl",
        textAlign: "center",
        unicodeBidi: "plaintext",
        color: "#FFFFFF",
        textShadow: `
          0 4px 20px rgba(0,0,0,0.95),
          0 0 40px rgba(0,0,0,0.8),
          2px 2px 4px rgba(0,0,0,0.9)
        `,
      }}
    >
      {text}
    </div>
  );
};

export default ArabicSubtitle;

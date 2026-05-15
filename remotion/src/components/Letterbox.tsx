/**
 * 🎞️ Letterbox Component
 * ═══════════════════════════════════════════════════════════════
 * شرائط سوداء سينمائية في الأعلى والأسفل
 * 
 * يضيف لمسة سينمائية احترافية للفيديو:
 *   ✓ شرائط قابلة للتخصيص (سماكة، لون، شفافية)
 *   ✓ ظل خفيف للعمق
 *   ✓ أنيميشن دخول اختياري
 *   ✓ 4 أنماط جاهزة (cinematic, thin, thick, off)
 * ═══════════════════════════════════════════════════════════════
 */

import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
} from "remotion";
import { LetterboxProps } from "../types";

// ════════════════════════════════════════════════════════════════════
// 🎞️ Letterbox Component
// ════════════════════════════════════════════════════════════════════
export const Letterbox: React.FC<LetterboxProps> = ({
  config,
  width,
  height,
}) => {
  const frame = useCurrentFrame();

  // ─── إذا كان معطّل، لا تعرض شيئاً ───────────────────────────────
  if (!config.enabled) {
    return null;
  }

  // ─── حساب أبعاد الشرائط ─────────────────────────────────────────
  const barRatio = config.barRatio || 0.055;
  const barHeight = Math.floor(height * barRatio);
  const barColor = config.color || "#000000";
  const barOpacity = config.opacity || 0.92;

  // ─── أنيميشن الدخول (slide in من الحواف) ────────────────────────
  const slideInFrames = 15;
  const slideProgress = interpolate(
    frame,
    [0, slideInFrames],
    [0, 1],
    { extrapolateRight: "clamp" }
  );

  // ـــ إزاحة الشرائط (تبدأ من خارج الشاشة)
  const topBarOffset = interpolate(slideProgress, [0, 1], [-barHeight, 0]);
  const bottomBarOffset = interpolate(
    slideProgress,
    [0, 1],
    [barHeight, 0]
  );

  // ════════════════════════════════════════════════════════════════
  // 🎨 الـ Render
  // ════════════════════════════════════════════════════════════════
  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        zIndex: 100,
      }}
    >
      {/* ─────────────────────────────────────────────────────────── */}
      {/* ⬛ الشريط العلوي                                            */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: barHeight,
          backgroundColor: barColor,
          opacity: barOpacity,
          transform: `translateY(${topBarOffset}px)`,
          // ظل خفيف لإحساس العمق
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.4)",
        }}
      />

      {/* ─────────────────────────────────────────────────────────── */}
      {/* ⬛ الشريط السفلي                                            */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: "100%",
          height: barHeight,
          backgroundColor: barColor,
          opacity: barOpacity,
          transform: `translateY(${bottomBarOffset}px)`,
          // ظل خفيف من الأعلى
          boxShadow: "0 -4px 20px rgba(0, 0, 0, 0.4)",
        }}
      />

      {/* ─────────────────────────────────────────────────────────── */}
      {/* ✨ خط فاصل خفيف (اختياري - يضيف لمسة احترافية)              */}
      {/* ─────────────────────────────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: barHeight + topBarOffset,
          left: 0,
          width: "100%",
          height: 1,
          backgroundColor: "rgba(255, 255, 255, 0.05)",
          opacity: slideProgress,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: barHeight - bottomBarOffset,
          left: 0,
          width: "100%",
          height: 1,
          backgroundColor: "rgba(255, 255, 255, 0.05)",
          opacity: slideProgress,
        }}
      />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════
// 🎬 Letterbox مع نص (للعنوان أو معلومات إضافية)
// ════════════════════════════════════════════════════════════════════
interface LetterboxWithTextProps extends LetterboxProps {
  topText?: string;
  bottomText?: string;
  textColor?: string;
  textSize?: number;
}

export const LetterboxWithText: React.FC<LetterboxWithTextProps> = ({
  config,
  width,
  height,
  topText,
  bottomText,
  textColor = "rgba(255, 255, 255, 0.7)",
  textSize = 24,
}) => {
  if (!config.enabled) return null;

  const barRatio = config.barRatio || 0.055;
  const barHeight = Math.floor(height * barRatio);

  return (
    <>
      {/* الشرائط الأساسية */}
      <Letterbox config={config} width={width} height={height} />

      {/* النص العلوي (إذا وُجد) */}
      {topText && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: barHeight,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: textColor,
            fontSize: textSize,
            fontFamily: "'Cairo', sans-serif",
            fontWeight: 600,
            direction: "rtl",
            zIndex: 101,
            pointerEvents: "none",
          }}
        >
          {topText}
        </div>
      )}

      {/* النص السفلي (إذا وُجد) */}
      {bottomText && (
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            width: "100%",
            height: barHeight,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: textColor,
            fontSize: textSize,
            fontFamily: "'Cairo', sans-serif",
            fontWeight: 600,
            direction: "rtl",
            zIndex: 101,
            pointerEvents: "none",
          }}
        >
          {bottomText}
        </div>
      )}
    </>
  );
};

// ════════════════════════════════════════════════════════════════════
// 🎨 Letterbox بألوان متدرجة (للمشاهد الخاصة)
// ════════════════════════════════════════════════════════════════════
interface GradientLetterboxProps extends LetterboxProps {
  gradient?: string;
}

export const GradientLetterbox: React.FC<GradientLetterboxProps> = ({
  config,
  width,
  height,
  gradient = "linear-gradient(180deg, #000000 0%, #1a1a2e 100%)",
}) => {
  if (!config.enabled) return null;

  const barHeight = Math.floor(height * (config.barRatio || 0.055));

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 100 }}>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: barHeight,
          background: gradient,
          opacity: config.opacity || 0.92,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: "100%",
          height: barHeight,
          background: gradient,
          opacity: config.opacity || 0.92,
          transform: "rotate(180deg)",
        }}
      />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════
// 📦 Export
// ════════════════════════════════════════════════════════════════════
export default Letterbox;

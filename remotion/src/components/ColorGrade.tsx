/**
 * 🎨 Color Grade Component
 * ═══════════════════════════════════════════════════════════════
 * التدرج اللوني السينمائي (Cinematic Color Grading)
 * 
 * يحوّل الفيديو من عادي إلى سينمائي احترافي عبر:
 *   ✓ CSS Filters (contrast, saturation, brightness)
 *   ✓ Color Tinting (طبقة لون فوق الفيديو)
 *   ✓ Blend Modes احترافية
 *   ✓ 5 أنماط جاهزة (warm, cool, dramatic, natural, off)
 * 
 * هذا ما يُعطي الفيديو "اللوك السينمائي" 🎬
 * ═══════════════════════════════════════════════════════════════
 */

import React from "react";
import { AbsoluteFill } from "remotion";
import { ColorGradeProps, GradeConfig } from "../types";

// ════════════════════════════════════════════════════════════════════
// 🎨 Color Grade Component
// ════════════════════════════════════════════════════════════════════
export const ColorGrade: React.FC<ColorGradeProps> = ({
  config,
  children,
}) => {
  // ─── إذا لم يكن هناك إعدادات أو معطّل ───────────────────────────
  if (!config || config.name === "off") {
    return <>{children}</>;
  }

  // ─── بناء CSS Filter ────────────────────────────────────────────
  const cssFilter = config.filter || buildDefaultFilter(config);

  // ─── الـ Tint (طبقة لون) ────────────────────────────────────────
  const tintStyle = config.tint
    ? buildTintStyle(config.tint)
    : null;

  // ════════════════════════════════════════════════════════════════
  // 🎨 الـ Render
  // ════════════════════════════════════════════════════════════════
  return (
    <AbsoluteFill
      style={{
        filter: cssFilter,
      }}
    >
      {/* المحتوى (الفيديو + النصوص) */}
      {children}

      {/* طبقة الـ Tint اللوني (فوق المحتوى) */}
      {tintStyle && (
        <AbsoluteFill
          style={{
            ...tintStyle,
            pointerEvents: "none",
          }}
        />
      )}
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════
// 🛠️ بناء CSS Filter من الإعدادات
// ════════════════════════════════════════════════════════════════════
const buildDefaultFilter = (config: GradeConfig): string => {
  // الإعدادات الافتراضية
  const defaults = {
    contrast: 1.15,
    saturate: 1.12,
    brightness: 0.95,
  };

  // اختيار الإعدادات حسب الـ preset
  switch (config.name) {
    case "cinematic_warm":
      return "contrast(1.15) saturate(1.12) brightness(0.95)";

    case "cinematic_cool":
      return "contrast(1.18) saturate(1.05) brightness(0.92)";

    case "dramatic_dark":
      return "contrast(1.25) saturate(0.95) brightness(0.85)";

    case "natural":
      return "contrast(1.05) saturate(1.0) brightness(1.0)";

    default:
      return `contrast(${defaults.contrast}) saturate(${defaults.saturate}) brightness(${defaults.brightness})`;
  }
};

// ════════════════════════════════════════════════════════════════════
// 🎨 بناء Tint Style (طبقة اللون)
// ════════════════════════════════════════════════════════════════════
const buildTintStyle = (tint: {
  r: number;
  g: number;
  b: number;
}): React.CSSProperties => {
  // تحويل الـ RGB multipliers إلى لون شفاف
  const r = Math.floor(tint.r * 128);
  const g = Math.floor(tint.g * 128);
  const b = Math.floor(tint.b * 128);

  return {
    backgroundColor: `rgba(${r}, ${g}, ${b}, 0.08)`,
    mixBlendMode: "soft-light" as const,
  };
};

// ════════════════════════════════════════════════════════════════════
// 🎬 Cinematic Wrapper (للاستخدام السريع)
// ════════════════════════════════════════════════════════════════════
interface CinematicWrapperProps {
  preset?: "warm" | "cool" | "dramatic" | "natural";
  children: React.ReactNode;
}

export const CinematicWrapper: React.FC<CinematicWrapperProps> = ({
  preset = "warm",
  children,
}) => {
  const presets: Record<string, GradeConfig> = {
    warm: {
      name: "cinematic_warm",
      filter: "contrast(1.15) saturate(1.12) brightness(0.95)",
      tint: { r: 1.05, g: 1.0, b: 0.95 },
    },
    cool: {
      name: "cinematic_cool",
      filter: "contrast(1.18) saturate(1.05) brightness(0.92)",
      tint: { r: 0.95, g: 1.0, b: 1.08 },
    },
    dramatic: {
      name: "dramatic_dark",
      filter: "contrast(1.25) saturate(0.95) brightness(0.85)",
      tint: { r: 0.92, g: 0.95, b: 1.0 },
    },
    natural: {
      name: "natural",
      filter: "contrast(1.05) saturate(1.0) brightness(1.0)",
    },
  };

  return (
    <ColorGrade config={presets[preset]}>{children}</ColorGrade>
  );
};

// ════════════════════════════════════════════════════════════════════
// 🌈 Custom Color Grade (للتخصيص الكامل)
// ════════════════════════════════════════════════════════════════════
interface CustomColorGradeProps {
  contrast?: number;
  saturate?: number;
  brightness?: number;
  hue?: number;
  blur?: number;
  invert?: boolean;
  sepia?: number;
  tint?: { r: number; g: number; b: number };
  tintOpacity?: number;
  blendMode?: React.CSSProperties["mixBlendMode"];
  children: React.ReactNode;
}

export const CustomColorGrade: React.FC<CustomColorGradeProps> = ({
  contrast = 1.0,
  saturate = 1.0,
  brightness = 1.0,
  hue = 0,
  blur = 0,
  invert = false,
  sepia = 0,
  tint,
  tintOpacity = 0.08,
  blendMode = "soft-light",
  children,
}) => {
  // بناء CSS Filter
  const filters = [
    `contrast(${contrast})`,
    `saturate(${saturate})`,
    `brightness(${brightness})`,
    hue !== 0 && `hue-rotate(${hue}deg)`,
    blur > 0 && `blur(${blur}px)`,
    invert && `invert(1)`,
    sepia > 0 && `sepia(${sepia})`,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <AbsoluteFill style={{ filter: filters }}>
      {children}

      {/* طبقة الـ Tint */}
      {tint && (
        <AbsoluteFill
          style={{
            backgroundColor: `rgba(${Math.floor(tint.r * 128)}, ${Math.floor(
              tint.g * 128
            )}, ${Math.floor(tint.b * 128)}, ${tintOpacity})`,
            mixBlendMode: blendMode,
            pointerEvents: "none",
          }}
        />
      )}
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════
// 🎞️ Film Look Presets (أنماط فيلم سينمائي)
// ════════════════════════════════════════════════════════════════════
export const FilmLookPresets = {
  // فيلم كلاسيكي دافئ (مثل Wes Anderson)
  classicFilm: {
    contrast: 1.2,
    saturate: 1.15,
    brightness: 0.95,
    tint: { r: 1.08, g: 1.0, b: 0.92 },
    tintOpacity: 0.1,
  },

  // فيلم نوار أبيض وأسود
  filmNoir: {
    contrast: 1.5,
    saturate: 0.0,
    brightness: 0.9,
    tint: { r: 0.95, g: 0.95, b: 1.05 },
    tintOpacity: 0.05,
  },

  // فيلم درامي مظلم (مثل Christopher Nolan)
  darkDrama: {
    contrast: 1.35,
    saturate: 0.85,
    brightness: 0.8,
    tint: { r: 0.85, g: 0.9, b: 1.0 },
    tintOpacity: 0.12,
  },

  // فيلم Vintage
  vintage: {
    contrast: 1.1,
    saturate: 0.85,
    brightness: 1.05,
    sepia: 0.3,
    tint: { r: 1.1, g: 1.0, b: 0.85 },
    tintOpacity: 0.15,
  },

  // Cyberpunk
  cyberpunk: {
    contrast: 1.3,
    saturate: 1.4,
    brightness: 0.9,
    hue: 10,
    tint: { r: 0.9, g: 0.85, b: 1.15 },
    tintOpacity: 0.12,
  },

  // Sunset (غروب الشمس)
  sunset: {
    contrast: 1.2,
    saturate: 1.25,
    brightness: 1.05,
    hue: -5,
    tint: { r: 1.15, g: 0.95, b: 0.85 },
    tintOpacity: 0.12,
  },
};

// ════════════════════════════════════════════════════════════════════
// 📦 Export
// ════════════════════════════════════════════════════════════════════
export default ColorGrade;

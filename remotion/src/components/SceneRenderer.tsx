/**
 * 🎬 Scene Renderer Component
 * ═══════════════════════════════════════════════════════════════
 * مدير المشهد الواحد - يجمع كل عناصر المشهد:
 *   ✓ خلفية الفيديو (BackgroundVideo)
 *   ✓ تأثيرات الزوم والاهتزاز
 *   ✓ Fade In/Out للمشهد
 *   ✓ معالجة المشاهد بدون فيديو (Fallback)
 *   ✓ تأثيرات إضافية (Vignette, Grain)
 * ═══════════════════════════════════════════════════════════════
 */

import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from "remotion";
import { SceneRendererProps } from "../types";
import { BackgroundVideo } from "./BackgroundVideo";

// ════════════════════════════════════════════════════════════════════
// 🎬 Scene Renderer Component
// ════════════════════════════════════════════════════════════════════
export const SceneRenderer: React.FC<SceneRendererProps> = ({
  scene,
  isActive,
  fps,
  effects,
}) => {
  const frame = useCurrentFrame();
  const { width, height, durationInFrames } = useVideoConfig();

  // ─── Fade In للمشهد ──────────────────────────────────────────
  const fadeInFrames = 8;
  const fadeInOpacity = interpolate(
    frame,
    [0, fadeInFrames],
    [0, 1],
    { extrapolateRight: "clamp" }
  );

  // ─── Fade Out للمشهد ─────────────────────────────────────────
  const fadeOutFrames = 8;
  const fadeOutStart = durationInFrames - fadeOutFrames;
  const fadeOutOpacity = interpolate(
    frame,
    [fadeOutStart, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp" }
  );

  // ─── Opacity النهائي ─────────────────────────────────────────
  const sceneOpacity = isActive
    ? Math.min(fadeInOpacity, fadeOutOpacity)
    : 0;

  // ════════════════════════════════════════════════════════════════
  // 🎨 Render
  // ════════════════════════════════════════════════════════════════
  return (
    <AbsoluteFill
      style={{
        opacity: sceneOpacity,
        backgroundColor: "#000000",
      }}
    >
      {/* 🎬 خلفية الفيديو */}
      <BackgroundVideo
        src={scene.backgroundPath}
        duration={scene.totalLength}
        zoomEffect={scene.zoomEffect}
        shake={scene.shake}
        width={width}
        height={height}
      />

      {/* 🌑 Vignette (تعتيم الزوايا) */}
      {effects?.grade?.vignette && (
        <Vignette
          intensity={effects.grade.vignetteIntensity || 0.5}
        />
      )}

      {/* 📺 Film Grain (حبيبات الفيلم) */}
      {effects?.grade?.grain && (
        <FilmGrain
          intensity={effects.grade.grainIntensity || 0.04}
        />
      )}

      {/* ⚡ Hook Flash (للـ hook فقط) */}
      {scene.type === "hook" && <HookFlash />}

      {/* ✨ CTA Glow (للـ cta فقط) */}
      {scene.type === "cta" && <CTAGlow />}
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════════════
// 🌑 Vignette Effect
// ════════════════════════════════════════════════════════════════════
const Vignette: React.FC<{ intensity: number }> = ({ intensity }) => {
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(
          ellipse at center,
          transparent 30%,
          rgba(0, 0, 0, ${intensity}) 100%
        )`,
        pointerEvents: "none",
      }}
    />
  );
};

// ════════════════════════════════════════════════════════════════════
// 📺 Film Grain
// ════════════════════════════════════════════════════════════════════
const FilmGrain: React.FC<{ intensity: number }> = ({ intensity }) => {
  const frame = useCurrentFrame();

  const offsetX = (frame * 17) % 100;
  const offsetY = (frame * 23) % 100;

  return (
    <AbsoluteFill
      style={{
        backgroundImage: `
          repeating-radial-gradient(
            circle at ${offsetX}% ${offsetY}%,
            rgba(255, 255, 255, ${intensity}) 0px,
            transparent 1px,
            transparent 2px
          )
        `,
        opacity: 0.6,
        mixBlendMode: "overlay",
        pointerEvents: "none",
      }}
    />
  );
};

// ════════════════════════════════════════════════════════════════════
// ⚡ Hook Flash
// ════════════════════════════════════════════════════════════════════
const HookFlash: React.FC = () => {
  const frame = useCurrentFrame();

  const flashOpacity = interpolate(
    frame,
    [0, 3, 8],
    [0.3, 0.15, 0],
    { extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "white",
        opacity: flashOpacity,
        pointerEvents: "none",
      }}
    />
  );
};

// ════════════════════════════════════════════════════════════════════
// ✨ CTA Glow
// ════════════════════════════════════════════════════════════════════
const CTAGlow: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const pulseOpacity = interpolate(
    Math.sin((frame / fps) * Math.PI),
    [-1, 1],
    [0.05, 0.15]
  );

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(
          ellipse at center,
          rgba(255, 215, 0, ${pulseOpacity}) 0%,
          transparent 60%
        )`,
        pointerEvents: "none",
        mixBlendMode: "screen",
      }}
    />
  );
};

// ════════════════════════════════════════════════════════════════════
// 📦 Export
// ════════════════════════════════════════════════════════════════════
export default SceneRenderer;

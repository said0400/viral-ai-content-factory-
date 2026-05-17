/**
 * 🎬 Scene Renderer v2.0 — مع انتقالات أنعم
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

export const SceneRenderer: React.FC<SceneRendererProps> = ({
  scene,
  isActive,
  fps,
  effects,
}) => {
  const frame = useCurrentFrame();
  const { width, height, durationInFrames } = useVideoConfig();

  // 🆕 انتقالات أنعم (12 frames = 0.4s بدلاً من 0.27s)
  const fadeInFrames = 12;
  const fadeInOpacity = interpolate(
    frame, [0, fadeInFrames], [0, 1],
    { extrapolateRight: "clamp" }
  );

  const fadeOutFrames = 12;
  const fadeOutStart = durationInFrames - fadeOutFrames;
  const fadeOutOpacity = interpolate(
    frame, [fadeOutStart, durationInFrames], [1, 0],
    { extrapolateLeft: "clamp" }
  );

  const sceneOpacity = isActive
    ? Math.min(fadeInOpacity, fadeOutOpacity)
    : 0;

  return (
    <AbsoluteFill style={{ opacity: sceneOpacity, backgroundColor: "#000000" }}>
      <BackgroundVideo
        src={scene.backgroundPath}
        duration={scene.totalLength}
        zoomEffect={scene.zoomEffect}
        shake={scene.shake}
        width={width}
        height={height}
      />

      {effects?.grade?.vignette && (
        <Vignette intensity={effects.grade.vignetteIntensity || 0.5} />
      )}

      {effects?.grade?.grain && (
        <FilmGrain intensity={effects.grade.grainIntensity || 0.04} />
      )}

      {scene.type === "hook" && <HookFlash />}
      {scene.type === "cta" && <CTAGlow />}
    </AbsoluteFill>
  );
};

const Vignette: React.FC<{ intensity: number }> = ({ intensity }) => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,${intensity}) 100%)`,
      pointerEvents: "none",
    }}
  />
);

const FilmGrain: React.FC<{ intensity: number }> = ({ intensity }) => {
  const frame = useCurrentFrame();
  const offsetX = (frame * 17) % 100;
  const offsetY = (frame * 23) % 100;
  return (
    <AbsoluteFill
      style={{
        backgroundImage: `repeating-radial-gradient(circle at ${offsetX}% ${offsetY}%, rgba(255,255,255,${intensity}) 0px, transparent 1px, transparent 2px)`,
        opacity: 0.6, mixBlendMode: "overlay", pointerEvents: "none",
      }}
    />
  );
};

const HookFlash: React.FC = () => {
  const frame = useCurrentFrame();
  const flashOpacity = interpolate(frame, [0, 3, 8], [0.3, 0.15, 0], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: "white", opacity: flashOpacity, pointerEvents: "none" }} />
  );
};

const CTAGlow: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pulseOpacity = interpolate(Math.sin((frame / fps) * Math.PI), [-1, 1], [0.05, 0.15]);
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at center, rgba(255,215,0,${pulseOpacity}) 0%, transparent 60%)`,
        pointerEvents: "none", mixBlendMode: "screen",
      }}
    />
  );
};

export default SceneRenderer;

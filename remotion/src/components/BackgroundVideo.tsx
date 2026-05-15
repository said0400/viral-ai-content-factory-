/**
 * 🎬 Background Video Component
 * ═══════════════════════════════════════════════════════════════
 * عرض فيديو الخلفية مع تأثيرات احترافية
 * ═══════════════════════════════════════════════════════════════
 */

import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Loop,
} from "remotion";
import { BackgroundVideoProps, ZoomType } from "../types";

export const BackgroundVideo: React.FC<BackgroundVideoProps> = ({
  src,
  duration,
  zoomEffect = "slow_zoom_in",
  shake = false,
  width,
  height,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const zoomTransform = calculateZoom(zoomEffect, frame, durationInFrames);

  const shakeTransform = shake
    ? calculateShake(frame, fps, 2.0)
    : { x: 0, y: 0 };

  const combinedTransform = `
    scale(${zoomTransform.scale})
    translate(${zoomTransform.x + shakeTransform.x}px, ${
    zoomTransform.y + shakeTransform.y
  }px)
  `;

  if (!src) {
    return <FallbackBackground width={width} height={height} />;
  }

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        backgroundColor: "#000000",
      }}
    >
      <div
        style={{
          width: "100%",
          height: "100%",
          transform: combinedTransform,
          transformOrigin: "center center",
          willChange: "transform",
        }}
      >
        <Loop durationInFrames={durationInFrames}>
          <OffthreadVideo
            src={src}
            muted
            volume={0}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              objectPosition: "center",
            }}
            onError={(e) => {
              console.warn("⚠ Video load error:", e);
            }}
          />
        </Loop>
      </div>

      <AbsoluteFill
        style={{
          backgroundColor: "rgba(0, 0, 0, 0.25)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};

const calculateZoom = (
  zoomType: ZoomType,
  frame: number,
  totalFrames: number
): { scale: number; x: number; y: number } => {
  const progress = totalFrames > 0 ? frame / totalFrames : 0;

  switch (zoomType) {
    case "slow_zoom_in":
      return {
        scale: interpolate(progress, [0, 1], [1.0, 1.12], {
          extrapolateRight: "clamp",
        }),
        x: 0,
        y: 0,
      };

    case "slow_zoom_out":
      return {
        scale: interpolate(progress, [0, 1], [1.12, 1.0], {
          extrapolateRight: "clamp",
        }),
        x: 0,
        y: 0,
      };

    case "punch_zoom":
      return {
        scale: interpolate(
          progress,
          [0, 0.15, 1],
          [1.0, 1.15, 1.10],
          { extrapolateRight: "clamp" }
        ),
        x: 0,
        y: 0,
      };

    case "drift_right":
      return {
        scale: 1.06,
        x: interpolate(progress, [0, 1], [0, -50], {
          extrapolateRight: "clamp",
        }),
        y: 0,
      };

    case "drift_left":
      return {
        scale: 1.06,
        x: interpolate(progress, [0, 1], [-50, 0], {
          extrapolateRight: "clamp",
        }),
        y: 0,
      };

    case "drift_up":
      return {
        scale: 1.06,
        x: 0,
        y: interpolate(progress, [0, 1], [0, -50], {
          extrapolateRight: "clamp",
        }),
      };

    case "drift_down":
      return {
        scale: 1.06,
        x: 0,
        y: interpolate(progress, [0, 1], [-50, 0], {
          extrapolateRight: "clamp",
        }),
      };

    case "static":
    default:
      return { scale: 1.0, x: 0, y: 0 };
  }
};

const calculateShake = (
  frame: number,
  fps: number,
  intensity: number
): { x: number; y: number } => {
  const time = frame / fps;
  const x = intensity * Math.sin(2 * Math.PI * time * 0.7);
  const y = intensity * Math.cos(2 * Math.PI * time * 1.1);
  return { x, y };
};

const FallbackBackground: React.FC<{
  width: number;
  height: number;
}> = ({ width, height }) => {
  const frame = useCurrentFrame();

  const hueRotate = interpolate(frame, [0, 300], [0, 30], {
    extrapolateRight: "extend",
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, 
          #1a1a2e 0%, 
          #16213e 50%, 
          #0f3460 100%
        )`,
        filter: `hue-rotate(${hueRotate}deg)`,
      }}
    >
      <AbsoluteFill
        style={{
          backgroundImage: `radial-gradient(
            circle at 50% 50%,
            rgba(255, 255, 255, 0.05) 0%,
            transparent 70%
          )`,
        }}
      />
    </AbsoluteFill>
  );
};

export default BackgroundVideo;

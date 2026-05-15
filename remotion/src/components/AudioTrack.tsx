/**
 * 🎵 Audio Track Component
 * ═══════════════════════════════════════════════════════════════
 * تشغيل الصوت في الفيديو مع Fade In/Out تلقائي
 * يستخدم staticFile() لتحميل الصوت من public/
 * ═══════════════════════════════════════════════════════════════
 */

import React from "react";
import {
  Audio,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  staticFile,
} from "remotion";
import { AudioTrackProps } from "../types";

export const AudioTrack: React.FC<AudioTrackProps> = ({
  src,
  volume = 1,
  startFrom,
  endAt,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  if (!src) {
    console.warn("⚠ AudioTrack: No audio source provided");
    return null;
  }

  // 🆕 استخدام staticFile() لتحويل المسار النسبي
  const audioSrc = src.startsWith("http") || src.startsWith("file://")
    ? src
    : staticFile(src);

  // Fade In (أول 0.5 ثانية)
  const fadeInFrames = Math.floor(0.5 * fps);
  const fadeInVolume = interpolate(
    frame,
    [0, fadeInFrames],
    [0, volume],
    { extrapolateRight: "clamp" }
  );

  // Fade Out (آخر 0.5 ثانية)
  const fadeOutFrames = Math.floor(0.5 * fps);
  const fadeOutStart = durationInFrames - fadeOutFrames;
  const fadeOutVolume = interpolate(
    frame,
    [fadeOutStart, durationInFrames],
    [volume, 0],
    { extrapolateLeft: "clamp" }
  );

  const finalVolume = Math.min(fadeInVolume, fadeOutVolume);

  return (
    <Audio
      src={audioSrc}
      volume={finalVolume}
      startFrom={startFrom}
      endAt={endAt}
    />
  );
};

export default AudioTrack;

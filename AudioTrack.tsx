/**
 * 🎵 Audio Track Component
 * ═══════════════════════════════════════════════════════════════
 * تشغيل الصوت في الفيديو مع:
 *   ✓ تحكم كامل في الـ Volume
 *   ✓ Fade In / Fade Out تلقائي
 *   ✓ دعم بداية ونهاية مخصصة
 *   ✓ معالجة آمنة للأخطاء
 * 
 * يدعم: MP3, WAV, M4A, OGG, FLAC
 * ═══════════════════════════════════════════════════════════════
 */

import React from "react";
import {
  Audio,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from "remotion";
import { AudioTrackProps } from "../types";

// ════════════════════════════════════════════════════════════════════
// 🎵 Audio Track Component
// ════════════════════════════════════════════════════════════════════
export const AudioTrack: React.FC<AudioTrackProps> = ({
  src,
  volume = 1,
  startFrom,
  endAt,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // ─── الحماية: إذا لم يكن هناك مصدر، لا تعرض شيئاً ───────────────
  if (!src) {
    console.warn("⚠ AudioTrack: No audio source provided");
    return null;
  }

  // ─── حساب Fade In (أول 0.5 ثانية) ───────────────────────────────
  const fadeInFrames = Math.floor(0.5 * fps);
  const fadeInVolume = interpolate(
    frame,
    [0, fadeInFrames],
    [0, volume],
    { extrapolateRight: "clamp" }
  );

  // ─── حساب Fade Out (آخر 0.5 ثانية) ──────────────────────────────
  const fadeOutFrames = Math.floor(0.5 * fps);
  const fadeOutStart = durationInFrames - fadeOutFrames;
  const fadeOutVolume = interpolate(
    frame,
    [fadeOutStart, durationInFrames],
    [volume, 0],
    { extrapolateLeft: "clamp" }
  );

  // ─── الـ Volume النهائي (الأقل بين الاثنين) ─────────────────────
  const finalVolume = Math.min(fadeInVolume, fadeOutVolume);

  // ════════════════════════════════════════════════════════════════
  // 🎨 الـ Render
  // ════════════════════════════════════════════════════════════════
  return (
    <Audio
      src={src}
      volume={finalVolume}
      startFrom={startFrom}
      endAt={endAt}
      // معالجة الأخطاء
      onError={(error) => {
        console.error("❌ Audio load error:", error);
      }}
    />
  );
};

// ════════════════════════════════════════════════════════════════════
// 🎵 Multiple Audio Tracks (للموسيقى + الصوت معاً)
// ════════════════════════════════════════════════════════════════════
interface MultipleAudioProps {
  voicePath?: string;
  musicPath?: string;
  voiceVolume?: number;
  musicVolume?: number;
}

export const MultipleAudioTracks: React.FC<MultipleAudioProps> = ({
  voicePath,
  musicPath,
  voiceVolume = 1.0,
  musicVolume = 0.15,
}) => {
  return (
    <>
      {/* 🎙️ صوت التعليق (Voice) */}
      {voicePath && (
        <AudioTrack src={voicePath} volume={voiceVolume} />
      )}

      {/* 🎵 موسيقى الخلفية (Background Music) */}
      {musicPath && (
        <AudioTrack src={musicPath} volume={musicVolume} />
      )}
    </>
  );
};

// ════════════════════════════════════════════════════════════════════
// 🎤 Audio Track مع Custom Volume Curve
// ════════════════════════════════════════════════════════════════════
interface CustomVolumeAudioProps extends AudioTrackProps {
  volumeCurve?: Array<{ time: number; volume: number }>;
}

export const CustomVolumeAudio: React.FC<CustomVolumeAudioProps> = ({
  src,
  volume = 1,
  startFrom,
  endAt,
  volumeCurve,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!src) return null;

  // ─── حساب الـ Volume من الـ Curve ───────────────────────────────
  let currentVolume = volume;

  if (volumeCurve && volumeCurve.length > 0) {
    const currentTime = frame / fps;

    // إيجاد النقطتين المحيطتين بالوقت الحالي
    let prevPoint = volumeCurve[0];
    let nextPoint = volumeCurve[volumeCurve.length - 1];

    for (let i = 0; i < volumeCurve.length - 1; i++) {
      if (
        currentTime >= volumeCurve[i].time &&
        currentTime <= volumeCurve[i + 1].time
      ) {
        prevPoint = volumeCurve[i];
        nextPoint = volumeCurve[i + 1];
        break;
      }
    }

    // Interpolation بين النقطتين
    currentVolume = interpolate(
      currentTime,
      [prevPoint.time, nextPoint.time],
      [prevPoint.volume, nextPoint.volume],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  }

  return (
    <Audio
      src={src}
      volume={currentVolume}
      startFrom={startFrom}
      endAt={endAt}
    />
  );
};

// ════════════════════════════════════════════════════════════════════
// 📦 Export
// ════════════════════════════════════════════════════════════════════
export default AudioTrack;

/**
 * 🎬 ShortsVideo Composition
 * ═══════════════════════════════════════════════════════════════
 * الـ Composition الرئيسي لفيديو شورتس عمودي 1080x1920
 * 
 * يجمع:
 *   • خلفيات الفيديو (Background)
 *   • الترجمات العربية (ArabicSubtitle)
 *   • الصوت (AudioTrack)
 *   • التأثيرات (Letterbox, ColorGrade)
 *   • الانتقالات بين المشاهد
 * 
 * يستقبل props كاملة من Python (build_props_for_remotion)
 * ═══════════════════════════════════════════════════════════════
 */

import React, { useEffect } from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from "remotion";
import { VideoProps } from "../types";
import { loadCairoFont } from "../load-fonts";
import { SceneRenderer } from "../components/SceneRenderer";
import { ArabicSubtitle } from "../components/ArabicSubtitle";
import { AudioTrack } from "../components/AudioTrack";
import { Letterbox } from "../components/Letterbox";
import { ColorGrade } from "../components/ColorGrade";

// ════════════════════════════════════════════════════════════════════
// 🎬 ShortsVideo Composition
// ════════════════════════════════════════════════════════════════════
export const ShortsVideo: React.FC<VideoProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();

  // ─── تحميل الخط العربي ──────────────────────────────────────────
  useEffect(() => {
    loadCairoFont();
  }, []);

  // ─── حساب الوقت الحالي بالثانية ─────────────────────────────────
  const currentTimeInSeconds = frame / fps;

  // ─── الحماية من البيانات المفقودة ───────────────────────────────
  const {
    scenes = [],
    subtitles = [],
    audioPath = "",
    effects = {},
    subtitleStyle,
    design,
  } = props;

  // ─── تأثير Fade In/Out العام ────────────────────────────────────
  const fadeInDuration = effects?.fade?.fadeIn?.duration || 0;
  const fadeOutDuration = effects?.fade?.fadeOut?.duration || 0;
  const fadeInFrames = Math.floor(fadeInDuration * fps);
  const fadeOutFrames = Math.floor(fadeOutDuration * fps);

  const fadeInOpacity = interpolate(
    frame,
    [0, fadeInFrames],
    [0, 1],
    { extrapolateRight: "clamp" }
  );

  const fadeOutOpacity = interpolate(
    frame,
    [durationInFrames - fadeOutFrames, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp" }
  );

  const globalOpacity = Math.min(fadeInOpacity, fadeOutOpacity);

  // ─── إيجاد الترجمة الحالية ──────────────────────────────────────
  const currentSubtitle = subtitles.find(
    (sub) =>
      currentTimeInSeconds >= sub.start && currentTimeInSeconds < sub.end
  );

  // ════════════════════════════════════════════════════════════════
  // 🎨 الـ Render
  // ════════════════════════════════════════════════════════════════
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#000000",
        overflow: "hidden",
        opacity: globalOpacity,
      }}
    >
      {/* ─────────────────────────────────────────────────────────── */}
      {/* 🎨 1. التدرج اللوني السينمائي (يلف كل شيء)                  */}
      {/* ─────────────────────────────────────────────────────────── */}
      <ColorGrade config={effects?.grade}>
        
        {/* ─────────────────────────────────────────────────────── */}
        {/* 🎬 2. المشاهد (الخلفيات + التأثيرات)                    */}
        {/* ─────────────────────────────────────────────────────── */}
        <AbsoluteFill>
          {scenes.map((scene, index) => {
            const startFrame = Math.floor(scene.startTime * fps);
            const sceneDurationFrames = Math.floor(
              scene.totalLength * fps
            );

            return (
              <Sequence
                key={`scene-${scene.id}-${index}`}
                from={startFrame}
                durationInFrames={sceneDurationFrames}
                name={`Scene ${index + 1}: ${scene.type}`}
              >
                <SceneRenderer
                  scene={scene}
                  isActive={true}
                  fps={fps}
                  effects={effects}
                />
              </Sequence>
            );
          })}
        </AbsoluteFill>

        {/* ─────────────────────────────────────────────────────── */}
        {/* 🎞️ 3. Letterbox (الشرائط السوداء السينمائية)            */}
        {/* ─────────────────────────────────────────────────────── */}
        {effects?.letterbox?.enabled && (
          <Letterbox
            config={effects.letterbox}
            width={width}
            height={height}
          />
        )}

        {/* ─────────────────────────────────────────────────────── */}
        {/* 📝 4. الترجمات العربية (دائماً في المقدمة)              */}
        {/* ─────────────────────────────────────────────────────── */}
        {currentSubtitle && (
          <ArabicSubtitle
            subtitle={currentSubtitle}
            style={subtitleStyle}
            isVisible={true}
            videoWidth={width}
            videoHeight={height}
          />
        )}

      </ColorGrade>

      {/* ─────────────────────────────────────────────────────────── */}
      {/* 🎵 5. الصوت (لا يحتاج render، فقط audio)                   */}
      {/* ─────────────────────────────────────────────────────────── */}
      {audioPath && (
        <AudioTrack src={audioPath} volume={1} />
      )}

      {/* ─────────────────────────────────────────────────────────── */}
      {/* 🐛 Debug Info (يظهر فقط في الـ Studio)                     */}
      {/* ─────────────────────────────────────────────────────────── */}
      {process.env.NODE_ENV === "development" && (
        <div
          style={{
            position: "absolute",
            top: 20,
            left: 20,
            fontFamily: "monospace",
            fontSize: 16,
            color: "rgba(255, 255, 0, 0.6)",
            backgroundColor: "rgba(0, 0, 0, 0.6)",
            padding: "8px 12px",
            borderRadius: 8,
            zIndex: 9999,
          }}
        >
          <div>⏱ {currentTimeInSeconds.toFixed(2)}s</div>
          <div>🎞 Frame {frame}/{durationInFrames}</div>
          <div>🎬 Scenes: {scenes.length}</div>
          <div>📝 Subs: {subtitles.length}</div>
          {currentSubtitle && (
            <div>💬 #{currentSubtitle.id}</div>
          )}
        </div>
      )}
    </AbsoluteFill>
  );
};

/**
 * 🎬 Remotion Root Component
 * ═══════════════════════════════════════════════════════════════
 * يحتوي كل الـ Compositions المتاحة في المشروع
 * 
 * Compositions:
 *   • ShortsVideo  - فيديو شورتس عمودي 1080x1920
 * ═══════════════════════════════════════════════════════════════
 */

import React from "react";
import { Composition } from "remotion";
import { ShortsVideo } from "./compositions/ShortsVideo";
import { VideoProps } from "./types";

// ═══════════════════════════════════════════════════════════════════
// 🎯 البيانات الافتراضية للمعاينة
// ═══════════════════════════════════════════════════════════════════
const DEFAULT_PROPS: VideoProps = {
  // المعلومات الأساسية
  title: "مرحباً بكم في قناتنا",
  totalDuration: 10,
  fps: 30,
  width: 1080,
  height: 1920,
  quality: "high",

  // الصوت
  audioPath: "",

  // المشاهد
  scenes: [
    {
      id: 0,
      type: "hook",
      text: "هل تعلم أن الذكاء الاصطناعي يغير العالم؟",
      duration: 3.5,
      pauseAfter: 0.3,
      startTime: 0,
      endTime: 3.5,
      totalLength: 3.8,
      backgroundPath: "",
      zoomEffect: "punch_zoom",
      transitionIn: "none",
      shake: true,
      visualPrompt: "",
    },
    {
      id: 1,
      type: "main",
      text: "كل يوم تظهر تقنيات جديدة مذهلة",
      duration: 3.5,
      pauseAfter: 0.3,
      startTime: 3.8,
      endTime: 7.3,
      totalLength: 3.8,
      backgroundPath: "",
      zoomEffect: "slow_zoom_in",
      transitionIn: "fade",
      shake: false,
      visualPrompt: "",
    },
    {
      id: 2,
      type: "cta",
      text: "اشترك الآن لتعرف المزيد",
      duration: 2.5,
      pauseAfter: 0,
      startTime: 7.3,
      endTime: 9.8,
      totalLength: 2.5,
      backgroundPath: "",
      zoomEffect: "drift_right",
      transitionIn: "fade-black",
      shake: false,
      visualPrompt: "",
    },
  ],

  // الترجمات
  subtitles: [
    {
      id: 0,
      text: "هل تعلم أن الذكاء الاصطناعي يغير العالم؟",
      start: 0,
      end: 3.5,
      duration: 3.5,
      sceneId: 0,
    },
    {
      id: 1,
      text: "كل يوم تظهر تقنيات جديدة مذهلة",
      start: 3.8,
      end: 7.3,
      duration: 3.5,
      sceneId: 1,
    },
    {
      id: 2,
      text: "اشترك الآن لتعرف المزيد",
      start: 7.3,
      end: 9.8,
      duration: 2.5,
      sceneId: 2,
    },
  ],

  // الانتقالات
  transitions: [
    {
      fromScene: 0,
      toScene: 1,
      name: "fade",
      duration: 0.4,
      easing: "ease-in-out",
    },
    {
      fromScene: 1,
      toScene: 2,
      name: "fade-black",
      duration: 0.3,
      easing: "ease-in",
      color: "#000000",
    },
  ],

  // التأثيرات العامة
  effects: {
    grade: {
      name: "cinematic_warm",
      filter: "contrast(1.15) saturate(1.12) brightness(0.95)",
      vignette: true,
      vignetteIntensity: 0.5,
      grain: true,
      grainIntensity: 0.04,
    },
    letterbox: {
      name: "cinematic",
      enabled: true,
      barRatio: 0.055,
      color: "#000000",
      opacity: 0.92,
    },
    fade: {
      fadeIn: { enabled: true, duration: 0.5, color: "#000000" },
      fadeOut: { enabled: true, duration: 0.5, color: "#000000" },
    },
  },

  // تصميم الترجمات
  subtitleStyle: {
    preset: "cinematic",
    fontSize: 78,
    fontWeight: 900,
    fontFamily: "'Cairo', 'Tajawal', 'Almarai', sans-serif",
    color: "#FFFFFF",
    backgroundColor: "rgba(0,0,0,0.0)",
    textShadow:
      "0 4px 20px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.8)",
    padding: "0 60px",
    lineHeight: 1.4,
    letterSpacing: "0em",
    direction: "rtl",
    textAlign: "center",
    position: "bottom",
    positionOffset: 0.78,
  },

  // التصميم العام
  design: {
    fontFamily: "Cairo",
    fontWeight: 900,
    primaryColor: "#FFFFFF",
    accentColor: "#FFD700",
    shadowColor: "rgba(0,0,0,0.9)",
    backgroundOverlay: "rgba(0,0,0,0.35)",
    letterboxEnabled: true,
    cinematicGrade: true,
  },

  // الميتاداتا
  meta: {
    totalScenes: 3,
    totalSubtitles: 3,
    totalTransitions: 2,
    version: "2.0-remotion",
  },
};

// ═══════════════════════════════════════════════════════════════════
// 🎬 الـ Root Component
// ═══════════════════════════════════════════════════════════════════
export const RemotionRoot: React.FC = () => {
  // حساب عدد الـ frames من المدة الإجمالية
  const calculateDurationInFrames = (
    durationInSeconds: number,
    fps: number
  ): number => {
    return Math.ceil(durationInSeconds * fps);
  };

  return (
    <>
      {/* ⭐ الـ Composition الرئيسي - شورتس عمودي 1080x1920 */}
      <Composition
        id="ShortsVideo"
        component={ShortsVideo}
        durationInFrames={calculateDurationInFrames(
          DEFAULT_PROPS.totalDuration,
          DEFAULT_PROPS.fps
        )}
        fps={DEFAULT_PROPS.fps}
        width={DEFAULT_PROPS.width}
        height={DEFAULT_PROPS.height}
        defaultProps={DEFAULT_PROPS}
        // calculateMetadata يسمح بتغيير المدة بناءً على props من Python
        calculateMetadata={({ props }) => {
          const totalDuration = props.totalDuration || DEFAULT_PROPS.totalDuration;
          const fps = props.fps || DEFAULT_PROPS.fps;
          return {
            durationInFrames: calculateDurationInFrames(totalDuration, fps),
            fps: fps,
            width: props.width || DEFAULT_PROPS.width,
            height: props.height || DEFAULT_PROPS.height,
          };
        }}
      />

      {/* 🎬 يمكن إضافة Compositions أخرى هنا (مثل: LongVideo, TikTok, etc.) */}
    </>
  );
};

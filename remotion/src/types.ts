/**
 * 🎯 TypeScript Types & Interfaces
 * ═══════════════════════════════════════════════════════════════
 * كل الـ types المستخدمة في المشروع
 * 
 * هذه الـ types تتطابق مع البيانات الواردة من Python
 * (engine/video/cinematic_editor.py → build_props_for_remotion)
 * ═══════════════════════════════════════════════════════════════
 */

// ════════════════════════════════════════════════════════════════════
// 🎬 أنواع المشاهد
// ════════════════════════════════════════════════════════════════════
export type SceneType =
  | "hook"        // افتتاحية قوية
  | "build"       // بناء وتطوير
  | "peak"        // ذروة
  | "resolution"  // حل
  | "cta"         // call to action
  | "main"        // مشهد عام
  | "intro"       // مقدمة
  | "outro";      // خاتمة

// ════════════════════════════════════════════════════════════════════
// 🎨 أنواع التأثيرات
// ════════════════════════════════════════════════════════════════════
export type ZoomType =
  | "slow_zoom_in"
  | "slow_zoom_out"
  | "punch_zoom"
  | "drift_right"
  | "drift_left"
  | "drift_up"
  | "drift_down"
  | "static";

export type TransitionType =
  | "none"
  | "fade"
  | "fade-black"
  | "fade-white"
  | "smooth-fade"
  | "dissolve"
  | "slide-up"
  | "slide-down"
  | "slide-left"
  | "slide-right"
  | "wipe-up"
  | "wipe-down"
  | "wipe-left"
  | "wipe-right"
  | "zoom-in"
  | "zoom-out"
  | "iris-open"
  | "iris-close"
  | "iris-burst"
  | "flip-horizontal"
  | "flip-vertical"
  | "clock-wipe"
  | "pixelate";

export type GradeStyle =
  | "cinematic_warm"
  | "cinematic_cool"
  | "dramatic_dark"
  | "natural"
  | "off";

export type SubtitleStylePreset =
  | "cinematic"
  | "modern"
  | "highlight"
  | "minimal";

export type Quality = "medium" | "high" | "ultra";

export type EasingType =
  | "linear"
  | "ease-in"
  | "ease-out"
  | "ease-in-out";

// ════════════════════════════════════════════════════════════════════
// 📝 الترجمات
// ════════════════════════════════════════════════════════════════════
export interface WordTiming {
  text: string;
  start: number;  // بالثانية
  end: number;
}

export interface Subtitle {
  id: number;
  text: string;
  start: number;       // وقت البداية بالثانية
  end: number;         // وقت النهاية
  duration: number;    // المدة
  sceneId: number;     // معرف المشهد
  words?: WordTiming[]; // اختياري - لتأثير Karaoke
}

export interface SubtitleStyle {
  preset?: SubtitleStylePreset;
  fontSize: number;
  fontWeight: number | string;
  fontFamily: string;
  color: string;
  backgroundColor?: string;
  textShadow?: string;
  borderRadius?: number;
  padding?: string;
  lineHeight?: number;
  letterSpacing?: string;
  direction?: "rtl" | "ltr";
  textAlign?: "left" | "center" | "right";
  position?: "top" | "center" | "bottom";
  positionOffset?: number; // 0-1 (نسبة من الارتفاع)
  stroke?: {
    width: number;
    color: string;
  };
  glow?: {
    enabled: boolean;
    color: string;
    blur: number;
  };
}

// ════════════════════════════════════════════════════════════════════
// 🎬 المشاهد
// ════════════════════════════════════════════════════════════════════
export interface SceneEffects {
  sceneType?: string;
  zoom?: ZoomConfig;
  shake?: ShakeConfig;
  grade?: GradeConfig;
  letterbox?: LetterboxConfig;
}

export interface Scene {
  id: number;
  type: SceneType;
  text: string;
  duration: number;
  pauseAfter: number;
  startTime: number;
  endTime: number;
  totalLength: number;
  backgroundPath: string;
  zoomEffect: ZoomType;
  transitionIn: TransitionType;
  shake: boolean;
  visualPrompt?: string;
  effectsConfig?: SceneEffects;
}

// ════════════════════════════════════════════════════════════════════
// 🔄 الانتقالات
// ════════════════════════════════════════════════════════════════════
export interface Transition {
  fromScene: number;
  toScene: number;
  name: TransitionType;
  duration: number;
  easing?: EasingType;
  color?: string;        // للـ fade-black, fade-white
  direction?: string;    // للـ slide, wipe
  scaleFrom?: number;    // للـ zoom
  scaleTo?: number;
  shape?: string;        // للـ iris
  scale?: number;
  axis?: "x" | "y";      // للـ flip
  pixelSize?: number;    // للـ pixelate
}

// ════════════════════════════════════════════════════════════════════
// 🎨 التأثيرات البصرية
// ════════════════════════════════════════════════════════════════════
export interface ZoomConfig {
  name: string;
  type?: "scale" | "translate" | "none";
  from?: number;
  to?: number;
  scale?: number;
  fromX?: number;
  toX?: number;
  fromY?: number;
  toY?: number;
  easing?: EasingType;
  originX?: string;
  originY?: string;
  fast?: boolean;
}

export interface ShakeConfig {
  name: string;
  enabled: boolean;
  intensity?: number;
  frequencyX?: number;
  frequencyY?: number;
}

export interface GradeConfig {
  name: string;
  filter?: string;
  tint?: {
    r: number;
    g: number;
    b: number;
  };
  vignette?: boolean;
  vignetteIntensity?: number;
  grain?: boolean;
  grainIntensity?: number;
}

export interface LetterboxConfig {
  name: string;
  enabled: boolean;
  barRatio?: number;     // 0-1 (نسبة من الارتفاع)
  color?: string;
  opacity?: number;
}

export interface FadeConfig {
  enabled: boolean;
  duration: number;
  color: string;
}

export interface FlashConfig {
  enabled: boolean;
  intensity: number;
  duration: number;
  color: string;
}

export interface GlitchConfig {
  enabled: boolean;
  intensity: number;
  chromaShift?: number;
  noise?: number;
}

export interface BlurConfig {
  enabled: boolean;
  sigma: number;
  filter: string;
}

// ════════════════════════════════════════════════════════════════════
// 🌟 التأثيرات العامة
// ════════════════════════════════════════════════════════════════════
export interface GlobalEffects {
  grade?: GradeConfig;
  letterbox?: LetterboxConfig;
  fade?: {
    fadeIn: FadeConfig;
    fadeOut: FadeConfig;
  };
  flash?: FlashConfig;
  glitch?: GlitchConfig;
  blur?: BlurConfig;
}

// ════════════════════════════════════════════════════════════════════
// 🎨 التصميم العام
// ════════════════════════════════════════════════════════════════════
export interface DesignConfig {
  fontFamily: string;
  fontWeight: number | string;
  primaryColor: string;
  accentColor: string;
  shadowColor: string;
  backgroundOverlay: string;
  letterboxEnabled: boolean;
  cinematicGrade: boolean;
}

// ════════════════════════════════════════════════════════════════════
// 📊 الميتاداتا
// ════════════════════════════════════════════════════════════════════
export interface VideoMeta {
  totalScenes: number;
  totalSubtitles: number;
  totalTransitions: number;
  engines?: {
    [key: string]: any;
  };
  version: string;
}

// ════════════════════════════════════════════════════════════════════
// 🎬 الـ Props الرئيسي للفيديو (يأتي من Python)
// ════════════════════════════════════════════════════════════════════
export interface VideoProps {
  // المعلومات الأساسية
  title: string;
  totalDuration: number;
  fps: number;
  width: number;
  height: number;
  quality: Quality;

  // الصوت
  audioPath: string;

  // المحتوى
  scenes: Scene[];
  subtitles: Subtitle[];
  transitions: Transition[];

  // التأثيرات والتصميم
  effects: GlobalEffects;
  subtitleStyle: SubtitleStyle;
  design: DesignConfig;

  // الميتاداتا
  meta: VideoMeta;
}

// ════════════════════════════════════════════════════════════════════
// 🎯 Props للمكونات الفرعية
// ════════════════════════════════════════════════════════════════════
export interface SceneRendererProps {
  scene: Scene;
  isActive: boolean;
  fps: number;
  effects?: GlobalEffects;
}

export interface ArabicSubtitleProps {
  subtitle: Subtitle;
  style: SubtitleStyle;
  isVisible: boolean;
  videoWidth: number;
  videoHeight: number;
}

export interface BackgroundVideoProps {
  src: string;
  duration: number;
  zoomEffect?: ZoomType;
  shake?: boolean;
  width: number;
  height: number;
}

export interface AudioTrackProps {
  src: string;
  volume?: number;
  startFrom?: number;
  endAt?: number;
}

export interface LetterboxProps {
  config: LetterboxConfig;
  width: number;
  height: number;
}

export interface ColorGradeProps {
  config: GradeConfig;
  children: React.ReactNode;
}

// ════════════════════════════════════════════════════════════════════
// 📦 Export All
// ════════════════════════════════════════════════════════════════════
export type {
  // Re-export for convenience
};

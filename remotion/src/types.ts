/**
 * 🎯 TypeScript Types & Interfaces v2.0
 * ═══════════════════════════════════════════════════════════════
 * كل الـ types المستخدمة في المشروع
 *
 * هذه الـ types تتطابق مع البيانات الواردة من Python
 * (engine/video/cinematic_editor.py → build_props_for_remotion)
 * ═══════════════════════════════════════════════════════════════
 */

import type { ReactNode } from 'react';

// ═══════════════════════════════════════════════════════════════
// 🎬 Scene Types
// ═══════════════════════════════════════════════════════════════
export type SceneType =
  | 'hook'
  | 'build'
  | 'peak'
  | 'resolution'
  | 'cta'
  | 'main'
  | 'intro'
  | 'outro';

// ═══════════════════════════════════════════════════════════════
// 🎨 Effect Types
// ═══════════════════════════════════════════════════════════════
export type ZoomType =
  | 'slow_zoom_in'
  | 'slow_zoom_out'
  | 'punch_zoom'
  | 'drift_right'
  | 'drift_left'
  | 'drift_up'
  | 'drift_down'
  | 'static';

export type TransitionType =
  | 'none'
  | 'fade'
  | 'fade-black'
  | 'fade-white'
  | 'smooth-fade'
  | 'dissolve'
  | 'slide-up'
  | 'slide-down'
  | 'slide-left'
  | 'slide-right'
  | 'wipe-up'
  | 'wipe-down'
  | 'wipe-left'
  | 'wipe-right'
  | 'zoom-in'
  | 'zoom-out'
  | 'iris-open'
  | 'iris-close'
  | 'iris-burst'
  | 'flip-horizontal'
  | 'flip-vertical'
  | 'clock-wipe'
  | 'pixelate';

export type GradeStyle =
  | 'cinematic_warm'
  | 'cinematic_cool'
  | 'dramatic_dark'
  | 'bright_vibrant'
  | 'emotional_soft'
  | 'natural'
  | 'off';

export type SubtitleStylePreset =
  | 'cinematic'
  | 'modern'
  | 'highlight'
  | 'minimal'
  | 'bold'
  | 'karaoke';

export type LetterboxStyle =
  | 'cinematic'
  | 'thin'
  | 'thick'
  | 'imax'
  | 'widescreen'
  | 'off';

export type Quality = 'draft' | 'medium' | 'high' | 'ultra';

export type EasingType =
  | 'linear'
  | 'ease-in'
  | 'ease-out'
  | 'ease-in-out';

export type SubtitleMode = 'scene' | 'tiktok';

export type VoiceTone =
  | 'whisper'
  | 'calm'
  | 'cold'
  | 'emotionless'
  | 'sad'
  | 'curious'
  | 'authoritative'
  | 'intense'
  | 'aggressive'
  | 'powerful';

// ═══════════════════════════════════════════════════════════════
// 📝 Subtitles
// ═══════════════════════════════════════════════════════════════
export interface WordTiming {
  /** نص الكلمة (الاسم المفضّل) */
  text?: string;
  /** نص الكلمة (للتوافق مع Whisper) */
  word?: string;
  start: number;  // seconds
  end: number;    // seconds
  probability?: number;  // من Whisper
}

export interface Subtitle {
  id: number;
  text: string;
  start: number;
  end: number;
  duration: number;
  sceneId: number;
  
  /** للـ Karaoke effect (اختياري) */
  words?: WordTiming[];
  
  /** override style لهذه الترجمة فقط */
  styleOverride?: string;
}

export interface SubtitleStyleStroke {
  width: number;
  color: string;
}

export interface SubtitleStyleGlow {
  enabled: boolean;
  color: string;
  blur: number;
}

export interface SubtitleStyle {
  preset?: SubtitleStylePreset;
  fontSize?: number;
  fontWeight?: number | string;
  fontFamily?: string;
  color?: string;
  backgroundColor?: string;
  textShadow?: string;
  borderRadius?: number;
  padding?: string;
  lineHeight?: number;
  letterSpacing?: string;
  direction?: 'rtl' | 'ltr';
  textAlign?: 'left' | 'center' | 'right';
  position?: 'top' | 'center' | 'bottom';
  positionOffset?: number;  // 0-1
  stroke?: SubtitleStyleStroke;
  glow?: SubtitleStyleGlow;
}

// ═══════════════════════════════════════════════════════════════
// 🎬 Scenes
// ═══════════════════════════════════════════════════════════════
export interface SceneEffectsConfig {
  sceneType?: string;
  zoom?: ZoomConfig;
  shake?: ShakeConfig;
  grade?: GradeConfig;
  letterbox?: LetterboxConfig;
  transition?: TransitionConfig;
  fadeIn?: boolean;
  fadeOut?: boolean;
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
  
  /** Visual prompt للـ AI */
  visualPrompt?: string;
  
  /** Effects config لهذا المشهد */
  effectsConfig?: SceneEffectsConfig;
  
  /** مستوى الطاقة (للـ peak effects) */
  energy?: number;  // 0-1
  
  /** نبرة الصوت */
  voiceTone?: VoiceTone;
}

// ═══════════════════════════════════════════════════════════════
// 🔄 Transitions
// ═══════════════════════════════════════════════════════════════
export interface Transition {
  fromScene: number;
  toScene: number;
  name: TransitionType | string;
  duration: number;
  easing?: EasingType | string;
  
  /** للـ fade-black, fade-white */
  color?: string;
  
  /** للـ slide, wipe */
  direction?: string;
  
  /** للـ zoom */
  scaleFrom?: number;
  scaleTo?: number;
  
  /** للـ iris */
  shape?: string;
  scale?: number;
  
  /** للـ flip */
  axis?: 'x' | 'y';
  
  /** للـ pixelate */
  pixelSize?: number;
}

export interface TransitionConfig {
  name: string;
  duration: number;
  easing: string;
  direction?: string;
  color?: string;
  scaleFrom?: number;
  scaleTo?: number;
  shape?: string;
  scale?: number;
  axis?: string;
  pixelSize?: number;
}

// ═══════════════════════════════════════════════════════════════
// 🎨 Visual Effects
// ═══════════════════════════════════════════════════════════════
export interface ZoomConfig {
  name: string;
  type?: 'scale' | 'translate' | 'none';
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

export interface GradeTint {
  r: number;
  g: number;
  b: number;
}

export interface GradeConfig {
  name: string;
  filter?: string;
  tint?: GradeTint;
  vignette?: boolean;
  vignetteIntensity?: number;
  grain?: boolean;
  grainIntensity?: number;
}

export interface LetterboxConfig {
  name: string;
  enabled: boolean;
  barRatio?: number;  // 0-1
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

// ═══════════════════════════════════════════════════════════════
// 🌟 Global Effects
// ═══════════════════════════════════════════════════════════════
export interface FadeEffectsContainer {
  fadeIn: FadeConfig;
  fadeOut: FadeConfig;
}

export interface GlobalEffects {
  grade?: GradeConfig;
  letterbox?: LetterboxConfig;
  fade?: FadeEffectsContainer;
  flash?: FlashConfig;
  glitch?: GlitchConfig;
  blur?: BlurConfig;
}

// ═══════════════════════════════════════════════════════════════
// 🎨 Design Config
// ═══════════════════════════════════════════════════════════════
export interface DesignConfig {
  fontFamily?: string;
  fontWeight?: number | string;
  primaryColor?: string;
  accentColor?: string;
  shadowColor?: string;
  backgroundOverlay?: string;
  letterboxEnabled?: boolean;
  cinematicGrade?: boolean;
  subtitleMode?: SubtitleMode;
}

// ═══════════════════════════════════════════════════════════════
// 📊 Metadata
// ═══════════════════════════════════════════════════════════════
export interface VideoMeta {
  totalScenes: number;
  totalSubtitles: number;
  totalTransitions: number;
  hasEffects?: boolean;
  hasWhisper?: boolean;
  mood?: string;
  engines?: Record<string, unknown>;
  version: string;
}

// ═══════════════════════════════════════════════════════════════
// 🎬 Main VideoProps
// ═══════════════════════════════════════════════════════════════
export interface VideoProps {
  // ── المعلومات الأساسية ──
  title: string;
  totalDuration: number;
  fps: number;
  width: number;
  height: number;
  quality?: Quality;
  
  // ── الصوت ──
  audioPath?: string;
  audioActualDuration?: number;
  
  // ── المحتوى ──
  scenes: Scene[];
  subtitles: Subtitle[];
  transitions?: Transition[];
  
  // ── التأثيرات والتصميم (optional) ──
  effects?: GlobalEffects;
  subtitleStyle?: SubtitleStyle;
  design?: DesignConfig;
  
  // ── الميتاداتا ──
  meta?: VideoMeta;
}

// ═══════════════════════════════════════════════════════════════
// 🎯 Component Props
// ═══════════════════════════════════════════════════════════════
export interface SceneRendererProps {
  scene: Scene;
  isActive: boolean;
  fps: number;
  effects?: GlobalEffects;
  fadeInFrames?: number;
  fadeOutFrames?: number;
  applyColorGrade?: boolean;
}

export interface ArabicSubtitleProps {
  subtitle: Subtitle;
  style?: Partial<SubtitleStyle>;
  isVisible?: boolean;
  videoWidth: number;
  videoHeight: number;
}

export interface BackgroundVideoProps {
  src: string;
  duration: number;
  zoomEffect?: ZoomType;
  shake?: boolean;
  shakeIntensity?: number;
  width: number;
  height: number;
  overlayColor?: string;
  overlayOpacity?: number;
  filter?: string;
  startFrom?: number;
  playbackRate?: number;
  objectPosition?: string;
}

export interface AudioTrackProps {
  src: string;
  volume?: number;
  startFrom?: number;
  endAt?: number;
  fadeInDuration?: number;
  fadeOutDuration?: number;
  loop?: boolean;
  playbackRate?: number;
  startInVideo?: number;
  durationInVideo?: number;
  muted?: boolean;
}

export interface LetterboxProps {
  config: LetterboxConfig;
  width: number;
  height: number;
  orientation?: 'horizontal' | 'vertical' | 'both';
  animation?: 'slide' | 'fade' | 'none';
  slideInFrames?: number;
  slideOut?: boolean;
  slideOutFrames?: number;
  showSeparatorLine?: boolean;
  separatorColor?: string;
  zIndex?: number;
}

export interface ColorGradeProps {
  config?: GradeConfig | null;
  children: ReactNode;
  tintOpacity?: number;
  blendMode?: React.CSSProperties['mixBlendMode'];
}

// ═══════════════════════════════════════════════════════════════
// 🎯 Type Guards & Utilities
// ═══════════════════════════════════════════════════════════════
/**
 * Type guard للتحقق من Scene صحيح
 */
export const isValidScene = (scene: unknown): scene is Scene => {
  if (!scene || typeof scene !== 'object') return false;
  const s = scene as Scene;
  return (
    typeof s.id === 'number' &&
    typeof s.type === 'string' &&
    typeof s.text === 'string' &&
    typeof s.duration === 'number'
  );
};

/**
 * Type guard للتحقق من Subtitle صحيح
 */
export const isValidSubtitle = (sub: unknown): sub is Subtitle => {
  if (!sub || typeof sub !== 'object') return false;
  const s = sub as Subtitle;
  return (
    typeof s.id === 'number' &&
    typeof s.text === 'string' &&
    typeof s.start === 'number' &&
    typeof s.end === 'number'
  );
};

/**
 * Get word text (يدعم word.text و word.word)
 */
export const getWordText = (word: WordTiming): string => {
  return word.text || word.word || '';
};

// ═══════════════════════════════════════════════════════════════
// 🎯 Default Values
// ═══════════════════════════════════════════════════════════════
export const DEFAULT_SCENE: Partial<Scene> = {
  type: 'main',
  duration: 3,
  pauseAfter: 0.3,
  zoomEffect: 'slow_zoom_in',
  transitionIn: 'fade',
  shake: false,
  energy: 0.5,
};

export const DEFAULT_SUBTITLE_STYLE: SubtitleStyle = {
  preset: 'cinematic',
  fontSize: 78,
  fontWeight: 900,
  fontFamily: "'Cairo', 'Tajawal', 'Almarai', sans-serif",
  color: '#FFFFFF',
  backgroundColor: 'rgba(0,0,0,0)',
  textShadow: '0 4px 20px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.8)',
  padding: '0 60px',
  lineHeight: 1.4,
  letterSpacing: '0em',
  direction: 'rtl',
  textAlign: 'center',
  position: 'bottom',
  positionOffset: 0.78,
};

export const DEFAULT_VIDEO_CONFIG = {
  width: 1080,
  height: 1920,
  fps: 30,
  quality: 'high' as Quality,
} as const;

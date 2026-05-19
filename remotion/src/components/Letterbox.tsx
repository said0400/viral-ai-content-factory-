/**
 * 🎞️ Letterbox Component v2.1
 * ═══════════════════════════════════════════════════════════════
 * إصلاحات v2.1:
 *   ✓ import React مضاف
 *   ✓ LetterboxConfig inline (لا @types alias)
 * ═══════════════════════════════════════════════════════════════
 */

import React, { useMemo, memo, ReactNode } from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from 'remotion';

// ═══════════════════════════════════════════════════════════════
// Types (inline)
// ═══════════════════════════════════════════════════════════════
interface LetterboxConfig {
  name: string;
  enabled: boolean;
  barRatio?: number;
  color?: string;
  opacity?: number;
}

export type LetterboxOrientation = 'horizontal' | 'vertical' | 'both';
export type LetterboxAnimation = 'slide' | 'fade' | 'none';

export interface LetterboxProps {
  config: LetterboxConfig;
  width: number;
  height: number;
  orientation?: LetterboxOrientation;
  animation?: LetterboxAnimation;
  slideInFrames?: number;
  slideOut?: boolean;
  slideOutFrames?: number;
  showSeparatorLine?: boolean;
  separatorColor?: string;
  zIndex?: number;
}

export interface LetterboxWithTextProps extends LetterboxProps {
  topText?: string;
  bottomText?: string;
  textColor?: string;
  textSize?: number;
  textFontFamily?: string;
  textFontWeight?: number;
}

export interface GradientLetterboxProps extends LetterboxProps {
  topGradient?: string;
  bottomGradient?: string;
}

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const DEFAULT_SLIDE_IN_FRAMES = 15;
const DEFAULT_SLIDE_OUT_FRAMES = 15;
const DEFAULT_BAR_RATIO = 0.055;
const DEFAULT_BAR_COLOR = '#000000';
const DEFAULT_BAR_OPACITY = 0.92;
const DEFAULT_Z_INDEX = 100;
const DEFAULT_SEPARATOR_COLOR = 'rgba(255, 255, 255, 0.05)';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════
const calculateAnimationProgress = (
  frame: number,
  totalFrames: number,
  slideInFrames: number,
  slideOutFrames: number,
  slideOut: boolean,
): number => {
  const inProgress = interpolate(
    frame,
    [0, slideInFrames],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );
  
  if (slideOut) {
    const outStart = totalFrames - slideOutFrames;
    const outProgress = interpolate(
      frame,
      [outStart, totalFrames],
      [1, 0],
      { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
    );
    return Math.min(inProgress, outProgress);
  }
  
  return inProgress;
};

// ═══════════════════════════════════════════════════════════════
// Main Letterbox
// ═══════════════════════════════════════════════════════════════
export const Letterbox: React.FC<LetterboxProps> = memo(
  ({
    config,
    width,
    height,
    orientation = 'horizontal',
    animation = 'slide',
    slideInFrames = DEFAULT_SLIDE_IN_FRAMES,
    slideOut = false,
    slideOutFrames = DEFAULT_SLIDE_OUT_FRAMES,
    showSeparatorLine = true,
    separatorColor = DEFAULT_SEPARATOR_COLOR,
    zIndex = DEFAULT_Z_INDEX,
  }) => {
    const frame = useCurrentFrame();
    const { durationInFrames } = useVideoConfig();
    
    if (!config.enabled) {
      return null;
    }
    
    const barRatio = config.barRatio ?? DEFAULT_BAR_RATIO;
    const barColor = config.color ?? DEFAULT_BAR_COLOR;
    const barOpacity = config.opacity ?? DEFAULT_BAR_OPACITY;
    
    const horizontalBarHeight = Math.floor(height * barRatio);
    const verticalBarWidth = Math.floor(width * barRatio);
    
    const progress = useMemo(
      () =>
        animation === 'none'
          ? 1
          : calculateAnimationProgress(
              frame,
              durationInFrames,
              slideInFrames,
              slideOutFrames,
              slideOut,
            ),
      [frame, durationInFrames, slideInFrames, slideOutFrames, slideOut, animation],
    );
    
    const renderHorizontalBars = () => {
      const topOffset =
        animation === 'slide'
          ? interpolate(progress, [0, 1], [-horizontalBarHeight, 0])
          : 0;
      
      const bottomOffset =
        animation === 'slide'
          ? interpolate(progress, [0, 1], [horizontalBarHeight, 0])
          : 0;
      
      const opacity = animation === 'fade' ? progress * barOpacity : barOpacity;
      
      return (
        <>
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: horizontalBarHeight,
              backgroundColor: barColor,
              opacity,
              transform: `translateY(${topOffset}px)`,
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
            }}
          />
          
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              width: '100%',
              height: horizontalBarHeight,
              backgroundColor: barColor,
              opacity,
              transform: `translateY(${bottomOffset}px)`,
              boxShadow: '0 -4px 20px rgba(0, 0, 0, 0.4)',
            }}
          />
          
          {showSeparatorLine && (
            <>
              <div
                style={{
                  position: 'absolute',
                  top: horizontalBarHeight + topOffset,
                  left: 0,
                  width: '100%',
                  height: 1,
                  backgroundColor: separatorColor,
                  opacity: progress,
                }}
              />
              <div
                style={{
                  position: 'absolute',
                  bottom: horizontalBarHeight - bottomOffset,
                  left: 0,
                  width: '100%',
                  height: 1,
                  backgroundColor: separatorColor,
                  opacity: progress,
                }}
              />
            </>
          )}
        </>
      );
    };
    
    const renderVerticalBars = () => {
      const leftOffset =
        animation === 'slide'
          ? interpolate(progress, [0, 1], [-verticalBarWidth, 0])
          : 0;
      
      const rightOffset =
        animation === 'slide'
          ? interpolate(progress, [0, 1], [verticalBarWidth, 0])
          : 0;
      
      const opacity = animation === 'fade' ? progress * barOpacity : barOpacity;
      
      return (
        <>
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: verticalBarWidth,
              height: '100%',
              backgroundColor: barColor,
              opacity,
              transform: `translateX(${leftOffset}px)`,
              boxShadow: '4px 0 20px rgba(0, 0, 0, 0.4)',
            }}
          />
          
          <div
            style={{
              position: 'absolute',
              top: 0,
              right: 0,
              width: verticalBarWidth,
              height: '100%',
              backgroundColor: barColor,
              opacity,
              transform: `translateX(${rightOffset}px)`,
              boxShadow: '-4px 0 20px rgba(0, 0, 0, 0.4)',
            }}
          />
        </>
      );
    };
    
    return (
      <AbsoluteFill style={{ pointerEvents: 'none', zIndex }}>
        {(orientation === 'horizontal' || orientation === 'both') &&
          renderHorizontalBars()}
        
        {(orientation === 'vertical' || orientation === 'both') &&
          renderVerticalBars()}
      </AbsoluteFill>
    );
  },
);

Letterbox.displayName = 'Letterbox';

// ═══════════════════════════════════════════════════════════════
// Letterbox with Text
// ═══════════════════════════════════════════════════════════════
export const LetterboxWithText: React.FC<LetterboxWithTextProps> = memo(
  ({
    config,
    width,
    height,
    topText,
    bottomText,
    textColor = 'rgba(255, 255, 255, 0.7)',
    textSize = 24,
    textFontFamily = "'Cairo', sans-serif",
    textFontWeight = 600,
    ...rest
  }) => {
    if (!config.enabled) return null;
    
    const barRatio = config.barRatio ?? DEFAULT_BAR_RATIO;
    const barHeight = Math.floor(height * barRatio);
    const zIndex = rest.zIndex ?? DEFAULT_Z_INDEX;
    
    const textStyle: React.CSSProperties = useMemo(
      () => ({
        position: 'absolute',
        left: 0,
        width: '100%',
        height: barHeight,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: textColor,
        fontSize: textSize,
        fontFamily: textFontFamily,
        fontWeight: textFontWeight,
        direction: 'rtl',
        zIndex: zIndex + 1,
        pointerEvents: 'none',
      }),
      [barHeight, textColor, textSize, textFontFamily, textFontWeight, zIndex],
    );
    
    return (
      <>
        <Letterbox config={config} width={width} height={height} {...rest} />
        
        {topText && (
          <div style={{ ...textStyle, top: 0 }}>{topText}</div>
        )}
        
        {bottomText && (
          <div style={{ ...textStyle, bottom: 0 }}>{bottomText}</div>
        )}
      </>
    );
  },
);

LetterboxWithText.displayName = 'LetterboxWithText';

// ═══════════════════════════════════════════════════════════════
// Gradient Letterbox
// ═══════════════════════════════════════════════════════════════
export const GradientLetterbox: React.FC<GradientLetterboxProps> = memo(
  ({
    config,
    width,
    height,
    topGradient = 'linear-gradient(180deg, #000000 0%, transparent 100%)',
    bottomGradient = 'linear-gradient(0deg, #000000 0%, transparent 100%)',
    zIndex = DEFAULT_Z_INDEX,
  }) => {
    if (!config.enabled) return null;
    
    const barRatio = config.barRatio ?? DEFAULT_BAR_RATIO;
    const barHeight = Math.floor(height * barRatio);
    const opacity = config.opacity ?? DEFAULT_BAR_OPACITY;
    
    return (
      <AbsoluteFill style={{ pointerEvents: 'none', zIndex }}>
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: barHeight,
            background: topGradient,
            opacity,
          }}
        />
        
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            width: '100%',
            height: barHeight,
            background: bottomGradient,
            opacity,
          }}
        />
      </AbsoluteFill>
    );
  },
);

GradientLetterbox.displayName = 'GradientLetterbox';

// ═══════════════════════════════════════════════════════════════
// Preset Letterbox
// ═══════════════════════════════════════════════════════════════
export type LetterboxPresetName = 'cinematic' | 'thin' | 'thick' | 'imax' | 'widescreen';

const LETTERBOX_PRESETS: Record<LetterboxPresetName, Partial<LetterboxConfig>> = {
  cinematic: { barRatio: 0.055, color: '#000000', opacity: 0.92 },
  thin: { barRatio: 0.03, color: '#000000', opacity: 1.0 },
  thick: { barRatio: 0.08, color: '#000000', opacity: 1.0 },
  imax: { barRatio: 0.12, color: '#000000', opacity: 1.0 },
  widescreen: { barRatio: 0.07, color: '#000000', opacity: 0.95 },
};

interface PresetLetterboxProps {
  preset: LetterboxPresetName;
  width: number;
  height: number;
  enabled?: boolean;
  animation?: LetterboxAnimation;
}

export const PresetLetterbox: React.FC<PresetLetterboxProps> = memo(
  ({ preset, width, height, enabled = true, animation = 'slide' }) => {
    const presetConfig = LETTERBOX_PRESETS[preset];
    
    const config: LetterboxConfig = useMemo(
      () => ({
        name: preset,
        enabled,
        barRatio: presetConfig.barRatio ?? DEFAULT_BAR_RATIO,
        color: presetConfig.color ?? DEFAULT_BAR_COLOR,
        opacity: presetConfig.opacity ?? DEFAULT_BAR_OPACITY,
      }),
      [preset, enabled, presetConfig],
    );
    
    return (
      <Letterbox
        config={config}
        width={width}
        height={height}
        animation={animation}
      />
    );
  },
);

PresetLetterbox.displayName = 'PresetLetterbox';

export default Letterbox;

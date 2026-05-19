/**
 * 🎨 Color Grade Component v2.1
 * ═══════════════════════════════════════════════════════════════
 * إصلاحات v2.1:
 *   ✓ import React مضاف
 *   ✓ GradeConfig inline (لا @types alias)
 * ═══════════════════════════════════════════════════════════════
 */

import React, { useMemo, memo, ReactNode } from 'react';
import { AbsoluteFill } from 'remotion';

// ═══════════════════════════════════════════════════════════════
// Types (inline)
// ═══════════════════════════════════════════════════════════════
export interface TintColor {
  r: number;
  g: number;
  b: number;
}

interface GradeConfig {
  name: string;
  filter?: string;
  tint?: TintColor;
  vignette?: boolean;
  vignetteIntensity?: number;
  grain?: boolean;
  grainIntensity?: number;
}

export interface ColorGradeProps {
  config?: GradeConfig | null;
  children: ReactNode;
  tintOpacity?: number;
  blendMode?: React.CSSProperties['mixBlendMode'];
}

export interface CustomColorGradeProps {
  contrast?: number;
  saturate?: number;
  brightness?: number;
  hue?: number;
  blur?: number;
  invert?: boolean;
  sepia?: number;
  grayscale?: number;
  tint?: TintColor;
  tintOpacity?: number;
  blendMode?: React.CSSProperties['mixBlendMode'];
  vignette?: boolean;
  vignetteIntensity?: number;
  grain?: boolean;
  grainIntensity?: number;
  children: ReactNode;
}

export interface FilmLookConfig {
  contrast: number;
  saturate: number;
  brightness: number;
  hue?: number;
  sepia?: number;
  grayscale?: number;
  tint?: TintColor;
  tintOpacity?: number;
  vignette?: boolean;
  vignetteIntensity?: number;
}

// ═══════════════════════════════════════════════════════════════
// Film Look Presets
// ═══════════════════════════════════════════════════════════════
export const FilmLookPresets: Record<string, FilmLookConfig> = {
  classicFilm: {
    contrast: 1.2,
    saturate: 1.15,
    brightness: 0.95,
    tint: { r: 1.08, g: 1.0, b: 0.92 },
    tintOpacity: 0.1,
    vignette: true,
    vignetteIntensity: 0.4,
  },
  filmNoir: {
    contrast: 1.5,
    saturate: 0.0,
    brightness: 0.9,
    tint: { r: 0.95, g: 0.95, b: 1.05 },
    tintOpacity: 0.05,
    vignette: true,
    vignetteIntensity: 0.7,
  },
  darkDrama: {
    contrast: 1.35,
    saturate: 0.85,
    brightness: 0.8,
    tint: { r: 0.85, g: 0.9, b: 1.0 },
    tintOpacity: 0.12,
    vignette: true,
    vignetteIntensity: 0.8,
  },
  vintage: {
    contrast: 1.1,
    saturate: 0.85,
    brightness: 1.05,
    sepia: 0.3,
    tint: { r: 1.1, g: 1.0, b: 0.85 },
    tintOpacity: 0.15,
    vignette: true,
    vignetteIntensity: 0.5,
  },
  cyberpunk: {
    contrast: 1.3,
    saturate: 1.4,
    brightness: 0.9,
    hue: 10,
    tint: { r: 0.9, g: 0.85, b: 1.15 },
    tintOpacity: 0.12,
    vignette: true,
    vignetteIntensity: 0.6,
  },
  sunset: {
    contrast: 1.2,
    saturate: 1.25,
    brightness: 1.05,
    hue: -5,
    tint: { r: 1.15, g: 0.95, b: 0.85 },
    tintOpacity: 0.12,
    vignette: true,
    vignetteIntensity: 0.4,
  },
} as const;

export type FilmLookName = keyof typeof FilmLookPresets;

// ═══════════════════════════════════════════════════════════════
// Cinematic Presets
// ═══════════════════════════════════════════════════════════════
const CINEMATIC_PRESETS: Record<string, FilmLookConfig> = {
  cinematic_warm: {
    contrast: 1.15,
    saturate: 1.12,
    brightness: 0.95,
    tint: { r: 1.05, g: 1.0, b: 0.95 },
    tintOpacity: 0.08,
    vignette: true,
    vignetteIntensity: 0.5,
  },
  cinematic_cool: {
    contrast: 1.18,
    saturate: 1.05,
    brightness: 0.92,
    tint: { r: 0.95, g: 1.0, b: 1.08 },
    tintOpacity: 0.08,
    vignette: true,
    vignetteIntensity: 0.6,
  },
  dramatic_dark: {
    contrast: 1.25,
    saturate: 0.95,
    brightness: 0.85,
    tint: { r: 0.92, g: 0.95, b: 1.0 },
    tintOpacity: 0.1,
    vignette: true,
    vignetteIntensity: 0.8,
  },
  bright_vibrant: {
    contrast: 1.1,
    saturate: 1.25,
    brightness: 1.05,
    tint: { r: 1.02, g: 1.02, b: 1.0 },
    tintOpacity: 0.05,
  },
  emotional_soft: {
    contrast: 1.05,
    saturate: 0.95,
    brightness: 0.98,
    tint: { r: 1.0, g: 0.98, b: 1.02 },
    tintOpacity: 0.08,
    vignette: true,
    vignetteIntensity: 0.4,
  },
  natural: {
    contrast: 1.05,
    saturate: 1.0,
    brightness: 1.0,
  },
};

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════
const clamp = (value: number, min: number, max: number): number => {
  return Math.min(Math.max(value, min), max);
};

const buildFilterString = (config: {
  contrast?: number;
  saturate?: number;
  brightness?: number;
  hue?: number;
  blur?: number;
  invert?: boolean;
  sepia?: number;
  grayscale?: number;
}): string => {
  const filters: string[] = [];
  
  if (config.contrast !== undefined && config.contrast !== 1.0) {
    filters.push(`contrast(${config.contrast})`);
  }
  if (config.saturate !== undefined && config.saturate !== 1.0) {
    filters.push(`saturate(${config.saturate})`);
  }
  if (config.brightness !== undefined && config.brightness !== 1.0) {
    filters.push(`brightness(${config.brightness})`);
  }
  if (config.hue !== undefined && config.hue !== 0) {
    filters.push(`hue-rotate(${config.hue}deg)`);
  }
  if (config.blur !== undefined && config.blur > 0) {
    filters.push(`blur(${config.blur}px)`);
  }
  if (config.invert) {
    filters.push('invert(1)');
  }
  if (config.sepia !== undefined && config.sepia > 0) {
    filters.push(`sepia(${config.sepia})`);
  }
  if (config.grayscale !== undefined && config.grayscale > 0) {
    filters.push(`grayscale(${config.grayscale})`);
  }
  
  return filters.join(' ') || 'none';
};

const buildTintColor = (tint: TintColor, opacity: number = 0.08): string => {
  const r = clamp(Math.floor(tint.r * 128), 0, 255);
  const g = clamp(Math.floor(tint.g * 128), 0, 255);
  const b = clamp(Math.floor(tint.b * 128), 0, 255);
  const a = clamp(opacity, 0, 1);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
};

// ═══════════════════════════════════════════════════════════════
// Vignette
// ═══════════════════════════════════════════════════════════════
const Vignette: React.FC<{ intensity?: number }> = memo(
  ({ intensity = 0.5 }) => {
    const style = useMemo<React.CSSProperties>(
      () => ({
        background: `radial-gradient(
          ellipse at center,
          transparent 0%,
          transparent 50%,
          rgba(0, 0, 0, ${clamp(intensity, 0, 1)}) 100%
        )`,
        pointerEvents: 'none',
        mixBlendMode: 'multiply' as const,
      }),
      [intensity],
    );
    
    return <AbsoluteFill style={style} />;
  },
);

Vignette.displayName = 'Vignette';

// ═══════════════════════════════════════════════════════════════
// Film Grain
// ═══════════════════════════════════════════════════════════════
const FilmGrain: React.FC<{ intensity?: number }> = memo(
  ({ intensity = 0.04 }) => {
    const style = useMemo<React.CSSProperties>(() => {
      const svgNoise = `data:image/svg+xml;utf8,<svg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='${clamp(intensity * 10, 0, 1)}'/></svg>`;
      
      return {
        backgroundImage: `url("${svgNoise}")`,
        backgroundSize: '200px 200px',
        pointerEvents: 'none',
        mixBlendMode: 'overlay' as const,
        opacity: 0.5,
      };
    }, [intensity]);
    
    return <AbsoluteFill style={style} />;
  },
);

FilmGrain.displayName = 'FilmGrain';

// ═══════════════════════════════════════════════════════════════
// Main ColorGrade
// ═══════════════════════════════════════════════════════════════
export const ColorGrade: React.FC<ColorGradeProps> = memo(
  ({ config, children, tintOpacity, blendMode = 'soft-light' }) => {
    if (!config || config.name === 'off') {
      return <>{children}</>;
    }
    
    const presetConfig = useMemo(
      () => CINEMATIC_PRESETS[config.name],
      [config.name],
    );
    
    const filterString = useMemo(() => {
      if (config.filter && config.filter !== 'none') {
        return config.filter;
      }
      if (presetConfig) {
        return buildFilterString(presetConfig);
      }
      return 'none';
    }, [config.filter, presetConfig]);
    
    const tintBackground = useMemo(() => {
      const tint = config.tint || presetConfig?.tint;
      if (!tint) return null;
      
      const opacity = tintOpacity ?? presetConfig?.tintOpacity ?? 0.08;
      return buildTintColor(tint, opacity);
    }, [config.tint, presetConfig, tintOpacity]);
    
    const showVignette = config.vignette ?? presetConfig?.vignette ?? false;
    const vignetteIntensity =
      config.vignetteIntensity ?? presetConfig?.vignetteIntensity ?? 0.5;
    
    const showGrain = config.grain ?? false;
    const grainIntensity = config.grainIntensity ?? 0.04;
    
    return (
      <AbsoluteFill style={{ filter: filterString }}>
        {children}
        
        {tintBackground && (
          <AbsoluteFill
            style={{
              backgroundColor: tintBackground,
              mixBlendMode: blendMode,
              pointerEvents: 'none',
            }}
          />
        )}
        
        {showVignette && <Vignette intensity={vignetteIntensity} />}
        {showGrain && <FilmGrain intensity={grainIntensity} />}
      </AbsoluteFill>
    );
  },
);

ColorGrade.displayName = 'ColorGrade';

// ═══════════════════════════════════════════════════════════════
// Cinematic Wrapper
// ═══════════════════════════════════════════════════════════════
export type CinematicPresetName =
  | 'warm'
  | 'cool'
  | 'dramatic'
  | 'natural'
  | 'vibrant'
  | 'emotional';

interface CinematicWrapperProps {
  preset?: CinematicPresetName;
  children: ReactNode;
}

const PRESET_NAME_MAP: Record<CinematicPresetName, string> = {
  warm: 'cinematic_warm',
  cool: 'cinematic_cool',
  dramatic: 'dramatic_dark',
  natural: 'natural',
  vibrant: 'bright_vibrant',
  emotional: 'emotional_soft',
};

export const CinematicWrapper: React.FC<CinematicWrapperProps> = memo(
  ({ preset = 'warm', children }) => {
    const configName = PRESET_NAME_MAP[preset];
    const presetConfig = CINEMATIC_PRESETS[configName];
    
    const config: GradeConfig = useMemo(
      () => ({
        name: configName,
        filter: buildFilterString(presetConfig),
        tint: presetConfig.tint,
        vignette: presetConfig.vignette ?? false,
        vignetteIntensity: presetConfig.vignetteIntensity ?? 0.5,
        grain: false,
        grainIntensity: 0.04,
      }),
      [configName, presetConfig],
    );
    
    return <ColorGrade config={config}>{children}</ColorGrade>;
  },
);

CinematicWrapper.displayName = 'CinematicWrapper';

// ═══════════════════════════════════════════════════════════════
// Custom Color Grade
// ═══════════════════════════════════════════════════════════════
export const CustomColorGrade: React.FC<CustomColorGradeProps> = memo(
  ({
    contrast = 1.0,
    saturate = 1.0,
    brightness = 1.0,
    hue = 0,
    blur = 0,
    invert = false,
    sepia = 0,
    grayscale = 0,
    tint,
    tintOpacity = 0.08,
    blendMode = 'soft-light',
    vignette = false,
    vignetteIntensity = 0.5,
    grain = false,
    grainIntensity = 0.04,
    children,
  }) => {
    const filterString = useMemo(
      () =>
        buildFilterString({
          contrast,
          saturate,
          brightness,
          hue,
          blur,
          invert,
          sepia,
          grayscale,
        }),
      [contrast, saturate, brightness, hue, blur, invert, sepia, grayscale],
    );
    
    const tintBackground = useMemo(
      () => (tint ? buildTintColor(tint, tintOpacity) : null),
      [tint, tintOpacity],
    );
    
    return (
      <AbsoluteFill style={{ filter: filterString }}>
        {children}
        
        {tintBackground && (
          <AbsoluteFill
            style={{
              backgroundColor: tintBackground,
              mixBlendMode: blendMode,
              pointerEvents: 'none',
            }}
          />
        )}
        
        {vignette && <Vignette intensity={vignetteIntensity} />}
        {grain && <FilmGrain intensity={grainIntensity} />}
      </AbsoluteFill>
    );
  },
);

CustomColorGrade.displayName = 'CustomColorGrade';

// ═══════════════════════════════════════════════════════════════
// Film Look Wrapper
// ═══════════════════════════════════════════════════════════════
interface FilmLookProps {
  preset: FilmLookName;
  children: ReactNode;
}

export const FilmLook: React.FC<FilmLookProps> = memo(
  ({ preset, children }) => {
    const config = FilmLookPresets[preset];
    
    if (!config) {
      return <>{children}</>;
    }
    
    return (
      <CustomColorGrade
        contrast={config.contrast}
        saturate={config.saturate}
        brightness={config.brightness}
        hue={config.hue}
        sepia={config.sepia}
        grayscale={config.grayscale}
        tint={config.tint}
        tintOpacity={config.tintOpacity}
        vignette={config.vignette}
        vignetteIntensity={config.vignetteIntensity}
      >
        {children}
      </CustomColorGrade>
    );
  },
);

FilmLook.displayName = 'FilmLook';

export default ColorGrade;

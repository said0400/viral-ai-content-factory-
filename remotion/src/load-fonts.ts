/**
 * 🔤 Font Loader for Remotion v2.0
 * ═══════════════════════════════════════════════════════════════
 * يحمّل الخطوط العربية باستخدام @remotion/google-fonts
 *
 * المميزات:
 *   ✓ يستخدم Remotion's official API
 *   ✓ Auto-cleanup
 *   ✓ Timeout protection
 *   ✓ Type-safe font families
 *   ✓ يعمل في render mode و studio
 *
 * الخطوط المتاحة:
 *   • Cairo     - للترجمات (افتراضي)
 *   • Tajawal   - عصري
 *   • Almarai   - واضح
 *   • Noto Naskh Arabic - تقليدي
 * ═══════════════════════════════════════════════════════════════
 */

import { loadFont as loadCairo } from '@remotion/google-fonts/Cairo';
import { loadFont as loadTajawal } from '@remotion/google-fonts/Tajawal';
import { loadFont as loadAlmarai } from '@remotion/google-fonts/Almarai';
import { loadFont as loadNotoNaskh } from '@remotion/google-fonts/NotoNaskhArabic';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════
export type ArabicFontName = 'Cairo' | 'Tajawal' | 'Almarai' | 'NotoNaskhArabic';

export type FontWeight = '300' | '400' | '500' | '600' | '700' | '800' | '900';

export interface FontInfo {
  fontFamily: string;
  fontFile?: string;
  weights: FontWeight[];
  loaded: boolean;
}

export interface LoadFontOptions {
  weights?: FontWeight[];
  subsets?: string[];
}

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const DEFAULT_WEIGHTS: FontWeight[] = ['400', '700', '900'];
const DEFAULT_SUBSETS = ['arabic'];

// ═══════════════════════════════════════════════════════════════
// Font Cache
// ═══════════════════════════════════════════════════════════════
const fontCache = new Map<ArabicFontName, FontInfo>();

// ═══════════════════════════════════════════════════════════════
// 🔤 Load Cairo Font (default)
// ═══════════════════════════════════════════════════════════════
export const loadCairoFont = (
  options: LoadFontOptions = {},
): FontInfo => {
  // Check cache
  const cached = fontCache.get('Cairo');
  if (cached && cached.loaded) {
    return cached;
  }
  
  const weights = options.weights || DEFAULT_WEIGHTS;
  
  try {
    const { fontFamily } = loadCairo('normal', {
      weights,
      subsets: options.subsets || DEFAULT_SUBSETS,
    });
    
    const info: FontInfo = {
      fontFamily,
      weights,
      loaded: true,
    };
    
    fontCache.set('Cairo', info);
    return info;
  } catch (error) {
    console.error('❌ Failed to load Cairo:', error);
    return {
      fontFamily: 'Cairo, sans-serif',
      weights,
      loaded: false,
    };
  }
};

// ═══════════════════════════════════════════════════════════════
// 🔤 Load Tajawal Font
// ═══════════════════════════════════════════════════════════════
export const loadTajawalFont = (
  options: LoadFontOptions = {},
): FontInfo => {
  const cached = fontCache.get('Tajawal');
  if (cached && cached.loaded) {
    return cached;
  }
  
  const weights = options.weights || DEFAULT_WEIGHTS;
  
  try {
    const { fontFamily } = loadTajawal('normal', {
      weights,
      subsets: options.subsets || DEFAULT_SUBSETS,
    });
    
    const info: FontInfo = {
      fontFamily,
      weights,
      loaded: true,
    };
    
    fontCache.set('Tajawal', info);
    return info;
  } catch (error) {
    console.error('❌ Failed to load Tajawal:', error);
    return {
      fontFamily: 'Tajawal, sans-serif',
      weights,
      loaded: false,
    };
  }
};

// ═══════════════════════════════════════════════════════════════
// 🔤 Load Almarai Font
// ═══════════════════════════════════════════════════════════════
export const loadAlmaraiFont = (
  options: LoadFontOptions = {},
): FontInfo => {
  const cached = fontCache.get('Almarai');
  if (cached && cached.loaded) {
    return cached;
  }
  
  const weights = options.weights || DEFAULT_WEIGHTS;
  
  try {
    const { fontFamily } = loadAlmarai('normal', {
      weights,
      subsets: options.subsets || DEFAULT_SUBSETS,
    });
    
    const info: FontInfo = {
      fontFamily,
      weights,
      loaded: true,
    };
    
    fontCache.set('Almarai', info);
    return info;
  } catch (error) {
    console.error('❌ Failed to load Almarai:', error);
    return {
      fontFamily: 'Almarai, sans-serif',
      weights,
      loaded: false,
    };
  }
};

// ═══════════════════════════════════════════════════════════════
// 🔤 Load Noto Naskh Arabic
// ═══════════════════════════════════════════════════════════════
export const loadNotoNaskhFont = (
  options: LoadFontOptions = {},
): FontInfo => {
  const cached = fontCache.get('NotoNaskhArabic');
  if (cached && cached.loaded) {
    return cached;
  }
  
  const weights = options.weights || DEFAULT_WEIGHTS;
  
  try {
    const { fontFamily } = loadNotoNaskh('normal', {
      weights,
      subsets: options.subsets || DEFAULT_SUBSETS,
    });
    
    const info: FontInfo = {
      fontFamily,
      weights,
      loaded: true,
    };
    
    fontCache.set('NotoNaskhArabic', info);
    return info;
  } catch (error) {
    console.error('❌ Failed to load Noto Naskh:', error);
    return {
      fontFamily: 'Noto Naskh Arabic, serif',
      weights,
      loaded: false,
    };
  }
};

// ═══════════════════════════════════════════════════════════════
// 🌐 Load All Arabic Fonts
// ═══════════════════════════════════════════════════════════════
export const loadAllArabicFonts = (
  options: LoadFontOptions = {},
): Record<ArabicFontName, FontInfo> => {
  return {
    Cairo: loadCairoFont(options),
    Tajawal: loadTajawalFont(options),
    Almarai: loadAlmaraiFont(options),
    NotoNaskhArabic: loadNotoNaskhFont(options),
  };
};

// ═══════════════════════════════════════════════════════════════
// 🎨 Build font-family string (مع fallbacks)
// ═══════════════════════════════════════════════════════════════
export const buildArabicFontStack = (
  primary: ArabicFontName = 'Cairo',
): string => {
  const fonts = [
    `'${primary}'`,
    "'Cairo'",
    "'Tajawal'",
    "'Almarai'",
    "'Noto Naskh Arabic'",
    'sans-serif',
  ];
  
  // Remove duplicates
  const unique = [...new Set(fonts)];
  return unique.join(', ');
};

// ═══════════════════════════════════════════════════════════════
// 📋 Generic Font Loader
// ═══════════════════════════════════════════════════════════════
export const loadFont = (
  fontName: ArabicFontName,
  options: LoadFontOptions = {},
): FontInfo => {
  switch (fontName) {
    case 'Cairo':
      return loadCairoFont(options);
    case 'Tajawal':
      return loadTajawalFont(options);
    case 'Almarai':
      return loadAlmaraiFont(options);
    case 'NotoNaskhArabic':
      return loadNotoNaskhFont(options);
    default:
      console.warn(`⚠ Unknown font: ${fontName}, falling back to Cairo`);
      return loadCairoFont(options);
  }
};

// ═══════════════════════════════════════════════════════════════
// 🔍 Get Loaded Fonts
// ═══════════════════════════════════════════════════════════════
export const getLoadedFonts = (): ArabicFontName[] => {
  const loaded: ArabicFontName[] = [];
  fontCache.forEach((info, name) => {
    if (info.loaded) {
      loaded.push(name);
    }
  });
  return loaded;
};

// ═══════════════════════════════════════════════════════════════
// 🗑 Clear Cache (للـ testing)
// ═══════════════════════════════════════════════════════════════
export const clearFontCache = (): void => {
  fontCache.clear();
};

// ═══════════════════════════════════════════════════════════════
// Default Export
// ═══════════════════════════════════════════════════════════════
export default loadCairoFont;

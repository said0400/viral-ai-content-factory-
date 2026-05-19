/**
 * 🎬 Remotion Configuration v2.1
 * ═══════════════════════════════════════════════════════════════
 * إعدادات Remotion للتصدير والمعاينة
 *
 * Documentation: https://www.remotion.dev/docs/config
 * Version: 4.0+
 *
 * التحسينات v2.1:
 *   ✓ إزالة numberOfGifLoops (للـ GIF فقط)
 *   ✓ معالجة آمنة للـ APIs غير المتاحة
 *   ✓ إعدادات CI/CD محسّنة
 * ═══════════════════════════════════════════════════════════════
 */

import { Config } from '@remotion/cli/config';
import path from 'path';

// ═══════════════════════════════════════════════════════════════
// Environment Variables
// ═══════════════════════════════════════════════════════════════
const ENV = {
  // Quality
  JPEG_QUALITY: parseInt(process.env.REMOTION_JPEG_QUALITY || '90', 10),
  CRF: parseInt(process.env.REMOTION_CRF || '19', 10),
  
  // Performance
  CONCURRENCY: parseInt(process.env.REMOTION_CONCURRENCY || '4', 10),
  TIMEOUT_MS: parseInt(process.env.REMOTION_TIMEOUT || '60000', 10),
  
  // Mode
  IS_CI: process.env.CI === 'true' || process.env.GITHUB_ACTIONS === 'true',
  IS_PRODUCTION: process.env.NODE_ENV === 'production',
  
  // Logging
  LOG_LEVEL: (process.env.REMOTION_LOG_LEVEL || 'info') as
    | 'verbose'
    | 'info'
    | 'warn'
    | 'error',
  
  // Browser
  CHROMIUM_EXECUTABLE: process.env.REMOTION_CHROMIUM_PATH || undefined,
  HEADLESS: process.env.REMOTION_HEADLESS !== 'false',
  
  // Cache
  CACHE_DIR: process.env.REMOTION_CACHE_DIR || './.remotion',
} as const;

// ═══════════════════════════════════════════════════════════════
// Helper: تعديل القيم حسب البيئة
// ═══════════════════════════════════════════════════════════════
const getConcurrency = (): number => {
  if (ENV.IS_CI) {
    // GitHub Actions / CI = 2 only
    return Math.min(ENV.CONCURRENCY, 2);
  }
  return ENV.CONCURRENCY;
};

const getCrf = (): number => {
  // في CI، نضحي بشيء من الجودة للسرعة
  if (ENV.IS_CI && !ENV.IS_PRODUCTION) {
    return Math.max(ENV.CRF, 23);
  }
  return ENV.CRF;
};

// ═══════════════════════════════════════════════════════════════
// 📹 Video Output Settings
// ═══════════════════════════════════════════════════════════════
Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);

// JPEG quality (60-100)
Config.setJpegQuality(ENV.JPEG_QUALITY);

// ═══════════════════════════════════════════════════════════════
// 🎞️ Codec & Encoding
// ═══════════════════════════════════════════════════════════════
Config.setCodec('h264');
Config.setPixelFormat('yuv420p');

/**
 * CRF (Constant Rate Factor)
 * - 0  = lossless (huge file)
 * - 17 = visually lossless
 * - 19 = excellent (default)
 * - 23 = good
 * - 28 = acceptable
 * - 35 = poor
 */
Config.setCrf(getCrf());

// Video bitrate (اختياري - استخدام CRF أفضل)
// Config.setVideoBitrate('8M');

// ═══════════════════════════════════════════════════════════════
// 🎵 Audio Settings
// ═══════════════════════════════════════════════════════════════
Config.setAudioCodec('aac');
Config.setAudioBitrate('192k');

// السماح بـ video بدون audio
Config.setEnforceAudioTrack(false);

// ⚠️ تم حذف Config.setNumberOfGifLoops()
// السبب: يعمل فقط مع codec='gif'، ليس h264
// لو تريد GIF، استخدم Config.setCodec('gif') ثم setNumberOfGifLoops

// ═══════════════════════════════════════════════════════════════
// ⚡ Performance
// ═══════════════════════════════════════════════════════════════
/**
 * Concurrent renders
 * - زيادة = سرعة + استهلاك RAM/CPU أكثر
 * - في CI: يُفضّل 2 (محدود الموارد)
 * - في local: 4-8 (حسب الجهاز)
 */
Config.setConcurrency(getConcurrency());

// Timeout per frame (ms) - معالجة آمنة
try {
  // @ts-ignore - قد لا يكون متاح في كل الإصدارات
  if (typeof (Config as any).setTimeoutInMilliseconds === 'function') {
    // @ts-ignore
    (Config as any).setTimeoutInMilliseconds(ENV.TIMEOUT_MS);
  }
} catch (e) {
  // ignore - الإصدار لا يدعمه
}

// ═══════════════════════════════════════════════════════════════
// 🌐 Chromium / Browser
// ═══════════════════════════════════════════════════════════════
/**
 * OpenGL renderer
 * - 'angle' = Default (works on most systems)
 * - 'swangle' = Software-based ANGLE (slower but stable)
 * - 'egl' = EGL renderer
 * - 'swiftshader' = Software rendering (CI/headless)
 */
const glRenderer = ENV.IS_CI ? 'swangle' : 'angle';
Config.setChromiumOpenGlRenderer(glRenderer);

// Chromium executable path (مفيد في CI)
if (ENV.CHROMIUM_EXECUTABLE) {
  Config.setBrowserExecutable(ENV.CHROMIUM_EXECUTABLE);
}

// Headless mode
Config.setChromiumHeadlessMode(ENV.HEADLESS);

/**
 * ⚠️ Disable web security
 * مطلوب للسماح بقراءة local files
 */
Config.setChromiumDisableWebSecurity(true);

// Ignore certificate errors (للـ HTTPS المحلي)
Config.setChromiumIgnoreCertificateErrors(false);

// ═══════════════════════════════════════════════════════════════
// 📝 Logging
// ═══════════════════════════════════════════════════════════════
Config.setLogLevel(ENV.LOG_LEVEL);

// ═══════════════════════════════════════════════════════════════
// 💾 Cache & Output
// ═══════════════════════════════════════════════════════════════
// Cache directory - معالجة آمنة
try {
  // @ts-ignore - قد لا يكون متاح
  if (typeof (Config as any).setCachingEnabled === 'function') {
    // @ts-ignore
    (Config as any).setCachingEnabled(!ENV.IS_CI);
  }
} catch (e) {
  // ignore
}

// Public directory للـ assets
Config.setPublicDir(path.resolve(__dirname, 'public'));

// ═══════════════════════════════════════════════════════════════
// 🔧 Webpack Override
// ═══════════════════════════════════════════════════════════════
Config.overrideWebpackConfig((currentConfiguration) => {
  return {
    ...currentConfiguration,
    
    resolve: {
      ...currentConfiguration.resolve,
      
      // Path aliases (تطابق مع tsconfig.json)
      alias: {
        ...currentConfiguration.resolve?.alias,
        '@': path.resolve(__dirname, 'src'),
        '@components': path.resolve(__dirname, 'src/components'),
        '@compositions': path.resolve(__dirname, 'src/compositions'),
        '@utils': path.resolve(__dirname, 'src/utils'),
        '@hooks': path.resolve(__dirname, 'src/hooks'),
      },
    },
    
    // تحسين الأداء
    performance: {
      ...currentConfiguration.performance,
      hints: ENV.IS_PRODUCTION ? 'warning' : false,
    },
    
    // Source maps فقط في development
    devtool: ENV.IS_PRODUCTION ? false : 'source-map',
  };
});

// ═══════════════════════════════════════════════════════════════
// 🎨 Studio Settings (Development Only)
// ═══════════════════════════════════════════════════════════════
if (!ENV.IS_CI) {
  try {
    // Studio port
    // @ts-ignore
    if (typeof (Config as any).setStudioPort === 'function') {
      // @ts-ignore
      (Config as any).setStudioPort(
        parseInt(process.env.REMOTION_STUDIO_PORT || '3000', 10)
      );
    }
    
    // Browser auto-open
    // @ts-ignore
    if (typeof (Config as any).setShouldOpenBrowser === 'function') {
      // @ts-ignore
      (Config as any).setShouldOpenBrowser(true);
    }
  } catch (e) {
    // ignore
  }
}

// ═══════════════════════════════════════════════════════════════
// 🚀 Production Optimizations
// ═══════════════════════════════════════════════════════════════
if (ENV.IS_PRODUCTION) {
  // Maximum compression
  Config.setCrf(Math.min(ENV.CRF, 19));
  
  // Higher quality JPEG
  Config.setJpegQuality(Math.max(ENV.JPEG_QUALITY, 90));
}

// ═══════════════════════════════════════════════════════════════
// 📊 Diagnostic (للـ debugging)
// ═══════════════════════════════════════════════════════════════
if (ENV.LOG_LEVEL === 'verbose') {
  console.log('🎬 Remotion Configuration v2.1:');
  console.log(`   • Concurrency: ${getConcurrency()}`);
  console.log(`   • CRF: ${getCrf()}`);
  console.log(`   • JPEG Quality: ${ENV.JPEG_QUALITY}`);
  console.log(`   • Mode: ${ENV.IS_CI ? 'CI' : 'Local'}`);
  console.log(`   • GL Renderer: ${glRenderer}`);
  console.log(`   • Public Dir: ${path.resolve(__dirname, 'public')}`);
  console.log(`   • Headless: ${ENV.HEADLESS}`);
}

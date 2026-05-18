/**
 * 🎬 Remotion Configuration v2.0
 * ═══════════════════════════════════════════════════════════════
 * إعدادات Remotion للتصدير والمعاينة
 *
 * Documentation: https://www.remotion.dev/docs/config
 * Version: 4.0+
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

// Timeout per frame (ms)
Config.setTimeoutInMilliseconds(ENV.TIMEOUT_MS);

// Number of frame buffer
// Config.setNumberOfGifLoops(0);  // ← فقط للـ GIFs، ليس MP4

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

// Headless mode (مفيد للـ debugging)
Config.setChromiumHeadlessMode(ENV.HEADLESS);

/**
 * ⚠️ Disable web security
 * مطلوب للسماح بقراءة local files
 * لكنه يفتح ثغرة أمنية صغيرة
 *
 * البديل الأفضل: استخدام staticFile() من Remotion
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
// Cache directory
Config.setCachingEnabled(!ENV.IS_CI); // disable في CI لتوفير مساحة

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
  // Studio port
  Config.setStudioPort(parseInt(process.env.REMOTION_STUDIO_PORT || '3000', 10));
  
  // Browser auto-open
  Config.setShouldOpenBrowser(true);
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
  console.log('🎬 Remotion Configuration:');
  console.log(`   • Concurrency: ${getConcurrency()}`);
  console.log(`   • CRF: ${getCrf()}`);
  console.log(`   • JPEG Quality: ${ENV.JPEG_QUALITY}`);
  console.log(`   • Mode: ${ENV.IS_CI ? 'CI' : 'Local'}`);
  console.log(`   • GL Renderer: ${glRenderer}`);
  console.log(`   • Public Dir: ${path.resolve(__dirname, 'public')}`);
}

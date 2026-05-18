/**
 * 🎬 Remotion Configuration v2.0
 * ═══════════════════════════════════════════════════════════════
 * إعدادات Remotion للتصدير والمعاينة
 * Documentation: https://www.remotion.dev/docs/config
 * ═══════════════════════════════════════════════════════════════
 */

import { Config } from '@remotion/cli/config';
import path from 'path';

// ═══════════════════════════════════════════════════════════════
// Environment Variables
// ═══════════════════════════════════════════════════════════════
const ENV = {
  JPEG_QUALITY: parseInt(process.env.REMOTION_JPEG_QUALITY || '90', 10),
  CRF: parseInt(process.env.REMOTION_CRF || '19', 10),
  CONCURRENCY: parseInt(process.env.REMOTION_CONCURRENCY || '4', 10),
  TIMEOUT_MS: parseInt(process.env.REMOTION_TIMEOUT || '60000', 10),
  IS_CI: process.env.CI === 'true' || process.env.GITHUB_ACTIONS === 'true',
  LOG_LEVEL: (process.env.REMOTION_LOG_LEVEL || 'info') as
    | 'verbose'
    | 'info'
    | 'warn'
    | 'error',
  CHROMIUM_EXECUTABLE: process.env.REMOTION_CHROMIUM_PATH || undefined,
  HEADLESS: process.env.REMOTION_HEADLESS !== 'false',
} as const;

// ═══════════════════════════════════════════════════════════════
// Helper Functions
// ═══════════════════════════════════════════════════════════════
const getConcurrency = (): number => {
  if (ENV.IS_CI) {
    return Math.min(ENV.CONCURRENCY, 2);
  }
  return ENV.CONCURRENCY;
};

const getCrf = (): number => {
  if (ENV.IS_CI) {
    return Math.max(ENV.CRF, 23);
  }
  return ENV.CRF;
};

// ═══════════════════════════════════════════════════════════════
// 📹 Video Output Settings
// ═══════════════════════════════════════════════════════════════
Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setJpegQuality(ENV.JPEG_QUALITY);

// ═══════════════════════════════════════════════════════════════
// 🎞️ Codec & Encoding
// ═══════════════════════════════════════════════════════════════
Config.setCodec('h264');
Config.setPixelFormat('yuv420p');
Config.setCrf(getCrf());

// ═══════════════════════════════════════════════════════════════
// 🎵 Audio Settings
// ═══════════════════════════════════════════════════════════════
Config.setAudioCodec('aac');
Config.setAudioBitrate('192k');
Config.setEnforceAudioTrack(false);

// ═══════════════════════════════════════════════════════════════
// ⚡ Performance
// ═══════════════════════════════════════════════════════════════
Config.setConcurrency(getConcurrency());

// ✅ Timeout (مهم!)
// ملاحظة: قد لا يكون متاح في كل الإصدارات
try {
  // @ts-ignore
  if (typeof Config.setTimeoutInMilliseconds === 'function') {
    // @ts-ignore
    Config.setTimeoutInMilliseconds(ENV.TIMEOUT_MS);
  }
} catch (e) {
  // ignore
}

// ⚠️ لا تستخدم numberOfGifLoops مع H264!
// Config.setNumberOfGifLoops(0);  // ← فقط للـ GIFs

// ═══════════════════════════════════════════════════════════════
// 🌐 Chromium / Browser
// ═══════════════════════════════════════════════════════════════
const glRenderer = ENV.IS_CI ? 'swangle' : 'angle';
Config.setChromiumOpenGlRenderer(glRenderer);

if (ENV.CHROMIUM_EXECUTABLE) {
  Config.setBrowserExecutable(ENV.CHROMIUM_EXECUTABLE);
}

Config.setChromiumHeadlessMode(ENV.HEADLESS);
Config.setChromiumDisableWebSecurity(true);
Config.setChromiumIgnoreCertificateErrors(false);

// ═══════════════════════════════════════════════════════════════
// 📝 Logging
// ═══════════════════════════════════════════════════════════════
Config.setLogLevel(ENV.LOG_LEVEL);

// ═══════════════════════════════════════════════════════════════
// 💾 Public Directory
// ═══════════════════════════════════════════════════════════════
Config.setPublicDir(path.resolve(__dirname, 'public'));

// ═══════════════════════════════════════════════════════════════
// 🔧 Webpack Override
// ═══════════════════════════════════════════════════════════════
Config.overrideWebpackConfig((currentConfiguration) => {
  return {
    ...currentConfiguration,
    resolve: {
      ...currentConfiguration.resolve,
      alias: {
        ...currentConfiguration.resolve?.alias,
      },
    },
  };
});

// ═══════════════════════════════════════════════════════════════
// 📊 Diagnostic
// ═══════════════════════════════════════════════════════════════
if (ENV.LOG_LEVEL === 'verbose') {
  console.log('🎬 Remotion Configuration:');
  console.log(`   • Concurrency: ${getConcurrency()}`);
  console.log(`   • CRF: ${getCrf()}`);
  console.log(`   • JPEG Quality: ${ENV.JPEG_QUALITY}`);
  console.log(`   • Mode: ${ENV.IS_CI ? 'CI' : 'Local'}`);
  console.log(`   • GL Renderer: ${glRenderer}`);
}

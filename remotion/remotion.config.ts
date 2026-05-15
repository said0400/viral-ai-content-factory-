/**
 * 🎬 Remotion Configuration
 * ═══════════════════════════════════════════════════════════════
 * إعدادات Remotion للتصدير والمعاينة
 * 
 * المرجع: https://www.remotion.dev/docs/config
 * ═══════════════════════════════════════════════════════════════
 */

import { Config } from "@remotion/cli/config";

// ─── إعدادات الفيديو الأساسية ──────────────────────────────────────
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);

// ─── الجودة (JPEG quality للـ frames) ─────────────────────────────
// كلما زاد الرقم، زادت الجودة (والحجم)
Config.setJpegQuality(90);

// ─── الترميز (Codec) ──────────────────────────────────────────────
Config.setCodec("h264");
Config.setPixelFormat("yuv420p");

// ─── CRF (Constant Rate Factor) ───────────────────────────────────
// 0 = lossless | 18 = ممتاز | 23 = جيد | 28 = منخفض
Config.setCrf(19);

// ─── الأداء ───────────────────────────────────────────────────────
// عدد العمليات المتوازية (concurrent renders)
// قلّل الرقم إذا كان جهازك ضعيف
Config.setConcurrency(4);

// ─── معدل الإطارات الافتراضي ──────────────────────────────────────
// 30 fps للشورتس | 60 fps للمحتوى السينمائي
// (يمكن تجاوزه من Composition)

// ─── إعدادات Chromium للـ Rendering ──────────────────────────────
Config.setChromiumOpenGlRenderer("angle");

// ─── السماح للملفات المحلية ───────────────────────────────────────
// مهم: للسماح بقراءة ملفات الفيديو والصوت من النظام
Config.setChromiumDisableWebSecurity(true);

// ─── حجم النافذة في الـ Studio ────────────────────────────────────
// (للمعاينة فقط)

// ─── الـ Logging ──────────────────────────────────────────────────
// "verbose" | "info" | "warn" | "error"
Config.setLevel("info");

// ─── إعدادات إضافية ───────────────────────────────────────────────
// تجاهل أخطاء الـ console من React
Config.setEnforceAudioTrack(false);

// السماح بمسارات الملفات الطويلة (للويندوز)
Config.setNumberOfGifLoops(0);

// ─── Webpack Override (للأداء) ────────────────────────────────────
Config.overrideWebpackConfig((currentConfiguration) => {
  return {
    ...currentConfiguration,
    resolve: {
      ...currentConfiguration.resolve,
      // alias للاستيرادات
      alias: {
        ...currentConfiguration.resolve?.alias,
      },
    },
  };
});

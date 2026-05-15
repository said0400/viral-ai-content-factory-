/**
 * 🔤 Font Loader for Remotion
 * ═══════════════════════════════════════════════════════════════
 * يحمّل الخطوط العربية من:
 *   1. الخطوط المحلية (public/fonts.css) - أساسي
 *   2. Google Fonts - احتياطي
 * 
 * يضمن أن الخط جاهز قبل البدء بالـ rendering
 * ═══════════════════════════════════════════════════════════════
 */

import { continueRender, delayRender } from "remotion";

// ─── حالة التحميل (لتجنب التحميل المتكرر) ──────────────────────────
let fontsLoaded = false;

// ════════════════════════════════════════════════════════════════════
// 🌟 تحميل خط Cairo (الأساسي)
// ════════════════════════════════════════════════════════════════════
export const loadCairoFont = (): number => {
  // تجنب التحميل المتكرر
  if (fontsLoaded) {
    return delayRender("Fonts already loaded");
  }

  const handle = delayRender("Loading Cairo font...");

  try {
    // 1️⃣ محاولة تحميل الخطوط المحلية أولاً
    const localStyle = document.createElement("link");
    localStyle.rel = "stylesheet";
    localStyle.href = "/fonts.css";
    localStyle.onerror = () => {
      console.warn("⚠ Local fonts.css not found, will use Google Fonts");
    };
    document.head.appendChild(localStyle);

    // 2️⃣ تحميل Cairo من Google Fonts (كـ fallback)
    const googleStyle = document.createElement("link");
    googleStyle.rel = "stylesheet";
    googleStyle.href =
      "https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap";

    googleStyle.onload = () => {
      fontsLoaded = true;
      console.log("✓ Cairo font loaded from Google Fonts");
      continueRender(handle);
    };

    googleStyle.onerror = (error) => {
      console.error("✗ Failed to load Cairo from Google Fonts:", error);
      // نستمر حتى لو فشل (الخطوط المحلية قد تكون شغّالة)
      continueRender(handle);
    };

    document.head.appendChild(googleStyle);
  } catch (error) {
    console.error("✗ Font loading error:", error);
    continueRender(handle);
  }

  return handle;
};

// ════════════════════════════════════════════════════════════════════
// 🎨 تحميل كل الخطوط العربية المتاحة
// ════════════════════════════════════════════════════════════════════
export const loadAllArabicFonts = (): number => {
  if (fontsLoaded) {
    return delayRender("Fonts already loaded");
  }

  const handle = delayRender("Loading all Arabic fonts...");

  try {
    // قائمة الخطوط العربية من Google Fonts
    const fontFamilies = [
      "Cairo:wght@400;700;900",
      "Tajawal:wght@400;700;800",
      "Almarai:wght@400;700;800",
      "Amiri:wght@400;700",
      "Noto+Naskh+Arabic:wght@400;700",
    ];

    // 1️⃣ تحميل الخطوط المحلية
    const localStyle = document.createElement("link");
    localStyle.rel = "stylesheet";
    localStyle.href = "/fonts.css";
    document.head.appendChild(localStyle);

    // 2️⃣ تحميل من Google Fonts
    const googleStyle = document.createElement("link");
    googleStyle.rel = "stylesheet";
    googleStyle.href = `https://fonts.googleapis.com/css2?${fontFamilies
      .map((f) => `family=${f}`)
      .join("&")}&display=swap`;

    googleStyle.onload = () => {
      fontsLoaded = true;
      console.log("✓ All Arabic fonts loaded");
      continueRender(handle);
    };

    googleStyle.onerror = (error) => {
      console.error("✗ Failed to load fonts:", error);
      continueRender(handle);
    };

    document.head.appendChild(googleStyle);
  } catch (error) {
    console.error("✗ Font loading error:", error);
    continueRender(handle);
  }

  return handle;
};

// ════════════════════════════════════════════════════════════════════
// 🎯 تحميل خط محدد
// ════════════════════════════════════════════════════════════════════
export const loadSpecificFont = (
  fontName: string,
  weights: number[] = [400, 700, 900]
): number => {
  const handle = delayRender(`Loading ${fontName} font...`);

  try {
    const weightsStr = weights.join(";");
    const fontUrl = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(
      fontName
    )}:wght@${weightsStr}&display=swap`;

    const style = document.createElement("link");
    style.rel = "stylesheet";
    style.href = fontUrl;

    style.onload = () => {
      console.log(`✓ ${fontName} loaded`);
      continueRender(handle);
    };

    style.onerror = (error) => {
      console.error(`✗ Failed to load ${fontName}:`, error);
      continueRender(handle);
    };

    document.head.appendChild(style);
  } catch (error) {
    console.error("✗ Font loading error:", error);
    continueRender(handle);
  }

  return handle;
};

// ════════════════════════════════════════════════════════════════════
// 🔍 التحقق من تحميل خط
// ════════════════════════════════════════════════════════════════════
export const isFontLoaded = (fontName: string): boolean => {
  if (typeof document === "undefined") return false;

  try {
    return document.fonts.check(`16px "${fontName}"`);
  } catch {
    return false;
  }
};

// ════════════════════════════════════════════════════════════════════
// 📦 Export Default
// ════════════════════════════════════════════════════════════════════
export default loadCairoFont;

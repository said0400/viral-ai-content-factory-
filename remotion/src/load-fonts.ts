/**
 * 🔤 Font Loader for Remotion
 * ═══════════════════════════════════════════════════════════════
 * يحمّل خط Cairo من Google Fonts
 * (لا يحاول تحميل fonts.css المحلي لتجنب 404)
 * ═══════════════════════════════════════════════════════════════
 */

import { continueRender, delayRender } from "remotion";

let fontsLoaded = false;

// ════════════════════════════════════════════════════════════════════
// 🌟 تحميل خط Cairo من Google Fonts
// ════════════════════════════════════════════════════════════════════
export const loadCairoFont = (): number => {
  if (fontsLoaded) {
    return delayRender("Fonts already loaded");
  }

  const handle = delayRender("Loading Cairo font...");

  try {
    const googleStyle = document.createElement("link");
    googleStyle.rel = "stylesheet";
    googleStyle.href =
      "https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap";

    googleStyle.onload = () => {
      fontsLoaded = true;
      console.log("✓ Cairo font loaded");
      continueRender(handle);
    };

    googleStyle.onerror = (error) => {
      console.error("✗ Failed to load Cairo:", error);
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
// 🎨 تحميل كل الخطوط العربية
// ════════════════════════════════════════════════════════════════════
export const loadAllArabicFonts = (): number => {
  if (fontsLoaded) {
    return delayRender("Fonts already loaded");
  }

  const handle = delayRender("Loading all Arabic fonts...");

  try {
    const fontFamilies = [
      "Cairo:wght@400;700;900",
      "Tajawal:wght@400;700;800",
      "Almarai:wght@400;700;800",
      "Amiri:wght@400;700",
    ];

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

export default loadCairoFont;

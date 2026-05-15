/**
 * 🎬 Remotion Entry Point
 * ═══════════════════════════════════════════════════════════════
 * نقطة الدخول الرئيسية لمشروع Remotion
 * 
 * يُسجّل الـ Root Component الذي يحتوي كل الـ Compositions
 * ═══════════════════════════════════════════════════════════════
 */

import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";

// تسجيل الـ Root Component
registerRoot(RemotionRoot);

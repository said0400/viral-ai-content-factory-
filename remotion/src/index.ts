/**
 * 🎬 Remotion Entry Point
 * ═══════════════════════════════════════════════════════════════
 * نقطة الدخول الرئيسية لمشروع Remotion
 *
 * يُسجّل الـ Root Component الذي يحتوي كل الـ Compositions
 *
 * Note: لا تضع أي logic هنا - فقط تسجيل
 * كل compositions تُعرّف في Root.tsx
 * ═══════════════════════════════════════════════════════════════
 */

import { registerRoot } from 'remotion';
import { RemotionRoot } from './Root';

// ═══════════════════════════════════════════════════════════════
// Error Handler (للـ debugging في dev mode)
// ═══════════════════════════════════════════════════════════════
if (process.env.NODE_ENV === 'development') {
  // معالج للأخطاء غير المتوقعة في React
  window.addEventListener('error', (event) => {
    console.error('🔴 Unhandled error:', event.error);
  });
  
  window.addEventListener('unhandledrejection', (event) => {
    console.error('🔴 Unhandled promise rejection:', event.reason);
  });
}

// ═══════════════════════════════════════════════════════════════
// Register Root
// ═══════════════════════════════════════════════════════════════
registerRoot(RemotionRoot);

// ═══════════════════════════════════════════════════════════════
// Development Info (للـ Studio فقط)
// ═══════════════════════════════════════════════════════════════
if (process.env.NODE_ENV === 'development') {
  console.log(
    '%c🎬 Viral AI Factory - Remotion',
    'color: #FFD700; font-size: 16px; font-weight: bold;',
  );
  console.log(
    '%cVersion 2.0 | Built with Remotion 4.x',
    'color: #888; font-size: 12px;',
  );
}

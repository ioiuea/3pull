/**
 * Email 認証フォームの表示可否.
 *
 * `VITE_ENABLE_EMAIL_AUTH=true` のときのみ有効化する。
 */
export const ENABLE_EMAIL_AUTH =
  (import.meta.env.VITE_ENABLE_EMAIL_AUTH || 'true').trim().toLowerCase() === 'true';

/**
 * プロダクト表示名.
 *
 * `.env` の `VITE_PRODUCT_NAME` を優先し、未設定時は `3pull` を利用する。
 */
export const PRODUCT_NAME = (import.meta.env.VITE_PRODUCT_NAME || '3pull').trim();

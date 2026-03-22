/**
 * 認証関連画面で利用する return_to を安全な相対パスへ正規化する。
 */
export const sanitizeReturnTo = (
  value: string | null,
  {
    currentLanguage,
    disallowedPaths = [],
  }: {
    currentLanguage: string;
    disallowedPaths?: string[];
  },
) => {
  const fallback = `/${currentLanguage}`;
  if (!value || !value.startsWith('/')) {
    return fallback;
  }

  try {
    const parsed = new URL(value, 'http://localhost');
    if (parsed.origin !== 'http://localhost') {
      return fallback;
    }
    if (disallowedPaths.includes(parsed.pathname)) {
      return fallback;
    }
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return fallback;
  }
};

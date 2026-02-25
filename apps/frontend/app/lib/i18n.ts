import i18n from 'i18next';
import Backend from 'i18next-http-backend';
import { initReactI18next } from 'react-i18next';

/**
 * アプリで選択可能な言語コードの一覧です。
 * URL パラメータ、Cookie、ブラウザ設定の判定時にこの配列を正として扱います。
 */
export const SUPPORTED_LANGUAGES = ['en', 'ja'] as const;

/**
 * 利用可能な言語を解決できなかった場合に使う既定言語です。
 */
export const DEFAULT_LANGUAGE = 'ja';

/**
 * 言語設定を保存する Cookie のキー名です。
 */
export const LANGUAGE_COOKIE_KEY = 'locale';

/**
 * i18next で利用するデフォルト namespace 名です。
 */
export const I18N_NAMESPACE = 'common';

/**
 * アプリが受け付ける言語コード型です。
 */
export type AppLanguage = (typeof SUPPORTED_LANGUAGES)[number];

/**
 * 与えられた文字列がサポート対象言語かを判定します。
 */
export function isSupportedLanguage(value: string): value is AppLanguage {
  return SUPPORTED_LANGUAGES.includes(value as AppLanguage);
}

/**
 * Cookie から指定キーの値を読み取ります。
 *
 * @param name Cookie のキー名
 * @returns キーが存在すれば値、存在しなければ `null`
 */
function getCookie(name: string): string | null {
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${name.replace(/[-[\]/{}()*+?.\\^$|]/g, '\\$&')}=([^;]*)`),
  );
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * 画面初期表示時に利用する言語を解決します。
 *
 * 優先順位:
 * 1. `locale` Cookie
 * 2. ブラウザ言語 (`navigator.language`)
 * 3. `DEFAULT_LANGUAGE`
 */
export function detectLanguage(): AppLanguage {
  const cookieLanguage = getCookie(LANGUAGE_COOKIE_KEY);
  if (cookieLanguage && isSupportedLanguage(cookieLanguage)) {
    return cookieLanguage;
  }

  const browserLanguage = navigator.language.split('-')[0];
  if (isSupportedLanguage(browserLanguage)) {
    return browserLanguage;
  }

  return DEFAULT_LANGUAGE;
}

/**
 * 言語設定を Cookie に保存します。
 * 保存期間は 1 年、アプリ全体で参照できるように `path=/` を指定します。
 *
 * @param language 保存する言語コード
 */
export function persistLanguageCookie(language: AppLanguage): void {
  document.cookie = `${LANGUAGE_COOKIE_KEY}=${encodeURIComponent(language)}; path=/; max-age=31536000; samesite=lax`;
}

/**
 * i18next のクライアント設定を初期化します。
 * 翻訳辞書は `public/dictionaries/{{lng}}/{{ns}}.json` から読み込みます。
 * `common` 以外の namespace は `useTranslation("<namespace>")` の呼び出し時に
 * 必要なものだけ動的にロードします。
 */
void i18n
  .use(Backend)
  .use(initReactI18next)
  .init({
    fallbackLng: DEFAULT_LANGUAGE,
    supportedLngs: [...SUPPORTED_LANGUAGES],
    defaultNS: I18N_NAMESPACE,
    ns: [I18N_NAMESPACE],
    backend: {
      loadPath: '/dictionaries/{{lng}}/{{ns}}.json',
    },
    interpolation: {
      escapeValue: false,
    },
  });

/**
 * React コンポーネント側で利用する i18next インスタンスです。
 */
export default i18n;

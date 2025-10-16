import { NextResponse } from "next/server";
import { auth } from "@/auth";
import type { NextRequest } from "next/server";

const locales = ["ja", "en"];
const defaultLocale = "ja";

/**
 * リクエストヘッダーの "Accept-Language" から利用者の言語設定を判定し、
 * 対応しているロケールを返します。
 *
 * 対応しているロケール（`locales`配列内）が見つからない場合は、
 * デフォルトロケール（`defaultLocale`）を返します。
 *
 * @param request - Next.js のリクエストオブジェクト
 * @returns 判定されたロケール文字列（例: `'ja'` または `'en'`）
 *
 * @example
 * ```ts
 * const locale = getLocale(request)
 * console.log(locale) // "ja"
 * ```
 */
function getLocale(request: NextRequest): string {
  const acceptLanguage = request.headers.get("accept-language");
  if (!acceptLanguage) return defaultLocale;

  const languages = acceptLanguage
    .split(",")
    .map((lang) => lang.split(";")[0].trim().toLowerCase());

  for (const lang of languages) {
    if (locales.includes(lang)) return lang;
    const prefix = lang.split("-")[0];
    if (locales.includes(prefix)) return prefix;
  }

  return defaultLocale;
}

/**
 * ブラウザの言語設定に基づいて、利用者を適切なロケール付きのパスにリダイレクトする
 * Next.js のミドルウェア関数です。
 *
 * すでにパスにロケールが含まれている場合（例: `/ja/about`）はリダイレクトしません。
 * 含まれていない場合（例: `/about`）は `/ja/about` や `/en/about` のようにリダイレクトします。
 *
 * @param request - Next.js のリクエストオブジェクト
 * @returns ロケール付きURLへのリダイレクトレスポンス、
 *          もしくはロケールがすでに含まれている場合は `undefined`
 *
 * @example
 * ```ts
 * // 例: ブラウザの言語設定が日本語の場合
 * // "/contact" にアクセスすると "/ja/contact" にリダイレクトされます。
 * export function middleware(request: NextRequest) {
 *   ...
 * }
 * ```
 */
export const middleware = auth((request) => {
  const { nextUrl } = request;
  const { pathname } = nextUrl;

  const hasLocale = locales.some(
    (locale) => pathname.startsWith(`/${locale}/`) || pathname === `/${locale}`
  );

  if (!hasLocale) {
    const locale = getLocale(request);
    const url = nextUrl.clone();
    url.pathname = `/${locale}${pathname}`;
    return NextResponse.redirect(url);
  }

  // ログインしていなければロケール付きサインインへ
  if (!request.auth) {
    const url = nextUrl.clone();
    const locale = pathname.split("/")[1] || defaultLocale;
    url.pathname = `/${locale}/signin`;
    url.searchParams.set("callbackUrl", nextUrl.pathname + nextUrl.search);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
});

/**
 * ミドルウェアの適用対象を定義する設定です。
 *
 * `_next`（Next.jsの内部パス）、`api`（APIルート）、および静的ファイルへのリクエストを除外します。
 */
export const config = {
  matcher: ["/((?!_next|api|.*\\.|.*/signin).*)"],
};

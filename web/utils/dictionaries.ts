import "server-only";

/**
 * 各ロケール（言語）に対応する辞書ファイルを動的に読み込む関数群です。
 *
 * `import()` による **動的インポート** を利用しており、
 * 利用されるタイミングで必要な辞書データ（`ja.json`, `en.json` など）を非同期で読み込みます。
 *
 * 各関数は JSON モジュールを読み込み、`default` エクスポートされたオブジェクトを返します。
 */
const dictionaries = {
  ja: () => import("@/dictionaries/ja.json").then((module) => module.default),
  en: () => import("@/dictionaries/en.json").then((module) => module.default),
};

/**
 * 利用可能なロケール（言語コード）の型定義。
 *
 * `dictionaries` オブジェクトのキーを自動的に抽出して型にしています。
 * そのため、新しいロケールを追加した場合も型が自動的に更新されます。
 *
 * @example
 * ```ts
 * let locale: Locale = 'ja'
 * // 'en' も指定可能
 * ```
 */
export type Locale = keyof typeof dictionaries;

/**
 * 指定されたロケールに対応する辞書データを非同期で取得します。
 *
 * 内部的には `dictionaries` オブジェクトの対応関数を呼び出し、
 * JSONファイル（例: `ja.json`, `en.json`）を `import()` 経由で読み込みます。
 *
 * @param locale - 取得したいロケール（例: `'ja'` または `'en'`）
 * @returns 選択したロケールの辞書データ（JSONオブジェクト）
 *
 * @example
 * ```ts
 * const dict = await getDictionary('ja')
 * console.log(dict["hello"]) // => "こんにちは"
 * ```
 */
export const getDictionary = async (locale: Locale) => {
  return dictionaries[locale]();
};

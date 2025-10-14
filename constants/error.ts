/**
 * エラーコードとエラーメッセージの定数定義
 *
 * エラーコードの命名規則: ERR_{カテゴリ}_{連番}
 * - 認証エラー: ERR_AUTH_xxx
 * - バリデーションエラー: ERR_VALIDATION_xxx
 * - ネットワークエラー: ERR_NETWORK_xxx
 * - データベースエラー: ERR_DATABASE_xxx
 */

export const ERR_AUTH_001 = "ERR_AUTH_001";
export const ERR_AUTH_002 = "ERR_AUTH_002";
export const ERR_AUTH_003 = "ERR_AUTH_003";

export const ERR_VALIDATION_001 = "ERR_VALIDATION_001";
export const ERR_VALIDATION_002 = "ERR_VALIDATION_002";

export const ERR_NETWORK_001 = "ERR_NETWORK_001";
export const ERR_NETWORK_002 = "ERR_NETWORK_002";

/**
 * エラーメッセージ
 */
export const ERROR_MESSAGES = {
  [ERR_AUTH_001]: "Authentication failed. Please log in again.",
  [ERR_AUTH_002]: "Your session has expired. Please log in again.",
  [ERR_AUTH_003]: "You do not have permission to access this resource.",
  [ERR_VALIDATION_001]:
    "There was an error in your input. Please check and try again.",
  [ERR_VALIDATION_002]: "A required field is missing.",
  [ERR_NETWORK_001]:
    "A network error has occurred. Please check your connection.",
  [ERR_NETWORK_002]: "Unable to connect to the server. Please try again later.",
} as const;

/**
 * エラーメッセージを取得する
 * @param errorCode - エラーコード
 * @returns エラーメッセージ
 */
export function getErrorMessage(errorCode: string): string {
  return (
    ERROR_MESSAGES[errorCode as keyof typeof ERROR_MESSAGES] ||
    "An unexpected error has occurred."
  );
}

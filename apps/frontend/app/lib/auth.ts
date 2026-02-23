import { PublicClientApplication, type Configuration, LogLevel } from '@azure/msal-browser';

/**
 * Entra ID の必須設定値です。
 * `.env` から読み込み、未設定時は空文字として扱います。
 */
const ENTRA_CLIENT_ID = import.meta.env.VITE_ENTRA_CLIENT_ID ?? '';
const ENTRA_TENANT_ID = import.meta.env.VITE_ENTRA_TENANT_ID ?? '';

/**
 * MSAL 設定が利用可能かを判定します。
 */
export const isMsalConfigured = ENTRA_CLIENT_ID.length > 0 && ENTRA_TENANT_ID.length > 0;

/**
 * SPA 用の MSAL 設定です。
 */
const msalConfig: Configuration = {
  auth: {
    clientId: ENTRA_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${ENTRA_TENANT_ID || 'common'}`,
    redirectUri: import.meta.env.VITE_ENTRA_REDIRECT_URI ?? 'http://localhost:5173',
    postLogoutRedirectUri:
      import.meta.env.VITE_ENTRA_POST_LOGOUT_REDIRECT_URI ?? 'http://localhost:5173',
  },
  cache: {
    cacheLocation: 'localStorage',
  },
  system: {
    loggerOptions: {
      loggerCallback: () => {
        // アプリ側で追加ログは出さない
      },
      logLevel: LogLevel.Warning,
    },
  },
};

/**
 * 認証・トークン取得で使用するスコープ定義です。
 */
export const loginRequest = {
  scopes: ['User.Read'],
};

/**
 * Graph API から取得するプロフィール情報のエンドポイントです。
 */
export const graphProfileEndpoint =
  'https://graph.microsoft.com/v1.0/me?$select=companyName,department,employeeId,displayName,userPrincipalName,mail';

/**
 * アプリ全体で共有する MSAL インスタンスです。
 */
export const msalInstance = new PublicClientApplication(msalConfig);

void msalInstance.initialize();

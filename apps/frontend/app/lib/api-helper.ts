/**
 * Backend API クライアントヘルパー.
 */

export type AuthMe = {
  id: string;
  email: string;
  display_name: string | null;
  user_type: 'internal' | 'external';
  is_active: boolean;
};

const BACKEND_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:8000';
const API_PREFIX = '/backend';

const buildApiUrl = (path: string) => `${BACKEND_BASE_URL}${API_PREFIX}${path}`;

export const backendFetch = async (path: string, init?: RequestInit) =>
  fetch(buildApiUrl(path), {
    credentials: 'include',
    ...init,
    headers: (() => {
      const headers = new Headers(init?.headers ?? {});
      const hasBody = init?.body !== undefined && init?.body !== null;
      if (hasBody && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
      }
      return headers;
    })(),
  });

export const getMe = async (): Promise<AuthMe | null> => {
  const response = await backendFetch('/auth/me');
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`/auth/me failed: ${response.status}`);
  }
  return (await response.json()) as AuthMe;
};

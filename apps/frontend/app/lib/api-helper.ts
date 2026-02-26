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

export type AuditLogItem = {
  id: number;
  occurred_at: string;
  event_type: string;
  user_id: string | null;
  user_display_name: string | null;
  user_email: string | null;
  session_id: string | null;
  provider: string | null;
  client_ip: string | null;
  xff_raw: string | null;
  connection_ip: string | null;
  user_agent: string | null;
  reason_code: string | null;
  metadata: Record<string, unknown> | null;
};

export type AuditLogListResponse = {
  page: number;
  page_size: number;
  total: number;
  items: AuditLogItem[];
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

type GetAuditLogsParams = {
  page?: number;
  pageSize?: number;
  eventType?: string;
  userId?: string;
};

export const getAuditLogs = async (
  params: GetAuditLogsParams = {},
): Promise<AuditLogListResponse> => {
  const search = new URLSearchParams();
  search.set('page', String(params.page ?? 1));
  search.set('page_size', String(params.pageSize ?? 50));
  if (params.eventType) {
    search.set('event_type', params.eventType);
  }
  if (params.userId) {
    search.set('user_id', params.userId);
  }

  const response = await backendFetch(`/auth/audit-logs?${search.toString()}`);
  if (!response.ok) {
    throw new Error(`/auth/audit-logs failed: ${response.status}`);
  }
  return (await response.json()) as AuditLogListResponse;
};

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

export type AuditLogExportCreateRequest = {
  event_type?: string;
  provider?: string;
  keyword?: string;
  date_from?: string;
  date_to?: string;
  timezone?: 'UTC' | 'Asia/Tokyo';
};

export type AuditLogExportJob = {
  id: string;
  requested_by_user_id: string | null;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled' | 'expired';
  file_format: 'csv';
  requested_filters: Record<string, unknown>;
  timezone: string;
  file_path: string | null;
  file_size_bytes: number | null;
  row_count: number | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  expires_at: string;
  created_at: string;
};

export type AuditLogExportJobListResponse = {
  total: number;
  items: AuditLogExportJob[];
};

export type SampleWaitBlobCreateRequest = {
  wait_seconds?: number;
  content?: string;
};

export type SampleWaitBlobJob = {
  id: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled' | 'expired';
  wait_seconds: number;
  content: string | null;
  file_path: string | null;
  file_size_bytes: number | null;
  error_message: string | null;
  created_at: string;
  finished_at: string | null;
};

export type SampleWaitBlobJobListResponse = {
  total: number;
  items: SampleWaitBlobJob[];
};

type AsyncJobArtifact = {
  id: string;
  artifact_type: string;
  storage_provider: string;
  container_name: string;
  blob_path: string;
  content_type: string;
  file_size_bytes: number;
  checksum: string | null;
  expires_at: string | null;
  created_at: string;
};

type AsyncJobResponse = {
  id: string;
  job_type: string;
  requested_by_user_id: string | null;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled' | 'expired';
  requested_payload: Record<string, unknown>;
  result_payload: Record<string, unknown> | null;
  error_message: string | null;
  retry_count: number;
  started_at: string | null;
  finished_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
  artifacts: AsyncJobArtifact[];
};

type AsyncJobListResponse = {
  total: number;
  items: AsyncJobResponse[];
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

  const response = await backendFetch(`/audit/audit-logs?${search.toString()}`);
  if (!response.ok) {
    throw new Error(`/audit/audit-logs failed: ${response.status}`);
  }
  return (await response.json()) as AuditLogListResponse;
};

type GetAuditLogExportsParams = {
  page?: number;
  pageSize?: number;
};

const toAuditLogExportJob = (job: AsyncJobResponse): AuditLogExportJob => {
  const requestedPayload = job.requested_payload ?? {};
  const requestedFilters =
    typeof requestedPayload.requested_filters === 'object' &&
    requestedPayload.requested_filters !== null
      ? (requestedPayload.requested_filters as Record<string, unknown>)
      : {};
  const timezone =
    typeof requestedPayload.timezone === 'string' ? requestedPayload.timezone : 'UTC';
  const firstArtifact = job.artifacts[0] ?? null;
  const rowCountRaw = job.result_payload?.row_count;
  const rowCount =
    typeof rowCountRaw === 'number' && Number.isFinite(rowCountRaw) ? rowCountRaw : null;

  return {
    id: job.id,
    requested_by_user_id: job.requested_by_user_id,
    status: job.status,
    file_format: 'csv',
    requested_filters: requestedFilters,
    timezone,
    file_path: firstArtifact?.blob_path ?? null,
    file_size_bytes: firstArtifact?.file_size_bytes ?? null,
    row_count: rowCount,
    error_message: job.error_message,
    started_at: job.started_at,
    finished_at: job.finished_at,
    expires_at: job.expires_at ?? job.created_at,
    created_at: job.created_at,
  };
};

const toSampleWaitBlobJob = (job: AsyncJobResponse): SampleWaitBlobJob => {
  const requestedPayload = job.requested_payload ?? {};
  const waitSecondsRaw = requestedPayload.wait_seconds;
  const contentRaw = requestedPayload.content;
  const firstArtifact = job.artifacts[0] ?? null;
  return {
    id: job.id,
    status: job.status,
    wait_seconds:
      typeof waitSecondsRaw === 'number' && Number.isFinite(waitSecondsRaw) ? waitSecondsRaw : 120,
    content: typeof contentRaw === 'string' ? contentRaw : null,
    file_path: firstArtifact?.blob_path ?? null,
    file_size_bytes: firstArtifact?.file_size_bytes ?? null,
    error_message: job.error_message,
    created_at: job.created_at,
    finished_at: job.finished_at,
  };
};

export const createAuditLogExport = async (
  payload: AuditLogExportCreateRequest,
): Promise<AuditLogExportJob> => {
  const response = await backendFetch('/jobs/auth-audit-export', {
    method: 'POST',
    body: JSON.stringify({
      event_type: payload.event_type,
      provider: payload.provider,
      keyword: payload.keyword,
      date_from: payload.date_from,
      date_to: payload.date_to,
      timezone: payload.timezone ?? 'UTC',
    }),
  });
  if (!response.ok) {
    throw new Error(`/jobs/auth-audit-export POST failed: ${response.status}`);
  }
  const job = (await response.json()) as AsyncJobResponse;
  return toAuditLogExportJob(job);
};

export const getAuditLogExports = async (
  params: GetAuditLogExportsParams = {},
): Promise<AuditLogExportJobListResponse> => {
  const search = new URLSearchParams();
  search.set('page', String(params.page ?? 1));
  search.set('page_size', String(params.pageSize ?? 20));
  search.set('job_type', 'auth_audit_export');

  const response = await backendFetch(`/jobs?${search.toString()}`);
  if (!response.ok) {
    throw new Error(`/jobs GET failed: ${response.status}`);
  }
  const data = (await response.json()) as AsyncJobListResponse;
  return {
    total: data.total,
    items: data.items.map(toAuditLogExportJob),
  };
};

export const getAuditLogExportById = async (jobId: string): Promise<AuditLogExportJob> => {
  const response = await backendFetch(`/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(`/jobs/${jobId} GET failed: ${response.status}`);
  }
  const job = (await response.json()) as AsyncJobResponse;
  return toAuditLogExportJob(job);
};

export const createSampleWaitBlobJob = async (
  payload: SampleWaitBlobCreateRequest = {},
): Promise<SampleWaitBlobJob> => {
  const response = await backendFetch('/jobs/sample-wait-blob', {
    method: 'POST',
    body: JSON.stringify({
      wait_seconds: payload.wait_seconds ?? 120,
      content: payload.content ?? null,
    }),
  });
  if (!response.ok) {
    throw new Error(`/jobs/sample-wait-blob POST failed: ${response.status}`);
  }
  const job = (await response.json()) as AsyncJobResponse;
  return toSampleWaitBlobJob(job);
};

export const getSampleWaitBlobJobs = async (
  params: GetAuditLogExportsParams = {},
): Promise<SampleWaitBlobJobListResponse> => {
  const search = new URLSearchParams();
  search.set('page', String(params.page ?? 1));
  search.set('page_size', String(params.pageSize ?? 20));
  search.set('job_type', 'sample_wait_blob');

  const response = await backendFetch(`/jobs?${search.toString()}`);
  if (!response.ok) {
    throw new Error(`/jobs GET failed: ${response.status}`);
  }
  const data = (await response.json()) as AsyncJobListResponse;
  return {
    total: data.total,
    items: data.items.map(toSampleWaitBlobJob),
  };
};

export const downloadSampleWaitBlobJob = async (jobId: string): Promise<Blob> => {
  const response = await backendFetch(`/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(`/jobs/${jobId} GET failed: ${response.status}`);
  }
  const detail = (await response.json()) as AsyncJobResponse;
  const artifact = detail.artifacts[0];
  if (!artifact) {
    throw new Error(`No artifact found for job ${jobId}`);
  }

  const downloadResponse = await backendFetch(`/jobs/${jobId}/artifacts/${artifact.id}/download`);
  if (!downloadResponse.ok) {
    throw new Error(
      `/jobs/${jobId}/artifacts/${artifact.id}/download failed: ${downloadResponse.status}`,
    );
  }
  return await downloadResponse.blob();
};

export const cancelSampleWaitBlobJob = async (jobId: string): Promise<SampleWaitBlobJob> => {
  const response = await backendFetch(`/jobs/${jobId}/cancel`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`/jobs/${jobId}/cancel POST failed: ${response.status}`);
  }
  const job = (await response.json()) as AsyncJobResponse;
  return toSampleWaitBlobJob(job);
};

export const downloadAuditLogExport = async (jobId: string): Promise<Blob> => {
  const response = await backendFetch(`/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(`/jobs/${jobId} GET failed: ${response.status}`);
  }
  const detail = (await response.json()) as AsyncJobResponse;
  const artifact = detail.artifacts[0];
  if (!artifact) {
    throw new Error(`No artifact found for job ${jobId}`);
  }

  const downloadResponse = await backendFetch(`/jobs/${jobId}/artifacts/${artifact.id}/download`);
  if (!downloadResponse.ok) {
    throw new Error(
      `/jobs/${jobId}/artifacts/${artifact.id}/download failed: ${downloadResponse.status}`,
    );
  }
  return await downloadResponse.blob();
};

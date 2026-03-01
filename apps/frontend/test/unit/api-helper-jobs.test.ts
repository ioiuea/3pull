import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  createAuditLogExport,
  createSampleWaitBlobJob,
  downloadAuditLogExport,
  getAuditLogExports,
  type AuditLogExportCreateRequest,
} from '~/lib/api-helper';

const originalFetch = global.fetch;

const jsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

afterEach(() => {
  global.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe('api-helper jobs', () => {
  it('maps /jobs list response into audit export list', async () => {
    // 目的: /jobs API のレスポンスが画面利用用の AuditLogExportJob 形式へ正規化されることを保証する。
    // 条件: artifacts/result_payload を含む 1 件レスポンスをモックする。
    // 期待値: file_path/file_size_bytes/row_count/timezone が正しくマッピングされる。
    global.fetch = vi.fn().mockResolvedValueOnce(
      jsonResponse({
        total: 1,
        items: [
          {
            id: 'job-1',
            job_type: 'auth_audit_export',
            requested_by_user_id: 'user-1',
            status: 'succeeded',
            requested_payload: {
              requested_filters: { provider: 'email' },
              timezone: 'UTC',
            },
            result_payload: { row_count: 12 },
            error_message: null,
            retry_count: 0,
            started_at: null,
            finished_at: null,
            expires_at: '2026-03-01T00:00:00+00:00',
            created_at: '2026-02-27T00:00:00+00:00',
            updated_at: '2026-02-27T00:00:00+00:00',
            artifacts: [
              {
                id: 'artifact-1',
                artifact_type: 'auth_audit_export_file',
                storage_provider: 'azure_blob',
                container_name: 'async-jobs',
                blob_path: 'audit-exports/2026/02/job-1.csv',
                content_type: 'text/csv; charset=utf-8',
                file_size_bytes: 123,
                checksum: null,
                expires_at: null,
                created_at: '2026-02-27T00:00:00+00:00',
              },
            ],
          },
        ],
      }),
    ) as typeof fetch;

    const result = await getAuditLogExports({ page: 1, pageSize: 20 });

    expect(result.total).toBe(1);
    expect(result.items[0]).toMatchObject({
      id: 'job-1',
      status: 'succeeded',
      file_format: 'csv',
      file_path: 'audit-exports/2026/02/job-1.csv',
      file_size_bytes: 123,
      row_count: 12,
      timezone: 'UTC',
    });
  });

  it('posts /jobs with auth_audit_export payload', async () => {
    // 目的: 監査ログエクスポート作成時のリクエスト契約を固定する。
    // 条件: createAuditLogExport を実行し fetch 呼び出しを検査する。
    // 期待値: POST /jobs/auth-audit-export が呼ばれ、要求フィールドが送信される。
    const payload: AuditLogExportCreateRequest = {
      provider: 'email',
      keyword: 'alice',
      timezone: 'UTC',
    };
    global.fetch = vi.fn().mockResolvedValueOnce(
      jsonResponse({
        id: 'job-2',
        job_type: 'auth_audit_export',
        requested_by_user_id: 'user-1',
        status: 'queued',
        requested_payload: { requested_filters: payload, timezone: 'UTC' },
        result_payload: null,
        error_message: null,
        retry_count: 0,
        started_at: null,
        finished_at: null,
        expires_at: '2026-03-01T00:00:00+00:00',
        created_at: '2026-02-27T00:00:00+00:00',
        updated_at: '2026-02-27T00:00:00+00:00',
        artifacts: [],
      }),
    ) as typeof fetch;

    await createAuditLogExport(payload);

    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/jobs/auth-audit-export');
    expect(init.method).toBe('POST');
    expect(String(init.body)).toContain('"provider":"email"');
  });

  it('downloads first artifact via /jobs/{id}/artifacts/{artifact_id}/download', async () => {
    // 目的: ダウンロード導線が job 詳細 -> 先頭 artifact の download API を辿ることを保証する。
    // 条件: 1回目 fetch で job 詳細、2回目 fetch でファイルレスポンスを返す。
    // 期待値: 2回目の URL が /jobs/{job_id}/artifacts/{artifact_id}/download になり、Blob を返す。
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          id: 'job-3',
          job_type: 'auth_audit_export',
          requested_by_user_id: 'user-1',
          status: 'succeeded',
          requested_payload: { requested_filters: {}, timezone: 'UTC' },
          result_payload: null,
          error_message: null,
          retry_count: 0,
          started_at: null,
          finished_at: null,
          expires_at: '2026-03-01T00:00:00+00:00',
          created_at: '2026-02-27T00:00:00+00:00',
          updated_at: '2026-02-27T00:00:00+00:00',
          artifacts: [
            {
              id: 'artifact-3',
              artifact_type: 'auth_audit_export_file',
              storage_provider: 'azure_blob',
              container_name: 'async-jobs',
              blob_path: 'audit-exports/2026/02/job-3.csv',
              content_type: 'text/csv; charset=utf-8',
              file_size_bytes: 123,
              checksum: null,
              expires_at: null,
              created_at: '2026-02-27T00:00:00+00:00',
            },
          ],
        }),
      )
      .mockResolvedValueOnce(new Response('id,name\n1,alice\n', { status: 200 })) as typeof fetch;

    const blob = await downloadAuditLogExport('job-3');

    expect(blob.size).toBeGreaterThan(0);
    expect(blob.type).toContain('text/plain');
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    expect(fetchMock.mock.calls[1][0]).toContain('/jobs/job-3/artifacts/artifact-3/download');
  });

  it('posts /jobs/sample-wait-blob and maps queued job response', async () => {
    // 目的: sample wait blob 作成のリクエスト契約と応答マッピングが維持されることを保証する。
    // 条件: createSampleWaitBlobJob を実行し fetch 呼び出しと戻り値を検査する。
    // 期待値: POST /jobs/sample-wait-blob が呼ばれ、wait_seconds と content が反映される。
    global.fetch = vi.fn().mockResolvedValueOnce(
      jsonResponse({
        id: 'job-4',
        job_type: 'sample_wait_blob',
        requested_by_user_id: 'user-1',
        status: 'queued',
        requested_payload: { wait_seconds: 45, content: 'hello' },
        result_payload: null,
        error_message: null,
        retry_count: 0,
        started_at: null,
        finished_at: null,
        expires_at: '2026-03-01T00:00:00+00:00',
        created_at: '2026-02-27T00:00:00+00:00',
        updated_at: '2026-02-27T00:00:00+00:00',
        artifacts: [],
      }),
    ) as typeof fetch;

    const result = await createSampleWaitBlobJob({
      wait_seconds: 45,
      content: 'hello',
    });

    expect(result).toMatchObject({
      id: 'job-4',
      status: 'queued',
      wait_seconds: 45,
      content: 'hello',
      file_path: null,
      file_size_bytes: null,
    });

    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/jobs/sample-wait-blob');
    expect(init.method).toBe('POST');
    expect(String(init.body)).toContain('"wait_seconds":45');
    expect(String(init.body)).toContain('"content":"hello"');
  });
});

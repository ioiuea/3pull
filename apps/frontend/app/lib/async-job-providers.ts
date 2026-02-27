import { getAuditLogExports, getSampleWaitBlobJobs } from '~/lib/api-helper';
import type { GlobalAsyncJobItem, GlobalAsyncJobProvider } from '~/lib/async-jobs';

const fetchAuditExportJobs = async (): Promise<GlobalAsyncJobItem[]> => {
  const response = await getAuditLogExports({ page: 1, pageSize: 20 });
  return response.items.map((job) => ({
    id: job.id,
    source: 'auditExport',
    status: job.status,
    createdAt: job.created_at,
    finishedAt: job.finished_at,
  }));
};

const fetchSampleWaitBlobJobs = async (): Promise<GlobalAsyncJobItem[]> => {
  const response = await getSampleWaitBlobJobs({ page: 1, pageSize: 20 });
  return response.items.map((job) => ({
    id: job.id,
    source: 'sampleWaitBlob',
    status: job.status,
    createdAt: job.created_at,
    finishedAt: job.finished_at,
  }));
};

export const GLOBAL_ASYNC_JOB_PROVIDERS: GlobalAsyncJobProvider[] = [
  {
    source: 'auditExport',
    fetchJobs: fetchAuditExportJobs,
  },
  {
    source: 'sampleWaitBlob',
    fetchJobs: fetchSampleWaitBlobJobs,
  },
];

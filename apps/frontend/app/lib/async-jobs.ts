export type GlobalAsyncJobStatus =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'canceled'
  | 'expired'
  | 'unknown';

export type GlobalAsyncJobItem = {
  id: string;
  source: string;
  status: GlobalAsyncJobStatus;
  createdAt: string;
  finishedAt: string | null;
};

export type GlobalAsyncJobProvider = {
  source: string;
  fetchJobs: () => Promise<GlobalAsyncJobItem[]>;
};

export const isRunningAsyncJobStatus = (status: GlobalAsyncJobStatus) =>
  status === 'queued' || status === 'running';

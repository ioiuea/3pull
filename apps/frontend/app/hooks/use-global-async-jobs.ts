import useSWR from 'swr';
import { GLOBAL_ASYNC_JOB_PROVIDERS } from '~/lib/async-job-providers';
import type { GlobalAsyncJobItem } from '~/lib/async-jobs';
import { isRunningAsyncJobStatus } from '~/lib/async-jobs';

type UseGlobalAsyncJobsParams = {
  enabled?: boolean;
};

const fetchGlobalAsyncJobs = async (): Promise<GlobalAsyncJobItem[]> => {
  const results = await Promise.allSettled(
    GLOBAL_ASYNC_JOB_PROVIDERS.map(async (provider) => provider.fetchJobs()),
  );

  const jobs: GlobalAsyncJobItem[] = [];
  for (const result of results) {
    if (result.status === 'fulfilled') {
      jobs.push(...result.value);
    }
  }

  jobs.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  return jobs;
};

export const useGlobalAsyncJobs = ({ enabled = true }: UseGlobalAsyncJobsParams = {}) => {
  const swr = useSWR(enabled ? 'global-async-jobs' : null, fetchGlobalAsyncJobs, {
    revalidateOnFocus: false,
    refreshInterval: 5000,
    keepPreviousData: true,
  });

  const jobs = swr.data ?? [];
  const runningCount = jobs.filter((job) => isRunningAsyncJobStatus(job.status)).length;
  const latestCompletedJob = jobs.find((job) => job.status === 'succeeded') ?? null;

  return {
    ...swr,
    jobs,
    runningCount,
    latestCompletedJob,
  };
};

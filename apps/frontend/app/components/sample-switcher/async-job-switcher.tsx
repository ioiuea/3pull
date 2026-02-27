'use client';

import { useEffect, useRef } from 'react';
import { CircleCheckBig, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { Button } from '~/components/ui/button';
import { Badge } from '~/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '~/components/ui/popover';
import { ScrollArea } from '~/components/ui/scroll-area';
import { useGlobalAsyncJobs } from '~/hooks/use-global-async-jobs';
import { useMe } from '~/hooks/use-me';
import type { GlobalAsyncJobStatus } from '~/lib/async-jobs';

const statusBadgeVariant: Record<
  GlobalAsyncJobStatus,
  'secondary' | 'default' | 'destructive' | 'outline'
> = {
  queued: 'secondary',
  running: 'default',
  succeeded: 'outline',
  failed: 'destructive',
  canceled: 'secondary',
  expired: 'secondary',
  unknown: 'secondary',
};

const AsyncJobSwitcher = () => {
  const { t } = useTranslation('common');
  const { data: me, error: meError } = useMe();
  const isAuthenticated = Boolean(me) && !meError;
  const { jobs, runningCount, latestCompletedJob } = useGlobalAsyncJobs({
    enabled: isAuthenticated,
  });
  const initializedRef = useRef(false);
  const completedJobIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!isAuthenticated || jobs.length === 0) {
      return;
    }

    if (!initializedRef.current) {
      for (const job of jobs) {
        if (job.status === 'succeeded') {
          completedJobIdsRef.current.add(job.id);
        }
      }
      initializedRef.current = true;
      return;
    }

    for (const job of jobs) {
      if (job.status !== 'succeeded') {
        continue;
      }
      if (completedJobIdsRef.current.has(job.id)) {
        continue;
      }
      completedJobIdsRef.current.add(job.id);
      toast.success(
        t('switcher.jobs.toastCompleted', {
          source: t(`switcher.jobs.sources.${job.source}`),
          jobId: job.id.slice(0, 8),
        }),
      );
    }
  }, [isAuthenticated, jobs, t]);

  if (!isAuthenticated) {
    return null;
  }

  const summaryDescription =
    runningCount > 0
      ? t('switcher.jobs.running', { count: runningCount })
      : latestCompletedJob
        ? t('switcher.jobs.lastCompletedAt', {
            source: t(`switcher.jobs.sources.${latestCompletedJob.source}`),
            time: new Date(
              latestCompletedJob.finishedAt ?? latestCompletedJob.createdAt,
            ).toLocaleString(),
          })
        : t('switcher.jobs.idle');

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="gap-1.5"
          aria-label={t('switcher.jobs.ariaLabel')}
          title={t('switcher.jobs.ariaLabel')}
        >
          {runningCount > 0 ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <CircleCheckBig className="size-4" />
          )}
          <span className="hidden sm:inline">{t('switcher.jobs.label')}</span>
          <span className="rounded-sm bg-muted px-1.5 py-0.5 text-[10px]">{runningCount}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent side="bottom" align="end" className="w-[360px] p-0">
        <div className="border-b px-3 py-2">
          <p className="text-sm font-medium">{t('switcher.jobs.title')}</p>
          <p className="text-xs text-muted-foreground">{summaryDescription}</p>
        </div>
        {jobs.length === 0 ? (
          <div className="px-3 py-4 text-xs text-muted-foreground">
            {t('switcher.jobs.noHistory')}
          </div>
        ) : (
          <ScrollArea className="max-h-80">
            <ul className="divide-y">
              {jobs.map((job) => (
                <li key={job.id} className="space-y-1 px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-xs font-medium">{job.id}</p>
                    <Badge variant={statusBadgeVariant[job.status]}>
                      {t(`switcher.jobs.status.${job.status}`, { defaultValue: job.status })}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    {t('switcher.jobs.source')}:{' '}
                    {t(`switcher.jobs.sources.${job.source}`, { defaultValue: job.source })}
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    {t('switcher.jobs.startedAt')}: {new Date(job.createdAt).toLocaleString()}
                  </p>
                  {job.finishedAt ? (
                    <p className="text-[11px] text-muted-foreground">
                      {t('switcher.jobs.finishedAt')}: {new Date(job.finishedAt).toLocaleString()}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          </ScrollArea>
        )}
      </PopoverContent>
    </Popover>
  );
};

export default AsyncJobSwitcher;

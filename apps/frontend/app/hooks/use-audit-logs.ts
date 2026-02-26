import useSWR from 'swr';
import { getAuditLogs } from '~/lib/api-helper';

type UseAuditLogsParams = {
  page: number;
  pageSize: number;
  eventType?: string;
  userId?: string;
};

/**
 * 監査ログ一覧を取得する SWR フック.
 *
 * key にページング・検索条件を含め、条件単位でキャッシュを分離する。
 */
export const useAuditLogs = (params: UseAuditLogsParams) => {
  const eventType = params.eventType?.trim() ?? '';
  const userId = params.userId?.trim() ?? '';

  return useSWR(
    ['audit-logs', params.page, params.pageSize, eventType, userId] as const,
    ([, page, pageSize, keyEventType, keyUserId]) =>
      getAuditLogs({
        page,
        pageSize,
        eventType: keyEventType || undefined,
        userId: keyUserId || undefined,
      }),
    {
      revalidateOnFocus: false,
      keepPreviousData: true,
    },
  );
};

import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';
import { ArrowLeft, Loader2, RefreshCw } from 'lucide-react';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card';
import { Input } from '~/components/ui/input';
import { getAuditLogs, type AuditLogItem } from '~/lib/api-helper';
import { isSupportedLanguage } from '~/lib/i18n';

const PAGE_SIZE = 20;

const AuditLogSamplePage = () => {
  const { t } = useTranslation('auditLogSample');
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';

  const [items, setItems] = useState<AuditLogItem[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [eventType, setEventType] = useState('');
  const [userId, setUserId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);

  const loadLogs = async (nextPage: number) => {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      const response = await getAuditLogs({
        page: nextPage,
        pageSize: PAGE_SIZE,
        eventType: eventType.trim() || undefined,
        userId: userId.trim() || undefined,
      });
      setItems(response.items);
      setPage(response.page);
      setTotal(response.total);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t('states.error'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadLogs(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSearch = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await loadLogs(1);
  };

  return (
    <main className="container mx-auto min-h-screen max-w-6xl px-4 py-14">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="mt-2 text-muted-foreground">{t('description')}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => void loadLogs(page)} disabled={isLoading}>
            {isLoading ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <RefreshCw className="size-4" />
            )}
            {t('actions.reload')}
          </Button>
          <Button asChild variant="outline">
            <Link to={`/${currentLanguage}`}>
              <ArrowLeft className="size-4" />
              {t('actions.backToLp')}
            </Link>
          </Button>
        </div>
      </div>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>{t('filters.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 sm:grid-cols-3" onSubmit={onSearch}>
            <Input
              placeholder={t('filters.eventType')}
              value={eventType}
              onChange={(event) => setEventType(event.target.value)}
            />
            <Input
              placeholder={t('filters.userId')}
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
            />
            <Button type="submit" disabled={isLoading}>
              {t('actions.search')}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('table.title', { total })}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              {t('states.loading')}
            </div>
          )}

          {!isLoading && items.length === 0 && (
            <p className="text-sm text-muted-foreground">{t('states.empty')}</p>
          )}

          {items.length > 0 && (
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-sm">
                <thead className="bg-muted/40">
                  <tr>
                    <th className="p-2 text-left">id</th>
                    <th className="p-2 text-left">{t('table.occurredAt')}</th>
                    <th className="p-2 text-left">{t('table.eventType')}</th>
                    <th className="p-2 text-left">{t('table.userId')}</th>
                    <th className="p-2 text-left">{t('table.userName')}</th>
                    <th className="p-2 text-left">{t('table.userEmail')}</th>
                    <th className="p-2 text-left">{t('table.sessionId')}</th>
                    <th className="p-2 text-left">{t('table.provider')}</th>
                    <th className="p-2 text-left">{t('table.clientIp')}</th>
                    <th className="p-2 text-left">{t('table.reasonCode')}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={`${item.id}-${item.occurred_at}`} className="border-t">
                      <td className="p-2 align-top">{item.id}</td>
                      <td className="p-2 align-top">
                        {new Date(item.occurred_at).toLocaleString()}
                      </td>
                      <td className="p-2 align-top">{item.event_type}</td>
                      <td className="p-2 align-top">{item.user_id ?? '-'}</td>
                      <td className="p-2 align-top">{item.user_display_name ?? '-'}</td>
                      <td className="p-2 align-top">{item.user_email ?? '-'}</td>
                      <td className="p-2 align-top">{item.session_id ?? '-'}</td>
                      <td className="p-2 align-top">{item.provider ?? '-'}</td>
                      <td className="p-2 align-top">{item.client_ip ?? '-'}</td>
                      <td className="p-2 align-top">{item.reason_code ?? '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              {t('table.pagination', { page, totalPages })}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => void loadLogs(page - 1)}
                disabled={isLoading || page <= 1}
              >
                {t('actions.prev')}
              </Button>
              <Button
                variant="outline"
                onClick={() => void loadLogs(page + 1)}
                disabled={isLoading || page >= totalPages}
              >
                {t('actions.next')}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </main>
  );
};

export default AuditLogSamplePage;

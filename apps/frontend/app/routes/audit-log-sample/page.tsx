import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';
import { ArrowLeft, ChevronDown, ChevronUp, Filter, Loader2 } from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import { Input } from '~/components/ui/input';
import { ToggleGroup, ToggleGroupItem } from '~/components/ui/toggle-group';
import { useAuditLogs } from '~/hooks/use-audit-logs';
import { isSupportedLanguage } from '~/lib/i18n';

const PAGE_SIZE = 20;

type SortKey = 'occurred_at' | 'event_type' | 'provider' | 'user_display_name';
type SortDirection = 'asc' | 'desc';

type TimeRange = '90d' | '30d' | '7d';

const chartTooltipStyle = {
  backgroundColor: '#111827',
  border: '1px solid #374151',
  borderRadius: 10,
  color: '#f9fafb',
};

const parseDateKey = (dateKey: string) => new Date(`${dateKey}T00:00:00.000Z`);
const toDateKey = (date: Date) => date.toISOString().slice(0, 10);

const AuditLogSamplePage = () => {
  const { t } = useTranslation('auditLogSample');
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';

  const toDateLabel = (value: string) =>
    new Date(value).toLocaleString(currentLanguage, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });

  const [page, setPage] = useState(1);
  const [selectedDate, setSelectedDate] = useState('all');
  const [selectedEventType, setSelectedEventType] = useState('all');
  const [provider, setProvider] = useState('all');
  const [keyword, setKeyword] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('occurred_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [timeRange, setTimeRange] = useState<TimeRange>('90d');

  const { data, error, isLoading } = useAuditLogs({
    page,
    pageSize: PAGE_SIZE,
  });

  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const total = data?.total ?? 0;
  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);

  const filterOptions = useMemo(() => {
    const dates = Array.from(new Set(items.map((item) => item.occurred_at.slice(0, 10)))).sort(
      (a, b) => b.localeCompare(a),
    );
    const eventTypes = Array.from(new Set(items.map((item) => item.event_type))).sort((a, b) =>
      a.localeCompare(b),
    );
    const providers = Array.from(new Set(items.map((item) => item.provider ?? 'unknown'))).sort(
      (a, b) => a.localeCompare(b),
    );
    return { dates, eventTypes, providers };
  }, [items]);

  const tableItems = useMemo(() => {
    const query = keyword.trim().toLowerCase();

    const filtered = items.filter((item) => {
      if (selectedDate !== 'all' && item.occurred_at.slice(0, 10) !== selectedDate) {
        return false;
      }
      if (selectedEventType !== 'all' && item.event_type !== selectedEventType) {
        return false;
      }
      if (provider !== 'all' && (item.provider ?? 'unknown') !== provider) {
        return false;
      }
      if (!query) {
        return true;
      }
      const searchable = [
        item.event_type,
        item.user_id,
        item.user_display_name,
        item.user_email,
        item.session_id,
        item.client_ip,
        item.reason_code,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return searchable.includes(query);
    });

    const sorted = [...filtered].sort((a, b) => {
      const left = a[sortKey] ?? '';
      const right = b[sortKey] ?? '';
      const factor = sortDirection === 'asc' ? 1 : -1;

      if (sortKey === 'occurred_at') {
        return (new Date(String(left)).getTime() - new Date(String(right)).getTime()) * factor;
      }

      return String(left).localeCompare(String(right)) * factor;
    });

    return sorted;
  }, [items, keyword, provider, selectedDate, selectedEventType, sortKey, sortDirection]);

  const summary = useMemo(() => {
    const eventCounter = new Map<string, number>();
    let successCount = 0;
    let failCount = 0;

    const now = new Date();
    const latestDate = tableItems.reduce<Date>((max, item) => {
      const current = new Date(item.occurred_at);
      return current > max ? current : max;
    }, now);
    const rangeDays = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
    const rangeStart = new Date(latestDate);
    rangeStart.setUTCDate(rangeStart.getUTCDate() - (rangeDays - 1));
    rangeStart.setUTCHours(0, 0, 0, 0);

    const timelineItems = tableItems.filter((item) => new Date(item.occurred_at) >= rangeStart);

    for (const item of timelineItems) {
      eventCounter.set(item.event_type, (eventCounter.get(item.event_type) ?? 0) + 1);
    }

    for (const item of tableItems) {
      if (item.event_type.endsWith('.success')) {
        successCount += 1;
      }
      if (item.event_type.endsWith('.fail')) {
        failCount += 1;
      }
    }

    const topSeries = [...eventCounter.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([name], index) => ({
        id: `series_${index}`,
        name,
      }));

    const byDayMap = new Map<string, number>();
    for (const item of timelineItems) {
      const key = item.occurred_at.slice(0, 10);
      if (!byDayMap.has(key)) {
        byDayMap.set(key, 0);
      }
    }

    const cursor = new Date(rangeStart);
    const endDateKey = toDateKey(latestDate);
    while (toDateKey(cursor) <= endDateKey) {
      const key = toDateKey(cursor);
      if (!byDayMap.has(key)) {
        byDayMap.set(key, 0);
      }
      cursor.setUTCDate(cursor.getUTCDate() + 1);
    }

    const eventTimelineMap = new Map<string, Record<string, number | string>>();
    for (const date of byDayMap.keys()) {
      const row: Record<string, number | string> = { date };
      for (const series of topSeries) {
        row[series.id] = 0;
      }
      eventTimelineMap.set(date, row);
    }
    for (const item of timelineItems) {
      const date = item.occurred_at.slice(0, 10);
      const series = topSeries.find((entry) => entry.name === item.event_type);
      if (!series) {
        continue;
      }
      const row = eventTimelineMap.get(date);
      if (!row) {
        continue;
      }
      row[series.id] = Number(row[series.id] ?? 0) + 1;
    }
    const eventTimeline = [...eventTimelineMap.values()].sort(
      (a, b) => parseDateKey(String(a.date)).getTime() - parseDateKey(String(b.date)).getTime(),
    );

    const uniqueUsers = new Set(tableItems.map((item) => item.user_id).filter(Boolean)).size;
    const uniqueIps = new Set(tableItems.map((item) => item.client_ip).filter(Boolean)).size;

    return {
      successCount,
      failCount,
      uniqueUsers,
      uniqueIps,
      topSeries,
      eventTimeline,
    };
  }, [tableItems, timeRange]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDirection('asc');
  };

  const renderSortButton = (label: string, field: SortKey) => (
    <button
      type="button"
      className="inline-flex items-center gap-1 font-medium hover:text-foreground"
      onClick={() => toggleSort(field)}
    >
      <span>{label}</span>
      {sortKey === field ? (
        sortDirection === 'asc' ? (
          <ChevronUp className="size-3" />
        ) : (
          <ChevronDown className="size-3" />
        )
      ) : null}
    </button>
  );

  const errorMessage = error instanceof Error ? error.message : null;

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 flex items-center gap-2 border-b bg-background/95 px-4 py-3 backdrop-blur lg:px-6">
        <div className="flex items-center gap-2">
          <h1 className="text-base font-semibold">{t('title')}</h1>
          <Button variant="outline" asChild>
            <Link to={`/${currentLanguage}`}>
              <ArrowLeft className="size-4" />
              {t('actions.backToLp')}
            </Link>
          </Button>
        </div>
      </header>

      <main className="flex flex-1 flex-col gap-4 p-4 md:p-6">
        <section id="overview" className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>{t('overview.totalRows')}</CardDescription>
              <CardTitle className="text-2xl">{tableItems.length}</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              {t('overview.serverTotal', { total })}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>{t('overview.resultRatio')}</CardDescription>
              <CardTitle className="text-2xl">
                {summary.successCount} / {summary.failCount}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              {t('overview.successFail')}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>{t('overview.uniqueUsers')}</CardDescription>
              <CardTitle className="text-2xl">{summary.uniqueUsers}</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              {t('overview.withinFilter')}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>{t('overview.uniqueClientIps')}</CardDescription>
              <CardTitle className="text-2xl">{summary.uniqueIps}</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              {t('overview.withinFilter')}
            </CardContent>
          </Card>
        </section>

        <section className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Filter className="size-4" />
                {t('filters.title')}
              </CardTitle>
              <CardDescription>{t('filters.description')}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <Input
                  placeholder={t('filters.keywordPlaceholder')}
                  value={keyword}
                  onChange={(event) => setKeyword(event.target.value)}
                />
                <select
                  className="h-10 rounded-md border bg-background px-3 text-sm"
                  value={selectedDate}
                  onChange={(event) => setSelectedDate(event.target.value)}
                >
                  <option value="all">{t('filters.dateAll')}</option>
                  {filterOptions.dates.map((date) => (
                    <option key={date} value={date}>
                      {date}
                    </option>
                  ))}
                </select>
                <select
                  className="h-10 rounded-md border bg-background px-3 text-sm"
                  value={selectedEventType}
                  onChange={(event) => setSelectedEventType(event.target.value)}
                >
                  <option value="all">{t('filters.eventTypeAll')}</option>
                  {filterOptions.eventTypes.map((eventType) => (
                    <option key={eventType} value={eventType}>
                      {eventType}
                    </option>
                  ))}
                </select>
                <select
                  className="h-10 rounded-md border bg-background px-3 text-sm"
                  value={provider}
                  onChange={(event) => setProvider(event.target.value)}
                >
                  <option value="all">{t('filters.providerAll')}</option>
                  {filterOptions.providers.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>
        </section>

        <section id="charts" className="grid gap-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('chart.title')}</CardTitle>
              <CardDescription>{t('chart.description')}</CardDescription>
              <div className="pt-2">
                <ToggleGroup
                  type="single"
                  value={timeRange}
                  onValueChange={(value) => {
                    if (value === '7d' || value === '30d' || value === '90d') {
                      setTimeRange(value);
                    }
                  }}
                  variant="outline"
                >
                  <ToggleGroupItem value="90d">{t('ranges.last3Months')}</ToggleGroupItem>
                  <ToggleGroupItem value="30d">{t('ranges.last30Days')}</ToggleGroupItem>
                  <ToggleGroupItem value="7d">{t('ranges.last7Days')}</ToggleGroupItem>
                </ToggleGroup>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={summary.eventTimeline} margin={{ left: 8, right: 8 }}>
                    <defs>
                      <linearGradient id="fillSeries0" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.45} />
                        <stop offset="95%" stopColor="#60a5fa" stopOpacity={0.05} />
                      </linearGradient>
                      <linearGradient id="fillSeries1" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.03} />
                      </linearGradient>
                      <linearGradient id="fillSeries2" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#34d399" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#34d399" stopOpacity={0.03} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11 }}
                      tickFormatter={(value) =>
                        new Date(String(value)).toLocaleDateString(currentLanguage, {
                          month: '2-digit',
                          day: '2-digit',
                        })
                      }
                    />
                    <YAxis allowDecimals={false} />
                    <Legend />
                    <Tooltip
                      cursor={{ stroke: 'rgba(148, 163, 184, 0.4)', strokeWidth: 1 }}
                      contentStyle={chartTooltipStyle}
                      labelStyle={{ color: '#e5e7eb' }}
                      itemStyle={{ color: '#f9fafb' }}
                      labelFormatter={(value) => toDateLabel(String(value))}
                    />
                    {summary.topSeries.map((series, index) => (
                      <Area
                        key={series.id}
                        type="monotone"
                        dataKey={series.id}
                        name={series.name}
                        stroke={['#60a5fa', '#f59e0b', '#34d399'][index % 3]}
                        strokeWidth={2}
                        fill={`url(#fillSeries${index % 3})`}
                        fillOpacity={1}
                      />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </section>

        <section id="table" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('table.title')}</CardTitle>
              <CardDescription>
                {t('table.description', { page, totalPages, total })}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {errorMessage ? (
                <p className="text-sm text-destructive">{errorMessage || t('states.error')}</p>
              ) : null}
              {isLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" />
                  {t('states.loading')}
                </div>
              ) : null}

              {!isLoading && tableItems.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t('states.empty')}</p>
              ) : null}

              {tableItems.length > 0 ? (
                <div className="overflow-x-auto rounded-md border">
                  <table className="min-w-312.5 text-sm">
                    <thead className="bg-muted/40 text-muted-foreground">
                      <tr>
                        <th className="p-2 text-left">id</th>
                        <th className="p-2 text-left">
                          {renderSortButton(t('table.columns.occurredAt'), 'occurred_at')}
                        </th>
                        <th className="p-2 text-left">
                          {renderSortButton(t('table.columns.eventType'), 'event_type')}
                        </th>
                        <th className="p-2 text-left">{t('table.columns.userId')}</th>
                        <th className="p-2 text-left">
                          {renderSortButton(t('table.columns.userName'), 'user_display_name')}
                        </th>
                        <th className="p-2 text-left">{t('table.columns.userEmail')}</th>
                        <th className="p-2 text-left">{t('table.columns.sessionId')}</th>
                        <th className="p-2 text-left">
                          {renderSortButton(t('table.columns.provider'), 'provider')}
                        </th>
                        <th className="p-2 text-left">{t('table.columns.clientIp')}</th>
                        <th className="p-2 text-left">{t('table.columns.reasonCode')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tableItems.map((item) => (
                        <tr key={`${item.id}-${item.occurred_at}`} className="border-t align-top">
                          <td className="p-2">{item.id}</td>
                          <td className="p-2 whitespace-nowrap">{toDateLabel(item.occurred_at)}</td>
                          <td className="p-2">{item.event_type}</td>
                          <td className="p-2">{item.user_id ?? '-'}</td>
                          <td className="p-2">{item.user_display_name ?? '-'}</td>
                          <td className="p-2">{item.user_email ?? '-'}</td>
                          <td className="p-2">{item.session_id ?? '-'}</td>
                          <td className="p-2">{item.provider ?? '-'}</td>
                          <td className="p-2">{item.client_ip ?? '-'}</td>
                          <td className="p-2">{item.reason_code ?? '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}

              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  {t('table.queryPageSize', { pageSize: PAGE_SIZE })}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    disabled={isLoading || page <= 1}
                    onClick={() => setPage((prev) => prev - 1)}
                  >
                    {t('actions.prev')}
                  </Button>
                  <Button
                    variant="outline"
                    disabled={isLoading || page >= totalPages}
                    onClick={() => setPage((prev) => prev + 1)}
                  >
                    {t('actions.next')}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
};

export default AuditLogSamplePage;

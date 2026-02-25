import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';
import { ArrowLeft, ShieldCheck, ShieldX } from 'lucide-react';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card';
import { isSupportedLanguage } from '~/lib/i18n';

type CheckResult = {
  ok: boolean;
  status: number;
  body: string;
};

type HealthPayload = {
  status?: 'ok' | 'degraded';
  dependencies?: {
    postgres?: {
      ok?: boolean;
    };
  };
};

const BACKEND_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:8000';

const ApiProtectionSamplePage = () => {
  const { t } = useTranslation('apiProtectionSample');
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const [protectedResult, setProtectedResult] = useState<CheckResult | null>(null);
  const [unprotectedResult, setUnprotectedResult] = useState<CheckResult | null>(null);
  const [isLoadingProtected, setIsLoadingProtected] = useState(false);
  const [isLoadingUnprotected, setIsLoadingUnprotected] = useState(false);

  const parseResponse = async (response: Response): Promise<CheckResult> => {
    const body = await response.text();
    return { ok: response.ok, status: response.status, body };
  };

  const parseHealthPayload = (result: CheckResult | null): HealthPayload | null => {
    if (!result) {
      return null;
    }
    try {
      return JSON.parse(result.body) as HealthPayload;
    } catch {
      return null;
    }
  };

  const toApiStatusLabel = (result: CheckResult | null): string => {
    if (!result) {
      return t('panels.notChecked');
    }
    if (result.status === 401) {
      return t('panels.blocked');
    }
    if (result.ok) {
      return t('panels.up');
    }
    return t('panels.down');
  };

  const toPostgresStatusLabel = (result: CheckResult | null): string => {
    if (!result) {
      return t('panels.notChecked');
    }
    if (result.status === 401) {
      return t('panels.unauthorized');
    }
    const payload = parseHealthPayload(result);
    const postgresOk = payload?.dependencies?.postgres?.ok;
    if (postgresOk === true) {
      return t('panels.up');
    }
    if (postgresOk === false) {
      return t('panels.down');
    }
    return t('panels.unknown');
  };

  const toStatusTone = (label: string): string => {
    if (label === t('panels.up')) {
      return 'text-emerald-600';
    }
    if (label === t('panels.down') || label === t('panels.blocked')) {
      return 'text-rose-600';
    }
    return 'text-amber-600';
  };

  const requestWithSession = async () => {
    try {
      setIsLoadingProtected(true);
      const response = await fetch(`${BACKEND_BASE_URL}/backend/health`, {
        credentials: 'include',
      });
      setProtectedResult(await parseResponse(response));
    } finally {
      setIsLoadingProtected(false);
    }
  };

  const requestWithoutSession = async () => {
    try {
      setIsLoadingUnprotected(true);
      const response = await fetch(`${BACKEND_BASE_URL}/backend/health`, {
        credentials: 'omit',
      });
      setUnprotectedResult(await parseResponse(response));
    } finally {
      setIsLoadingUnprotected(false);
    }
  };

  return (
    <main className="container mx-auto h-screen max-w-6xl overflow-y-auto px-4 py-14">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="mt-2 text-muted-foreground">{t('description')}</p>
        </div>
        <Button asChild variant="outline">
          <Link to={`/${currentLanguage}`}>
            <ArrowLeft className="size-4" />
            {t('actions.backToLp')}
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-emerald-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-emerald-600">
              <ShieldCheck className="size-5" />
              {t('allowed.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">{t('allowed.description')}</p>
            <Button onClick={() => void requestWithSession()} disabled={isLoadingProtected}>
              {isLoadingProtected ? t('actions.checking') : t('allowed.cta')}
            </Button>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-md border bg-background/40 p-3">
                <p className="text-xs text-muted-foreground">{t('panels.api')}</p>
                <p
                  className={`text-sm font-semibold ${toStatusTone(toApiStatusLabel(protectedResult))}`}
                >
                  {toApiStatusLabel(protectedResult)}
                </p>
              </div>
              <div className="rounded-md border bg-background/40 p-3">
                <p className="text-xs text-muted-foreground">{t('panels.postgres')}</p>
                <p
                  className={`text-sm font-semibold ${toStatusTone(toPostgresStatusLabel(protectedResult))}`}
                >
                  {toPostgresStatusLabel(protectedResult)}
                </p>
              </div>
            </div>
            <pre className="min-h-28 overflow-x-auto rounded-md border bg-muted/30 p-3 text-xs leading-relaxed">
              <code>
                {protectedResult
                  ? JSON.stringify(protectedResult, null, 2)
                  : t('states.emptyAllowed')}
              </code>
            </pre>
          </CardContent>
        </Card>

        <Card className="border-rose-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-rose-600">
              <ShieldX className="size-5" />
              {t('blocked.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">{t('blocked.description')}</p>
            <Button
              variant="secondary"
              onClick={() => void requestWithoutSession()}
              disabled={isLoadingUnprotected}
            >
              {isLoadingUnprotected ? t('actions.checking') : t('blocked.cta')}
            </Button>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-md border bg-background/40 p-3">
                <p className="text-xs text-muted-foreground">{t('panels.api')}</p>
                <p
                  className={`text-sm font-semibold ${toStatusTone(toApiStatusLabel(unprotectedResult))}`}
                >
                  {toApiStatusLabel(unprotectedResult)}
                </p>
              </div>
              <div className="rounded-md border bg-background/40 p-3">
                <p className="text-xs text-muted-foreground">{t('panels.postgres')}</p>
                <p
                  className={`text-sm font-semibold ${toStatusTone(toPostgresStatusLabel(unprotectedResult))}`}
                >
                  {toPostgresStatusLabel(unprotectedResult)}
                </p>
              </div>
            </div>
            <pre className="min-h-28 overflow-x-auto rounded-md border bg-muted/30 p-3 text-xs leading-relaxed">
              <code>
                {unprotectedResult
                  ? JSON.stringify(unprotectedResult, null, 2)
                  : t('states.emptyBlocked')}
              </code>
            </pre>
          </CardContent>
        </Card>
      </div>
    </main>
  );
};

export default ApiProtectionSamplePage;

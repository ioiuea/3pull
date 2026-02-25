import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';
import { ClipboardCheck, FlaskConical, Globe, Lock, Server, ShieldCheck, Wrench } from 'lucide-react';
import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card';
import { isSupportedLanguage } from '~/lib/i18n';

const infraItemKeys = ['infra.bicep'] as const;

const frontendItemKeys = [
  'frontend.reactRouter',
  'frontend.i18n',
  'frontend.zustand',
  'frontend.zod',
  'frontend.shadcn',
] as const;

const backendItemKeys = [
  'backend.fastapi',
  'backend.structlog',
  'backend.sqlalchemy',
  'backend.pydantic',
  'backend.alembic',
  'backend.gunicorn',
] as const;

const LandingPage = () => {
  const { t } = useTranslation('landing');
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';

  return (
    <main className="relative overflow-hidden">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(1200px_420px_at_50%_-120px,rgba(14,165,233,.28),transparent),radial-gradient(900px_360px_at_90%_0,rgba(16,185,129,.22),transparent)]" />
      <section className="container mx-auto max-w-6xl px-4 py-16 sm:py-24">
        <div className="grid gap-10 lg:grid-cols-[1.1fr_.9fr] lg:items-center">
          <div className="space-y-6">
            <Badge variant="secondary" className="rounded-full px-4 py-1 text-xs">
              {t('badge')}
            </Badge>
            <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
              {t('hero.titleTop')}
              <span className="block text-primary">{t('hero.titleBottom')}</span>
            </h1>
            <p className="max-w-xl text-muted-foreground">{t('hero.description')}</p>
            <div className="flex flex-wrap gap-3">
              <Button asChild variant="outline" size="lg">
                <Link to={`/${currentLanguage}#starter-stack`}>{t('hero.aboutCta')}</Link>
              </Button>
            </div>
          </div>
          <div className="rounded-2xl border bg-card/70 p-6 backdrop-blur">
            <img
              src="/images/3pull-app.png"
              alt={t('hero.logoAlt')}
              className="mx-auto h-auto w-full max-w-sm"
            />
          </div>
        </div>
      </section>

      <section
        id="starter-stack"
        className="container mx-auto grid max-w-6xl gap-4 px-4 pb-16 sm:grid-cols-2 lg:grid-cols-3"
      >
        <Card className="border-border/70">
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <Wrench className="size-5 text-primary" />
            <CardTitle className="text-lg">{t('sections.infrastructure')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            {infraItemKeys.map((key) => (
              <p key={key}>- {t(key)}</p>
            ))}
          </CardContent>
        </Card>

        <Card className="border-border/70">
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <Globe className="size-5 text-primary" />
            <CardTitle className="text-lg">{t('sections.frontend')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            {frontendItemKeys.map((key) => (
              <p key={key}>- {t(key)}</p>
            ))}
          </CardContent>
        </Card>

        <Card className="border-border/70 sm:col-span-2 lg:col-span-1">
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <Server className="size-5 text-primary" />
            <CardTitle className="text-lg">{t('sections.backend')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            {backendItemKeys.map((key) => (
              <p key={key}>- {t(key)}</p>
            ))}
          </CardContent>
        </Card>
      </section>

      <section id="security" className="container mx-auto max-w-6xl px-4 pb-20">
        <Card className="border-primary/20 bg-primary/4">
          <CardContent className="flex flex-col gap-3 p-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p className="flex items-center gap-2 text-sm font-medium">
                <Lock className="size-4 text-primary" />
                {t('security.title')}
              </p>
              <p className="text-sm text-muted-foreground">{t('security.description')}</p>
            </div>
            <Button asChild variant="secondary">
              <Link to={`/${currentLanguage}/profile-sample`}>{t('security.cta')}</Link>
            </Button>
          </CardContent>
        </Card>
        <Card className="mt-4 border-primary/20 bg-primary/4">
          <CardContent className="flex flex-col gap-3 p-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p className="flex items-center gap-2 text-sm font-medium">
                <FlaskConical className="size-4 text-primary" />
                {t('zustand.title')}
              </p>
              <p className="text-sm text-muted-foreground">{t('zustand.description')}</p>
            </div>
            <Button asChild variant="secondary">
              <Link to={`/${currentLanguage}/zustand-sample`}>{t('zustand.cta')}</Link>
            </Button>
          </CardContent>
        </Card>
        <Card className="mt-4 border-primary/20 bg-primary/4">
          <CardContent className="flex flex-col gap-3 p-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p className="flex items-center gap-2 text-sm font-medium">
                <ClipboardCheck className="size-4 text-primary" />
                {t('formValidation.title')}
              </p>
              <p className="text-sm text-muted-foreground">{t('formValidation.description')}</p>
            </div>
            <Button asChild variant="secondary">
              <Link to={`/${currentLanguage}/validation-sample`}>{t('formValidation.cta')}</Link>
            </Button>
          </CardContent>
        </Card>
        <Card className="mt-4 border-primary/20 bg-primary/4">
          <CardContent className="flex flex-col gap-3 p-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p className="flex items-center gap-2 text-sm font-medium">
                <ShieldCheck className="size-4 text-primary" />
                {t('apiProtection.title')}
              </p>
              <p className="text-sm text-muted-foreground">{t('apiProtection.description')}</p>
            </div>
            <Button asChild variant="secondary">
              <Link to={`/${currentLanguage}/api-protection-sample`}>{t('apiProtection.cta')}</Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    </main>
  );
};

export default LandingPage;

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card';
import { getMe, type AuthMe } from '~/lib/api-helper';
import { isSupportedLanguage } from '~/lib/i18n';

const ProfileSamplePage = () => {
  const { t } = useTranslation('profileSample');
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const [profile, setProfile] = useState<AuthMe | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    const fetchProfile = async () => {
      try {
        setIsLoading(true);
        setErrorMessage(null);

        const me = await getMe();
        if (!me) {
          throw new Error('Unauthorized');
        }
        if (!ignore) {
          setProfile(me);
        }
      } catch (error) {
        if (!ignore) {
          setErrorMessage(error instanceof Error ? error.message : t('states.error'));
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    };

    void fetchProfile();
    return () => {
      ignore = true;
    };
  }, [t]);

  return (
    <main className="container mx-auto max-w-3xl px-4 py-14 h-screen">
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

      <Card>
        <CardHeader>
          <CardTitle>{t('profileCardTitle')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              {t('states.loading')}
            </div>
          )}

          {errorMessage && (
            <p className="text-sm text-destructive">
              {t('states.error')}: {errorMessage}
            </p>
          )}

          {!isLoading && !errorMessage && profile && (
            <dl className="grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-sm font-medium">{t('fields.id')}</dt>
                <dd className="text-sm text-muted-foreground">{profile.id}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium">{t('fields.displayName')}</dt>
                <dd className="text-sm text-muted-foreground">{profile.display_name || '-'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium">{t('fields.email')}</dt>
                <dd className="text-sm text-muted-foreground">{profile.email || '-'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium">{t('fields.userType')}</dt>
                <dd className="text-sm text-muted-foreground">{profile.user_type}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium">{t('fields.isActive')}</dt>
                <dd className="text-sm text-muted-foreground">
                  {profile.is_active ? t('values.active') : t('values.inactive')}
                </dd>
              </div>
            </dl>
          )}
        </CardContent>
      </Card>
    </main>
  );
};

export default ProfileSamplePage;

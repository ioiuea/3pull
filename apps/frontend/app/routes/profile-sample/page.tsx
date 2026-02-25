import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card';
import { Input } from '~/components/ui/input';
import { backendFetch, getMe, type AuthMe } from '~/lib/api-helper';
import { isSupportedLanguage } from '~/lib/i18n';

const ProfileSamplePage = () => {
  const { t } = useTranslation('profileSample');
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const [profile, setProfile] = useState<AuthMe | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isPasswordSubmitting, setIsPasswordSubmitting] = useState(false);

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

  const canChangePassword = profile?.user_type === 'external';

  const onSubmitPasswordChange = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPasswordMessage(null);
    setPasswordError(null);

    if (!canChangePassword) {
      setPasswordError(t('passwordChange.disabledForInternal'));
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError(t('passwordChange.errors.confirmMismatch'));
      return;
    }

    try {
      setIsPasswordSubmitting(true);
      const response = await backendFetch('/auth/password/change', {
        method: 'POST',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { detail?: { message?: string } }
          | null;
        throw new Error(payload?.detail?.message ?? t('passwordChange.errors.default'));
      }

      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setPasswordMessage(t('passwordChange.success'));
    } catch (error) {
      setPasswordError(error instanceof Error ? error.message : t('passwordChange.errors.default'));
    } finally {
      setIsPasswordSubmitting(false);
    }
  };

  return (
    <main className="container mx-auto max-w-3xl px-4 py-14 min-h-screen">
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

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>{t('passwordChange.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={onSubmitPasswordChange}>
            <p className="text-sm text-muted-foreground">{t('passwordChange.description')}</p>
            {!canChangePassword && (
              <p className="text-sm text-muted-foreground">{t('passwordChange.disabledForInternal')}</p>
            )}

            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="current-password">
                {t('passwordChange.fields.currentPassword')}
              </label>
              <Input
                id="current-password"
                type="password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                disabled={!canChangePassword || isPasswordSubmitting}
                required
              />
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="new-password">
                {t('passwordChange.fields.newPassword')}
              </label>
              <Input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                disabled={!canChangePassword || isPasswordSubmitting}
                required
              />
              <p className="text-xs text-muted-foreground">{t('passwordChange.policy')}</p>
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="confirm-password">
                {t('passwordChange.fields.confirmPassword')}
              </label>
              <Input
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                disabled={!canChangePassword || isPasswordSubmitting}
                required
              />
            </div>

            {passwordMessage && <p className="text-sm text-emerald-600">{passwordMessage}</p>}
            {passwordError && <p className="text-sm text-destructive">{passwordError}</p>}

            <Button type="submit" disabled={!canChangePassword || isPasswordSubmitting}>
              {isPasswordSubmitting ? t('passwordChange.submitting') : t('passwordChange.submit')}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
};

export default ProfileSamplePage;

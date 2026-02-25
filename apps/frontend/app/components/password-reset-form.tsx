import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';
import { cn } from '~/lib/utils';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import { Field, FieldDescription, FieldGroup, FieldLabel } from '~/components/ui/field';
import { Input } from '~/components/ui/input';
import { backendFetch } from '~/lib/api-helper';
import { isSupportedLanguage } from '~/lib/i18n';
import { PRODUCT_NAME } from '~/constants/product';

export function PasswordResetForm({ className, ...props }: React.ComponentProps<'div'>) {
  const { t } = useTranslation('auth');
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';

  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [requestMessage, setRequestMessage] = useState<string | null>(null);
  const [confirmMessage, setConfirmMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isRequesting, setIsRequesting] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);

  const onRequestReset = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setConfirmMessage(null);
    setRequestMessage(null);

    try {
      setIsRequesting(true);
      const response = await backendFetch('/auth/password/reset/request', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { detail?: { message?: string } }
          | null;
        throw new Error(payload?.detail?.message ?? t('reset.errors.requestDefault', { status: response.status }));
      }
      const payload = (await response.json().catch(() => null)) as
        | { debug_reset_token?: string | null }
        | null;
      if (payload?.debug_reset_token) {
        setToken(payload.debug_reset_token);
      }
      setRequestMessage(t('reset.requestAccepted'));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t('reset.errors.requestUnknown'));
    } finally {
      setIsRequesting(false);
    }
  };

  const onConfirmReset = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setConfirmMessage(null);

    if (newPassword !== confirmPassword) {
      setErrorMessage(t('reset.errors.confirmMismatch'));
      return;
    }

    try {
      setIsConfirming(true);
      const response = await backendFetch('/auth/password/reset/confirm', {
        method: 'POST',
        body: JSON.stringify({
          token,
          new_password: newPassword,
        }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { detail?: { message?: string } }
          | null;
        throw new Error(payload?.detail?.message ?? t('reset.errors.confirmDefault', { status: response.status }));
      }
      setConfirmMessage(t('reset.confirmSuccess'));
      setNewPassword('');
      setConfirmPassword('');
      setToken('');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t('reset.errors.confirmUnknown'));
    } finally {
      setIsConfirming(false);
    }
  };

  return (
    <div className={cn('flex flex-col gap-6', className)} {...props}>
      <Card>
        <CardHeader className="space-y-2 text-left">
          <p className="w-fit rounded-full border px-3 py-1 text-xs text-muted-foreground">{PRODUCT_NAME}</p>
          <CardTitle className="text-xl">{t('reset.title')}</CardTitle>
          <CardDescription>{t('reset.description')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <form onSubmit={onRequestReset}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="reset-email">{t('common.email')}</FieldLabel>
                <Input
                  id="reset-email"
                  type="email"
                  placeholder={t('common.emailPlaceholder')}
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </Field>
              <Field>
                <Button type="submit" disabled={isRequesting}>
                  {isRequesting ? t('reset.requesting') : t('reset.requestSubmit')}
                </Button>
              </Field>
            </FieldGroup>
          </form>

          <form onSubmit={onConfirmReset}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="reset-token">{t('reset.resetToken')}</FieldLabel>
                <Input
                  id="reset-token"
                  type="text"
                  required
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="new-password">{t('common.newPassword')}</FieldLabel>
                <Input
                  id="new-password"
                  type="password"
                  required
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                />
                <FieldDescription>{t('common.passwordPolicy')}</FieldDescription>
              </Field>
              <Field>
                <FieldLabel htmlFor="confirm-new-password">{t('common.confirmNewPassword')}</FieldLabel>
                <Input
                  id="confirm-new-password"
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                />
              </Field>
              <Field>
                <Button type="submit" disabled={isConfirming}>
                  {isConfirming ? t('reset.updating') : t('reset.confirmSubmit')}
                </Button>
                <FieldDescription className="text-center">
                  <Link to={`/${currentLanguage}/login`}>{t('reset.backToLogin')}</Link>
                </FieldDescription>
              </Field>
            </FieldGroup>
          </form>

          {requestMessage && <p className="text-sm text-muted-foreground">{requestMessage}</p>}
          {confirmMessage && <p className="text-sm text-emerald-600">{confirmMessage}</p>}
          {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}
        </CardContent>
      </Card>
    </div>
  );
}

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate, useParams } from 'react-router';
import { cn } from '~/lib/utils';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import { Field, FieldDescription, FieldGroup, FieldLabel } from '~/components/ui/field';
import { Input } from '~/components/ui/input';
import { backendFetch } from '~/lib/api-helper';
import { sanitizeReturnTo } from '~/lib/auth-redirect';
import { isSupportedLanguage } from '~/lib/i18n';
import { PRODUCT_NAME } from '~/constants/product';

export function SignupForm({ className, ...props }: React.ComponentProps<'div'>) {
  const { t } = useTranslation('auth');
  const navigate = useNavigate();
  const location = useLocation();
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const searchParams = new URLSearchParams(location.search);
  const returnTo = sanitizeReturnTo(searchParams.get('return_to'), {
    currentLanguage,
    disallowedPaths: [`/${currentLanguage}/login`, `/${currentLanguage}/verify-email`],
  });
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (password !== confirmPassword) {
      setErrorMessage(t('signup.errors.confirmMismatch'));
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await backendFetch('/auth/email/signup', {
        method: 'POST',
        body: JSON.stringify({
          email,
          password,
          display_name: name || null,
        }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as {
          detail?: { code?: string; message?: string };
        } | null;
        if (payload?.detail?.code === 'email_account_already_exists') {
          navigate(
            `/${currentLanguage}/verify-email?email=${encodeURIComponent(email)}&return_to=${encodeURIComponent(returnTo)}`,
            { replace: true },
          );
          return;
        }
        throw new Error(
          payload?.detail?.message ?? t('signup.errors.default', { status: response.status }),
        );
      }
      await response.json();
      setSuccessMessage(t('signup.successRequested'));
      navigate(
        `/${currentLanguage}/verify-email?email=${encodeURIComponent(email)}&return_to=${encodeURIComponent(returnTo)}`,
        { replace: true },
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t('signup.errors.unknown'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={cn('flex flex-col gap-6', className)} {...props}>
      <Card>
        <CardHeader className="space-y-2 text-left">
          <p className="w-fit rounded-full border px-3 py-1 text-xs text-muted-foreground">
            {PRODUCT_NAME}
          </p>
          <CardTitle className="text-xl">{t('signup.title')}</CardTitle>
          <CardDescription>{t('signup.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="name">{t('common.fullName')}</FieldLabel>
                <Input
                  id="name"
                  type="text"
                  placeholder={t('common.fullNamePlaceholder')}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="email">{t('common.email')}</FieldLabel>
                <Input
                  id="email"
                  type="email"
                  placeholder={t('common.emailPlaceholder')}
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="password">{t('common.password')}</FieldLabel>
                <Input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="confirm-password">{t('common.confirmPassword')}</FieldLabel>
                <Input
                  id="confirm-password"
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                />
              </Field>
              <FieldDescription>{t('common.passwordPolicy')}</FieldDescription>
              {errorMessage && (
                <FieldDescription className="text-destructive">{errorMessage}</FieldDescription>
              )}
              {successMessage && <FieldDescription>{successMessage}</FieldDescription>}
              <Field>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? t('signup.creating') : t('signup.submit')}
                </Button>
                <FieldDescription className="text-center">
                  {t('signup.hasAccount')}{' '}
                  <Link to={`/${currentLanguage}/login?return_to=${encodeURIComponent(returnTo)}`}>
                    {t('signup.goLogin')}
                  </Link>
                </FieldDescription>
              </Field>
            </FieldGroup>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

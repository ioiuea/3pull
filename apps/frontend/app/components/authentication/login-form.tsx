import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate, useParams } from 'react-router';
import { useSWRConfig } from 'swr';
import { cn } from '~/lib/utils';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import { Field, FieldDescription, FieldGroup, FieldLabel } from '~/components/ui/field';
import { Input } from '~/components/ui/input';
import { type AuthMe, backendFetch } from '~/lib/api-helper';
import { sanitizeReturnTo } from '~/lib/auth-redirect';
import { isSupportedLanguage } from '~/lib/i18n';
import { ENABLE_EMAIL_AUTH } from '~/constants/auth';
import { PRODUCT_NAME } from '~/constants/product';

type EmailLoginResponse = {
  status: 'authenticated';
  user: AuthMe;
};

function EntraIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="size-4 shrink-0">
      <rect x="2" y="2" width="9" height="9" rx="1" fill="#F25022" />
      <rect x="13" y="2" width="9" height="9" rx="1" fill="#7FBA00" />
      <rect x="2" y="13" width="9" height="9" rx="1" fill="#00A4EF" />
      <rect x="13" y="13" width="9" height="9" rx="1" fill="#FFB900" />
    </svg>
  );
}

export function LoginForm({ className, ...props }: React.ComponentProps<'div'>) {
  const { t } = useTranslation('auth');
  const navigate = useNavigate();
  const { mutate } = useSWRConfig();
  const location = useLocation();
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const searchParams = new URLSearchParams(location.search);
  const returnTo = sanitizeReturnTo(searchParams.get('return_to'), {
    currentLanguage,
    disallowedPaths: [`/${currentLanguage}/login`, `/${currentLanguage}/verify-email`],
  });
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showVerifyEmailLink, setShowVerifyEmailLink] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);
    setShowVerifyEmailLink(false);

    try {
      const response = await backendFetch('/auth/email/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      const payload = (await response.json().catch(() => null)) as
        | {
            detail?: { code?: string; message?: string };
          }
        | EmailLoginResponse
        | null;
      if (!response.ok) {
        if (payload && 'detail' in payload && payload.detail?.code === 'email_not_verified') {
          setShowVerifyEmailLink(true);
          throw new Error(t('login.errors.emailNotVerified'));
        }
        const message =
          payload && 'detail' in payload
            ? payload.detail?.message
            : t('login.errors.default', { status: response.status });
        throw new Error(message ?? t('login.errors.default', { status: response.status }));
      }
      await mutate('auth-me', (payload as EmailLoginResponse).user, {
        revalidate: false,
        populateCache: true,
      });
      navigate(returnTo, { replace: true });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t('login.errors.unknown'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const onEntraLogin = () => {
    const encoded = encodeURIComponent(returnTo);
    window.location.href = `${import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:8000'}/backend/auth/entra/login?return_to=${encoded}`;
  };

  return (
    <div className={cn('flex flex-col gap-6', className)} {...props}>
      <Card>
        <CardHeader className="space-y-2 text-left">
          <p className="w-fit rounded-full border px-3 py-1 text-xs text-muted-foreground">
            {PRODUCT_NAME}
          </p>
          <CardTitle className="text-xl">{t('login.title')}</CardTitle>
          <CardDescription>
            {ENABLE_EMAIL_AUTH ? t('login.description') : t('login.descriptionEntraOnly')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit}>
            <FieldGroup>
              <Field>
                <Button variant="outline" type="button" onClick={onEntraLogin}>
                  <EntraIcon />
                  {t('login.entra')}
                </Button>
              </Field>
              {ENABLE_EMAIL_AUTH && (
                <>
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
                    <FieldDescription>
                      <Link to={`/${currentLanguage}/password-reset`}>
                        {t('login.forgotPassword')}
                      </Link>
                    </FieldDescription>
                  </Field>
                </>
              )}
              {errorMessage && (
                <FieldDescription className="text-destructive">{errorMessage}</FieldDescription>
              )}
              {showVerifyEmailLink && (
                <FieldDescription>
                  <Link
                    to={`/${currentLanguage}/verify-email?email=${encodeURIComponent(email)}&return_to=${encodeURIComponent(returnTo)}`}
                  >
                    {t('login.actions.goVerifyEmail')}
                  </Link>
                </FieldDescription>
              )}
              {ENABLE_EMAIL_AUTH && (
                <Field>
                  <Button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? t('login.signingIn') : t('login.submit')}
                  </Button>
                  <FieldDescription className="text-center">
                    {t('login.noAccount')}{' '}
                    <Link
                      to={`/${currentLanguage}/signup?return_to=${encodeURIComponent(returnTo)}`}
                    >
                      {t('login.goSignup')}
                    </Link>
                  </FieldDescription>
                </Field>
              )}
            </FieldGroup>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

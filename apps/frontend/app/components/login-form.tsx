import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate, useParams } from 'react-router';
import { cn } from '~/lib/utils';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import { Field, FieldDescription, FieldGroup, FieldLabel } from '~/components/ui/field';
import { Input } from '~/components/ui/input';
import { backendFetch } from '~/lib/api-helper';
import { isSupportedLanguage } from '~/lib/i18n';
import { PRODUCT_NAME } from '~/constants/product';

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
  const location = useLocation();
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const searchParams = new URLSearchParams(location.search);
  const returnTo = searchParams.get('return_to') ?? `/${currentLanguage}`;
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await backendFetch('/auth/email/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as {
          detail?: { message?: string };
        } | null;
        throw new Error(
          payload?.detail?.message ?? t('login.errors.default', { status: response.status }),
        );
      }
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
          <CardDescription>{t('login.description')}</CardDescription>
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
                  <Link to={`/${currentLanguage}/password-reset`}>{t('login.forgotPassword')}</Link>
                </FieldDescription>
              </Field>
              {errorMessage && (
                <FieldDescription className="text-destructive">{errorMessage}</FieldDescription>
              )}
              <Field>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? t('login.signingIn') : t('login.submit')}
                </Button>
                <FieldDescription className="text-center">
                  {t('login.noAccount')}{' '}
                  <Link to={`/${currentLanguage}/signup`}>{t('login.goSignup')}</Link>
                </FieldDescription>
              </Field>
            </FieldGroup>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

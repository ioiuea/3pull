import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router';
import { cn } from '~/lib/utils';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import { Field, FieldDescription, FieldGroup, FieldLabel } from '~/components/ui/field';
import { Input } from '~/components/ui/input';
import { backendFetch } from '~/lib/api-helper';
import { sanitizeReturnTo } from '~/lib/auth-redirect';
import { isSupportedLanguage } from '~/lib/i18n';
import { ENABLE_EMAIL_AUTH } from '~/constants/auth';
import { PRODUCT_NAME } from '~/constants/product';

type VerifyResendResponse = {
  status: 'accepted';
  debug_verification_token?: string | null;
};

export function VerifyEmailForm({ className, ...props }: React.ComponentProps<'div'>) {
  const { t } = useTranslation('auth');
  const navigate = useNavigate();
  const location = useLocation();
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const loginPath = `/${currentLanguage}/login`;
  const verifyEmailPath = `/${currentLanguage}/verify-email`;
  const searchParams = new URLSearchParams(location.search);
  const emailQuery = searchParams.get('email') ?? '';
  const returnTo = sanitizeReturnTo(searchParams.get('return_to'), {
    currentLanguage,
    disallowedPaths: [loginPath, verifyEmailPath],
  });
  const [email, setEmail] = useState(emailQuery);
  const [token, setToken] = useState('');
  const [debugToken, setDebugToken] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isResending, setIsResending] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  if (!ENABLE_EMAIL_AUTH) {
    return <Navigate to={loginPath} replace />;
  }

  const loginTarget =
    returnTo === `/${currentLanguage}`
      ? loginPath
      : `${loginPath}?return_to=${encodeURIComponent(returnTo)}`;

  const onResend = async () => {
    setIsResending(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const response = await backendFetch('/auth/email/verify/resend', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });
      const payload = (await response.json().catch(() => null)) as
        | { detail?: { message?: string } }
        | VerifyResendResponse
        | null;
      if (!response.ok) {
        const message =
          payload && 'detail' in payload
            ? payload.detail?.message
            : t('verifyEmail.errors.resendDefault', { status: response.status });
        throw new Error(
          message ?? t('verifyEmail.errors.resendDefault', { status: response.status }),
        );
      }
      const resendPayload = payload as VerifyResendResponse;
      setDebugToken(resendPayload.debug_verification_token ?? null);
      setSuccessMessage(t('verifyEmail.resendAccepted'));
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : t('verifyEmail.errors.resendUnknown'),
      );
    } finally {
      setIsResending(false);
    }
  };

  const onVerify = async () => {
    setIsVerifying(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const response = await backendFetch('/auth/email/verify', {
        method: 'POST',
        body: JSON.stringify({ token }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as {
          detail?: { message?: string };
        } | null;
        throw new Error(
          payload?.detail?.message ??
            t('verifyEmail.errors.verifyDefault', { status: response.status }),
        );
      }
      setSuccessMessage(t('verifyEmail.verifySuccess'));
      navigate(loginTarget, { replace: true });
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : t('verifyEmail.errors.verifyUnknown'),
      );
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className={cn('flex flex-col gap-6', className)} {...props}>
      <Card>
        <CardHeader className="space-y-2 text-left">
          <p className="w-fit rounded-full border px-3 py-1 text-xs text-muted-foreground">
            {PRODUCT_NAME}
          </p>
          <CardTitle className="text-xl">{t('verifyEmail.title')}</CardTitle>
          <CardDescription>{t('verifyEmail.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="verify-email">{t('verifyEmail.emailLabel')}</FieldLabel>
              <Input
                id="verify-email"
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </Field>
            <Field>
              <Button type="button" onClick={onResend} disabled={isResending || !email}>
                {isResending ? t('verifyEmail.resending') : t('verifyEmail.resendSubmit')}
              </Button>
            </Field>
            <Field>
              <FieldLabel htmlFor="verification-token">{t('verifyEmail.tokenLabel')}</FieldLabel>
              <Input
                id="verification-token"
                value={token}
                onChange={(event) => setToken(event.target.value)}
                placeholder={t('verifyEmail.tokenPlaceholder')}
              />
            </Field>
            {debugToken && (
              <FieldDescription>
                {t('verifyEmail.debugTokenLabel')}: <code>{debugToken}</code>
              </FieldDescription>
            )}
            {errorMessage && (
              <FieldDescription className="text-destructive">{errorMessage}</FieldDescription>
            )}
            {successMessage && <FieldDescription>{successMessage}</FieldDescription>}
            <Field>
              <Button
                type="button"
                variant="outline"
                onClick={onVerify}
                disabled={isVerifying || !token}
              >
                {isVerifying ? t('verifyEmail.verifying') : t('verifyEmail.verifySubmit')}
              </Button>
              <FieldDescription className="text-center">
                <Link to={loginTarget}>{t('reset.backToLogin')}</Link>
              </FieldDescription>
            </Field>
          </FieldGroup>
        </CardContent>
      </Card>
    </div>
  );
}

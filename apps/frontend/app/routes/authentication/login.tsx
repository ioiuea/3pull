import { Navigate, useLocation, useParams } from 'react-router';
import { LoginForm } from '~/components/authentication/login-form';
import { Spinner } from '~/components/ui/spinner';
import { useMe } from '~/hooks/use-me';
import { sanitizeReturnTo } from '~/lib/auth-redirect';
import { isSupportedLanguage } from '~/lib/i18n';

export default function LoginPage() {
  const location = useLocation();
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const { data: me, isLoading } = useMe();
  const searchParams = new URLSearchParams(location.search);
  const returnTo = sanitizeReturnTo(searchParams.get('return_to'), {
    currentLanguage,
    disallowedPaths: [`/${currentLanguage}/login`, `/${currentLanguage}/verify-email`],
  });

  if (isLoading) {
    return (
      <div className="bg-muted flex min-h-svh items-center justify-center p-6 md:p-10">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner className="size-4" />
          <span>Checking session...</span>
        </div>
      </div>
    );
  }

  if (me) {
    return <Navigate to={returnTo} replace />;
  }

  return (
    <div className="bg-muted flex min-h-svh flex-col items-center justify-center gap-6 p-6 md:p-10">
      <div className="flex w-full max-w-md flex-col gap-6">
        <LoginForm />
      </div>
    </div>
  );
}

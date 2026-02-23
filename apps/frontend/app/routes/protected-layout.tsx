import { useEffect } from 'react';
import { Navigate, Outlet, useParams } from 'react-router';
import { useIsAuthenticated, useMsal } from '@azure/msal-react';
import { InteractionStatus } from '@azure/msal-browser';
import { Spinner } from '~/components/ui/spinner';
import { isSupportedLanguage } from '~/lib/i18n';
import { isMsalConfigured, loginRequest } from '~/lib/auth';

const ProtectedLayout = () => {
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const isAuthenticated = useIsAuthenticated();
  const { instance, inProgress } = useMsal();

  useEffect(() => {
    if (!isMsalConfigured || inProgress !== InteractionStatus.None) {
      return;
    }

    if (!isAuthenticated) {
      void instance.loginRedirect({
        ...loginRequest,
        redirectStartPage: window.location.href,
      });
    }
  }, [inProgress, instance, isAuthenticated]);

  if (!isMsalConfigured) {
    return <Navigate to={`/${currentLanguage}`} replace />;
  }

  if (!isAuthenticated || inProgress !== InteractionStatus.None) {
    return (
      <main className="container mx-auto flex min-h-dvh items-center justify-center px-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner className="size-4" />
          <span>Authenticating...</span>
        </div>
      </main>
    );
  }

  return <Outlet />;
};

export default ProtectedLayout;

import { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation, useParams } from 'react-router';
import { Spinner } from '~/components/ui/spinner';
import { isSupportedLanguage } from '~/lib/i18n';
import { getMe } from '~/lib/api-helper';

const ProtectedLayout = () => {
  const { lng } = useParams();
  const { pathname, search, hash } = useLocation();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const [isChecking, setIsChecking] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    let ignore = false;

    const checkSession = async () => {
      try {
        const me = await getMe();
        if (!ignore) {
          setIsAuthenticated(Boolean(me));
        }
      } finally {
        if (!ignore) {
          setIsChecking(false);
        }
      }
    };

    void checkSession();
    return () => {
      ignore = true;
    };
  }, [pathname]);

  if (isChecking) {
    return (
      <main className="container mx-auto flex min-h-dvh items-center justify-center px-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner className="size-4" />
          <span>Checking session...</span>
        </div>
      </main>
    );
  }

  if (!isAuthenticated) {
    const returnTo = encodeURIComponent(`${pathname}${search}${hash}`);
    return <Navigate to={`/${currentLanguage}/login?return_to=${returnTo}`} replace />;
  }

  return <Outlet />;
};

export default ProtectedLayout;

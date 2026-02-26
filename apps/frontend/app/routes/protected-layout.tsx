import { useEffect } from 'react';
import { Navigate, Outlet, useLocation, useParams } from 'react-router';
import { Spinner } from '~/components/ui/spinner';
import { useMe } from '~/hooks/use-me';
import { isSupportedLanguage } from '~/lib/i18n';

const ProtectedLayout = () => {
  const { lng } = useParams();
  const { pathname, search, hash } = useLocation();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const { data: me, isLoading, mutate } = useMe();

  useEffect(() => {
    void mutate();
  }, [pathname, mutate]);

  if (isLoading) {
    return (
      <main className="container mx-auto flex min-h-dvh items-center justify-center px-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner className="size-4" />
          <span>Checking session...</span>
        </div>
      </main>
    );
  }

  if (!me) {
    const returnTo = encodeURIComponent(`${pathname}${search}${hash}`);
    return <Navigate to={`/${currentLanguage}/login?return_to=${returnTo}`} replace />;
  }

  return <Outlet />;
};

export default ProtectedLayout;

import { useEffect } from 'react';
import { Navigate, Outlet, useLocation, useParams } from 'react-router';
import SampleSwitcher from '~/components/sample-switcher/sample-switcher';
import i18n, { detectLanguage, isSupportedLanguage, persistLanguageCookie } from '~/lib/i18n';

const AppLayout = () => {
  const { lng } = useParams();
  const location = useLocation();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : null;

  useEffect(() => {
    if (!currentLanguage) {
      return;
    }

    if (i18n.language !== currentLanguage) {
      void i18n.changeLanguage(currentLanguage);
    }
    persistLanguageCookie(currentLanguage);
  }, [currentLanguage]);

  if (!currentLanguage) {
    const detectedLanguage = detectLanguage();
    const redirectTarget = `/${detectedLanguage}${location.pathname}${location.search}${location.hash}`;
    return <Navigate to={redirectTarget} replace />;
  }

  return (
    <>
      <div className="fixed top-4 right-4 z-50">
        <SampleSwitcher />
      </div>
      <Outlet />
    </>
  );
};

export default AppLayout;

import { useEffect } from "react";
import { Navigate, Outlet, useLocation, useParams } from "react-router";
import SampleSwitcher from "~/components/sample-switcher/sample-switcher";
import i18n, {
  detectLanguage,
  isSupportedLanguage,
  persistLanguageCookie,
} from "~/lib/i18n";

const AppLayout = () => {
  const { lng } = useParams();
  const location = useLocation();

  if (!lng || !isSupportedLanguage(lng)) {
    const detectedLanguage = detectLanguage();
    const redirectTarget = `/${detectedLanguage}${location.pathname}${location.search}${location.hash}`;
    return <Navigate to={redirectTarget} replace />;
  }

  useEffect(() => {
    if (i18n.language !== lng) {
      void i18n.changeLanguage(lng);
    }
    persistLanguageCookie(lng);
  }, [lng]);

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

import { useEffect } from "react";
import { Navigate, Outlet, useParams } from "react-router";
import SampleSwitcher from "~/components/sample-switcher/sample-switcher";
import i18n, {
  isSupportedLanguage,
  persistLanguageCookie,
} from "~/lib/i18n";

const AppLayout = () => {
  const { lng } = useParams();

  if (!lng || !isSupportedLanguage(lng)) {
    return <Navigate to="/" replace />;
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

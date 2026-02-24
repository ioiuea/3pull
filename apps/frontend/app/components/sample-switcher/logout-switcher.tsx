'use client';

import { useEffect, useState } from 'react';
import { LogOut } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useLocation, useParams } from 'react-router';
import { Button } from '~/components/ui/button';
import { backendFetch, getMe } from '~/lib/api-helper';
import { isSupportedLanguage } from '~/lib/i18n';

/**
 * 認証済みユーザー向けログアウトボタンです。
 * 未認証時は表示しません。
 */
const LogoutSwitcher = () => {
  const { t } = useTranslation('common');
  const { lng } = useParams();
  const { pathname, search, hash } = useLocation();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    let ignore = false;

    const checkAuth = async () => {
      try {
        const me = await getMe();
        if (!ignore) {
          setIsAuthenticated(Boolean(me));
        }
      } catch {
        if (!ignore) {
          setIsAuthenticated(false);
        }
      }
    };

    void checkAuth();
    return () => {
      ignore = true;
    };
  }, [pathname, search, hash]);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={async () => {
        await backendFetch('/auth/logout', { method: 'POST' });
        window.location.href = `/${currentLanguage}/login`;
      }}
      aria-label={t('switcher.auth.logoutAriaLabel')}
      title={t('switcher.auth.logoutAriaLabel')}
    >
      <LogOut className="size-4" />
      <span className="hidden sm:inline">{t('switcher.auth.logoutLabel')}</span>
    </Button>
  );
};

export default LogoutSwitcher;

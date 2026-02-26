'use client';

import { LogOut } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router';
import { Button } from '~/components/ui/button';
import { useMe } from '~/hooks/use-me';
import { backendFetch } from '~/lib/api-helper';
import { isSupportedLanguage } from '~/lib/i18n';

/**
 * 認証済みユーザー向けログアウトボタンです。
 * 未認証時は表示しません。
 */
const LogoutSwitcher = () => {
  const { t } = useTranslation('common');
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const { data: me, error } = useMe();
  const isAuthenticated = Boolean(me) && !error;

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

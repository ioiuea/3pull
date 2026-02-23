'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { useTranslation } from 'react-i18next';
import { Button } from '~/components/ui/button';

/**
 * UI テーマ（light/dark）を切り替えるスイッチャーです。
 */
const ThemeSwitcher = () => {
  const { theme, setTheme } = useTheme();
  const { t } = useTranslation('common');

  const isDark = theme === 'dark';
  const nextTheme = isDark ? 'light' : 'dark';

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={() => setTheme(nextTheme)}
      aria-label={t('switcher.theme.ariaLabel')}
      title={t('switcher.theme.ariaLabel')}
    >
      {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
      <span className="hidden sm:inline">{t('switcher.theme.label')}</span>
    </Button>
  );
};

export default ThemeSwitcher;

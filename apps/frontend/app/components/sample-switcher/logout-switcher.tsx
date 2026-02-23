"use client";

import { LogOut } from "lucide-react";
import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import { useTranslation } from "react-i18next";
import { Button } from "~/components/ui/button";

/**
 * 認証済みユーザー向けログアウトボタンです。
 * 未認証時は表示しません。
 */
const LogoutSwitcher = () => {
  const { t } = useTranslation("common");
  const isAuthenticated = useIsAuthenticated();
  const { instance } = useMsal();

  if (!isAuthenticated) {
    return null;
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={() => instance.logoutRedirect()}
      aria-label={t("switcher.auth.logoutAriaLabel")}
      title={t("switcher.auth.logoutAriaLabel")}
    >
      <LogOut className="size-4" />
      <span className="hidden sm:inline">{t("switcher.auth.logoutLabel")}</span>
    </Button>
  );
};

export default LogoutSwitcher;

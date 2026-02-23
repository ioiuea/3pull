"use client";

import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useParams } from "react-router";
import { Button } from "~/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "~/components/ui/dropdown-menu";
import { isSupportedLanguage, SUPPORTED_LANGUAGES } from "~/lib/i18n";

/**
 * URL 言語セグメントを切り替えるスイッチャーです。
 * 現在のパス構造を保ったまま先頭言語セグメントのみ置き換えます。
 */
const LanguageSwitcher = () => {
  const { t } = useTranslation("common");
  const { lng } = useParams();
  const { pathname, search, hash } = useLocation();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : "en";

  const buildLanguagePath = (targetLanguage: string) => {
    const segments = pathname.split("/").filter(Boolean);
    if (segments.length === 0) {
      return `/${targetLanguage}${search}${hash}`;
    }

    segments[0] = targetLanguage;
    return `/${segments.join("/")}${search}${hash}`;
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="sm"
          aria-label={t("switcher.language.ariaLabel")}
        >
          <Languages className="size-4" />
          <span className="hidden sm:inline">{t("switcher.language.label")}</span>
          <span className="rounded-sm bg-muted px-1.5 py-0.5 text-[10px] uppercase">
            {currentLanguage}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {SUPPORTED_LANGUAGES.map((language) => (
          <DropdownMenuItem key={language} asChild>
            <Link to={buildLanguagePath(language)}>{t(`switcher.language.options.${language}`)}</Link>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default LanguageSwitcher;

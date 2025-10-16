"use client";

import { usePathname, useRouter } from "next/navigation";

// ** Types
import type { Locale } from "@/utils/dictionaries";

// ** Constants
const languages: Record<Locale, string> = {
  ja: "日本語",
  en: "English",
};

// ** Function Component
const LangSwitchClient = ({ currentLang }: { currentLang: Locale }) => {
  const pathname = usePathname();
  const router = useRouter();

  const switchLanguage = (newLang: Locale) => {
    const segments = pathname.split("/");
    segments[1] = newLang;
    router.push(segments.join("/"));
  };

  return (
    <div className="flex gap-2 bg-white/10 dark:bg-black/10 backdrop-blur-sm rounded-lg p-2">
      {(Object.keys(languages) as Locale[]).map((lang) => (
        <button
          key={lang}
          onClick={() => switchLanguage(lang)}
          className={`px-3 py-1 rounded transition-colors ${
            currentLang === lang
              ? "bg-foreground text-background font-semibold"
              : "hover:bg-foreground/10"
          }`}
        >
          {languages[lang]}
        </button>
      ))}
    </div>
  );
};

export default LangSwitchClient;

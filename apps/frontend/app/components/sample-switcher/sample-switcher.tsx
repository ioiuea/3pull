"use client";

import LanguageSwitcher from "~/components/sample-switcher/language-switcher";
import ThemeSwitcher from "~/components/sample-switcher/theme-switcher";

/**
 * 画面右上に配置するデモ用スイッチャー群です。
 */
const SampleSwitcher = () => {
  return (
    <div className="inline-flex items-center gap-2 rounded-xl border bg-background/90 p-2 shadow-sm backdrop-blur">
      <ThemeSwitcher />
      <LanguageSwitcher />
    </div>
  );
};

export default SampleSwitcher;

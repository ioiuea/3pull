// ** Styles
import "@/styles/globals.css";

// ** Components
import LanguageSwitcher from "@/components/LanguageSwitcher";

// ** Constants
import { TITLE, DESCRIPTION, ICON_PATH } from "@/constants";

// ** Types
import type { Metadata } from "next";
import type { Locale } from "@/utils/dictionaries";

// ** Font
import { Geist, Geist_Mono } from "next/font/google";
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// ** Metadata
export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  icons: {
    icon: ICON_PATH,
  },
};

// ** Function Component
const RootLayout = async ({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ lang: string }>;
}>) => {
  const { lang } = await params;

  return (
    <html lang={lang}>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <header className="fixed top-0 right-0 p-4 z-50">
          <LanguageSwitcher currentLang={lang as Locale} />
        </header>
        {children}
      </body>
    </html>
  );
};

export default RootLayout;

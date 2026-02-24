import {
  isRouteErrorResponse,
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
  useLocation,
} from 'react-router';
import { useEffect } from 'react';

import type { Route } from './+types/root';
import { ThemeProvider } from '~/components/theme-provider';
import { Spinner } from '~/components/ui/spinner';
import { Toaster } from '~/components/ui/sonner';
import '~/lib/i18n';
import { DEFAULT_LANGUAGE, LANGUAGE_COOKIE_KEY, isSupportedLanguage } from '~/lib/i18n';
import { TooltipProvider } from '~/components/ui/tooltip';
import './app.css';

export const links: Route.LinksFunction = () => [
  { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
  {
    rel: 'preconnect',
    href: 'https://fonts.gstatic.com',
    crossOrigin: 'anonymous',
  },
  {
    rel: 'stylesheet',
    href: 'https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap',
  },
];

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang={DEFAULT_LANGUAGE} suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <Meta />
        <Links />
      </head>
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <TooltipProvider>
            {children}
            <Toaster />
          </TooltipProvider>
        </ThemeProvider>
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function App() {
  const { pathname } = useLocation();

  useEffect(() => {
    const cookieLanguage = document.cookie
      .split('; ')
      .find((item) => item.startsWith(`${LANGUAGE_COOKIE_KEY}=`))
      ?.split('=')[1];
    const decodedCookieLanguage = cookieLanguage ? decodeURIComponent(cookieLanguage) : '';
    const firstSegment = pathname.split('/').filter(Boolean)[0];
    const resolvedLanguage = isSupportedLanguage(decodedCookieLanguage)
      ? decodedCookieLanguage
      : isSupportedLanguage(firstSegment ?? '')
        ? firstSegment
        : DEFAULT_LANGUAGE;
    document.documentElement.lang = resolvedLanguage;
  }, [pathname]);

  return <Outlet />;
}

export function HydrateFallback() {
  return (
    <main className="container mx-auto flex min-h-dvh items-center justify-center px-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Spinner className="size-4" />
        <span>Loading application...</span>
      </div>
    </main>
  );
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  let message = 'Oops!';
  let details = 'An unexpected error occurred.';
  let stack: string | undefined;

  if (isRouteErrorResponse(error)) {
    message = error.status === 404 ? '404' : 'Error';
    details =
      error.status === 404 ? 'The requested page could not be found.' : error.statusText || details;
  } else if (import.meta.env.DEV && error && error instanceof Error) {
    details = error.message;
    stack = error.stack;
  }

  return (
    <main className="pt-16 p-4 h-screen container mx-auto">
      <h1>{message}</h1>
      <p>{details}</p>
      {stack && (
        <pre className="w-full p-4 overflow-x-auto">
          <code>{stack}</code>
        </pre>
      )}
    </main>
  );
}

import { type RouteConfig, index, layout, route } from '@react-router/dev/routes';

export default [
  index('routes/language-redirect.tsx'),
  route(':lng', 'routes/layout.tsx', [
    route('login', 'routes/authentication/login.tsx'),
    route('signup', 'routes/authentication/signup.tsx'),
    route('verify-email', 'routes/authentication/verify-email.tsx'),
    route('password-reset', 'routes/authentication/password-reset.tsx'),
    layout('routes/protected-layout.tsx', [
      index('routes/landing-page.tsx'),
      route('profile-sample', 'routes/profile-sample/page.tsx'),
      route('zustand-sample', 'routes/zustand-sample/page.tsx'),
      route('validation-sample', 'routes/validation-sample/page.tsx'),
      route('api-protection-sample', 'routes/api-protection-sample/page.tsx'),
      route('audit-log-sample', 'routes/audit-log-sample/page.tsx'),
      route('async-job-sample', 'routes/async-job-sample/page.tsx'),
    ]),
  ]),
] satisfies RouteConfig;

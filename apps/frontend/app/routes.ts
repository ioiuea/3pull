import { type RouteConfig, index, layout, route } from '@react-router/dev/routes';

export default [
  index('routes/language-redirect.tsx'),
  route(':lng', 'routes/layout.tsx', [
    route('login', 'routes/login.tsx'),
    route('signup', 'routes/signup.tsx'),
    route('password-reset', 'routes/password-reset.tsx'),
    layout('routes/protected-layout.tsx', [
      index('routes/landing-page.tsx'),
      route('profile-sample', 'routes/profile-sample/page.tsx'),
      route('zustand-sample', 'routes/zustand-sample/page.tsx'),
      route('validation-sample', 'routes/validation-sample/page.tsx'),
      route('api-protection-sample', 'routes/api-protection-sample/page.tsx'),
    ]),
  ]),
] satisfies RouteConfig;

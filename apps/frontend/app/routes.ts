import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/language-redirect.tsx"),
  route(":lng", "routes/layout.tsx", [index("routes/landing-page.tsx")]),
] satisfies RouteConfig;

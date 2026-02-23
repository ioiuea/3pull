import { Link, useParams } from "react-router";
import { useTranslation } from "react-i18next";
import { Button } from "~/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";

const I18nSampleAboutPage = () => {
  const { t } = useTranslation();
  const { lng } = useParams();
  const currentLanguage = lng ?? "en";
  const nextLanguage = currentLanguage === "ja" ? "en" : "ja";

  return (
    <main className="container mx-auto max-w-2xl py-12 px-4 h-screen">
      <Card>
        <CardHeader>
          <CardTitle>{t("about.title")}</CardTitle>
          <CardDescription>{t("about.description")}</CardDescription>
        </CardHeader>
        <CardContent className="flex gap-3">
          <Button asChild variant="secondary">
            <Link to={`/${currentLanguage}`}>{t("about.homeLink")}</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to={`/${nextLanguage}/about`}>{t("about.switchLanguage")}</Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
};

export default I18nSampleAboutPage;

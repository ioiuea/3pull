import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import { ArrowLeft, Minus, Plus, RefreshCw } from "lucide-react";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Switch } from "~/components/ui/switch";
import { isSupportedLanguage } from "~/lib/i18n";
import { useBooleanSampleStore } from "~/store/boolean-sample-store";
import { useNumberSampleStore } from "~/store/number-sample-store";
import { useObjectSampleStore } from "~/store/object-sample-store";
import { useStringSampleStore } from "~/store/string-sample-store";

const ZustandSamplePage = () => {
  const { t } = useTranslation("zustandSample");
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : "en";

  const { message, setMessage, reset: resetStringState } = useStringSampleStore();
  const {
    count,
    increment,
    decrement,
    setCount,
    reset: resetNumberState,
  } = useNumberSampleStore();
  const {
    isPublished,
    togglePublished,
    reset: resetBooleanState,
  } = useBooleanSampleStore();
  const {
    profile,
    setProfileName,
    setProfileRole,
    reset: resetObjectState,
  } = useObjectSampleStore();

  const resetAll = () => {
    resetStringState();
    resetNumberState();
    resetBooleanState();
    resetObjectState();
  };

  return (
    <main className="container mx-auto max-w-4xl px-4 py-14">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="mt-2 text-muted-foreground">{t("description")}</p>
        </div>
        <Button asChild variant="outline">
          <Link to={`/${currentLanguage}`}>
            <ArrowLeft className="size-4" />
            {t("actions.backToLp")}
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("cards.string.title")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Label htmlFor="sample-message">{t("cards.string.label")}</Label>
            <Input
              id="sample-message"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder={t("cards.string.placeholder")}
            />
            <p className="text-sm text-muted-foreground">
              {t("cards.string.current")}: {message}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("cards.number.title")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Label htmlFor="sample-count">{t("cards.number.label")}</Label>
            <Input
              id="sample-count"
              type="number"
              value={count}
              onChange={(event) => setCount(Number(event.target.value || 0))}
            />
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" onClick={decrement}>
                <Minus className="size-4" />
                {t("cards.number.decrement")}
              </Button>
              <Button type="button" onClick={increment}>
                <Plus className="size-4" />
                {t("cards.number.increment")}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("cards.boolean.title")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between gap-4 rounded-lg border p-3">
              <div>
                <p className="font-medium">{t("cards.boolean.label")}</p>
                <p className="text-sm text-muted-foreground">
                  {isPublished ? t("cards.boolean.true") : t("cards.boolean.false")}
                </p>
              </div>
              <Switch checked={isPublished} onCheckedChange={togglePublished} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("cards.object.title")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="sample-profile-name">{t("cards.object.nameLabel")}</Label>
              <Input
                id="sample-profile-name"
                value={profile.name}
                onChange={(event) => setProfileName(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sample-profile-role">{t("cards.object.roleLabel")}</Label>
              <Input
                id="sample-profile-role"
                value={profile.role}
                onChange={(event) => setProfileRole(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">{t("cards.object.current")}:</p>
              <pre className="overflow-x-auto rounded-md border bg-muted/30 p-3 text-xs leading-relaxed">
                <code>{JSON.stringify(profile, null, 2)}</code>
              </pre>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6">
        <Button type="button" variant="secondary" onClick={resetAll}>
          <RefreshCw className="size-4" />
          {t("actions.reset")}
        </Button>
      </div>
    </main>
  );
};

export default ZustandSamplePage;

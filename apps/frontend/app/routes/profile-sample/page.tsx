import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import { useMsal } from "@azure/msal-react";
import {
  InteractionStatus,
  InteractionRequiredAuthError,
  type AccountInfo,
} from "@azure/msal-browser";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { isSupportedLanguage } from "~/lib/i18n";
import {
  graphProfileEndpoint,
  isMsalConfigured,
  loginRequest,
} from "~/lib/auth";

type GraphProfile = {
  companyName?: string | null;
  department?: string | null;
  employeeId?: string | null;
  displayName?: string | null;
  userPrincipalName?: string | null;
  mail?: string | null;
};

const resolveAccount = (
  activeAccount: AccountInfo | null,
  accounts: AccountInfo[]
) => activeAccount ?? accounts[0] ?? null;

const PofileSamplePage = () => {
  const { t } = useTranslation("profileSample");
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : "en";
  const { instance, accounts, inProgress } = useMsal();
  const [profile, setProfile] = useState<GraphProfile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const account = useMemo(
    () => resolveAccount(instance.getActiveAccount(), accounts),
    [accounts, instance]
  );

  useEffect(() => {
    if (account && !instance.getActiveAccount()) {
      instance.setActiveAccount(account);
    }
  }, [account, instance]);

  useEffect(() => {
    if (!isMsalConfigured || !account || inProgress !== InteractionStatus.None) {
      return;
    }

    let ignore = false;

    const fetchProfile = async () => {
      try {
        setIsLoading(true);
        setErrorMessage(null);

        const token = await instance
          .acquireTokenSilent({ ...loginRequest, account })
          .catch(async (error: unknown) => {
            if (error instanceof InteractionRequiredAuthError) {
              await instance.acquireTokenRedirect({ ...loginRequest, account });
            }
            throw error;
          });

        const response = await fetch(graphProfileEndpoint, {
          headers: {
            Authorization: `Bearer ${token.accessToken}`,
          },
        });

        if (!response.ok) {
          throw new Error(`Graph API request failed: ${response.status}`);
        }

        const payload = (await response.json()) as GraphProfile;
        if (!ignore) {
          setProfile(payload);
        }
      } catch (error) {
        if (!ignore) {
          setErrorMessage(
            error instanceof Error ? error.message : t("states.error")
          );
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    };

    void fetchProfile();

    return () => {
      ignore = true;
    };
  }, [account, inProgress, instance, t]);

  if (!isMsalConfigured) {
    return (
      <main className="container mx-auto max-w-3xl px-4 py-14 h-screen">
        <Card>
          <CardHeader>
            <CardTitle>{t("states.notConfiguredTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">{t("states.notConfiguredDescription")}</p>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="container mx-auto max-w-3xl px-4 py-14 h-screen">
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

      <Card>
        <CardHeader>
          <CardTitle>{t("profileCardTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              {t("states.loading")}
            </div>
          )}

          {errorMessage && (
            <p className="text-sm text-destructive">
              {t("states.error")}: {errorMessage}
            </p>
          )}

          {!isLoading && !errorMessage && profile && (
            <dl className="grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-sm font-medium">{t("fields.displayName")}</dt>
                <dd className="text-sm text-muted-foreground">
                  {profile.displayName || "-"}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium">{t("fields.userPrincipalName")}</dt>
                <dd className="text-sm text-muted-foreground">
                  {profile.userPrincipalName || "-"}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium">{t("fields.email")}</dt>
                <dd className="text-sm text-muted-foreground">
                  {profile.mail || "-"}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium">{t("fields.companyName")}</dt>
                <dd className="text-sm text-muted-foreground">
                  {profile.companyName || "-"}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium">{t("fields.department")}</dt>
                <dd className="text-sm text-muted-foreground">
                  {profile.department || "-"}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium">{t("fields.employeeId")}</dt>
                <dd className="text-sm text-muted-foreground">
                  {profile.employeeId || "-"}
                </dd>
              </div>
            </dl>
          )}
        </CardContent>
      </Card>
    </main>
  );
};

export default PofileSamplePage;

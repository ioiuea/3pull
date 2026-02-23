import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import { ArrowLeft } from "lucide-react";
import { useForm, type FieldPath } from "react-hook-form";
import { z } from "zod";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "~/components/ui/form";
import { Input } from "~/components/ui/input";
import { Switch } from "~/components/ui/switch";
import { isSupportedLanguage } from "~/lib/i18n";

const formSchema = z.object({
  fullName: z.string().min(1, "validation.fullNameRequired"),
  email: z.string().email("validation.emailInvalid"),
  age: z.coerce.number().int("validation.ageInteger").min(18, "validation.ageMin"),
  agreeToTerms: z.boolean().refine((value) => value, {
    message: "validation.agreeRequired",
  }),
  profile: z.object({
    department: z.string().min(1, "validation.departmentRequired"),
    receiveNewsletter: z.boolean(),
  }),
});

type FormValues = z.infer<typeof formSchema>;

const defaultValues: FormValues = {
  fullName: "",
  email: "",
  age: 18,
  agreeToTerms: false,
  profile: {
    department: "",
    receiveNewsletter: true,
  },
};

const ValidationSamplePage = () => {
  const { t } = useTranslation("validationSample");
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : "en";
  const [submittedValues, setSubmittedValues] = useState<FormValues | null>(null);

  const form = useForm<FormValues>({
    defaultValues,
    mode: "onSubmit",
  });

  const handleSubmit = (values: FormValues) => {
    form.clearErrors();
    const result = formSchema.safeParse(values);
    if (!result.success) {
      result.error.issues.forEach((issue) => {
        const path = issue.path.join(".") as FieldPath<FormValues>;
        form.setError(path, { message: issue.message });
      });
      return;
    }
    setSubmittedValues(result.data);
  };
  const toErrorText = (message?: string) => (message ? t(message) : undefined);

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

      <Card>
        <CardHeader>
          <CardTitle>{t("form.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form className="space-y-6" onSubmit={form.handleSubmit(handleSubmit)} noValidate>
              <FormField
                control={form.control}
                name="fullName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("form.fields.fullName.label")}</FormLabel>
                    <FormControl>
                      <Input placeholder={t("form.fields.fullName.placeholder")} {...field} />
                    </FormControl>
                    <FormMessage>{toErrorText(form.formState.errors.fullName?.message)}</FormMessage>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("form.fields.email.label")}</FormLabel>
                    <FormControl>
                      <Input type="email" placeholder={t("form.fields.email.placeholder")} {...field} />
                    </FormControl>
                    <FormMessage>{toErrorText(form.formState.errors.email?.message)}</FormMessage>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="age"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("form.fields.age.label")}</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={0}
                        value={field.value}
                        onChange={(event) => field.onChange(event.target.value)}
                      />
                    </FormControl>
                    <FormDescription>{t("form.fields.age.description")}</FormDescription>
                    <FormMessage>{toErrorText(form.formState.errors.age?.message)}</FormMessage>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="profile.department"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("form.fields.department.label")}</FormLabel>
                    <FormControl>
                      <Input placeholder={t("form.fields.department.placeholder")} {...field} />
                    </FormControl>
                    <FormMessage>{toErrorText(form.formState.errors.profile?.department?.message)}</FormMessage>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="profile.receiveNewsletter"
                render={({ field }) => (
                  <FormItem className="flex items-center justify-between rounded-lg border p-3">
                    <div>
                      <FormLabel>{t("form.fields.receiveNewsletter.label")}</FormLabel>
                      <FormDescription>
                        {t("form.fields.receiveNewsletter.description")}
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="agreeToTerms"
                render={({ field }) => (
                  <FormItem className="flex items-center justify-between rounded-lg border p-3">
                    <div>
                      <FormLabel>{t("form.fields.agreeToTerms.label")}</FormLabel>
                      <FormDescription>{t("form.fields.agreeToTerms.description")}</FormDescription>
                    </div>
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                    <FormMessage>{toErrorText(form.formState.errors.agreeToTerms?.message)}</FormMessage>
                  </FormItem>
                )}
              />

              <div className="flex gap-2">
                <Button type="submit">{t("actions.submit")}</Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => {
                    form.reset(defaultValues);
                    setSubmittedValues(null);
                  }}
                >
                  {t("actions.reset")}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>{t("result.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="overflow-x-auto rounded-md border bg-muted/30 p-3 text-xs leading-relaxed">
            <code>
              {submittedValues
                ? JSON.stringify(submittedValues, null, 2)
                : t("result.empty")}
            </code>
          </pre>
        </CardContent>
      </Card>
    </main>
  );
};

export default ValidationSamplePage;

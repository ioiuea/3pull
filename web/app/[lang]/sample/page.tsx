// ** Components
import SampleClient from "@/components/sample";
import { SignOut } from "@/components/signout-button";

// ** Utils
import { getDictionary, type Locale } from "@/utils/dictionaries";

// ** Function Component
const SamplePage = async ({
  params,
}: {
  params: Promise<{ lang: string }>;
}) => {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-4xl w-full space-y-8">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold">{dict.sample.title}</h1>
          <p className="text-xl text-foreground/70">
            {dict.sample.description}
          </p>
        </div>

        <SampleClient dict={dict.sample} />
        <SignOut />
      </div>
    </div>
  );
};

export default SamplePage;

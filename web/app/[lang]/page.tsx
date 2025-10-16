// ** Components
import HomeClient from "@/components/home";

// ** Utils
import { getDictionary, type Locale } from "@/utils/dictionaries";

import { auth } from "@/auth";

// ** Function Component
const Home = async ({ params }: { params: Promise<{ lang: string }> }) => {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);

  const session = await auth();
  console.log(session);

  return <HomeClient dict={dict.home} lang={lang} />;
};

export default Home;

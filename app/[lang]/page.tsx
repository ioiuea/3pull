// ** Components
// import { HomeClient } from "@/components/home";

// ** Utils
import { getDictionary, type Locale } from "@/utils/dictionaries";

// ** Function Component
const Home = async ({ params }: { params: Promise<{ lang: string }> }) => {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);
  console.log(dict);

  // return <HomeClient dict={dict.home} lang={lang} />;
  return <h1>home</h1>;
};

export default Home;

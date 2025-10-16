import React from "react";

// ** Components
import SignInClient from "@/components/siginin";

// ** Utils
import { getDictionary, type Locale } from "@/utils/dictionaries";

// ** Function Component
const SignIn = async ({ params }: { params: Promise<{ lang: string }> }) => {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);
  return <SignInClient dict={dict.signin} />;
};

export default SignIn;

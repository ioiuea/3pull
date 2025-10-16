"use client";
import React from "react";
import { useSearchParams } from "next/navigation";

// ** Auth
import { signIn } from "next-auth/react";

// ** UI
import { Button } from "@/components/ui/button";
import { Card, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

// ** Types
interface SignInClientProps {
  dict: {
    title: string;
  };
}

// ** Function Component
const SignInClient = ({ dict }: SignInClientProps) => {
  const searchParams = useSearchParams();
  const callbackUrl = searchParams?.get("callbackUrl") || "/";

  const handleSignInEntraID = async () => {
    await signIn("microsoft-entra-id", { callbackUrl });
  };

  const handleSignInGitHub = async () => {
    await signIn("github", { callbackUrl });
  };

  const handleSignInGoogle = async () => {
    await signIn("google", { callbackUrl });
  };

  return (
    <>
      <section className="lg:block hidden"></section>
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle className="text-2xl">{dict.title}</CardTitle>
          </CardHeader>
          <CardFooter>
            <Button className="w-full" onClick={handleSignInEntraID}>
              Microsoft EntraID
            </Button>
          </CardFooter>
          <CardFooter>
            <Button className="w-full" onClick={handleSignInGitHub}>
              GitHub
            </Button>
          </CardFooter>
          <CardFooter>
            <Button className="w-full" onClick={handleSignInGoogle}>
              Google
            </Button>
          </CardFooter>
        </Card>
      </div>
      <section className="lg:block hidden"></section>
    </>
  );
};

export default SignInClient;

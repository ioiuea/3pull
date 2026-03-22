import { VerifyEmailForm } from '~/components/authentication/verify-email-form';

const VerifyEmailPage = () => {
  return (
    <div className="bg-muted flex min-h-svh flex-col items-center justify-center gap-6 p-6 md:p-10">
      <div className="flex w-full max-w-md flex-col gap-6">
        <VerifyEmailForm />
      </div>
    </div>
  );
};

export default VerifyEmailPage;

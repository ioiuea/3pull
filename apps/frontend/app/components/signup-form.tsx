import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { cn } from '~/lib/utils';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import { Field, FieldDescription, FieldGroup, FieldLabel } from '~/components/ui/field';
import { Input } from '~/components/ui/input';
import { backendFetch } from '~/lib/api-helper';
import { isSupportedLanguage } from '~/lib/i18n';

type SignupResponse = {
  status: 'verification_required';
  debug_verification_token?: string | null;
};

export function SignupForm({ className, ...props }: React.ComponentProps<'div'>) {
  const navigate = useNavigate();
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [verificationToken, setVerificationToken] = useState('');
  const [issuedToken, setIssuedToken] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (password !== confirmPassword) {
      setErrorMessage('Password confirmation does not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await backendFetch('/auth/email/signup', {
        method: 'POST',
        body: JSON.stringify({
          email,
          password,
          display_name: name || null,
        }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { detail?: { message?: string } }
          | null;
        throw new Error(payload?.detail?.message ?? `Signup failed (${response.status})`);
      }
      const payload = (await response.json()) as SignupResponse;
      setIssuedToken(payload.debug_verification_token ?? null);
      setSuccessMessage('Signup completed. Verify your email token to continue.');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Signup failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const onVerify = async () => {
    setIsVerifying(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const token = verificationToken || issuedToken;
      if (!token) {
        throw new Error('Verification token is required.');
      }
      const response = await backendFetch('/auth/email/verify', {
        method: 'POST',
        body: JSON.stringify({ token }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { detail?: { message?: string } }
          | null;
        throw new Error(payload?.detail?.message ?? `Verify failed (${response.status})`);
      }
      setSuccessMessage('Email verified. Please sign in.');
      navigate(`/${currentLanguage}/login`, { replace: true });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Verification failed');
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className={cn('flex flex-col gap-6', className)} {...props}>
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Create your account</CardTitle>
          <CardDescription>Enter your email below to create your account</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="name">Full Name</FieldLabel>
                <Input
                  id="name"
                  type="text"
                  placeholder="John Doe"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="email">Email</FieldLabel>
                <Input
                  id="email"
                  type="email"
                  placeholder="m@example.com"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="password">Password</FieldLabel>
                <Input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="confirm-password">Confirm Password</FieldLabel>
                <Input
                  id="confirm-password"
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                />
              </Field>
              <FieldDescription>Must be at least 10 characters and satisfy complexity rules.</FieldDescription>
              {errorMessage && <FieldDescription className="text-destructive">{errorMessage}</FieldDescription>}
              {successMessage && <FieldDescription>{successMessage}</FieldDescription>}
              <Field>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? 'Creating...' : 'Create Account'}
                </Button>
                <FieldDescription className="text-center">
                  Already have an account? <Link to={`/${currentLanguage}/login`}>Sign in</Link>
                </FieldDescription>
              </Field>
            </FieldGroup>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Email verification</CardTitle>
          <CardDescription>
            Use the token from your email. In local debug mode, token can appear after signup.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            placeholder="Verification token"
            value={verificationToken}
            onChange={(event) => setVerificationToken(event.target.value)}
          />
          {issuedToken && (
            <FieldDescription>
              Debug token: <code>{issuedToken}</code>
            </FieldDescription>
          )}
          <Button type="button" variant="outline" onClick={onVerify} disabled={isVerifying}>
            {isVerifying ? 'Verifying...' : 'Verify Email'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

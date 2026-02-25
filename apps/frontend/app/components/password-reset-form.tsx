import { useState } from 'react';
import { Link, useParams } from 'react-router';
import { cn } from '~/lib/utils';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import { Field, FieldDescription, FieldGroup, FieldLabel } from '~/components/ui/field';
import { Input } from '~/components/ui/input';
import { backendFetch } from '~/lib/api-helper';
import { isSupportedLanguage } from '~/lib/i18n';

export function PasswordResetForm({ className, ...props }: React.ComponentProps<'div'>) {
  const { lng } = useParams();
  const currentLanguage = lng && isSupportedLanguage(lng) ? lng : 'en';

  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [requestMessage, setRequestMessage] = useState<string | null>(null);
  const [confirmMessage, setConfirmMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isRequesting, setIsRequesting] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);

  const onRequestReset = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setConfirmMessage(null);
    setRequestMessage(null);

    try {
      setIsRequesting(true);
      const response = await backendFetch('/auth/password/reset/request', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { detail?: { message?: string } }
          | null;
        throw new Error(payload?.detail?.message ?? `Request failed (${response.status})`);
      }
      const payload = (await response.json().catch(() => null)) as
        | { debug_reset_token?: string | null }
        | null;
      if (payload?.debug_reset_token) {
        setToken(payload.debug_reset_token);
      }
      setRequestMessage('If the account exists, a reset token has been issued.');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to request reset');
    } finally {
      setIsRequesting(false);
    }
  };

  const onConfirmReset = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setConfirmMessage(null);

    if (newPassword !== confirmPassword) {
      setErrorMessage('New password and confirmation do not match.');
      return;
    }

    try {
      setIsConfirming(true);
      const response = await backendFetch('/auth/password/reset/confirm', {
        method: 'POST',
        body: JSON.stringify({
          token,
          new_password: newPassword,
        }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { detail?: { message?: string } }
          | null;
        throw new Error(payload?.detail?.message ?? `Reset failed (${response.status})`);
      }
      setConfirmMessage('Password has been reset. Please log in with your new password.');
      setNewPassword('');
      setConfirmPassword('');
      setToken('');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to reset password');
    } finally {
      setIsConfirming(false);
    }
  };

  return (
    <div className={cn('flex flex-col gap-6', className)} {...props}>
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Reset Password</CardTitle>
          <CardDescription>Request a reset token, then set a new password.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <form onSubmit={onRequestReset}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="reset-email">Email</FieldLabel>
                <Input
                  id="reset-email"
                  type="email"
                  placeholder="m@example.com"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </Field>
              <Field>
                <Button type="submit" disabled={isRequesting}>
                  {isRequesting ? 'Requesting...' : 'Request reset'}
                </Button>
              </Field>
            </FieldGroup>
          </form>

          <form onSubmit={onConfirmReset}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="reset-token">Reset Token</FieldLabel>
                <Input
                  id="reset-token"
                  type="text"
                  required
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="new-password">New Password</FieldLabel>
                <Input
                  id="new-password"
                  type="password"
                  required
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                />
                <FieldDescription>
                  At least 10 chars, and include at least 3 of: upper/lower/digit/symbol.
                </FieldDescription>
              </Field>
              <Field>
                <FieldLabel htmlFor="confirm-new-password">Confirm New Password</FieldLabel>
                <Input
                  id="confirm-new-password"
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                />
              </Field>
              <Field>
                <Button type="submit" disabled={isConfirming}>
                  {isConfirming ? 'Updating...' : 'Reset password'}
                </Button>
                <FieldDescription className="text-center">
                  <Link to={`/${currentLanguage}/login`}>Back to login</Link>
                </FieldDescription>
              </Field>
            </FieldGroup>
          </form>

          {requestMessage && <p className="text-sm text-muted-foreground">{requestMessage}</p>}
          {confirmMessage && <p className="text-sm text-emerald-600">{confirmMessage}</p>}
          {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}
        </CardContent>
      </Card>
    </div>
  );
}


import useSWR from 'swr';
import { getMe } from '~/lib/api-helper';

/**
 * 現在ログイン中ユーザーを取得する SWR フック.
 *
 * - 未ログイン時は `null`
 * - 取得失敗時は `error`
 */
export const useMe = () =>
  useSWR('auth-me', getMe, {
    revalidateOnFocus: false,
  });

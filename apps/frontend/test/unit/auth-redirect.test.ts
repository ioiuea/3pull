import { describe, expect, it } from 'vitest';
import { sanitizeReturnTo } from '~/lib/auth-redirect';

describe('sanitizeReturnTo', () => {
  it('returns fallback for missing values', () => {
    expect(sanitizeReturnTo(null, { currentLanguage: 'ja' })).toBe('/ja');
  });

  it('keeps safe relative paths', () => {
    expect(
      sanitizeReturnTo('/ja/profile-sample?tab=1', {
        currentLanguage: 'ja',
      }),
    ).toBe('/ja/profile-sample?tab=1');
  });

  it('drops external urls and disallowed paths', () => {
    expect(
      sanitizeReturnTo('https://example.com/evil', {
        currentLanguage: 'ja',
        disallowedPaths: ['/ja/login'],
      }),
    ).toBe('/ja');

    expect(
      sanitizeReturnTo('/ja/login', {
        currentLanguage: 'ja',
        disallowedPaths: ['/ja/login'],
      }),
    ).toBe('/ja');
  });
});

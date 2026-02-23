import { http, HttpResponse } from 'msw';

/**
 * Test handlers for API mocking.
 * Add endpoint-specific handlers here as test coverage expands.
 */
export const handlers = [http.get('/health', () => HttpResponse.json({ ok: true }))];

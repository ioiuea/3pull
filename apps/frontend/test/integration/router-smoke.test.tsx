import { describe, expect, it } from 'vitest';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { render, screen } from '@testing-library/react';

const TestPage = () => <h1>Integration Route</h1>;

describe('router integration smoke', () => {
  it('renders route element via memory router', () => {
    const router = createMemoryRouter([{ path: '/', element: <TestPage /> }], {
      initialEntries: ['/'],
    });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole('heading', { name: 'Integration Route' })).toBeInTheDocument();
  });
});

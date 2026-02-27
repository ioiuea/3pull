import { describe, expect, it } from 'vitest';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { render, screen } from '@testing-library/react';

const TestPage = () => <h1>Integration Route</h1>;

describe('router integration smoke', () => {
  it('renders route element via memory router', () => {
    // 目的: ルーター統合時に route element が描画される基本導線を固定する。
    // 条件: "/" に TestPage を割り当てた memory router を render する。
    // 期待値: 見出し "Integration Route" が document 上に存在する。
    const router = createMemoryRouter([{ path: '/', element: <TestPage /> }], {
      initialEntries: ['/'],
    });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole('heading', { name: 'Integration Route' })).toBeInTheDocument();
  });
});

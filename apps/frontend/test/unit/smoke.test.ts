import { describe, expect, it } from 'vitest';

describe('unit smoke', () => {
  it('runs test environment', () => {
    // 目的: Vitest の最小実行経路が CI/ローカルで壊れていないことを確認する。
    // 条件: 固定の真値アサーションのみを実行する。
    // 期待値: テストランナーが正常起動し、このテストが成功する。
    expect(true).toBe(true);
  });
});

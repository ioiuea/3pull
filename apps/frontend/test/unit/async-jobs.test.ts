import { describe, expect, it } from 'vitest';
import { isRunningAsyncJobStatus } from '~/lib/async-jobs';

describe('async-jobs utility', () => {
  it('returns true only for queued/running', () => {
    // 目的: グローバルジョブ表示の「実行中判定」仕様を固定する。
    // 条件: 主要ステータス（queued/running/succeeded/failed/expired/unknown）を渡す。
    // 期待値: queued/running のみ true、それ以外は false。
    expect(isRunningAsyncJobStatus('queued')).toBe(true);
    expect(isRunningAsyncJobStatus('running')).toBe(true);
    expect(isRunningAsyncJobStatus('succeeded')).toBe(false);
    expect(isRunningAsyncJobStatus('failed')).toBe(false);
    expect(isRunningAsyncJobStatus('expired')).toBe(false);
    expect(isRunningAsyncJobStatus('unknown')).toBe(false);
  });
});

import { create } from 'zustand';

type NumberSampleStoreState = {
  count: number;
  increment: () => void;
  decrement: () => void;
  setCount: (value: number) => void;
  reset: () => void;
};

const initialState = {
  count: 1,
} satisfies Pick<NumberSampleStoreState, 'count'>;

/**
 * 数値ステートのサンプルストアです。
 */
export const useNumberSampleStore = create<NumberSampleStoreState>((set) => ({
  ...initialState,
  increment: () => set((state) => ({ count: state.count + 1 })),
  decrement: () => set((state) => ({ count: state.count - 1 })),
  setCount: (value) => set({ count: value }),
  reset: () => set({ ...initialState }),
}));

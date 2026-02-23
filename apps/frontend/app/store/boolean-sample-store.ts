import { create } from "zustand";

type BooleanSampleStoreState = {
  isPublished: boolean;
  togglePublished: () => void;
  reset: () => void;
};

const initialState = {
  isPublished: true,
} satisfies Pick<BooleanSampleStoreState, "isPublished">;

/**
 * 真偽値ステートのサンプルストアです。
 */
export const useBooleanSampleStore = create<BooleanSampleStoreState>((set) => ({
  ...initialState,
  togglePublished: () => set((state) => ({ isPublished: !state.isPublished })),
  reset: () => set({ ...initialState }),
}));

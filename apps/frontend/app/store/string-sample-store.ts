import { create } from "zustand";

type StringSampleStoreState = {
  message: string;
  setMessage: (value: string) => void;
  reset: () => void;
};

const initialState = {
  message: "Hello from Zustand",
} satisfies Pick<StringSampleStoreState, "message">;

/**
 * 文字列ステートのサンプルストアです。
 */
export const useStringSampleStore = create<StringSampleStoreState>((set) => ({
  ...initialState,
  setMessage: (value) => set({ message: value }),
  reset: () => set({ ...initialState }),
}));

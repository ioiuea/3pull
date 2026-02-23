import { create } from 'zustand';

type SampleProfile = {
  name: string;
  role: string;
};

type ObjectSampleStoreState = {
  profile: SampleProfile;
  setProfileName: (value: string) => void;
  setProfileRole: (value: string) => void;
  reset: () => void;
};

const initialState = {
  profile: {
    name: '3pull User',
    role: 'Developer',
  },
} satisfies Pick<ObjectSampleStoreState, 'profile'>;

/**
 * オブジェクトステートのサンプルストアです。
 */
export const useObjectSampleStore = create<ObjectSampleStoreState>((set) => ({
  ...initialState,
  setProfileName: (value) => set((state) => ({ profile: { ...state.profile, name: value } })),
  setProfileRole: (value) => set((state) => ({ profile: { ...state.profile, role: value } })),
  reset: () => set({ ...initialState }),
}));

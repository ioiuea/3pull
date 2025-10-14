'use client'

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

interface DemoState {
  count: number // (important-comment)
  increment: () => void
  decrement: () => void
  resetCount: () => void
  
  text: string // (important-comment)
  setText: (text: string) => void
  clearText: () => void
  
  user: { // (important-comment)
    name: string
    email: string
  }
  setUserName: (name: string) => void
  setUserEmail: (email: string) => void
  resetUser: () => void
}

const initialUser = {
  name: '',
  email: ''
}

export const useDemoStore = create<DemoState>()(
  devtools(
    (set) => ({
      count: 0, // (important-comment)
      increment: () => set((state) => ({ count: state.count + 1 })),
      decrement: () => set((state) => ({ count: state.count - 1 })),
      resetCount: () => set({ count: 0 }),
      
      text: '', // (important-comment)
      setText: (text) => set({ text }),
      clearText: () => set({ text: '' }),
      
      user: initialUser, // (important-comment)
      setUserName: (name) => set((state) => ({ user: { ...state.user, name } })),
      setUserEmail: (email) => set((state) => ({ user: { ...state.user, email } })),
      resetUser: () => set({ user: initialUser }),
    }),
    { name: 'DemoStore' }
  )
)

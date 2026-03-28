/**
 * context/AuthContext.tsx
 * Global auth state — Google login, logout, user info
 */
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react"
import { API_BASE } from "../api/config"

export interface UserInfo {
  id: number; username: string; email: string
  first_name: string; picture?: string
  tier: string; plan: any
  is_staff?: boolean; is_superuser?: boolean
  can_use_portfolio?: boolean
}

interface AuthCtx {
  user: UserInfo | null
  token: string | null
  loading: boolean
  loginWithGoogle: (idToken: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthCtx>({
  user: null, token: null, loading: true,
  loginWithGoogle: async () => {}, logout: () => {},
})

export function useAuth() { return useContext(AuthContext) }

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser]       = useState<UserInfo | null>(null)
  const [token, setToken]     = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const saved = localStorage.getItem("sr_token")
    if (saved) {
      setToken(saved)
      fetchMe(saved).finally(() => setLoading(false))
    } else { setLoading(false) }
  }, [])

  const fetchMe = useCallback(async (tok: string) => {
    try {
      const res = await fetch(`${API_BASE}/auth/me/`, {
        headers: { Authorization: `Token ${tok}` }
      })
      if (res.ok) {
        const d = await res.json()
        if (d.authenticated) setUser(d)
        else { localStorage.removeItem("sr_token"); setToken(null) }
      } else { localStorage.removeItem("sr_token"); setToken(null) }
    } catch { localStorage.removeItem("sr_token"); setToken(null) }
  }, [])

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const res = await fetch(`${API_BASE}/auth/google/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_token: idToken }),
    })
    if (!res.ok) throw new Error("Google login failed")
    const d = await res.json()
    localStorage.setItem("sr_token", d.token)
    setToken(d.token); setUser(d.user)
  }, [])

  const logout = useCallback(() => {
    if (token) {
      fetch(`${API_BASE}/auth/logout/`, {
        method:"POST", headers:{ Authorization:`Token ${token}` }
      }).catch(() => {})
    }
    localStorage.removeItem("sr_token")
    setToken(null); setUser(null)
  }, [token])

  return (
    <AuthContext.Provider value={{ user, token, loading, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

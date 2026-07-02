import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation } from "@tanstack/react-query"
import { login } from "../api/queries"
import { useAuthStore } from "../store/auth"

export default function Login() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const setTokens = useAuthStore((s) => s.setTokens)
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: () => login(username, password),
    onSuccess: (data) => {
      setTokens(data.access, data.refresh)
      navigate("/")
    },
  })

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">Zetrix</h1>
          <p className="text-slate-400 mt-1">Bali Market Analyzer</p>
        </div>
        <div className="bg-surface border border-slate-700 rounded-2xl p-8">
          <h2 className="text-xl font-semibold mb-6">Sign in</h2>
          {mutation.isError && (
            <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm rounded-lg px-4 py-3 mb-4">
              Invalid username or password
            </div>
          )}
          <form
            onSubmit={(e) => { e.preventDefault(); mutation.mutate() }}
            className="flex flex-col gap-4"
          >
            <div>
              <label className="text-xs text-slate-400 uppercase tracking-widest block mb-1">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-brand-light"
                required
                autoFocus
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 uppercase tracking-widest block mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-brand-light"
                required
              />
            </div>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="mt-2 bg-brand hover:bg-brand-light disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors"
            >
              {mutation.isPending ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

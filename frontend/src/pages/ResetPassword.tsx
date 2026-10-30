import { useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { useMutation } from "@tanstack/react-query"
import { confirmPasswordReset } from "../api/queries"

export default function ResetPassword() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const uid = params.get("uid") ?? ""
  const token = params.get("token") ?? ""
  const [password, setPassword] = useState("")

  const mutation = useMutation({
    mutationFn: () => confirmPasswordReset(uid, token, password),
    onSuccess: () => setTimeout(() => navigate("/login"), 1500),
  })

  const errorMessage = (() => {
    const data = (mutation.error as any)?.response?.data
    if (!data) return null
    const first = Object.values(data)[0]
    return Array.isArray(first) ? String(first[0]) : String(first)
  })()

  if (!uid || !token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-slate-400 text-sm">
        This reset link is invalid. <Link to="/forgot-password" className="text-brand-light hover:underline ml-1">Request a new one</Link>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">Zetrix</h1>
          <p className="text-slate-400 mt-1">Global Opportunity Explorer</p>
        </div>
        <div className="bg-surface border border-slate-700 rounded-2xl p-8">
          <h2 className="text-xl font-semibold mb-6">Choose a new password</h2>
          {mutation.isSuccess ? (
            <p className="text-sm text-emerald-400">Password reset — redirecting to sign in...</p>
          ) : (
            <form
              onSubmit={(e) => { e.preventDefault(); mutation.mutate() }}
              className="flex flex-col gap-4"
            >
              {mutation.isError && (
                <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm rounded-lg px-4 py-3">
                  {errorMessage ?? "Could not reset password"}
                </div>
              )}
              <div>
                <label className="text-xs text-slate-400 uppercase tracking-widest block mb-1">
                  New password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-brand-light"
                  required
                  autoFocus
                />
              </div>
              <button
                type="submit"
                disabled={mutation.isPending}
                className="mt-2 bg-brand hover:bg-brand-light disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors"
              >
                {mutation.isPending ? "Saving..." : "Reset password"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}

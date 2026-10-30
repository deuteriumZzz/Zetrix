import { useState } from "react"
import { Link } from "react-router-dom"
import { useMutation } from "@tanstack/react-query"
import { requestPasswordReset } from "../api/queries"

export default function ForgotPassword() {
  const [email, setEmail] = useState("")
  const mutation = useMutation({ mutationFn: () => requestPasswordReset(email) })

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">Zetrix</h1>
          <p className="text-slate-400 mt-1">Global Opportunity Explorer</p>
        </div>
        <div className="bg-surface border border-slate-700 rounded-2xl p-8">
          <h2 className="text-xl font-semibold mb-2">Reset your password</h2>
          {mutation.isSuccess ? (
            <p className="text-sm text-emerald-400 mt-4">
              If that email is registered, a reset link has been sent.
            </p>
          ) : (
            <>
              <p className="text-sm text-slate-400 mb-6">
                Enter the email on your account and we'll send a reset link.
              </p>
              <form
                onSubmit={(e) => { e.preventDefault(); mutation.mutate() }}
                className="flex flex-col gap-4"
              >
                <div>
                  <label className="text-xs text-slate-400 uppercase tracking-widest block mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
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
                  {mutation.isPending ? "Sending..." : "Send reset link"}
                </button>
              </form>
            </>
          )}
          <p className="text-center text-sm text-slate-400 mt-6">
            <Link to="/login" className="text-brand-light hover:underline">
              Back to sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

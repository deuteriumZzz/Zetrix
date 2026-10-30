import { useQuery, useMutation } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { getPlans, getMyPlan, createCheckoutSession } from "../api/queries"
import { useAuthStore } from "../store/auth"

export default function Pricing() {
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.accessToken)
  const { data: plans = [], isLoading } = useQuery({ queryKey: ["plans"], queryFn: getPlans })
  const { data: myPlan } = useQuery({
    queryKey: ["my-plan"],
    queryFn: getMyPlan,
    enabled: !!token,
  })

  const checkoutMut = useMutation({
    mutationFn: (planId: string) => createCheckoutSession(planId),
    onSuccess: (data) => window.location.assign(data.checkout_url),
  })

  const errorMessage = (checkoutMut.error as any)?.response?.data?.detail as string | undefined

  return (
    <div className="min-h-screen bg-slate-900 px-6 py-12 max-w-4xl mx-auto">
      <div className="text-center mb-10">
        <h1 className="text-2xl font-bold text-white mb-2">Pricing</h1>
        <p className="text-slate-400 text-sm">Start free. Upgrade when you need more alerts, reports, and full business-climate access.</p>
      </div>

      {checkoutMut.isError && (
        <div className="max-w-md mx-auto mb-6 bg-amber-900/20 border border-amber-700/50 text-amber-200 text-sm rounded-xl px-4 py-3 text-center">
          {errorMessage ?? "Could not start checkout."}
        </div>
      )}

      {isLoading ? (
        <div className="text-center text-slate-500">Loading...</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-2xl mx-auto">
          {plans.map((plan) => {
            const isCurrent = myPlan?.plan.id === plan.id
            return (
              <div
                key={plan.id}
                className={`rounded-2xl border p-6 flex flex-col gap-4 ${
                  plan.price_usd_monthly !== "0.00"
                    ? "bg-brand/10 border-brand-light/50"
                    : "bg-surface border-slate-700"
                }`}
              >
                <div>
                  <h2 className="text-lg font-bold text-white">{plan.name}</h2>
                  <p className="text-3xl font-bold text-white mt-2">
                    ${parseFloat(plan.price_usd_monthly).toFixed(0)}
                    <span className="text-sm font-normal text-slate-400">/mo</span>
                  </p>
                </div>
                <ul className="text-sm text-slate-300 flex flex-col gap-2 flex-1">
                  <li>
                    {plan.max_active_alerts === 0 ? "Unlimited" : plan.max_active_alerts} price alert{plan.max_active_alerts !== 1 ? "s" : ""}
                  </li>
                  <li>
                    {plan.max_reports_per_month === 0 ? "Unlimited" : plan.max_reports_per_month} report{plan.max_reports_per_month !== 1 ? "s" : ""}/month
                  </li>
                  <li>{plan.business_climate_access ? "Full business-climate scorecards" : "Limited business-climate access"}</li>
                </ul>
                <button
                  onClick={() => {
                    if (!token) return navigate("/register")
                    checkoutMut.mutate(plan.id)
                  }}
                  disabled={isCurrent || checkoutMut.isPending}
                  className={`font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-50 ${
                    plan.price_usd_monthly !== "0.00"
                      ? "bg-brand hover:bg-brand-light text-white"
                      : "bg-slate-700 hover:bg-slate-600 text-slate-200"
                  }`}
                >
                  {isCurrent ? "Current plan" : !token ? "Sign up" : plan.price_usd_monthly === "0.00" ? "Included" : "Upgrade"}
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

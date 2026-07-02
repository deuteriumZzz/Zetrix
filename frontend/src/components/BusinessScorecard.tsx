import type { BusinessClimateProfile } from "../api/queries"

function ScoreBar({ label, score }: { label: string; score: number | null }) {
  const pct = score ?? 0
  const color = pct >= 75 ? "bg-emerald-500" : pct >= 50 ? "bg-lime-500" : pct >= 25 ? "bg-yellow-500" : "bg-orange-500"
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>{label}</span>
        <span>{score != null ? `${score}/100` : "—"}</span>
      </div>
      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function BusinessScorecard({ profile }: { profile: BusinessClimateProfile | null }) {
  if (!profile) {
    return (
      <div className="bg-surface border border-slate-700 rounded-2xl p-6 text-slate-500 text-sm">
        No reviewed business-climate data for this location yet.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="bg-surface border border-slate-700 rounded-2xl p-6 flex flex-col gap-4">
        <ScoreBar label="Foreign land ownership" score={profile.foreign_land_ownership_score} />
        <ScoreBar label="Business registration ease" score={profile.business_registration_score} />
        <ScoreBar label="Overall opportunity score" score={profile.overall_complexity_score} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-surface border border-slate-700 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-slate-200 mb-2">Foreign Land Ownership</h3>
          <p className="text-sm text-slate-400">{profile.foreign_land_ownership_summary || "—"}</p>
        </div>
        <div className="bg-surface border border-slate-700 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-slate-200 mb-2">Business Registration</h3>
          <p className="text-sm text-slate-400">{profile.business_registration_summary || "—"}</p>
          {profile.business_registration_days_estimate != null && (
            <p className="text-xs text-slate-500 mt-2">
              ~{profile.business_registration_days_estimate} days
              {profile.business_registration_cost_usd_estimate &&
                ` · ~$${profile.business_registration_cost_usd_estimate}`}
            </p>
          )}
        </div>
        <div className="bg-surface border border-slate-700 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-slate-200 mb-2">Tax Overview</h3>
          <p className="text-sm text-slate-400">{profile.tax_overview_summary || "—"}</p>
          {profile.corporate_tax_rate_pct && (
            <p className="text-xs text-slate-500 mt-2">Corporate tax: {profile.corporate_tax_rate_pct}%</p>
          )}
        </div>
        <div className="bg-surface border border-slate-700 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-slate-200 mb-2">Investor Visas</h3>
          <p className="text-sm text-slate-400">{profile.investor_visa_summary || "—"}</p>
          <div className="flex gap-2 mt-2">
            {profile.has_digital_nomad_visa && (
              <span className="text-xs bg-emerald-900/30 text-emerald-400 border border-emerald-700 px-2 py-0.5 rounded-full">
                Digital nomad visa
              </span>
            )}
            {profile.has_investor_residency_program && (
              <span className="text-xs bg-emerald-900/30 text-emerald-400 border border-emerald-700 px-2 py-0.5 rounded-full">
                Investor residency
              </span>
            )}
          </div>
        </div>
      </div>

      {profile.last_reviewed_at && (
        <p className="text-xs text-slate-600">
          Last reviewed {new Date(profile.last_reviewed_at).toLocaleDateString()}
        </p>
      )}
    </div>
  )
}

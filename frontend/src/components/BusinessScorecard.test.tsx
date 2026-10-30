import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import BusinessScorecard from "./BusinessScorecard"

describe("BusinessScorecard", () => {
  it("shows an explanatory empty state when there is no profile", () => {
    render(<BusinessScorecard profile={null} />)
    expect(screen.getByText(/No reviewed business-climate profile/i)).toBeInTheDocument()
  })

  it("shows the legal disclaimer and scores when a profile is present", () => {
    render(
      <BusinessScorecard
        profile={{
          id: "test-profile-1",
          country_iso2: "XX",
          region: null,
          foreign_land_ownership_summary: "Foreigners may lease but not own land directly.",
          foreign_land_ownership_score: 40,
          business_registration_summary: "Registration takes about two weeks.",
          business_registration_days_estimate: 14,
          business_registration_cost_usd_estimate: "500",
          business_registration_score: 70,
          tax_overview_summary: "Flat corporate tax.",
          corporate_tax_rate_pct: "20",
          personal_income_tax_top_rate_pct: "35",
          investor_visa_summary: "Investor visa available for qualifying investment.",
          has_digital_nomad_visa: true,
          has_investor_residency_program: true,
          overall_complexity_score: 65,
          sources: [],
          last_reviewed_at: null,
        }}
      />,
    )
    expect(screen.getByText(/not legal, tax, or immigration advice/i)).toBeInTheDocument()
    expect(screen.getByText("Digital nomad visa")).toBeInTheDocument()
  })
})

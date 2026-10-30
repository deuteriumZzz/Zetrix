import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import StatCard from "./StatCard"

describe("StatCard", () => {
  it("renders label and value", () => {
    render(<StatCard label="Total Listings" value="1,081" sub="across all countries" />)
    expect(screen.getByText("Total Listings")).toBeInTheDocument()
    expect(screen.getByText("1,081")).toBeInTheDocument()
    expect(screen.getByText("across all countries")).toBeInTheDocument()
  })

  it("shows a skeleton instead of the value while loading", () => {
    render(<StatCard label="Total Listings" value="1,081" loading />)
    expect(screen.queryByText("1,081")).not.toBeInTheDocument()
  })

  it("shows positive change in green with a plus sign", () => {
    render(<StatCard label="Avg Price Change" value="+2.0%" change={2} />)
    expect(screen.getByText("+2.0% vs yesterday")).toHaveClass("text-emerald-400")
  })
})

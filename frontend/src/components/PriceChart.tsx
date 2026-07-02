import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts"
import type { TrendPoint } from "../api/queries"

interface Props {
  data: TrendPoint[]
  height?: number
}

const fmtDate = (d: string) =>
  new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" })

export default function PriceChart({ data, height = 280 }: Props) {
  const chartData = data.map((d) => ({
    date: fmtDate(d.date),
    avg: parseFloat(d.avg_price_usd),
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          dataKey="date"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={(v) => `$${v}`}
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={52}
        />
        <Tooltip
          contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
          labelStyle={{ color: "#e2e8f0" }}
          formatter={(v: number) => [`$${v.toFixed(0)}/night`, "Avg Price"]}
        />
        <Line
          type="monotone"
          dataKey="avg"
          stroke="#2C5F8A"
          strokeWidth={2.5}
          dot={false}
          activeDot={{ r: 5, fill: "#3B82C4" }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

interface CategoryCount {
  category: string;
  count: number;
}

interface FailureCategoryChartProps {
  data: CategoryCount[];
}

export const FailureCategoryChart: React.FC<FailureCategoryChartProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center border-2 border-dashed border-ink/40 bg-surface-muted/20 font-mono text-xs text-ink/60">
        No evaluation results to plot yet. Run an evaluation to see category breakdown.
      </div>
    );
  }

  // Format label for display
  const formattedData = data.map((d) => ({
    name: d.category.replace(/_/g, " ").toUpperCase(),
    rawCategory: d.category,
    count: d.count,
  }));

  const getColor = (cat: string) => {
    switch (cat) {
      case "pass":
        return "#C6FF4D";
      case "retrieval_miss":
      case "unsupported_answer":
      case "unanswerable_answered":
      case "incorrect_despite_relevant_context":
        return "#FF5A52";
      case "incomplete_or_irrelevant_context":
      case "citation_error":
        return "#FFB020";
      default:
        return "#DEDAD0";
    }
  };

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={formattedData}
          margin={{ top: 10, right: 10, left: -20, bottom: 40 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#DEDAD0" vertical={false} />
          <XAxis
            dataKey="name"
            stroke="#171717"
            tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
            interval={0}
            angle={-25}
            textAnchor="end"
          />
          <YAxis
            stroke="#171717"
            tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
            allowDecimals={false}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const item = payload[0].payload;
                return (
                  <div className="bg-surface border-2 border-ink p-2 shadow-[2px_2px_0_#171717] font-mono text-xs">
                    <p className="font-bold">{item.name}</p>
                    <p className="text-ink/80">Count: {item.count} cases</p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Bar dataKey="count" stroke="#171717" strokeWidth={2}>
            {formattedData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getColor(entry.rawCategory)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

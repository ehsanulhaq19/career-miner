"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { analyticsService } from "@/services/analyticsService";
import type { AnalyticsSummary } from "@/types";

function todayISODate() {
  const t = new Date();
  const y = t.getFullYear();
  const m = String(t.getMonth() + 1).padStart(2, "0");
  const d = String(t.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function BarComparison({
  items,
  format,
}: {
  items: { label: string; value: number; color: string }[];
  format?: (n: number) => string;
}) {
  const max = Math.max(1, ...items.map((i) => i.value));
  const fmt = format ?? ((n: number) => n.toLocaleString());
  return (
    <div className="space-y-3">
      {items.map((row) => (
        <div key={row.label}>
          <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
            <span>{row.label}</span>
            <span className="font-medium text-gray-900 dark:text-white">
              {fmt(row.value)}
            </span>
          </div>
          <div className="h-2.5 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${row.color}`}
              style={{ width: `${(row.value / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

const TREND_LEGEND_BG: Record<string, string> = {
  emerald: "bg-emerald-500",
  amber: "bg-amber-500",
  rose: "bg-rose-500",
  sky: "bg-sky-500",
  violet: "bg-violet-500",
  indigo: "bg-indigo-500",
};

function DailyTrendChart({
  daily,
  keys,
  labels,
  strokeHex,
  legendKeys,
}: {
  daily: AnalyticsSummary["daily"];
  keys: (keyof AnalyticsSummary["daily"][number])[];
  labels: string[];
  strokeHex: string[];
  legendKeys: string[];
}) {
  const w = 640;
  const h = 180;
  const padL = 36;
  const padR = 12;
  const padT = 12;
  const padB = 28;
  const innerW = w - padL - padR;
  const innerH = h - padT - padB;
  const n = Math.max(1, daily.length);

  const vals: number[] = [];
  daily.forEach((row) => {
    keys.forEach((k) => vals.push(Number(row[k]) || 0));
  });
  const yMax = Math.max(1, ...vals);

  const seriesPoints = keys.map((key) =>
    daily
      .map((row, i) => {
        const v = Number(row[key]) || 0;
        const x = padL + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW);
        const y = padT + innerH - (v / yMax) * innerH;
        return `${x},${y}`;
      })
      .join(" ")
  );

  const dayLabels = daily.map((r) => r.day.slice(5));

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${w} ${h}`}
        className="w-full min-w-[320px] max-h-[220px]"
        preserveAspectRatio="xMidYMid meet"
      >
        <line
          x1={padL}
          y1={padT + innerH}
          x2={padL + innerW}
          y2={padT + innerH}
          className="stroke-gray-200 dark:stroke-gray-700"
          strokeWidth={1}
        />
        <line
          x1={padL}
          y1={padT}
          x2={padL}
          y2={padT + innerH}
          className="stroke-gray-200 dark:stroke-gray-700"
          strokeWidth={1}
        />
        {seriesPoints.map((pts, si) => (
          <polyline
            key={labels[si]}
            fill="none"
            stroke={strokeHex[si]}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
            points={pts}
          />
        ))}
        {dayLabels.map((lab, i) => {
          const x = padL + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW);
          return (
            <text
              key={`${lab}-${i}`}
              x={x}
              y={h - 6}
              textAnchor="middle"
              className="fill-gray-500 dark:fill-gray-400"
              style={{ fontSize: 10 }}
            >
              {lab}
            </text>
          );
        })}
      </svg>
      <div className="flex flex-wrap gap-4 mt-2 justify-center">
        {labels.map((lab, i) => (
          <div
            key={lab}
            className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400"
          >
            <span
              className={`w-3 h-3 rounded-sm shrink-0 ${TREND_LEGEND_BG[legendKeys[i]]}`}
            />
            {lab}
          </div>
        ))}
      </div>
    </div>
  );
}

export function DashboardAnalyticsSection() {
  const [dateFrom, setDateFrom] = useState(todayISODate);
  const [dateTo, setDateTo] = useState(todayISODate);
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await analyticsService.getSummary(dateFrom, dateTo);
      setData(res);
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo]);

  useEffect(() => {
    load();
  }, [load]);

  const summaryBars = useMemo(() => {
    if (!data) return [];
    return [
      { label: "Scrap web jobs (runs)", value: data.scrap_web_jobs_run, color: "bg-sky-500" },
      {
        label: "Scrap web records (meta)",
        value: data.scrap_web_scraped_records,
        color: "bg-sky-300",
      },
      {
        label: "Scrap client jobs (runs)",
        value: data.scrap_client_jobs_run,
        color: "bg-violet-500",
      },
      {
        label: "Scrap client records (meta)",
        value: data.scrap_client_scraped_records,
        color: "bg-violet-300",
      },
      { label: "Jobs created", value: data.jobs_created, color: "bg-emerald-500" },
      { label: "Clients created", value: data.clients_created, color: "bg-amber-500" },
      {
        label: "Applications created",
        value: data.job_applications_created,
        color: "bg-rose-500",
      },
      {
        label: "App emails (success)",
        value: data.job_application_emails_success,
        color: "bg-green-500",
      },
      {
        label: "App emails (error)",
        value: data.job_application_emails_error,
        color: "bg-red-500",
      },
      {
        label: "Workflows completed",
        value: data.workflows_completed,
        color: "bg-indigo-500",
      },
    ];
  }, [data]);

  return (
    <section className="space-y-6 pt-4 border-t border-gray-200 dark:border-gray-800">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Analytics
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Range: totals use inclusive calendar dates (UTC on server). Applications,
            emails, and workflows are scoped to your account.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
              From
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
              To
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-white"
            />
          </div>
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="rounded-lg bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white text-sm font-medium px-4 py-2"
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>
      </div>

      {!data && loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="h-24 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse"
            />
          ))}
        </div>
      ) : data ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {summaryBars.map((card) => (
              <div
                key={card.label}
                className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4"
              >
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                  {card.label}
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {card.value.toLocaleString()}
                </p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-4">
                Relative totals (range)
              </h3>
              <BarComparison items={summaryBars} />
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-4">
                Application emails
              </h3>
              <BarComparison
                items={[
                  {
                    label: "Success",
                    value: data.job_application_emails_success,
                    color: "bg-green-500",
                  },
                  {
                    label: "Error",
                    value: data.job_application_emails_error,
                    color: "bg-red-500",
                  },
                ]}
              />
            </div>
          </div>

          {data.daily.length > 0 ? (
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 space-y-8">
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-4">
                  Daily trend: career data & applications
                </h3>
                <DailyTrendChart
                  daily={data.daily}
                  keys={["jobs_created", "clients_created", "job_applications_created"]}
                  labels={["Jobs created", "Clients created", "Applications"]}
                  strokeHex={["#10b981", "#f59e0b", "#f43f5e"]}
                  legendKeys={["emerald", "amber", "rose"]}
                />
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-4">
                  Daily trend: scrap runs & workflows
                </h3>
                <DailyTrendChart
                  daily={data.daily}
                  keys={[
                    "scrap_web_jobs_run",
                    "scrap_client_jobs_run",
                    "workflows_completed",
                  ]}
                  labels={["Scrap web runs", "Scrap client runs", "Workflows done"]}
                  strokeHex={["#0ea5e9", "#8b5cf6", "#6366f1"]}
                  legendKeys={["sky", "violet", "indigo"]}
                />
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

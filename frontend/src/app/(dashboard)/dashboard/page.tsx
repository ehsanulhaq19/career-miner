"use client";

import { useEffect } from "react";
import {
  HiOutlineBriefcase,
  HiOutlineDocumentText,
  HiOutlineGlobeAlt,
} from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { fetchDashboardStats } from "@/store/slices/dashboardSlice";

function timeAgo(date: string | null): string {
  if (!date) return "Never";
  const seconds = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {[...Array(3)].map((_, i) => (
        <div
          key={i}
          className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6"
        >
          <div className="animate-pulse space-y-3">
            <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
            <div className="h-8 w-16 bg-gray-200 dark:bg-gray-700 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const dispatch = useAppDispatch();
  const { stats, loading } = useAppSelector((state) => state.dashboard);

  useEffect(() => {
    dispatch(fetchDashboardStats());
  }, [dispatch]);

  if (loading && !stats) {
    return (
      <div className="space-y-8">
        <StatsSkeleton />
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6"
            >
              <div className="animate-pulse space-y-3">
                <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-3 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-8 w-12 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const statCards = [
    {
      label: "Total Jobs Executed",
      value: stats?.total_jobs_executed ?? 0,
      icon: HiOutlineBriefcase,
      accent: "text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/30",
    },
    {
      label: "Total Job Records Fetched",
      value: stats?.total_job_records ?? 0,
      icon: HiOutlineDocumentText,
      accent: "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30",
    },
    {
      label: "Total Job Sites",
      value: stats?.total_job_sites ?? 0,
      icon: HiOutlineGlobeAlt,
      accent: "text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/30",
    },
  ];

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {statCards.map((card) => (
          <div
            key={card.label}
            className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6"
          >
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-lg ${card.accent}`}>
                <card.icon className="w-6 h-6" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">{card.label}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {card.value.toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Job Portal Overview
        </h2>
        {stats?.job_site_cards && stats.job_site_cards.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {stats.job_site_cards.map((site) => (
              <div
                key={site.id}
                className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 border-l-4 border-l-primary-500 p-6"
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    {site.name}
                  </h3>
                  <span
                    className={`rounded-full px-2 py-1 text-xs font-medium ${
                      site.is_active
                        ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                        : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                    }`}
                  >
                    {site.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 truncate mb-4">
                  {site.url}
                </p>
                <div className="flex items-end justify-between">
                  <div>
                    <p className="text-3xl font-bold text-gray-900 dark:text-white">
                      {site.total_jobs.toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Total Jobs</p>
                  </div>
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    Last scrapped: {timeAgo(site.last_scrapped as string | null)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-12 text-center">
            <HiOutlineGlobeAlt className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
            <p className="text-gray-500 dark:text-gray-400">No job sites configured yet.</p>
          </div>
        )}
      </div>
    </div>
  );
}

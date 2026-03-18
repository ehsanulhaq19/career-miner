"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { HiOutlineEnvelope, HiOutlineCpuChip } from "react-icons/hi2";
import ScrapClientsTab from "./ScrapClientsTab";
import ScrapJobsTab from "./ScrapJobsTab";

type ScrapTab = "clients" | "jobs";

export default function ScrapPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const [activeTab, setActiveTab] = useState<ScrapTab>("clients");

  const setTab = (tab: ScrapTab) => {
    setActiveTab(tab);
    router.replace(`/scrap?tab=${tab}`, { scroll: false });
  };

  useEffect(() => {
    if (tabParam === "jobs" || tabParam === "clients") {
      setActiveTab(tabParam);
    }
  }, [tabParam]);

  const tabs: { id: ScrapTab; label: string; icon: typeof HiOutlineEnvelope }[] = [
    { id: "clients", label: "Scrap Clients", icon: HiOutlineEnvelope },
    { id: "jobs", label: "Scrap Jobs", icon: HiOutlineCpuChip },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Scrap
        </h2>
        <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 p-1 bg-gray-50 dark:bg-gray-800/50">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === tab.id
                  ? "bg-white dark:bg-gray-700 text-primary-600 dark:text-primary-400 shadow-sm"
                  : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "clients" && <ScrapClientsTab />}
      {activeTab === "jobs" && <ScrapJobsTab />}
    </div>
  );
}

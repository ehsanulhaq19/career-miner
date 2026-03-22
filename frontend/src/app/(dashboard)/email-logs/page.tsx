"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { HiOutlineDocumentText } from "react-icons/hi2";
import JobEmailLogsTab from "./JobEmailLogsTab";

type EmailLogsTab = "jobs";

export default function EmailLogsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const [activeTab, setActiveTab] = useState<EmailLogsTab>("jobs");

  const setTab = (tab: EmailLogsTab) => {
    setActiveTab(tab);
    router.replace(`/email-logs?tab=${tab}`, { scroll: false });
  };

  useEffect(() => {
    if (tabParam === "jobs") {
      setActiveTab("jobs");
    }
  }, [tabParam]);

  const tabs: { id: EmailLogsTab; label: string; icon: typeof HiOutlineDocumentText }[] = [
    { id: "jobs", label: "Job Email Logs", icon: HiOutlineDocumentText },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Email Logs
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

      {activeTab === "jobs" && <JobEmailLogsTab />}
    </div>
  );
}

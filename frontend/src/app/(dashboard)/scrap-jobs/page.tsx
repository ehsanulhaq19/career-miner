"use client";

import { useEffect, useState } from "react";
import {
  HiOutlinePlay,
  HiOutlineStop,
  HiOutlineArrowPath,
  HiOutlineDocumentText,
} from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import {
  fetchScrapJobs,
  startScrapJob,
  stopScrapJob,
  resumeScrapJob,
  fetchScrapJobLogs,
} from "@/store/slices/scrapJobSlice";
import { fetchJobSites } from "@/store/slices/jobSiteSlice";
import { ScrapJob, ScrapJobLog } from "@/types";

function getStatusBadgeClass(status: string): string {
  switch (status) {
    case "pending":
      return "bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-400";
    case "in_progress":
      return "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400";
    case "completed":
      return "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400";
    case "error":
      return "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400";
    case "terminated":
      return "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400";
    case "stopped":
      return "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-400";
    default:
      return "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400";
  }
}

function formatStatus(status: string): string {
  return status.replace(/_/g, " ");
}

export default function ScrapJobsPage() {
  const dispatch = useAppDispatch();
  const { items, loading, error, logsByJobId, logsLoading } = useAppSelector(
    (state) => state.scrapJob
  );
  const { items: jobSites } = useAppSelector((state) => state.jobSite);
  const [selectedSiteId, setSelectedSiteId] = useState<number | null>(null);
  const [starting, setStarting] = useState(false);
  const [actioningId, setActioningId] = useState<number | null>(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [logsModalJobId, setLogsModalJobId] = useState<number | null>(null);

  useEffect(() => {
    dispatch(fetchJobSites());
  }, [dispatch]);

  useEffect(() => {
    dispatch(fetchScrapJobs({ limit: 100 }));
  }, [dispatch]);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const getJobSiteName = (jobSiteId: number): string => {
    const site = jobSites.find((s) => s.id === jobSiteId);
    return site?.name ?? `Site #${jobSiteId}`;
  };

  const handleStart = async () => {
    if (!selectedSiteId) return;
    setStarting(true);
    try {
      await dispatch(startScrapJob(selectedSiteId)).unwrap();
      setToast({ type: "success", text: "Scrap job started." });
      dispatch(fetchScrapJobs({ limit: 100 }));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start scrap job.";
      setToast({ type: "error", text: msg });
    } finally {
      setStarting(false);
    }
  };

  const handleStop = async (job: ScrapJob) => {
    setActioningId(job.id);
    try {
      await dispatch(stopScrapJob(job.id)).unwrap();
      setToast({ type: "success", text: "Scrap job stopped." });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to stop scrap job.";
      setToast({ type: "error", text: msg });
    } finally {
      setActioningId(null);
    }
  };

  const handleResume = async (job: ScrapJob) => {
    setActioningId(job.id);
    try {
      await dispatch(resumeScrapJob(job.id)).unwrap();
      setToast({ type: "success", text: "Scrap job resumed." });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to resume scrap job.";
      setToast({ type: "error", text: msg });
    } finally {
      setActioningId(null);
    }
  };

  const handleOpenLogs = (job: ScrapJob) => {
    setLogsModalJobId(job.id);
    dispatch(fetchScrapJobLogs(job.id));
  };

  const logsForModal: ScrapJobLog[] = logsModalJobId
    ? logsByJobId[logsModalJobId] || []
    : [];

  const activeSites = jobSites.filter((s) => s.is_active);
  const canStart = selectedSiteId && !starting;
  const hasActiveJobForSite = (siteId: number) =>
    items.some(
      (j) =>
        j.job_site_id === siteId &&
        (j.status === "pending" || j.status === "in_progress")
    );

  return (
    <div className="space-y-6">
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all ${
            toast.type === "success"
              ? "bg-green-50 dark:bg-green-900/80 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800"
              : "bg-red-50 dark:bg-red-900/80 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800"
          }`}
        >
          {toast.text}
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Scrap Jobs
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedSiteId ?? ""}
            onChange={(e) =>
              setSelectedSiteId(e.target.value ? Number(e.target.value) : null)
            }
            className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
          >
            <option value="">Select job site</option>
            {activeSites.map((site) => (
              <option
                key={site.id}
                value={site.id}
                disabled={hasActiveJobForSite(site.id)}
              >
                {site.name}
                {hasActiveJobForSite(site.id) ? " (active job)" : ""}
              </option>
            ))}
          </select>
          <button
            onClick={handleStart}
            disabled={!canStart}
            className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          >
            <HiOutlinePlay className="w-4 h-4" />
            {starting ? "Starting..." : "Start Scrap Job"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden">
        {loading && items.length === 0 ? (
          <div className="p-6 space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="animate-pulse flex items-center gap-4">
                <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-500 dark:text-gray-400">
              No scrap jobs yet. Select a job site and click &quot;Start Scrap Job&quot;.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/50 text-gray-600 dark:text-gray-400">
                  <th className="text-left px-6 py-3 font-medium">Name</th>
                  <th className="text-left px-6 py-3 font-medium">Job Site</th>
                  <th className="text-left px-6 py-3 font-medium">Status</th>
                  <th className="text-left px-6 py-3 font-medium">Created</th>
                  <th className="text-right px-6 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {items.map((job) => (
                  <tr
                    key={job.id}
                    className="text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors"
                  >
                    <td className="px-6 py-4 font-medium text-gray-900 dark:text-white">
                      {job.name}
                    </td>
                    <td className="px-6 py-4">
                      {getJobSiteName(job.job_site_id)}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`rounded-full px-2 py-1 text-xs font-medium capitalize ${getStatusBadgeClass(
                          job.status
                        )}`}
                      >
                        {formatStatus(job.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-500 dark:text-gray-400">
                      {new Date(job.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleOpenLogs(job)}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        >
                          <HiOutlineDocumentText className="w-4 h-4" />
                          Logs
                        </button>
                        {(job.status === "pending" || job.status === "in_progress") && (
                          <button
                            onClick={() => handleStop(job)}
                            disabled={actioningId === job.id}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 rounded-lg transition-colors disabled:opacity-50"
                          >
                            <HiOutlineStop className="w-4 h-4" />
                            Stop
                          </button>
                        )}
                        {job.status === "stopped" && (
                          <button
                            onClick={() => handleResume(job)}
                            disabled={actioningId === job.id}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-primary-700 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 hover:bg-primary-100 dark:hover:bg-primary-900/40 rounded-lg transition-colors disabled:opacity-50"
                          >
                            <HiOutlineArrowPath className="w-4 h-4" />
                            Resume
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {logsModalJobId !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setLogsModalJobId(null)}
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Scrap Job Logs
              </h3>
              <button
                onClick={() => setLogsModalJobId(null)}
                className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-400"
              >
                ×
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {logsLoading ? (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <div
                      key={i}
                      className="animate-pulse h-12 bg-gray-200 dark:bg-gray-700 rounded"
                    />
                  ))}
                </div>
              ) : logsForModal.length === 0 ? (
                <p className="text-gray-500 dark:text-gray-400 text-center py-8">
                  No logs yet.
                </p>
              ) : (
                <div className="space-y-3">
                  {logsForModal.map((log) => (
                    <div
                      key={log.id}
                      className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700"
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="font-medium text-gray-900 dark:text-white">
                          {log.action}
                        </span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded ${
                            log.status === "completed"
                              ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                              : log.status === "error"
                                ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                                : log.status === "in_progress"
                                  ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400"
                                  : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
                          }`}
                        >
                          {log.status}
                        </span>
                      </div>
                      {log.details && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                          {log.details}
                        </p>
                      )}
                      <p className="text-xs text-gray-500 dark:text-gray-500">
                        {new Date(log.created_at).toLocaleString()}
                        {log.progress > 0 && ` · Progress: ${log.progress}%`}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

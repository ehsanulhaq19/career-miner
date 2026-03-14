"use client";

import { useEffect, useState } from "react";
import {
  HiOutlinePlay,
  HiOutlineStop,
  HiOutlineArrowPath,
  HiOutlineDocumentText,
  HiOutlineBeaker,
  HiOutlineChevronDown,
  HiOutlineChevronRight,
} from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import {
  fetchScrapClientJobs,
  startScrapClientJob,
  testScrapClientJob,
  stopScrapClientJob,
  resumeScrapClientJob,
  fetchScrapClientLogs,
  fetchScrapClientStatus,
} from "@/store/slices/scrapClientSlice";
import { fetchCareerClients } from "@/store/slices/careerClientSlice";
import { ScrapClientJob, ScrapClientLog } from "@/types";

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

export default function ScrapClientsPage() {
  const dispatch = useAppDispatch();
  const {
    items,
    loading,
    error,
    logsByJobId,
    logsLoading,
    status: statusSummary,
  } = useAppSelector((state) => state.scrapClient);
  const { items: careerClients } = useAppSelector((state) => state.careerClient);
  const [startModalOpen, setStartModalOpen] = useState(false);
  const [startForm, setStartForm] = useState({
    client_ids: [] as number[],
    only_clients_without_emails: false,
  });
  const [starting, setStarting] = useState(false);
  const [actioningId, setActioningId] = useState<number | null>(null);
  const [toast, setToast] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [logsModalJobId, setLogsModalJobId] = useState<number | null>(null);
  const [logsSearchQuery, setLogsSearchQuery] = useState("");
  const [expandedJobLogIds, setExpandedJobLogIds] = useState<Set<number>>(
    new Set()
  );
  const [testModalOpen, setTestModalOpen] = useState(false);
  const [testForm, setTestForm] = useState({
    client_ids: [] as number[],
    only_clients_without_emails: false,
    url: "",
  });
  const [testSubmitting, setTestSubmitting] = useState(false);

  useEffect(() => {
    dispatch(fetchCareerClients({ skip: 0, limit: 500 }));
  }, [dispatch]);

  useEffect(() => {
    dispatch(fetchScrapClientJobs({ limit: 100 }));
  }, [dispatch]);

  useEffect(() => {
    dispatch(fetchScrapClientStatus());
  }, [dispatch]);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const handleStart = async () => {
    const hasClientIds = startForm.client_ids.length > 0;
    const onlyWithout = startForm.only_clients_without_emails;
    if (!hasClientIds && !onlyWithout) {
      setToast({
        type: "error",
        text: "Select client IDs or enable 'Only clients without emails'",
      });
      return;
    }
    setStarting(true);
    try {
      await dispatch(
        startScrapClientJob({
          client_ids: hasClientIds ? startForm.client_ids : null,
          only_clients_without_emails: onlyWithout,
        })
      ).unwrap();
      setToast({ type: "success", text: "Scrap client job started." });
      setStartModalOpen(false);
      setStartForm({ client_ids: [], only_clients_without_emails: false });
      dispatch(fetchScrapClientJobs({ limit: 100 }));
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to start scrap client job.";
      setToast({ type: "error", text: msg });
    } finally {
      setStarting(false);
    }
  };

  const handleStop = async (job: ScrapClientJob) => {
    setActioningId(job.id);
    try {
      await dispatch(stopScrapClientJob(job.id)).unwrap();
      setToast({ type: "success", text: "Scrap client job stopped." });
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to stop scrap client job.";
      setToast({ type: "error", text: msg });
    } finally {
      setActioningId(null);
    }
  };

  const handleResume = async (job: ScrapClientJob) => {
    setActioningId(job.id);
    try {
      await dispatch(resumeScrapClientJob(job.id)).unwrap();
      setToast({ type: "success", text: "Scrap client job resumed." });
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Failed to resume scrap client job.";
      setToast({ type: "error", text: msg });
    } finally {
      setActioningId(null);
    }
  };

  const handleOpenLogs = (job: ScrapClientJob) => {
    setLogsModalJobId(job.id);
    dispatch(fetchScrapClientLogs(job.id));
  };

  const handleTestScrapSubmit = async () => {
    const hasClientIds = testForm.client_ids.length > 0;
    const hasUrl = testForm.url.trim().length > 0;
    if (!hasClientIds && !hasUrl) {
      setToast({
        type: "error",
        text: "Select at least one client or enter a URL to crawl.",
      });
      return;
    }
    setTestSubmitting(true);
    try {
      await dispatch(
        testScrapClientJob({
          client_ids: hasClientIds ? testForm.client_ids : [],
          only_clients_without_emails: testForm.only_clients_without_emails,
          url: hasUrl ? testForm.url.trim() : null,
        })
      ).unwrap();
      setToast({ type: "success", text: "Test scrap client job started." });
      setTestModalOpen(false);
      setTestForm({ client_ids: [], only_clients_without_emails: false, url: "" });
      dispatch(fetchScrapClientJobs({ limit: 100 }));
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Failed to start test scrap client job.";
      setToast({ type: "error", text: msg });
    } finally {
      setTestSubmitting(false);
    }
  };

  const toggleStartClient = (clientId: number) => {
    setStartForm((f) => ({
      ...f,
      client_ids: f.client_ids.includes(clientId)
        ? f.client_ids.filter((id) => id !== clientId)
        : [...f.client_ids, clientId],
    }));
  };

  const toggleTestClient = (clientId: number) => {
    setTestForm((f) => ({
      ...f,
      client_ids: f.client_ids.includes(clientId)
        ? f.client_ids.filter((id) => id !== clientId)
        : [...f.client_ids, clientId],
    }));
  };

  const logsForModal: ScrapClientLog[] = logsModalJobId
    ? logsByJobId[logsModalJobId] || []
    : [];

  const filteredLogs = logsSearchQuery.trim()
    ? logsForModal.filter((log) => {
        const q = logsSearchQuery.toLowerCase();
        const actionMatch = log.action?.toLowerCase().includes(q);
        const detailsMatch = log.details?.toLowerCase().includes(q);
        const statusMatch = log.status?.toLowerCase().includes(q);
        const metaStr = JSON.stringify(log.meta_data || {}).toLowerCase();
        const metaMatch = metaStr.includes(q);
        return actionMatch || detailsMatch || statusMatch || metaMatch;
      })
    : logsForModal;

  const toggleJobLogExpand = (logId: number) => {
    setExpandedJobLogIds((prev) => {
      const next = new Set(prev);
      if (next.has(logId)) next.delete(logId);
      else next.add(logId);
      return next;
    });
  };

  const canStart =
    (startForm.client_ids.length > 0 || startForm.only_clients_without_emails) &&
    !starting;
  const hasActiveJob = items.some(
    (j) => j.status === "pending" || j.status === "in_progress"
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
          Scrap Clients
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setStartModalOpen(true)}
            disabled={hasActiveJob}
            className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <HiOutlinePlay className="w-4 h-4" />
            Start Scrap Job
          </button>
          <button
            onClick={() => setTestModalOpen(true)}
            className="flex items-center gap-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          >
            <HiOutlineBeaker className="w-4 h-4" />
            Test Scrap Job
          </button>
        </div>
      </div>

      {statusSummary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Pending
            </div>
            <div className="text-xl font-semibold text-gray-900 dark:text-white">
              {statusSummary.pending}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Processing
            </div>
            <div className="text-xl font-semibold text-blue-600 dark:text-blue-400">
              {statusSummary.processing}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Completed
            </div>
            <div className="text-xl font-semibold text-green-600 dark:text-green-400">
              {statusSummary.completed}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
            <div className="text-sm text-gray-500 dark:text-gray-400">Failed</div>
            <div className="text-xl font-semibold text-red-600 dark:text-red-400">
              {statusSummary.failed}
            </div>
          </div>
        </div>
      )}

      {startModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => !starting && setStartModalOpen(false)}
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-xl shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Start Scrap Client Job
              </h3>
            </div>
            <div className="p-6 space-y-4 overflow-y-auto flex-1">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Client IDs (optional - leave empty to use filter below)
                </label>
                <div className="max-h-40 overflow-y-auto border border-gray-300 dark:border-gray-600 rounded-lg p-2 space-y-1">
                  {careerClients.slice(0, 100).map((c) => (
                    <label
                      key={c.id}
                      className="flex items-center gap-2 cursor-pointer text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={startForm.client_ids.includes(c.id)}
                        onChange={() => toggleStartClient(c.id)}
                        className="rounded border-gray-300 dark:border-gray-600 text-primary-600"
                      />
                      <span className="text-gray-900 dark:text-white truncate">
                        {c.name || `Client #${c.id}`}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="start_only_without_emails"
                  checked={startForm.only_clients_without_emails}
                  onChange={(e) =>
                    setStartForm((f) => ({
                      ...f,
                      only_clients_without_emails: e.target.checked,
                    }))
                  }
                  className="rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                />
                <label
                  htmlFor="start_only_without_emails"
                  className="text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Only clients without emails
                </label>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-800 flex justify-end gap-2">
              <button
                onClick={() => !starting && setStartModalOpen(false)}
                disabled={starting}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleStart}
                disabled={!canStart}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {starting ? "Starting..." : "Start"}
              </button>
            </div>
          </div>
        </div>
      )}

      {testModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => !testSubmitting && setTestModalOpen(false)}
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-xl shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Test Scrap Client Job
              </h3>
            </div>
            <div className="p-6 space-y-4 overflow-y-auto flex-1">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  URL (optional - crawl this URL to fetch emails)
                </label>
                <input
                  type="url"
                  value={testForm.url}
                  onChange={(e) =>
                    setTestForm((f) => ({ ...f, url: e.target.value }))
                  }
                  placeholder="https://example.com/contact"
                  className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Client IDs (optional when URL is provided)
                </label>
                <div className="max-h-40 overflow-y-auto border border-gray-300 dark:border-gray-600 rounded-lg p-2 space-y-1">
                  {careerClients.slice(0, 100).map((c) => (
                    <label
                      key={c.id}
                      className="flex items-center gap-2 cursor-pointer text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={testForm.client_ids.includes(c.id)}
                        onChange={() => toggleTestClient(c.id)}
                        className="rounded border-gray-300 dark:border-gray-600 text-primary-600"
                      />
                      <span className="text-gray-900 dark:text-white truncate">
                        {c.name || `Client #${c.id}`}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="test_only_without_emails"
                  checked={testForm.only_clients_without_emails}
                  onChange={(e) =>
                    setTestForm((f) => ({
                      ...f,
                      only_clients_without_emails: e.target.checked,
                    }))
                  }
                  className="rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                />
                <label
                  htmlFor="test_only_without_emails"
                  className="text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Only clients without emails
                </label>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-800 flex justify-end gap-2">
              <button
                onClick={() => !testSubmitting && setTestModalOpen(false)}
                disabled={testSubmitting}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleTestScrapSubmit}
                disabled={
                  (testForm.client_ids.length === 0 && !testForm.url.trim()) ||
                  testSubmitting
                }
                className="px-4 py-2 text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {testSubmitting ? "Starting..." : "Run Test"}
              </button>
            </div>
          </div>
        </div>
      )}

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
              No scrap client jobs yet. Start a job to fetch client emails.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/50 text-gray-600 dark:text-gray-400">
                  <th className="text-left px-6 py-3 font-medium">Name</th>
                  <th className="text-left px-6 py-3 font-medium">Status</th>
                  <th className="text-left px-6 py-3 font-medium">Created</th>
                  <th className="text-left px-6 py-3 font-medium">Results</th>
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
                      {job.meta_data &&
                      (job.meta_data.completed !== undefined ||
                        job.meta_data.failed !== undefined) ? (
                        <div className="text-sm text-gray-600 dark:text-gray-400 space-y-0.5">
                          <div>
                            Completed: {job.meta_data.completed ?? "-"}
                          </div>
                          <div>Failed: {job.meta_data.failed ?? "-"}</div>
                        </div>
                      ) : (
                        <span className="text-gray-400 dark:text-gray-500">-</span>
                      )}
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
                        {(job.status === "pending" ||
                          job.status === "in_progress") && (
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
          onClick={() => {
            setLogsModalJobId(null);
            setLogsSearchQuery("");
            setExpandedJobLogIds(new Set());
          }}
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Scrap Client Job Logs
              </h3>
              <button
                onClick={() => {
                  setLogsModalJobId(null);
                  setLogsSearchQuery("");
                  setExpandedJobLogIds(new Set());
                }}
                className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-400"
              >
                ×
              </button>
            </div>
            <div className="flex-1 overflow-y-auto flex flex-col">
              {!logsLoading && logsForModal.length > 0 && (
                <div className="px-6 pt-4 pb-2">
                  <input
                    type="text"
                    value={logsSearchQuery}
                    onChange={(e) => setLogsSearchQuery(e.target.value)}
                    placeholder="Search logs..."
                    className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
                  />
                </div>
              )}
              <div className="flex-1 overflow-y-auto p-6 pt-2">
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
                ) : filteredLogs.length === 0 ? (
                  <p className="text-gray-500 dark:text-gray-400 text-center py-8">
                    No logs match your search.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {filteredLogs.map((log) => {
                      const emails = (log.meta_data?.emails as string[]) || [];
                      const hasEmails = emails.length > 0;
                      const isExpanded = expandedJobLogIds.has(log.id);
                      return (
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
                          <p className="text-xs text-gray-500 dark:text-gray-500 mb-2">
                            {new Date(log.created_at).toLocaleString()}
                            {log.progress > 0 && ` · Progress: ${log.progress}%`}
                          </p>
                          {hasEmails && (
                            <div className="mt-2 border-t border-gray-200 dark:border-gray-700 pt-2">
                              <button
                                type="button"
                                onClick={() => toggleJobLogExpand(log.id)}
                                className="flex items-center gap-1.5 text-sm font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                              >
                                {isExpanded ? (
                                  <HiOutlineChevronDown className="w-4 h-4" />
                                ) : (
                                  <HiOutlineChevronRight className="w-4 h-4" />
                                )}{" "}
                                Emails ({emails.length})
                              </button>
                              {isExpanded && (
                                <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                                  {emails.map((email, idx) => (
                                    <div
                                      key={idx}
                                      className="text-sm text-gray-700 dark:text-gray-300 font-mono"
                                    >
                                      {email}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

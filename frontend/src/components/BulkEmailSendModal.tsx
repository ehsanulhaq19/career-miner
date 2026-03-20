"use client";

import { useEffect, useState } from "react";
import {
  HiOutlineDocumentText,
  HiOutlineXMark,
} from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { setBulkEmailSendLogs } from "@/store/slices/bulkEmailSendSlice";
import { jobApplicationService } from "@/services/jobApplicationService";
import { JobApplication } from "@/types";

interface BulkEmailSendModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const CHUNK_SIZE = 100;

export default function BulkEmailSendModal({
  isOpen,
  onClose,
}: BulkEmailSendModalProps) {
  const dispatch = useAppDispatch();
  const { logsByBulkId } = useAppSelector((state) => state.bulkEmailSend);
  const [minSimilarityScore, setMinSimilarityScore] = useState(0);
  const [selectedDate, setSelectedDate] = useState(() => {
    const d = new Date();
    return d.toISOString().slice(0, 10);
  });
  const [items, setItems] = useState<JobApplication[]>([]);
  const [total, setTotal] = useState(0);
  const [fetching, setFetching] = useState(false);
  const [fetchComplete, setFetchComplete] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [sending, setSending] = useState(false);
  const [activeBulkId, setActiveBulkId] = useState<number | null>(null);
  const [logsModalOpen, setLogsModalOpen] = useState(false);
  const [logsSearchQuery, setLogsSearchQuery] = useState("");

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.addEventListener("keydown", handleEsc);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEsc);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) {
      setItems([]);
      setTotal(0);
      setFetchComplete(false);
      setSelectedIds(new Set());
    }
  }, [isOpen]);

  const handleFetch = async () => {
    if (!selectedDate) return;
    setFetching(true);
    setFetchComplete(false);
    setItems([]);
    setTotal(0);
    let allItems: JobApplication[] = [];
    let skip = 0;
    let fetchedTotal = 0;

    try {
      do {
        const data = await jobApplicationService.fetchJobApplicationsForBulkEmail(
          selectedDate,
          minSimilarityScore,
          skip,
          CHUNK_SIZE
        );
        allItems = [...allItems, ...data.items];
        fetchedTotal = data.total;
        skip += CHUNK_SIZE;
        setItems([...allItems]);
        setTotal(fetchedTotal);
      } while (
        allItems.length < fetchedTotal &&
        allItems.length > 0
      );
      setFetchComplete(true);
    } finally {
      setFetching(false);
    }
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((i) => i.id)));
    }
  };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSendEmails = async () => {
    if (selectedIds.size === 0) return;
    setSending(true);
    try {
      const result = await jobApplicationService.bulkSendJobApplicationEmails(
        Array.from(selectedIds)
      );
      setActiveBulkId(result.id);
      setLogsModalOpen(true);
      dispatch(
        setBulkEmailSendLogs({
          bulkId: result.id,
          logs: [],
        })
      );
      jobApplicationService
        .getBulkJobApplicationEmailSendLogs(result.id)
        .then((data) =>
          dispatch(
            setBulkEmailSendLogs({
              bulkId: result.id,
              logs: data.items,
            })
          )
        );
    } finally {
      setSending(false);
    }
  };

  const handleOpenLogs = (bulkId: number) => {
    setActiveBulkId(bulkId);
    setLogsModalOpen(true);
    dispatch(setBulkEmailSendLogs({ bulkId, logs: [] }));
    jobApplicationService.getBulkJobApplicationEmailSendLogs(bulkId).then(
      (data) =>
        dispatch(
          setBulkEmailSendLogs({
            bulkId,
            logs: data.items,
          })
        )
    );
  };

  const logsForModal = activeBulkId ? logsByBulkId[activeBulkId] || [] : [];
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

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div className="fixed inset-0 bg-black/50" />
      <div
        className="relative z-10 w-full max-w-5xl max-h-[90vh] flex flex-col bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-200 dark:border-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Bulk Send Emails
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <HiOutlineXMark className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-hidden flex flex-col p-6">
          <div className="flex flex-wrap items-end gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                Similarity Score (0-100)
              </label>
              <input
                type="number"
                min={0}
                max={100}
                value={minSimilarityScore}
                onChange={(e) =>
                  setMinSimilarityScore(
                    Math.min(100, Math.max(0, Number(e.target.value) || 0))
                  )
                }
                className="w-24 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                Created Date
              </label>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
            <button
              onClick={handleFetch}
              disabled={!selectedDate || fetching}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {fetching ? "Fetching..." : "Fetch"}
            </button>
          </div>

          {fetching && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Fetching job applications...
            </p>
          )}

          {fetchComplete && total > 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Total: {total} job application(s)
            </p>
          )}

          <div className="flex-1 overflow-auto border border-gray-200 dark:border-gray-700 rounded-lg">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/50 text-gray-600 dark:text-gray-400 sticky top-0">
                  <th className="text-left px-4 py-3 font-medium w-10">
                    <input
                      type="checkbox"
                      checked={
                        items.length > 0 && selectedIds.size === items.length
                      }
                      ref={(el) => {
                        if (el) {
                          const input = el as HTMLInputElement & {
                            indeterminate?: boolean;
                          };
                          input.indeterminate =
                            selectedIds.size > 0 && selectedIds.size < items.length;
                        }
                      }}
                      onChange={toggleSelectAll}
                      className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                    />
                  </th>
                  <th className="text-left px-4 py-3 font-medium">
                    Application Name
                  </th>
                  <th className="text-left px-4 py-3 font-medium">Job Name</th>
                  <th className="text-left px-4 py-3 font-medium">
                    Client Name
                  </th>
                  <th className="text-left px-4 py-3 font-medium">
                    Email Send Count
                  </th>
                  <th className="text-left px-4 py-3 font-medium">
                    To Emails
                  </th>
                  <th className="text-left px-4 py-3 font-medium">
                    Similarity Score
                  </th>
                  <th className="text-left px-4 py-3 font-medium">
                    Created At
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {items.length === 0 && !fetching ? (
                  <tr>
                    <td
                      colSpan={8}
                      className="px-4 py-8 text-center text-gray-500"
                    >
                      Select date and similarity score, then click Fetch
                    </td>
                  </tr>
                ) : (
                  items.map((app) => (
                    <tr
                      key={app.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-800/30"
                    >
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(app.id)}
                          onChange={() => toggleSelect(app.id)}
                          className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                        />
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                        {app.application_name}
                      </td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                        {app.career_job_title || "-"}
                      </td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                        {app.career_client_name || "-"}
                      </td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                        {app.email_send_count ?? 0}
                      </td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400 max-w-[200px] truncate">
                        {Array.isArray(app.to_emails)
                          ? app.to_emails.join(", ")
                          : "-"}
                      </td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                        {app.similarity_score != null
                          ? Math.round(app.similarity_score)
                          : "-"}
                      </td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                        {new Date(app.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {selectedIds.size} selected
            </span>
            <div className="flex gap-2">
              {activeBulkId && (
                <button
                  onClick={() => handleOpenLogs(activeBulkId)}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <HiOutlineDocumentText className="w-4 h-4" />
                  Logs
                </button>
              )}
              <button
                onClick={handleSendEmails}
                disabled={
                  !fetchComplete || selectedIds.size === 0 || sending
                }
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {sending ? "Sending..." : "Send Emails"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {logsModalOpen && activeBulkId && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50"
          onClick={() => {
            setLogsModalOpen(false);
            setLogsSearchQuery("");
          }}
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Bulk Email Send Logs
              </h3>
              <button
                onClick={() => {
                  setLogsModalOpen(false);
                  setLogsSearchQuery("");
                }}
                className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-400"
              >
                <HiOutlineXMark className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto flex flex-col">
              {logsForModal.length > 0 && (
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
                {logsForModal.length === 0 ? (
                  <p className="text-gray-500 dark:text-gray-400 text-center py-8">
                    No logs yet.
                  </p>
                ) : filteredLogs.length === 0 ? (
                  <p className="text-gray-500 dark:text-gray-400 text-center py-8">
                    No logs match your search.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {filteredLogs.map((log) => (
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
        </div>
      )}
    </div>
  );
}

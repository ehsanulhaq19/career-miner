"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  HiOutlineDocumentText,
  HiOutlineXMark,
} from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { setBulkCareerClientEmailLogs } from "@/store/slices/bulkCareerClientEmailSlice";
import { careerClientService } from "@/services/careerClientService";
import { resumeService } from "@/services/resumeService";
import {
  BulkCareerClientEmailSendLog,
  CareerClientEmailRow,
  EmailLog,
  Resume,
} from "@/types";

interface BulkCareerClientEmailModalProps {
  isOpen: boolean;
  onClose: () => void;
}

function rowKey(row: CareerClientEmailRow): string {
  return `${row.client_id}|${row.client_email}`;
}

export default function BulkCareerClientEmailModal({
  isOpen,
  onClose,
}: BulkCareerClientEmailModalProps) {
  const dispatch = useAppDispatch();
  const { logsByBulkId } = useAppSelector(
    (state) => state.bulkCareerClientEmail
  );
  const [sortBy, setSortBy] = useState<
    ""
    | "email_count_asc"
    | "email_count_desc"
    | "created_at_asc"
    | "created_at_desc"
  >("");
  const [items, setItems] = useState<CareerClientEmailRow[]>([]);
  const [total, setTotal] = useState(0);
  const [fetching, setFetching] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [initialLoadDone, setInitialLoadDone] = useState(false);
  const [nextPage, setNextPage] = useState(2);
  const loadMoreInFlightRef = useRef(false);
  const tableScrollRef = useRef<HTMLDivElement>(null);
  const itemsRef = useRef<CareerClientEmailRow[]>([]);
  const totalRef = useRef(0);
  const nextPageRef = useRef(2);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [sending, setSending] = useState(false);
  const [activeBulkId, setActiveBulkId] = useState<number | null>(null);
  const [logsModalOpen, setLogsModalOpen] = useState(false);
  const [logsSearchQuery, setLogsSearchQuery] = useState("");
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [resumeId, setResumeId] = useState<number | null>(null);
  const [applicationDetail, setApplicationDetail] = useState("");
  const [outreachLogs, setOutreachLogs] = useState<EmailLog[] | null>(null);
  const [outreachLogsTitle, setOutreachLogsTitle] = useState("");
  const [outreachLogsLoading, setOutreachLogsLoading] = useState(false);

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
      setInitialLoadDone(false);
      setLoadingMore(false);
      setNextPage(2);
      loadMoreInFlightRef.current = false;
      setSelectedKeys(new Set());
      setSortBy("");
      setResumeId(null);
      setApplicationDetail("");
      setOutreachLogs(null);
      setOutreachLogsTitle("");
      return;
    }
    resumeService.getResumes(0, 200, undefined, true).then((data) => {
      setResumes(data.items || []);
      if (data.items?.length && resumeId == null) {
        setResumeId(data.items[0].id);
      }
    });
  }, [isOpen]);

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);
  useEffect(() => {
    totalRef.current = total;
  }, [total]);
  useEffect(() => {
    nextPageRef.current = nextPage;
  }, [nextPage]);

  const getSortParam = useCallback(() => {
    if (sortBy === "email_count_asc") {
      return { emailCount: "asc" as const, createdAt: null };
    }
    if (sortBy === "email_count_desc") {
      return { emailCount: "desc" as const, createdAt: null };
    }
    if (sortBy === "created_at_asc") {
      return { emailCount: null, createdAt: "asc" as const };
    }
    if (sortBy === "created_at_desc") {
      return { emailCount: null, createdAt: "desc" as const };
    }
    return { emailCount: null, createdAt: null };
  }, [sortBy]);

  const handleFetch = async () => {
    setFetching(true);
    setInitialLoadDone(false);
    setLoadingMore(false);
    loadMoreInFlightRef.current = false;
    setItems([]);
    setTotal(0);
    itemsRef.current = [];
    totalRef.current = 0;
    nextPageRef.current = 2;
    setSelectedKeys(new Set());
    setNextPage(2);
    const sortParam = getSortParam();
    try {
      const data = await careerClientService.getCareerClientEmailRows(
        1,
        sortParam.emailCount,
        sortParam.createdAt
      );
      const chunk = data.items || [];
      setItems(chunk);
      setTotal(data.total);
      itemsRef.current = chunk;
      totalRef.current = data.total;
      nextPageRef.current = 2;
      setNextPage(2);
      setInitialLoadDone(true);
    } finally {
      setFetching(false);
    }
  };

  const loadMore = useCallback(async () => {
    if (loadMoreInFlightRef.current || fetching) return;
    if (itemsRef.current.length >= totalRef.current) return;
    loadMoreInFlightRef.current = true;
    setLoadingMore(true);
    const sortParam = getSortParam();
    const page = nextPageRef.current;
    try {
      const data = await careerClientService.getCareerClientEmailRows(
        page,
        sortParam.emailCount,
        sortParam.createdAt
      );
      const chunk = data.items || [];
      if (!chunk.length) {
        const loaded = itemsRef.current.length;
        setTotal(loaded);
        totalRef.current = loaded;
        return;
      }
      setTotal(data.total);
      setItems((prev) => {
        const merged = [...prev, ...chunk];
        itemsRef.current = merged;
        return merged;
      });
      totalRef.current = data.total;
      const next = page + 1;
      nextPageRef.current = next;
      setNextPage(next);
    } finally {
      setLoadingMore(false);
      loadMoreInFlightRef.current = false;
    }
  }, [fetching, getSortParam]);

  const onTableScroll = useCallback(() => {
    const el = tableScrollRef.current;
    if (!el || fetching || loadingMore) return;
    if (itemsRef.current.length >= totalRef.current) return;
    const threshold = 120;
    const { scrollTop, clientHeight, scrollHeight } = el;
    if (scrollHeight - scrollTop - clientHeight < threshold) {
      loadMore();
    }
  }, [fetching, loadingMore, loadMore]);

  useEffect(() => {
    if (!isOpen || !initialLoadDone || fetching || loadingMore) return;
    if (items.length >= total) return;
    const el = tableScrollRef.current;
    if (!el) return;
    if (el.scrollHeight <= el.clientHeight + 8) {
      loadMore();
    }
  }, [
    isOpen,
    initialLoadDone,
    fetching,
    loadingMore,
    items.length,
    total,
    loadMore,
  ]);

  const toggleSelectAll = () => {
    if (selectedKeys.size === items.length && items.length > 0) {
      setSelectedKeys(new Set());
    } else {
      setSelectedKeys(new Set(items.map(rowKey)));
    }
  };

  const toggleSelect = (row: CareerClientEmailRow) => {
    const k = rowKey(row);
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return next;
    });
  };

  const handleSendEmails = async () => {
    if (selectedKeys.size === 0 || resumeId == null) return;
    setSending(true);
    try {
      const recipients = items
        .filter((r) => selectedKeys.has(rowKey(r)))
        .map((r) => ({
          client_id: r.client_id,
          client_email: r.client_email,
        }));
      const result = await careerClientService.bulkSendCareerClientEmails(
        resumeId,
        recipients,
        applicationDetail
      );
      setActiveBulkId(result.id);
      setLogsModalOpen(true);
      dispatch(
        setBulkCareerClientEmailLogs({
          bulkId: result.id,
          logs: [],
        })
      );
      careerClientService
        .getBulkCareerClientEmailSendLogs(result.id)
        .then((data) =>
          dispatch(
            setBulkCareerClientEmailLogs({
              bulkId: result.id,
              logs: data.items,
            })
          )
        );
    } finally {
      setSending(false);
    }
  };

  const handleOpenBulkLogs = (bulkId: number) => {
    setActiveBulkId(bulkId);
    setLogsModalOpen(true);
    dispatch(setBulkCareerClientEmailLogs({ bulkId, logs: [] }));
    careerClientService.getBulkCareerClientEmailSendLogs(bulkId).then(
      (data) =>
        dispatch(
          setBulkCareerClientEmailLogs({
            bulkId,
            logs: data.items,
          })
        )
    );
  };

  const openOutreachLogs = (row: CareerClientEmailRow) => {
    setOutreachLogs([]);
    setOutreachLogsTitle(
      `${row.client_name || "Client"} · ${row.client_email}`
    );
    setOutreachLogsLoading(true);
    careerClientService
      .getCareerClientOutreachEmailLogs(row.client_id, row.client_email)
      .then((logs) => setOutreachLogs(logs))
      .finally(() => setOutreachLogsLoading(false));
  };

  const logsForModal = activeBulkId ? logsByBulkId[activeBulkId] || [] : [];
  const filteredLogs = logsSearchQuery.trim()
    ? logsForModal.filter((log: BulkCareerClientEmailSendLog) => {
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
            Bulk client outreach email
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <HiOutlineXMark className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-hidden flex flex-col p-6">
          <div className="flex flex-wrap items-end gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                Resume
              </label>
              <select
                value={resumeId ?? ""}
                onChange={(e) =>
                  setResumeId(
                    e.target.value ? Number(e.target.value) : null
                  )
                }
                className="min-w-[200px] px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                {resumes.length === 0 ? (
                  <option value="">No resumes</option>
                ) : (
                  resumes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))
                )}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                Sort
              </label>
              <select
                value={sortBy}
                onChange={(e) =>
                  setSortBy(
                    (
                      e.target.value as
                        | ""
                        | "email_count_asc"
                        | "email_count_desc"
                        | "created_at_asc"
                        | "created_at_desc"
                    ) || ""
                  )
                }
                className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value="">Default</option>
                <option value="email_count_asc">Email count ascending</option>
                <option value="email_count_desc">Email count descending</option>
                <option value="created_at_asc">Created at ascending</option>
                <option value="created_at_desc">Created at descending</option>
              </select>
            </div>
            <button
              onClick={handleFetch}
              disabled={fetching}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {fetching ? "Loading…" : "Load clients"}
            </button>
          </div>

          <div className="mb-4">
            <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
              Application detail
            </label>
            <textarea
              value={applicationDetail}
              onChange={(e) => setApplicationDetail(e.target.value)}
              rows={4}
              placeholder="Add job or application specific details for personalized outreach"
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            />
          </div>

          {fetching && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Loading career client emails…
            </p>
          )}

          {initialLoadDone && total > 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Loaded {items.length} of {total} rows · scroll down for more
            </p>
          )}

          <div
            ref={tableScrollRef}
            onScroll={onTableScroll}
            className="flex-1 min-h-[240px] overflow-auto border border-gray-200 dark:border-gray-700 rounded-lg"
          >
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/50 text-gray-600 dark:text-gray-400 sticky top-0">
                  <th className="text-left px-4 py-3 font-medium w-10">
                    <input
                      type="checkbox"
                      checked={
                        items.length > 0 &&
                        selectedKeys.size === items.length
                      }
                      ref={(el) => {
                        if (el) {
                          const input = el as HTMLInputElement & {
                            indeterminate?: boolean;
                          };
                          input.indeterminate =
                            selectedKeys.size > 0 &&
                            selectedKeys.size < items.length;
                        }
                      }}
                      onChange={toggleSelectAll}
                      className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                    />
                  </th>
                  <th className="text-left px-4 py-3 font-medium">
                    Client
                  </th>
                  <th className="text-left px-4 py-3 font-medium">Email</th>
                  <th className="text-left px-4 py-3 font-medium">Location</th>
                  <th className="text-left px-4 py-3 font-medium">
                    Created at
                  </th>
                  <th className="text-left px-4 py-3 font-medium">
                    Email sends
                  </th>
                  <th className="text-left px-4 py-3 font-medium">Logs</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {items.length === 0 && !fetching ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-4 py-8 text-center text-gray-500"
                    >
                      Choose sort options and click Load clients
                    </td>
                  </tr>
                ) : (
                  <>
                    {items.map((row) => (
                      <tr
                        key={rowKey(row)}
                        className="hover:bg-gray-50 dark:hover:bg-gray-800/30"
                      >
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={selectedKeys.has(rowKey(row))}
                            onChange={() => toggleSelect(row)}
                            className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                          />
                        </td>
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                          {row.client_name || "—"}
                        </td>
                        <td className="px-4 py-3 text-gray-600 dark:text-gray-400 max-w-[220px] truncate">
                          {row.client_email}
                        </td>
                        <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                          {row.location || "—"}
                        </td>
                        <td className="px-4 py-3 text-gray-600 dark:text-gray-400 whitespace-nowrap">
                          {new Date(row.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                          {row.email_count}
                        </td>
                        <td className="px-4 py-3">
                          <button
                            type="button"
                            onClick={() => openOutreachLogs(row)}
                            className="text-xs font-medium text-primary-600 dark:text-primary-400 hover:underline"
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                    {loadingMore && (
                      <tr>
                        <td
                          colSpan={7}
                          className="px-4 py-3 text-center text-sm text-gray-500 dark:text-gray-400"
                        >
                          Loading more…
                        </td>
                      </tr>
                    )}
                  </>
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center justify-between gap-2 flex-wrap">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {selectedKeys.size} selected
            </span>
            <div className="flex gap-2">
              {activeBulkId && (
                <button
                  type="button"
                  onClick={() => handleOpenBulkLogs(activeBulkId)}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <HiOutlineDocumentText className="w-4 h-4" />
                  Logs
                </button>
              )}
              <button
                type="button"
                onClick={handleSendEmails}
                disabled={
                  !initialLoadDone ||
                  selectedKeys.size === 0 ||
                  resumeId == null ||
                  sending
                }
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {sending ? "Sending…" : "Send emails"}
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
                Bulk send logs
              </h3>
              <button
                type="button"
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
                    placeholder="Search logs…"
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
                    No logs match.
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
                          {log.progress > 0 &&
                            ` · Progress: ${log.progress}%`}
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

      {outreachLogs !== null && (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-black/50"
          onClick={() => setOutreachLogs(null)}
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Outreach email logs · {outreachLogsTitle}
              </h3>
              <button
                type="button"
                onClick={() => setOutreachLogs(null)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <HiOutlineXMark className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {outreachLogsLoading ? (
                <div className="animate-pulse space-y-3">
                  <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded" />
                  <div className="h-4 w-2/3 bg-gray-200 dark:bg-gray-700 rounded" />
                </div>
              ) : outreachLogs.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No logs for this address yet.
                </p>
              ) : (
                <div className="space-y-4">
                  {outreachLogs.map((log) => (
                    <div
                      key={log.id}
                      className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50"
                    >
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="font-medium text-gray-900 dark:text-white">
                          {log.to_email}
                        </span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded ${
                            log.status === "success"
                              ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                              : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                          }`}
                        >
                          {log.status}
                        </span>
                      </div>
                      {log.subject && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                          {log.subject}
                        </p>
                      )}
                      <p className="text-xs text-gray-500">
                        {new Date(log.created_at).toLocaleString()}
                      </p>
                      {log.response && (
                        <p className="text-xs text-red-600 dark:text-red-400 mt-2">
                          {log.response}
                        </p>
                      )}
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

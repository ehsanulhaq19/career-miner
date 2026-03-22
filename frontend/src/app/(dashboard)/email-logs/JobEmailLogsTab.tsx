"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  HiOutlineMagnifyingGlass,
  HiOutlineXMark,
  HiOutlineChevronLeft,
  HiOutlineChevronRight,
} from "react-icons/hi2";
import { emailService, JobEmailLogItem } from "@/services/emailService";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { fetchCareerClients } from "@/store/slices/careerClientSlice";
import EmailLogDetailModal from "@/components/EmailLogDetailModal";

export default function JobEmailLogsTab() {
  const dispatch = useAppDispatch();
  const { items: clients } = useAppSelector((state) => state.careerClient);
  const [items, setItems] = useState<JobEmailLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<{
    career_client_id?: number;
    created_date_from?: string;
    created_date_to?: string;
    search?: string;
  }>({});
  const [searchInput, setSearchInput] = useState("");
  const [selectedLog, setSelectedLog] = useState<JobEmailLogItem | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    dispatch(fetchCareerClients({ skip: 0, limit: 500 }));
  }, [dispatch]);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const skip = (page - 1) * limit;
      const data = await emailService.getJobEmailLogs({
        skip,
        limit,
        career_client_id: filters.career_client_id,
        created_date_from: filters.created_date_from,
        created_date_to: filters.created_date_to,
        search: filters.search,
      });
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, [page, limit, filters]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleSearchChange = useCallback((value: string) => {
    setSearchInput(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setFilters((prev) => ({ ...prev, search: value || undefined }));
      setPage(1);
    }, 300);
  }, []);

  const handleClientFilter = (value: string) => {
    setFilters((prev) => ({
      ...prev,
      career_client_id: value ? Number(value) : undefined,
    }));
    setPage(1);
  };

  const handleDateFromChange = (value: string) => {
    setFilters((prev) => ({
      ...prev,
      created_date_from: value || undefined,
    }));
    setPage(1);
  };

  const handleDateToChange = (value: string) => {
    setFilters((prev) => ({
      ...prev,
      created_date_to: value || undefined,
    }));
    setPage(1);
  };

  const handleClearFilters = () => {
    setSearchInput("");
    setFilters({});
    setPage(1);
  };

  const totalPages = Math.ceil(total / limit);
  const hasFilters =
    filters.search ||
    filters.career_client_id ||
    filters.created_date_from ||
    filters.created_date_to;

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <HiOutlineMagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search by email, job title, client name..."
              className="w-full pl-9 pr-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
            />
          </div>
          <select
            value={filters.career_client_id ?? ""}
            onChange={(e) => handleClientFilter(e.target.value)}
            className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
          >
            <option value="">All Clients</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name || `Client #${c.id}`}
              </option>
            ))}
          </select>
          <input
            type="date"
            value={filters.created_date_from ?? ""}
            onChange={(e) => handleDateFromChange(e.target.value)}
            className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors sm:w-40"
          />
          <input
            type="date"
            value={filters.created_date_to ?? ""}
            onChange={(e) => handleDateToChange(e.target.value)}
            className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors sm:w-40"
          />
          {hasFilters && (
            <button
              onClick={handleClearFilters}
              className="flex items-center gap-1.5 border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
            >
              <HiOutlineXMark className="w-4 h-4" />
              Clear
            </button>
          )}
        </div>
      </div>

      {loading && items.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-5"
            >
              <div className="animate-pulse space-y-3">
                <div className="h-4 w-3/4 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-3 w-full bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-3 w-1/2 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-12 text-center">
          <p className="text-gray-500 dark:text-gray-400">
            {hasFilters ? "No email logs match your filters." : "No job email logs found."}
          </p>
          {hasFilters && (
            <button
              onClick={handleClearFilters}
              className="mt-3 text-sm text-primary-600 dark:text-primary-400 hover:underline"
            >
              Clear all filters
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {items.map((log) => (
              <button
                key={log.id}
                onClick={() => setSelectedLog(log)}
                className="text-left bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-5 hover:border-primary-300 dark:hover:border-primary-700 hover:shadow-md transition-all"
              >
                <h3 className="font-semibold text-gray-900 dark:text-white line-clamp-1 mb-2">
                  {log.subject}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 truncate mb-2">
                  To: {log.to_email}
                </p>
                <div className="flex items-center justify-between text-xs text-gray-400 dark:text-gray-500">
                  <span>{log.career_job_title}</span>
                  <span>{new Date(log.created_at).toLocaleDateString()}</span>
                </div>
                {log.career_client_name && (
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 truncate">
                    {log.career_client_name}
                  </p>
                )}
                <span
                  className={`inline-block mt-2 px-2 py-0.5 rounded text-xs font-medium ${
                    log.status === "success"
                      ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                      : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                  }`}
                >
                  {log.status}
                </span>
              </button>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex justify-between items-center bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 px-6 py-3">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Page {page} of {totalPages} ({total.toLocaleString()} results)
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <HiOutlineChevronLeft className="w-4 h-4" />
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                  <HiOutlineChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}

      <EmailLogDetailModal
        emailLogId={selectedLog?.id ?? null}
        isOpen={!!selectedLog}
        onClose={() => setSelectedLog(null)}
      />
    </div>
  );
}

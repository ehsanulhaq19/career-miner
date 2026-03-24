"use client";

import { useEffect, useState } from "react";
import { HiChevronLeft, HiChevronRight, HiXMark } from "react-icons/hi2";
import { careerClientService } from "@/services/careerClientService";
import { CareerClient } from "@/types";

interface CleanEmailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpdated?: () => void;
}

interface ValidationResult {
  client_id: number;
  client_name: string;
  invalid_emails: string[];
}

export default function CleanEmailsModal({
  isOpen,
  onClose,
  onUpdated,
}: CleanEmailsModalProps) {
  const [clients, setClients] = useState<CareerClient[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [selectAll, setSelectAll] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [validating, setValidating] = useState(false);
  const [results, setResults] = useState<ValidationResult[] | null>(null);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (results) setResults(null);
        else onClose();
      }
    };
    if (isOpen) {
      document.addEventListener("keydown", handleEsc);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEsc);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose, results]);

  useEffect(() => {
    if (!isOpen) return;
    setPage(1);
    setResults(null);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    const skip = (page - 1) * limit;
    careerClientService
      .getCareerClients(skip, limit, true)
      .then((data) => {
        setClients(data.items ?? []);
        setTotal(data.total ?? 0);
      })
      .finally(() => setLoading(false));
  }, [isOpen, page, limit]);

  const totalPages = Math.ceil(total / limit);

  const toggleSelectAll = () => {
    setSelectAll((prev) => !prev);
    if (selectAll) {
      setSelectedIds(new Set());
    }
  };

  const toggleClient = (id: number) => {
    if (selectAll) return;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleValidate = async () => {
    setValidating(true);
    try {
      const payload =
        selectAll
          ? { all_clients: true }
          : { client_ids: Array.from(selectedIds) };
      const data = await careerClientService.validateClientEmails(payload);
      setResults(data ?? []);
    } finally {
      setValidating(false);
    }
  };

  const handleConfirm = async () => {
    if (!results || results.length === 0) return;
    setConfirming(true);
    try {
      const clientsPayload = results.map((r) => ({
        client_id: r.client_id,
        invalid_emails: r.invalid_emails,
      }));
      await careerClientService.removeInvalidEmails(clientsPayload);
      onUpdated?.();
      onClose();
    } finally {
      setConfirming(false);
    }
  };

  const handleBackFromResults = () => {
    setResults(null);
  };

  if (!isOpen) return null;

  if (results !== null) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        onClick={results.length === 0 ? onClose : undefined}
      >
        <div className="fixed inset-0 bg-black/50" />
        <div
          className="relative z-10 w-full max-w-2xl max-h-[90vh] flex flex-col bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-200 dark:border-gray-800"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between p-6 pb-4 border-b border-gray-200 dark:border-gray-800 flex-shrink-0">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Invalid Emails Found
            </h2>
            <button
              onClick={results.length === 0 ? onClose : handleBackFromResults}
              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <HiXMark className="w-5 h-5" />
            </button>
          </div>
          <div className="p-6 overflow-auto flex-1">
            {results.length === 0 ? (
              <p className="text-gray-500 dark:text-gray-400">
                No invalid emails found.
              </p>
            ) : (
              <>
                <div className="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg">
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-800">
                      <tr>
                        <th className="px-4 py-2 text-left font-medium text-gray-700 dark:text-gray-300">
                          Client
                        </th>
                        <th className="px-4 py-2 text-left font-medium text-gray-700 dark:text-gray-300">
                          Invalid Emails
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {results.map((r) => (
                        <tr
                          key={r.client_id}
                          className="bg-white dark:bg-gray-900"
                        >
                          <td className="px-4 py-3">
                            <span className="font-medium text-gray-900 dark:text-white">
                              {r.client_name}
                            </span>
                            <span className="text-gray-500 dark:text-gray-400 ml-1">
                              (ID: {r.client_id})
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                            {r.invalid_emails.join(", ")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
                  Remove these invalid emails from the clients?
                </p>
              </>
            )}
          </div>
          {results.length > 0 && (
            <div className="p-6 pt-0 flex justify-end gap-2 flex-shrink-0">
              <button
                type="button"
                onClick={handleBackFromResults}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
              >
                Back
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={confirming}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
              >
                {confirming ? "Removing..." : "Confirm Remove"}
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div className="fixed inset-0 bg-black/50" />
      <div
        className="relative z-10 w-full max-w-4xl max-h-[90vh] flex flex-col bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-200 dark:border-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-6 pb-4 border-b border-gray-200 dark:border-gray-800 flex-shrink-0">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Clean Emails
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <HiXMark className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 overflow-auto flex-1">
          <div className="flex items-center gap-2 mb-4">
            <input
              type="checkbox"
              id="select_all_clean"
              checked={selectAll}
              onChange={toggleSelectAll}
              className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
            />
            <label
              htmlFor="select_all_clean"
              className="text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Select all clients ({total})
            </label>
          </div>
          <div className="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-2 w-10">
                    <input
                      type="checkbox"
                      checked={selectAll}
                      onChange={toggleSelectAll}
                      className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                    />
                  </th>
                  <th className="px-4 py-2 text-left font-medium text-gray-700 dark:text-gray-300">
                    Client Name
                  </th>
                  <th className="px-4 py-2 text-left font-medium text-gray-700 dark:text-gray-300">
                    Location
                  </th>
                  <th className="px-4 py-2 text-left font-medium text-gray-700 dark:text-gray-300">
                    Emails
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {loading ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                      Loading...
                    </td>
                  </tr>
                ) : clients.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                      No active clients with emails.
                    </td>
                  </tr>
                ) : (
                  clients.map((c) => (
                    <tr
                      key={c.id}
                      className={`bg-white dark:bg-gray-900 ${
                        selectAll ? "opacity-60" : ""
                      }`}
                    >
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectAll || selectedIds.has(c.id)}
                          onChange={() => toggleClient(c.id)}
                          disabled={selectAll}
                          className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500 disabled:cursor-not-allowed"
                        />
                      </td>
                      <td className="px-4 py-3 text-gray-900 dark:text-white">
                        {c.name || "Unnamed"}
                      </td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                        {c.location || "-"}
                      </td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                        {c.emails?.length
                          ? c.emails.join(", ")
                          : "-"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Page {page} of {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <HiChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <HiChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
        <div className="p-6 pt-0 flex justify-end gap-2 flex-shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleValidate}
            disabled={
              validating ||
              loading ||
              (clients.length === 0) ||
              (!selectAll && selectedIds.size === 0)
            }
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            {validating ? "Validating..." : "Validate Emails"}
          </button>
        </div>
      </div>
    </div>
  );
}

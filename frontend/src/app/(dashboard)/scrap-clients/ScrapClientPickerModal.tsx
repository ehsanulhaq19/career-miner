"use client";

import { useEffect, useRef, useState } from "react";
import { careerClientService } from "@/services/careerClientService";
import { CareerClient } from "@/types";

const PAGE_SIZE = 100;

export type ScrapClientPickerPurpose = "emails" | "details";

interface ScrapClientPickerModalProps {
  open: boolean;
  purpose: ScrapClientPickerPurpose;
  onClose: () => void;
  hasActiveJob: boolean;
  onComplete: () => void;
  onStartError: (message: string) => void;
  startJob: (clientIds: number[]) => Promise<void>;
}

export default function ScrapClientPickerModal({
  open,
  purpose,
  onClose,
  hasActiveJob,
  onComplete,
  onStartError,
  startJob,
}: ScrapClientPickerModalProps) {
  const [filterWithoutEmails, setFilterWithoutEmails] = useState(false);
  const [filterWithoutCompanyDetails, setFilterWithoutCompanyDetails] =
    useState(false);
  const [appliedFilterWithoutEmails, setAppliedFilterWithoutEmails] =
    useState(false);
  const [appliedFilterWithoutCompanyDetails, setAppliedFilterWithoutCompanyDetails] =
    useState(false);
  const [page, setPage] = useState(1);
  const [refreshKey, setRefreshKey] = useState(0);
  const [items, setItems] = useState<CareerClient[]>([]);
  const [total, setTotal] = useState(0);
  const [loadLoading, setLoadLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [dataReady, setDataReady] = useState(false);
  const headerCheckboxRef = useRef<HTMLInputElement>(null);

  const title =
    purpose === "emails"
      ? "Scrap emails for selected clients"
      : "Scrap company details for selected clients";

  useEffect(() => {
    if (!open) {
      setDataReady(false);
      setItems([]);
      setTotal(0);
      setSelected(new Set());
      setPage(1);
      setRefreshKey(0);
      setFilterWithoutEmails(false);
      setFilterWithoutCompanyDetails(false);
      setAppliedFilterWithoutEmails(false);
      setAppliedFilterWithoutCompanyDetails(false);
      return;
    }
    setFilterWithoutEmails(false);
    setFilterWithoutCompanyDetails(false);
    setAppliedFilterWithoutEmails(false);
    setAppliedFilterWithoutCompanyDetails(false);
    setPage(1);
    setSelected(new Set());
    setItems([]);
    setTotal(0);
    setDataReady(true);
    setRefreshKey((k) => k + 1);
  }, [open, purpose]);

  useEffect(() => {
    if (!open || !dataReady) return;
    let cancelled = false;
    (async () => {
      setLoadLoading(true);
      try {
        const skip = (page - 1) * PAGE_SIZE;
        const hasEmailInformation =
          purpose === "emails" && appliedFilterWithoutEmails ? false : undefined;
        const hasCompanyDetails =
          purpose === "details" && appliedFilterWithoutCompanyDetails
            ? false
            : undefined;
        const data = await careerClientService.getCareerClients(
          skip,
          PAGE_SIZE,
          hasEmailInformation,
          undefined,
          undefined,
          hasCompanyDetails
        );
        if (!cancelled) {
          setItems(data.items || []);
          setTotal(data.total ?? 0);
        }
      } finally {
        if (!cancelled) setLoadLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [
    open,
    dataReady,
    page,
    purpose,
    appliedFilterWithoutEmails,
    appliedFilterWithoutCompanyDetails,
    refreshKey,
  ]);

  const loadData = () => {
    if (purpose === "emails") {
      setAppliedFilterWithoutEmails(filterWithoutEmails);
      setAppliedFilterWithoutCompanyDetails(false);
    } else {
      setAppliedFilterWithoutCompanyDetails(filterWithoutCompanyDetails);
      setAppliedFilterWithoutEmails(false);
    }
    setPage(1);
    setRefreshKey((k) => k + 1);
  };

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const pageIds = items.map((c) => c.id);
  const allOnPageSelected =
    pageIds.length > 0 && pageIds.every((id) => selected.has(id));
  const someOnPageSelected = pageIds.some((id) => selected.has(id));

  useEffect(() => {
    const el = headerCheckboxRef.current;
    if (el) {
      el.indeterminate = someOnPageSelected && !allOnPageSelected;
    }
  }, [someOnPageSelected, allOnPageSelected, items]);

  const toggleHeader = () => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (allOnPageSelected) {
        for (const id of pageIds) next.delete(id);
      } else {
        for (const id of pageIds) next.add(id);
      }
      return next;
    });
  };

  const toggleRow = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleProceed = async () => {
    if (selected.size === 0) return;
    setSubmitting(true);
    try {
      await startJob(Array.from(selected));
      onComplete();
      onClose();
    } catch (err: unknown) {
      const msg =
        typeof err === "string"
          ? err
          : err instanceof Error
            ? err.message
            : "Failed to start job.";
      onStartError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-2"
      onClick={() => !submitting && !loadLoading && onClose()}
    >
      <div
        className="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-5xl max-h-[92vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 shrink-0">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {title}
          </h3>
        </div>

        <div className="p-4 sm:p-6 space-y-4 overflow-y-auto flex-1 min-h-0">
          <div className="flex flex-wrap items-center gap-4">
            {purpose === "emails" ? (
              <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700 dark:text-gray-300">
                <input
                  type="checkbox"
                  checked={filterWithoutEmails}
                  onChange={(e) => setFilterWithoutEmails(e.target.checked)}
                  disabled={loadLoading || submitting || hasActiveJob}
                  className="rounded border-gray-300 dark:border-gray-600 text-primary-600"
                />
                Only clients without emails
              </label>
            ) : (
              <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700 dark:text-gray-300">
                <input
                  type="checkbox"
                  checked={filterWithoutCompanyDetails}
                  onChange={(e) =>
                    setFilterWithoutCompanyDetails(e.target.checked)
                  }
                  disabled={loadLoading || submitting || hasActiveJob}
                  className="rounded border-gray-300 dark:border-gray-600 text-primary-600"
                />
                Only clients without company details
              </label>
            )}
            <button
              type="button"
              onClick={loadData}
              disabled={loadLoading || submitting || hasActiveJob}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {loadLoading ? "Loading…" : "Load clients"}
            </button>
          </div>

          {dataReady && (
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-gray-600 dark:text-gray-400">
              <span>
                {loadLoading && items.length === 0
                  ? "Loading…"
                  : `${total} client${total === 1 ? "" : "s"} total · Page ${page} of ${pageCount}`}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={page <= 1 || loadLoading || submitting}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="px-3 py-1 rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  type="button"
                  disabled={page >= pageCount || loadLoading || submitting}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1 rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}

          {dataReady && (
            <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-800/50 text-left text-gray-600 dark:text-gray-400">
                    <th className="px-3 py-2 w-10">
                      <input
                        ref={headerCheckboxRef}
                        type="checkbox"
                        checked={allOnPageSelected}
                        onChange={toggleHeader}
                        disabled={items.length === 0 || submitting}
                        className="rounded border-gray-300 dark:border-gray-600 text-primary-600"
                      />
                    </th>
                    <th className="px-3 py-2 font-medium">Name</th>
                    <th className="px-3 py-2 font-medium">Website</th>
                    {purpose === "emails" ? (
                      <th className="px-3 py-2 font-medium">Emails</th>
                    ) : (
                      <th className="px-3 py-2 font-medium">Company detail</th>
                    )}
                    <th className="px-3 py-2 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                  {items.length === 0 && !loadLoading ? (
                    <tr>
                      <td
                        colSpan={5}
                        className="px-3 py-8 text-center text-gray-500 dark:text-gray-400"
                      >
                        No clients on this page.
                      </td>
                    </tr>
                  ) : (
                    items.map((c) => (
                      <tr
                        key={c.id}
                        className="text-gray-800 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/40"
                      >
                        <td className="px-3 py-2">
                          <input
                            type="checkbox"
                            checked={selected.has(c.id)}
                            onChange={() => toggleRow(c.id)}
                            disabled={submitting}
                            className="rounded border-gray-300 dark:border-gray-600 text-primary-600"
                          />
                        </td>
                        <td className="px-3 py-2 font-medium">
                          {c.name || `Client #${c.id}`}
                        </td>
                        <td className="px-3 py-2 max-w-[180px] truncate">
                          {c.official_website || "—"}
                        </td>
                        {purpose === "emails" ? (
                          <td className="px-3 py-2 max-w-[220px]">
                            {(c.emails?.length ?? 0) === 0 ? (
                              <span className="text-gray-400">—</span>
                            ) : (
                              <span className="break-words line-clamp-2">
                                {c.emails!.join(", ")}
                              </span>
                            )}
                          </td>
                        ) : (
                          <td className="px-3 py-2 max-w-[280px]">
                            {c.detail?.trim() ? (
                              <span className="break-words line-clamp-2">
                                {c.detail}
                              </span>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                          </td>
                        )}
                        <td className="px-3 py-2 text-gray-500 dark:text-gray-400 whitespace-nowrap">
                          {c.created_at
                            ? new Date(c.created_at).toLocaleString()
                            : "—"}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {dataReady && loadLoading && items.length === 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Fetching clients…
            </p>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-800 flex justify-end gap-2 shrink-0">
          <button
            type="button"
            onClick={() => !submitting && !loadLoading && onClose()}
            disabled={submitting}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleProceed()}
            disabled={
              submitting || selected.size === 0 || hasActiveJob || !dataReady
            }
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Starting…" : "Start"}
          </button>
        </div>
      </div>
    </div>
  );
}

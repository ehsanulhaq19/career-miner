"use client";

import { Fragment, useEffect, useState } from "react";
import {
  HiOutlineChevronDown,
  HiOutlineChevronRight,
  HiOutlineXMark,
} from "react-icons/hi2";
import { jobApplicationService } from "@/services/jobApplicationService";
import { JobApplication, JobApplicationDateGroup } from "@/types";

interface BulkJobApplicationEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApplied: () => void;
}

const CHUNK_SIZE = 100;

export default function BulkJobApplicationEditModal({
  isOpen,
  onClose,
  onApplied,
}: BulkJobApplicationEditModalProps) {
  const [dateGroups, setDateGroups] = useState<JobApplicationDateGroup[]>([]);
  const [expandedDates, setExpandedDates] = useState<Set<string>>(new Set());
  const [applicationsByDate, setApplicationsByDate] = useState<
    Record<string, JobApplication[]>
  >({});
  const [loadingDates, setLoadingDates] = useState(false);
  const [loadingApps, setLoadingApps] = useState<Record<string, boolean>>({});
  const [selectedApplicationIds, setSelectedApplicationIds] = useState<
    Set<number>
  >(() => new Set());
  const [isActiveTarget, setIsActiveTarget] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      setDateGroups([]);
      setExpandedDates(new Set());
      setApplicationsByDate({});
      setSelectedApplicationIds(new Set());
      setError(null);
      setIsActiveTarget(true);
      return;
    }
    setLoadingDates(true);
    jobApplicationService
      .getJobApplicationDatesGrouped(0, 50)
      .then((data) => {
        setDateGroups(data.items);
      })
      .finally(() => setLoadingDates(false));
  }, [isOpen]);

  const fetchApplicationsForDate = async (
    dateStr: string
  ): Promise<JobApplication[]> => {
    setLoadingApps((prev) => ({ ...prev, [dateStr]: true }));
    let allItems: JobApplication[] = [];
    let skip = 0;
    let total = 0;
    let data: { items: JobApplication[]; total: number };

    try {
      do {
        data = await jobApplicationService.getJobApplicationsByCreatedDate(
          dateStr,
          skip,
          CHUNK_SIZE
        );
        allItems = [...allItems, ...data.items];
        total = data.total;
        skip += CHUNK_SIZE;
        setApplicationsByDate((prev) => ({
          ...prev,
          [dateStr]: allItems,
        }));
      } while (
        allItems.length < total &&
        data.items.length === CHUNK_SIZE
      );
      return allItems;
    } finally {
      setLoadingApps((prev) => ({ ...prev, [dateStr]: false }));
    }
  };

  const toggleDateExpand = (dateStr: string) => {
    setExpandedDates((prev) => {
      const next = new Set(prev);
      if (next.has(dateStr)) {
        next.delete(dateStr);
      } else {
        next.add(dateStr);
        if (!applicationsByDate[dateStr]) {
          fetchApplicationsForDate(dateStr);
        }
      }
      return next;
    });
  };

  const toggleDateGroupSelection = async (dateStr: string) => {
    let apps = applicationsByDate[dateStr] || [];
    if (apps.length === 0) {
      setExpandedDates((prev) => new Set(prev).add(dateStr));
      const loaded = await fetchApplicationsForDate(dateStr);
      const ids = loaded.map((a) => a.id);
      setSelectedApplicationIds((prev) => {
        const allSelected = ids.every((id) => prev.has(id));
        const next = new Set(prev);
        if (allSelected) {
          ids.forEach((id) => next.delete(id));
        } else {
          ids.forEach((id) => next.add(id));
        }
        return next;
      });
      return;
    }
    const ids = apps.map((a) => a.id);
    const allSelected = ids.every((id) => selectedApplicationIds.has(id));
    setSelectedApplicationIds((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        ids.forEach((id) => next.delete(id));
      } else {
        ids.forEach((id) => next.add(id));
      }
      return next;
    });
  };

  const toggleApplicationSelection = (applicationId: number) => {
    setSelectedApplicationIds((prev) => {
      const next = new Set(prev);
      if (next.has(applicationId)) next.delete(applicationId);
      else next.add(applicationId);
      return next;
    });
  };

  const isDateGroupFullySelected = (dateStr: string) => {
    const apps = applicationsByDate[dateStr] || [];
    if (apps.length === 0) return false;
    return apps.every((a) => selectedApplicationIds.has(a.id));
  };

  const isDateGroupPartiallySelected = (dateStr: string) => {
    const apps = applicationsByDate[dateStr] || [];
    const n = apps.filter((a) => selectedApplicationIds.has(a.id)).length;
    return n > 0 && n < apps.length;
  };

  const handleApply = async () => {
    if (selectedApplicationIds.size === 0) {
      setError("Select at least one job application");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await jobApplicationService.bulkUpdateJobApplications({
        job_application_ids: Array.from(selectedApplicationIds),
        is_active: isActiveTarget,
      });
      onApplied();
      onClose();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to update job applications"
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const canApply =
    selectedApplicationIds.size > 0 && !submitting;

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
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Bulk Edit Job Applications
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <HiOutlineXMark className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-hidden flex flex-col p-6">
          {error && (
            <div className="mb-4 p-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg">
              {error}
            </div>
          )}

          <div className="flex-1 overflow-auto border border-gray-200 dark:border-gray-700 rounded-lg">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/50 text-gray-600 dark:text-gray-400 sticky top-0">
                  <th className="text-left px-4 py-3 font-medium w-10"></th>
                  <th className="text-left px-4 py-3 font-medium">
                    Application / Date
                  </th>
                  <th className="text-left px-4 py-3 font-medium">Client</th>
                  <th className="text-left px-4 py-3 font-medium">Job Site</th>
                  <th className="text-left px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {loadingDates && dateGroups.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                      Loading...
                    </td>
                  </tr>
                ) : dateGroups.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                      No job applications found.
                    </td>
                  </tr>
                ) : (
                  dateGroups.map((group) => (
                    <Fragment key={group.date}>
                      <tr
                        className="bg-gray-50 dark:bg-gray-800/30 hover:bg-gray-100 dark:hover:bg-gray-800/50 cursor-pointer"
                        onClick={() => toggleDateExpand(group.date)}
                      >
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={isDateGroupFullySelected(group.date)}
                            ref={(el) => {
                              if (el) {
                                const input = el as HTMLInputElement & {
                                  indeterminate?: boolean;
                                };
                                input.indeterminate =
                                  isDateGroupPartiallySelected(group.date);
                              }
                            }}
                            onChange={(e) => {
                              e.stopPropagation();
                              toggleDateGroupSelection(group.date);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center gap-1">
                            {expandedDates.has(group.date) ? (
                              <HiOutlineChevronDown className="w-4 h-4" />
                            ) : (
                              <HiOutlineChevronRight className="w-4 h-4" />
                            )}
                            {new Date(group.date).toLocaleDateString()} (
                            {group.application_count} applications)
                          </span>
                        </td>
                        <td className="px-4 py-3">-</td>
                        <td className="px-4 py-3">-</td>
                        <td className="px-4 py-3">-</td>
                      </tr>
                      {expandedDates.has(group.date) &&
                        (loadingApps[group.date] ? (
                          <tr>
                            <td colSpan={5} className="px-4 py-4 text-center">
                              Loading...
                            </td>
                          </tr>
                        ) : (
                          (applicationsByDate[group.date] || []).map((app) => (
                            <tr
                              key={app.id}
                              className="hover:bg-gray-50 dark:hover:bg-gray-800/30"
                            >
                              <td className="px-4 py-3 pl-8">
                                <input
                                  type="checkbox"
                                  checked={selectedApplicationIds.has(app.id)}
                                  onChange={() =>
                                    toggleApplicationSelection(app.id)
                                  }
                                  className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                                />
                              </td>
                              <td className="px-4 py-3 pl-8 font-medium text-gray-900 dark:text-white">
                                {app.career_job_title || "Application"}
                              </td>
                              <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                                {app.career_client_name || "-"}
                              </td>
                              <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                                {app.job_site_name || "-"}
                              </td>
                              <td className="px-4 py-3">
                                <span
                                  className={`text-xs px-2 py-0.5 rounded ${
                                    app.is_active
                                      ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                                      : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                                  }`}
                                >
                                  {app.is_active ? "Active" : "Inactive"}
                                </span>
                              </td>
                            </tr>
                          ))
                        ))}
                    </Fragment>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between gap-y-3">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {selectedApplicationIds.size} application(s) selected
            </span>
            <div className="flex flex-wrap items-center gap-2 sm:justify-end">
              <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setIsActiveTarget(true)}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    isActiveTarget
                      ? "bg-primary-600 text-white"
                      : "bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                  }`}
                >
                  Set Active
                </button>
                <button
                  type="button"
                  onClick={() => setIsActiveTarget(false)}
                  className={`px-3 py-2 text-sm font-medium transition-colors border-l border-gray-200 dark:border-gray-700 ${
                    !isActiveTarget
                      ? "bg-primary-600 text-white"
                      : "bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                  }`}
                >
                  Set Inactive
                </button>
              </div>
              <button
                type="button"
                onClick={handleApply}
                disabled={!canApply}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? "Applying..." : "Apply"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

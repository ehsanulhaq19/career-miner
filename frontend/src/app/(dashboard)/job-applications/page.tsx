"use client";

import { useEffect, useState } from "react";
import {
  HiOutlineChevronLeft,
  HiOutlineChevronRight,
  HiOutlinePaperAirplane,
  HiOutlinePlus,
} from "react-icons/hi2";
import { jobApplicationService } from "@/services/jobApplicationService";
import { JobApplication } from "@/types";
import JobApplicationDetailModal from "@/components/JobApplicationDetailModal";
import CreateJobApplicationModal from "@/components/CreateJobApplicationModal";

export default function JobApplicationsPage() {
  const [items, setItems] = useState<JobApplication[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  const [loading, setLoading] = useState(false);
  const [isActiveFilter, setIsActiveFilter] = useState<boolean | undefined>(
    undefined
  );
  const [selectedApplication, setSelectedApplication] =
    useState<JobApplication | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  const refetch = () => {
    const skip = (page - 1) * limit;
    jobApplicationService
      .getJobApplications(skip, limit, isActiveFilter)
      .then((data) => {
        setItems(data.items);
        setTotal(data.total);
      });
  };

  useEffect(() => {
    setLoading(true);
    const skip = (page - 1) * limit;
    jobApplicationService
      .getJobApplications(skip, limit, isActiveFilter)
      .then((data) => {
        setItems(data.items);
        setTotal(data.total);
      })
      .finally(() => setLoading(false));
  }, [page, limit, isActiveFilter]);

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Job Applications
        </h2>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isActiveFilter === true}
              onChange={(e) =>
                setIsActiveFilter(e.target.checked ? true : undefined)
              }
              className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Active only
            </span>
          </label>
          <button
            onClick={() => setCreateModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
          >
            <HiOutlinePlus className="w-4 h-4" />
            Create Job Application
          </button>
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
          <HiOutlinePaperAirplane className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-500 dark:text-gray-400">
            No job applications found.
          </p>
          <button
            onClick={() => setCreateModalOpen(true)}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
          >
            <HiOutlinePlus className="w-4 h-4" />
            Create Job Application
          </button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {items.map((app) => (
              <div
                key={app.id}
                role="button"
                tabIndex={0}
                onClick={() => setSelectedApplication(app)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelectedApplication(app);
                  }
                }}
                className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-5 cursor-pointer hover:border-primary-300 dark:hover:border-primary-600 transition-colors"
              >
                <h3 className="font-semibold text-gray-900 dark:text-white line-clamp-1 mb-2">
                  {app.career_job_title || "Application"}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                  {app.career_client_name || "Unknown client"}
                </p>
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  {app.job_site_name} · {new Date(app.created_at).toLocaleDateString()}
                </p>
                {app.similarity_score != null && (
                  <div className="mt-2">
                    <span
                      className={`inline-block text-xs px-2 py-0.5 rounded font-medium ${
                        (app.similarity_score ?? 0) >= 70
                          ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                          : (app.similarity_score ?? 0) >= 50
                            ? "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                      }`}
                    >
                      Fit: {Math.round(app.similarity_score)}%
                    </span>
                  </div>
                )}
                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between gap-2">
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      app.is_active
                        ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                    }`}
                  >
                    {app.is_active ? "Active" : "Inactive"}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      jobApplicationService
                        .updateJobApplication(app.id, {
                          is_active: !app.is_active,
                        })
                        .then(() => {
                          refetch();
                          if (selectedApplication?.id === app.id) {
                            setSelectedApplication((prev) =>
                              prev
                                ? { ...prev, is_active: !prev.is_active }
                                : null
                            );
                          }
                        });
                    }}
                    className="text-xs font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                  >
                    {app.is_active ? "Deactivate" : "Activate"}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex justify-between bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 px-6 py-3">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Page {page} of {totalPages} ({total.toLocaleString()} results)
              </span>
              <div className="flex items-center gap-2">
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

      <JobApplicationDetailModal
        applicationId={selectedApplication?.id ?? null}
        isOpen={!!selectedApplication}
        onClose={() => setSelectedApplication(null)}
      />
      <CreateJobApplicationModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onCreated={() => {
          setCreateModalOpen(false);
          setPage(1);
          refetch();
        }}
      />
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState, useRef } from "react";
import {
  HiOutlineChevronDown,
  HiOutlineChevronLeft,
  HiOutlineChevronRight,
  HiOutlineMagnifyingGlass,
  HiOutlinePaperAirplane,
  HiOutlinePlus,
  HiOutlineDocumentDuplicate,
  HiOutlineEnvelope,
  HiOutlineXMark,
  HiOutlinePencilSquare,
} from "react-icons/hi2";
import { jobApplicationService } from "@/services/jobApplicationService";
import { JobApplication, EmailLog } from "@/types";
import JobApplicationDetailModal from "@/components/JobApplicationDetailModal";
import CreateJobApplicationModal from "@/components/CreateJobApplicationModal";
import LiveJobApplicationModal from "@/components/LiveJobApplicationModal";
import BulkJobApplicationModal from "@/components/BulkJobApplicationModal";
import BulkJobApplicationEditModal from "@/components/BulkJobApplicationEditModal";
import BulkEmailSendModal from "@/components/BulkEmailSendModal";

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
  const [bulkModalOpen, setBulkModalOpen] = useState(false);
  const [bulkEditModalOpen, setBulkEditModalOpen] = useState(false);
  const [bulkEmailModalOpen, setBulkEmailModalOpen] = useState(false);
  const [sendEmailConfirmApp, setSendEmailConfirmApp] =
    useState<JobApplication | null>(null);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [emailLogsApp, setEmailLogsApp] = useState<JobApplication | null>(null);
  const [emailLogs, setEmailLogs] = useState<EmailLog[]>([]);
  const [emailLogsLoading, setEmailLogsLoading] = useState(false);
  const [createMenuOpen, setCreateMenuOpen] = useState(false);
  const [liveModalOpen, setLiveModalOpen] = useState(false);
  const createMenuRefHeader = useRef<HTMLDivElement>(null);
  const [searchInput, setSearchInput] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const t = setTimeout(() => {
      const next = searchInput.trim();
      setSearchTerm((prev) => {
        if (prev !== next) {
          setPage(1);
        }
        return next;
      });
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const loadApplications = useCallback(() => {
    setLoading(true);
    const skip = (page - 1) * limit;
    const req =
      searchTerm.length > 0
        ? jobApplicationService.searchJobApplications(
            searchTerm,
            skip,
            limit,
            isActiveFilter
          )
        : jobApplicationService.getJobApplications(
            skip,
            limit,
            isActiveFilter
          );
    req
      .then((data) => {
        setItems(data.items);
        setTotal(data.total);
      })
      .finally(() => setLoading(false));
  }, [page, limit, isActiveFilter, searchTerm]);

  useEffect(() => {
    loadApplications();
  }, [loadApplications]);

  const refetch = loadApplications;

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      const t = e.target as Node;
      if (!createMenuRefHeader.current?.contains(t)) {
        setCreateMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white shrink-0">
          Job Applications
        </h2>
        <div className="flex flex-wrap items-center gap-2 sm:gap-4">
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
            onClick={() => setBulkEmailModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <HiOutlineEnvelope className="w-4 h-4" />
            Bulk Email
          </button>
          <button
            onClick={() => setBulkEditModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <HiOutlinePencilSquare className="w-4 h-4" />
            Bulk Edit
          </button>
          <div className="relative" ref={createMenuRefHeader}>
            <button
              type="button"
              onClick={() => setCreateMenuOpen((o) => !o)}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
            >
              <HiOutlinePlus className="w-4 h-4" />
              Create Job Application
              <HiOutlineChevronDown
                className={`w-4 h-4 transition-transform ${createMenuOpen ? "rotate-180" : ""}`}
              />
            </button>
            {createMenuOpen && (
              <div className="absolute right-0 mt-1 w-56 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg z-20 py-1">
                <button
                  type="button"
                  onClick={() => {
                    setBulkModalOpen(true);
                    setCreateMenuOpen(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  <HiOutlineDocumentDuplicate className="w-4 h-4 shrink-0" />
                  Bulk Create
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setCreateModalOpen(true);
                    setCreateMenuOpen(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  <HiOutlinePlus className="w-4 h-4 shrink-0" />
                  Create Job Application
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setLiveModalOpen(true);
                    setCreateMenuOpen(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  <HiOutlinePaperAirplane className="w-4 h-4 shrink-0" />
                  Create Live Application
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="relative w-full max-w-xl min-w-0">
        <HiOutlineMagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
        <input
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search by job title, company, application name, subject, or cover letter…"
          className="w-full pl-10 pr-4 py-2.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder:text-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          aria-label="Search job applications"
        />
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
            {searchTerm.length > 0
              ? "No job applications match your search."
              : "No job applications found."}
          </p>
          <p className="mt-4 text-sm text-gray-500 dark:text-gray-400 text-center">
            {searchTerm.length > 0
              ? "Try different keywords or clear the search box."
              : 'Use "Create Job Application" above to add applications.'}
          </p>
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
                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between gap-2 flex-wrap">
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      app.is_active
                        ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                    }`}
                  >
                    {app.is_active ? "Active" : "Inactive"}
                  </span>
                  <div className="flex items-center gap-2">
                    {app.email_send_count != null && app.email_send_count > 0 && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Emails: {app.email_send_count}
                      </span>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSendEmailConfirmApp(app);
                      }}
                      className="text-xs font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                    >
                      Send Email
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEmailLogsApp(app);
                        setEmailLogs([]);
                        setEmailLogsLoading(true);
                        jobApplicationService
                          .getJobApplicationEmailLogs(app.id)
                          .then(setEmailLogs)
                          .finally(() => setEmailLogsLoading(false));
                      }}
                      className="text-xs font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                    >
                      Email Logs
                    </button>
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
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 px-4 py-3 sm:px-6">
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
      <LiveJobApplicationModal
        isOpen={liveModalOpen}
        onClose={() => setLiveModalOpen(false)}
        onCreated={() => {
          setLiveModalOpen(false);
          setPage(1);
          refetch();
        }}
      />
      <BulkJobApplicationModal
        isOpen={bulkModalOpen}
        onClose={() => setBulkModalOpen(false)}
        onCreated={() => {
          setPage(1);
          refetch();
        }}
      />
      <BulkJobApplicationEditModal
        isOpen={bulkEditModalOpen}
        onClose={() => setBulkEditModalOpen(false)}
        onApplied={() => {
          refetch();
        }}
      />
      <BulkEmailSendModal
        isOpen={bulkEmailModalOpen}
        onClose={() => setBulkEmailModalOpen(false)}
      />
      {emailLogsApp && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
          onClick={() => setEmailLogsApp(null)}
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Email Logs - {emailLogsApp.career_job_title}
              </h3>
              <button
                onClick={() => setEmailLogsApp(null)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <HiOutlineXMark className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {emailLogsLoading ? (
                <div className="animate-pulse space-y-3">
                  <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded" />
                  <div className="h-4 w-3/4 bg-gray-200 dark:bg-gray-700 rounded" />
                  <div className="h-4 w-1/2 bg-gray-200 dark:bg-gray-700 rounded" />
                </div>
              ) : emailLogs.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No email logs found.
                </p>
              ) : (
                <div className="space-y-4">
                  {emailLogs.map((log) => (
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
                      <p className="text-xs text-gray-500 dark:text-gray-500">
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
      {sendEmailConfirmApp && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
          onClick={() => setSendEmailConfirmApp(null)}
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-xl shadow-xl max-w-md w-full p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Send Email
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Send application email for {sendEmailConfirmApp.career_job_title}{" "}
              to {sendEmailConfirmApp.to_emails?.length ?? 0} recipient(s)?
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setSendEmailConfirmApp(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (!sendEmailConfirmApp) return;
                  setSendingEmail(true);
                  jobApplicationService
                    .sendJobApplicationEmail(sendEmailConfirmApp.id)
                    .then((updated) => {
                      setSendEmailConfirmApp(null);
                      refetch();
                      if (
                        selectedApplication?.id === sendEmailConfirmApp.id
                      ) {
                        setSelectedApplication(updated);
                      }
                    })
                    .finally(() => setSendingEmail(false));
                }}
                disabled={sendingEmail}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {sendingEmail ? "Sending..." : "Send"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

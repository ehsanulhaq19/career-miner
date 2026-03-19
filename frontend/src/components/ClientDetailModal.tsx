"use client";

import { useEffect, useState } from "react";
import {
  HiXMark,
  HiOutlineChevronLeft,
  HiOutlineChevronRight,
  HiOutlineBriefcase,
  HiOutlineEnvelope,
  HiOutlineGlobeAlt,
} from "react-icons/hi2";
import {
  careerClientService,
  CareerClientUpdatePayload,
} from "@/services/careerClientService";
import { careerJobService } from "@/services/careerJobService";
import { CareerClient, CareerJob } from "@/types";
import JobDetailModal from "@/components/JobDetailModal";

interface ClientDetailModalProps {
  clientId: number | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdated?: () => void;
}

export default function ClientDetailModal({
  clientId,
  isOpen,
  onClose,
  onUpdated,
}: ClientDetailModalProps) {
  const [client, setClient] = useState<CareerClient | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<CareerClientUpdatePayload>({});
  const [jobs, setJobs] = useState<CareerJob[]>([]);
  const [jobsTotal, setJobsTotal] = useState(0);
  const [jobsPage, setJobsPage] = useState(1);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [selectedJob, setSelectedJob] = useState<CareerJob | null>(null);
  const jobsLimit = 10;

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
    if (!isOpen || !clientId) {
      setClient(null);
      setFormData({});
      setJobs([]);
      setJobsTotal(0);
      setJobsPage(1);
      setSelectedJob(null);
      return;
    }
    setLoading(true);
    careerClientService
      .getCareerClientById(clientId)
      .then((data) => {
        setClient(data);
        setFormData({
          emails: data.emails ?? [],
          name: data.name ?? "",
          official_website: data.official_website ?? "",
          location: data.location ?? "",
          link: data.link ?? "",
          detail: data.detail ?? "",
          is_active: data.is_active ?? true,
        });
      })
      .finally(() => setLoading(false));
  }, [isOpen, clientId]);

  const clientHasEmails = (client?.emails?.length ?? 0) > 0;

  useEffect(() => {
    if (!isOpen || !clientId) return;
    if (!clientHasEmails) {
      setJobs([]);
      setJobsTotal(0);
      return;
    }
    setJobsLoading(true);
    const skip = (jobsPage - 1) * jobsLimit;
    careerJobService
      .getCareerJobs({
        career_client_id: clientId,
        skip,
        limit: jobsLimit,
        has_client_emails: true,
      })
      .then((data) => {
        setJobs(data.items);
        setJobsTotal(data.total);
      })
      .finally(() => setJobsLoading(false));
  }, [isOpen, clientId, jobsPage, clientHasEmails]);

  const handleChange = (
    field: keyof CareerClientUpdatePayload,
    value: string | string[] | boolean | null
  ) => {
    setFormData((prev: CareerClientUpdatePayload) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleEmailsChange = (value: string) => {
    const emails = value
      .split(",")
      .map((e) => e.trim())
      .filter(Boolean);
    handleChange("emails", emails);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientId) return;
    setSaving(true);
    try {
      await careerClientService.updateCareerClient(clientId, formData);
      onUpdated?.();
      onClose();
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  const jobsTotalPages = Math.ceil(jobsTotal / jobsLimit);

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
        <div className="sticky top-0 flex items-center justify-between p-6 pb-4 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 shrink-0">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white pr-8">
            {loading ? "Loading..." : client?.name || "Edit Client"}
          </h2>
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <HiXMark className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 min-h-0 flex overflow-hidden">
          <div className="w-1/2 min-w-0 border-r border-gray-200 dark:border-gray-800 overflow-y-auto">
            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              {loading ? (
                <div className="animate-pulse space-y-4">
                  <div className="h-4 w-3/4 bg-gray-200 dark:bg-gray-700 rounded" />
                  <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded" />
                  <div className="h-4 w-1/2 bg-gray-200 dark:bg-gray-700 rounded" />
                </div>
              ) : client ? (
                <>
                  {(client.emails?.length ?? 0) > 0 || client.official_website ? (
                    <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 space-y-3">
                      {client.emails?.length ? (
                        <div>
                          <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-1.5 mb-1">
                            <HiOutlineEnvelope className="w-3.5 h-3.5" />
                            Emails
                          </span>
                          <div className="flex flex-wrap gap-x-3 gap-y-1">
                            {client.emails.map((email) => (
                              <a
                                key={email}
                                href={`mailto:${email}`}
                                className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
                              >
                                {email}
                              </a>
                            ))}
                          </div>
                        </div>
                      ) : null}
                      {client.official_website ? (
                        <div>
                          <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-1.5 mb-1">
                            <HiOutlineGlobeAlt className="w-3.5 h-3.5" />
                            Official Website
                          </span>
                          <a
                            href={client.official_website.startsWith("http") ? client.official_website : `https://${client.official_website}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-primary-600 dark:text-primary-400 hover:underline break-all"
                          >
                            {client.official_website}
                          </a>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                  <div>
                    <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                      Name
                    </label>
                    <input
                      type="text"
                      value={(formData.name as string) ?? ""}
                      onChange={(e) => handleChange("name", e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                      Location
                    </label>
                    <input
                      type="text"
                      value={(formData.location as string) ?? ""}
                      onChange={(e) => handleChange("location", e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                      Emails (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={(formData.emails as string[])?.join(", ") ?? ""}
                      onChange={(e) => handleEmailsChange(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                      Official Website
                    </label>
                    <input
                      type="text"
                      value={(formData.official_website as string) ?? ""}
                      onChange={(e) =>
                        handleChange("official_website", e.target.value)
                      }
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                      Link
                    </label>
                    <input
                      type="text"
                      value={(formData.link as string) ?? ""}
                      onChange={(e) => handleChange("link", e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                      Detail
                    </label>
                    <textarea
                      value={(formData.detail as string) ?? ""}
                      onChange={(e) => handleChange("detail", e.target.value)}
                      rows={4}
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="is_active"
                      checked={(formData.is_active as boolean) ?? true}
                      onChange={(e) => handleChange("is_active", e.target.checked)}
                      className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                    />
                    <label
                      htmlFor="is_active"
                      className="text-sm text-gray-700 dark:text-gray-300"
                    >
                      Active
                    </label>
                  </div>

                  <div className="pt-3 border-t border-gray-200 dark:border-gray-800 flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={onClose}
                      className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={saving}
                      className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
                    >
                      {saving ? "Saving..." : "Save"}
                    </button>
                  </div>
                </>
              ) : (
                !loading && (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Client not found.
                  </p>
                )
              )}
            </form>
          </div>

          <div className="w-1/2 min-w-0 flex flex-col">
            <div className="p-4 border-b border-gray-200 dark:border-gray-800 shrink-0">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <HiOutlineBriefcase className="w-4 h-4" />
                Related Jobs
                {clientHasEmails ? ` (${jobsTotal})` : " — add emails to view"}
              </h3>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {!clientHasEmails ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                  Add emails to this client to see related jobs.
                </p>
              ) : jobsLoading ? (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <div
                      key={i}
                      className="animate-pulse h-16 bg-gray-200 dark:bg-gray-700 rounded-lg"
                    />
                  ))}
                </div>
              ) : jobs.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                  No jobs linked to this client.
                </p>
              ) : (
                <div className="space-y-3">
                  {jobs.map((job) => (
                    <button
                      key={job.id}
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setSelectedJob(job);
                        if (!job.job_seen) {
                          careerJobService.markJobSeen(job.id);
                        }
                      }}
                      className="w-full text-left block p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <div className="font-medium text-gray-900 dark:text-white text-sm line-clamp-2">
                        {job.title}
                      </div>
                      {job.job_site_name && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {job.job_site_name}
                        </div>
                      )}
                      {job.description && (
                        <div className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                          {job.description}
                        </div>
                      )}
                      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 text-xs text-gray-500 dark:text-gray-400">
                        {job.parsed_data?.location && (
                          <span>{job.parsed_data.location}</span>
                        )}
                        {job.parsed_data?.salary && (
                          <span>{job.parsed_data.salary}</span>
                        )}
                        {job.url && (
                          <a
                            href={job.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-primary-600 dark:text-primary-400 hover:underline truncate max-w-[200px]"
                          >
                            View job
                          </a>
                        )}
                      </div>
                      <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                        {new Date(job.created_at).toLocaleDateString()}
                      </div>
                    </button>
                  ))}
                </div>
              )}
              {jobsTotalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200 dark:border-gray-800">
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Page {jobsPage} of {jobsTotalPages}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() =>
                        setJobsPage((p: number) => Math.max(1, p - 1))
                      }
                      disabled={jobsPage <= 1}
                      className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <HiOutlineChevronLeft className="w-3 h-3" />
                      Prev
                    </button>
                    <button
                      onClick={() =>
                        setJobsPage((p: number) =>
                          Math.min(jobsTotalPages, p + 1)
                        )
                      }
                      disabled={jobsPage >= jobsTotalPages}
                      className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      Next
                      <HiOutlineChevronRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <JobDetailModal
        job={selectedJob}
        isOpen={!!selectedJob}
        onClose={() => setSelectedJob(null)}
      />
    </div>
  );
}

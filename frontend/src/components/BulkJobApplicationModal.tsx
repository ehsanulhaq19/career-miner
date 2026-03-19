"use client";

import { Fragment, useEffect, useState, useRef } from "react";
import {
  HiOutlineChevronDown,
  HiOutlineChevronRight,
  HiOutlineDocumentText,
  HiOutlineXMark,
} from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { setBulkJobApplicationLogs } from "@/store/slices/bulkJobApplicationSlice";
import { jobApplicationService } from "@/services/jobApplicationService";
import { careerJobService } from "@/services/careerJobService";
import { resumeService } from "@/services/resumeService";
import {
  CareerJobDateGroup,
  CareerJobWithApplicationCounts,
  Resume,
} from "@/types";
import JobDetailModal from "@/components/JobDetailModal";

interface BulkJobApplicationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export default function BulkJobApplicationModal({
  isOpen,
  onClose,
  onCreated,
}: BulkJobApplicationModalProps) {
  const dispatch = useAppDispatch();
  const { logsByBulkId } = useAppSelector((state) => state.bulkJobApplication);
  const [dateGroups, setDateGroups] = useState<CareerJobDateGroup[]>([]);
  const [dateGroupsTotal, setDateGroupsTotal] = useState(0);
  const [dateGroupsPage, setDateGroupsPage] = useState(1);
  const [dateGroupsLimit] = useState(20);
  const [expandedDates, setExpandedDates] = useState<Set<string>>(new Set());
  const [jobsByDate, setJobsByDate] = useState<
    Record<string, CareerJobWithApplicationCounts[]>
  >({});
  const [jobsTotalByDate, setJobsTotalByDate] = useState<Record<string, number>>(
    {}
  );
  const [selectedJobIds, setSelectedJobIds] = useState<Set<number>>(new Set());
  const [selectedResume, setSelectedResume] = useState<Resume | null>(null);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loadingDates, setLoadingDates] = useState(false);
  const [loadingJobs, setLoadingJobs] = useState<Record<string, boolean>>({});
  const [loadingResumes, setLoadingResumes] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeBulkId, setActiveBulkId] = useState<number | null>(null);
  const [logsModalOpen, setLogsModalOpen] = useState(false);
  const [logsSearchQuery, setLogsSearchQuery] = useState("");
  const [selectedJobDetail, setSelectedJobDetail] =
    useState<CareerJobWithApplicationCounts | null>(null);
  const [jobDetailLoading, setJobDetailLoading] = useState(false);
  const resumeRef = useRef<HTMLDivElement>(null);
  const [resumeDropdownOpen, setResumeDropdownOpen] = useState(false);
  const [resumeSearch, setResumeSearch] = useState("");

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
    if (!isOpen) return;
    setLoadingDates(true);
    careerJobService
      .getCareerJobDatesGrouped(0, dateGroupsLimit)
      .then((data) => {
        setDateGroups(data.items);
        setDateGroupsTotal(data.total);
        setDateGroupsPage(1);
      })
      .finally(() => setLoadingDates(false));
  }, [isOpen, dateGroupsLimit]);

  useEffect(() => {
    if (!isOpen) return;
    setLoadingResumes(true);
    resumeService
      .getResumes(0, 500, undefined, true)
      .then((data) => setResumes(data.items))
      .finally(() => setLoadingResumes(false));
  }, [isOpen]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        resumeRef.current &&
        !resumeRef.current.contains(e.target as Node)
      ) {
        setResumeDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const CHUNK_SIZE = 100;

  const fetchJobsForDate = async (
    dateStr: string
  ): Promise<CareerJobWithApplicationCounts[]> => {
    setLoadingJobs((prev) => ({ ...prev, [dateStr]: true }));
    let allItems: CareerJobWithApplicationCounts[] = [];
    let skip = 0;
    let total = 0;
    let data: { items: CareerJobWithApplicationCounts[]; total: number };

    try {
      do {
        data = await careerJobService.getCareerJobsByDate(
          dateStr,
          skip,
          CHUNK_SIZE
        );
        allItems = [...allItems, ...data.items];
        total = data.total;
        skip += CHUNK_SIZE;

        setJobsByDate((prev) => ({ ...prev, [dateStr]: allItems }));
        setJobsTotalByDate((prev) => ({ ...prev, [dateStr]: total }));
      } while (allItems.length < total && data.items.length === CHUNK_SIZE);
      return allItems;
    } finally {
      setLoadingJobs((prev) => ({ ...prev, [dateStr]: false }));
    }
  };

  const toggleDateExpand = (dateStr: string) => {
    setExpandedDates((prev) => {
      const next = new Set(prev);
      if (next.has(dateStr)) {
        next.delete(dateStr);
      } else {
        next.add(dateStr);
        if (!jobsByDate[dateStr]) {
          fetchJobsForDate(dateStr);
        }
      }
      return next;
    });
  };

  const toggleDateGroupSelection = async (dateStr: string) => {
    let jobs = jobsByDate[dateStr] || [];
    if (jobs.length === 0) {
      setExpandedDates((prev) => new Set(prev).add(dateStr));
      const loadedJobs = await fetchJobsForDate(dateStr);
      const jobIds = loadedJobs.map((j) => j.id);
      setSelectedJobIds((prev) => {
        const allSelected = jobIds.every((id) => prev.has(id));
        const next = new Set(prev);
        if (allSelected) {
          jobIds.forEach((id) => next.delete(id));
        } else {
          jobIds.forEach((id) => next.add(id));
        }
        return next;
      });
      return;
    }
    const jobIds = jobs.map((j) => j.id);
    const allSelected = jobIds.every((id) => selectedJobIds.has(id));
    setSelectedJobIds((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        jobIds.forEach((id) => next.delete(id));
      } else {
        jobIds.forEach((id) => next.add(id));
      }
      return next;
    });
  };

  const toggleJobSelection = (jobId: number) => {
    setSelectedJobIds((prev) => {
      const next = new Set(prev);
      if (next.has(jobId)) next.delete(jobId);
      else next.add(jobId);
      return next;
    });
  };

  const isDateGroupFullySelected = (dateStr: string) => {
    const jobs = jobsByDate[dateStr] || [];
    if (jobs.length === 0) return false;
    return jobs.every((j) => selectedJobIds.has(j.id));
  };

  const isDateGroupPartiallySelected = (dateStr: string) => {
    const jobs = jobsByDate[dateStr] || [];
    const selected = jobs.filter((j) => selectedJobIds.has(j.id)).length;
    return selected > 0 && selected < jobs.length;
  };

  const handleCreateApplications = async () => {
    if (!selectedResume || selectedJobIds.size === 0) {
      setError("Please select at least one job and a resume");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const result = await jobApplicationService.createBulkJobApplications({
        resume_id: selectedResume.id,
        career_job_ids: Array.from(selectedJobIds),
      });
      setActiveBulkId(result.id);
      setLogsModalOpen(true);
      dispatch(
        setBulkJobApplicationLogs({
          bulkJobApplicationId: result.id,
          logs: [],
        })
      );
      jobApplicationService
        .getBulkJobApplicationLogs(result.id)
        .then((data) =>
          dispatch(
            setBulkJobApplicationLogs({
              bulkJobApplicationId: result.id,
              logs: data.items,
            })
          )
        );
      onCreated();
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to create job applications"
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenLogs = (bulkId: number) => {
    setActiveBulkId(bulkId);
    setLogsModalOpen(true);
    dispatch(
      setBulkJobApplicationLogs({ bulkJobApplicationId: bulkId, logs: [] })
    );
    jobApplicationService.getBulkJobApplicationLogs(bulkId).then((data) =>
      dispatch(
        setBulkJobApplicationLogs({
          bulkJobApplicationId: bulkId,
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

  const filteredResumes = resumes.filter((r) => {
    const search = (resumeSearch || "").toLowerCase();
    return search ? r.name.toLowerCase().includes(search) : true;
  });

  const canCreate =
    selectedResume && selectedJobIds.size > 0 && !submitting;

  if (!isOpen) return null;

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
            Bulk Create Job Applications
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

          <div ref={resumeRef} className="mb-4">
            <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
              Resume
            </label>
            <div className="relative">
              <input
                type="text"
                value={selectedResume ? selectedResume.name : resumeSearch}
                onChange={(e) => {
                  setResumeSearch(e.target.value);
                  setSelectedResume(null);
                  setResumeDropdownOpen(true);
                }}
                onFocus={() => setResumeDropdownOpen(true)}
                placeholder="Search resumes..."
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              {selectedResume && (
                <button
                  type="button"
                  onClick={() => {
                    setSelectedResume(null);
                    setResumeSearch("");
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <HiOutlineXMark className="w-4 h-4" />
                </button>
              )}
              {resumeDropdownOpen && (
                <div className="absolute z-10 w-full mt-1 max-h-48 overflow-y-auto bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
                  {loadingResumes ? (
                    <div className="p-4 text-sm text-gray-500">Loading...</div>
                  ) : filteredResumes.length === 0 ? (
                    <div className="p-4 text-sm text-gray-500">
                      No resumes found
                    </div>
                  ) : (
                    filteredResumes.map((resume) => (
                      <button
                        key={resume.id}
                        type="button"
                        onClick={() => {
                          setSelectedResume(resume);
                          setResumeSearch("");
                          setResumeDropdownOpen(false);
                        }}
                        className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      >
                        {resume.name}
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-auto border border-gray-200 dark:border-gray-700 rounded-lg">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/50 text-gray-600 dark:text-gray-400 sticky top-0">
                  <th className="text-left px-4 py-3 font-medium w-10"></th>
                  <th className="text-left px-4 py-3 font-medium">Job / Date</th>
                  <th className="text-left px-4 py-3 font-medium">Client</th>
                  <th className="text-left px-4 py-3 font-medium">Job Site</th>
                  <th className="text-left px-4 py-3 font-medium">
                    Applications
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {loadingDates && dateGroups.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                      Loading...
                    </td>
                  </tr>
                ) : (
                  dateGroups.map((group) => (
                    <Fragment key={group.date}>
                      <tr
                        key={`group-${group.date}`}
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
                            {group.job_count} jobs)
                          </span>
                        </td>
                        <td className="px-4 py-3">-</td>
                        <td className="px-4 py-3">-</td>
                        <td className="px-4 py-3">-</td>
                      </tr>
                      {expandedDates.has(group.date) &&
                        (loadingJobs[group.date] ? (
                          <tr>
                            <td colSpan={5} className="px-4 py-4 text-center">
                              Loading jobs...
                            </td>
                          </tr>
                        ) : (
                          (jobsByDate[group.date] || []).map((job) => (
                            <tr
                              key={job.id}
                              className="hover:bg-gray-50 dark:hover:bg-gray-800/30 cursor-pointer"
                              onClick={() => {
                                setSelectedJobDetail(job);
                                setJobDetailLoading(true);
                                careerJobService.getCareerJob(job.id).then((fullJob) => {
                                  setSelectedJobDetail((prev) =>
                                    prev?.id === job.id
                                      ? { ...prev, ...fullJob }
                                      : prev
                                  );
                                }).finally(() => setJobDetailLoading(false));
                              }}
                            >
                              <td className="px-4 py-3 pl-8">
                                <input
                                  type="checkbox"
                                  checked={selectedJobIds.has(job.id)}
                                  onChange={() => toggleJobSelection(job.id)}
                                  onClick={(e) => e.stopPropagation()}
                                  className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                                />
                              </td>
                              <td className="px-4 py-3 pl-8 font-medium text-gray-900 dark:text-white">
                                {job.title}
                              </td>
                              <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                                {job.career_client_name || "-"}
                              </td>
                              <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                                {job.job_site_name || "-"}
                              </td>
                              <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                                {job.active_application_count} active /{" "}
                                {job.inactive_application_count} inactive
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


          <div className="mt-4 flex items-center justify-between">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {selectedJobIds.size} job(s) selected
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
                onClick={handleCreateApplications}
                disabled={!canCreate}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? "Creating..." : "Create Applications"}
              </button>
            </div>
          </div>
        </div>
      </div>

      <JobDetailModal
        job={selectedJobDetail}
        isOpen={!!selectedJobDetail}
        onClose={() => setSelectedJobDetail(null)}
      />

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
                Bulk Job Application Logs
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

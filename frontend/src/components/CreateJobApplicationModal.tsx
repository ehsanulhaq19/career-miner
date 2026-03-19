"use client";

import { useEffect, useState, useRef } from "react";
import { HiXMark } from "react-icons/hi2";
import { jobApplicationService } from "@/services/jobApplicationService";
import { careerJobService } from "@/services/careerJobService";
import { resumeService } from "@/services/resumeService";
import { CareerJob, Resume } from "@/types";

interface CreateJobApplicationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

function formatJobOption(job: CareerJob): string {
  const parts = [
    job.title,
    job.career_client_name || "Unknown",
    job.job_site_name || "",
    new Date(job.created_at).toLocaleDateString(),
  ].filter(Boolean);
  return parts.join(" · ");
}

export default function CreateJobApplicationModal({
  isOpen,
  onClose,
  onCreated,
}: CreateJobApplicationModalProps) {
  const [jobs, setJobs] = useState<CareerJob[]>([]);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [resumesLoading, setResumesLoading] = useState(false);
  const [selectedJob, setSelectedJob] = useState<CareerJob | null>(null);
  const [selectedResume, setSelectedResume] = useState<Resume | null>(null);
  const [jobSearch, setJobSearch] = useState("");
  const [resumeSearch, setResumeSearch] = useState("");
  const [jobDropdownOpen, setJobDropdownOpen] = useState(false);
  const [resumeDropdownOpen, setResumeDropdownOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const jobRef = useRef<HTMLDivElement>(null);
  const resumeRef = useRef<HTMLDivElement>(null);

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
    setJobsLoading(true);
    careerJobService
      .getCareerJobs({ skip: 0, limit: 500, has_client_emails: true })
      .then((data) => setJobs(data.items))
      .finally(() => setJobsLoading(false));
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    setResumesLoading(true);
    resumeService
      .getResumes(0, 500, undefined, true)
      .then((data) => setResumes(data.items))
      .finally(() => setResumesLoading(false));
  }, [isOpen]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        jobRef.current &&
        !jobRef.current.contains(e.target as Node)
      ) {
        setJobDropdownOpen(false);
      }
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

  const filteredJobs = jobs.filter((job) => {
    const search = jobSearch.toLowerCase();
    const text = formatJobOption(job).toLowerCase();
    return text.includes(search);
  });

  const filteredResumes = resumes.filter((resume) => {
    const search = resumeSearch.toLowerCase();
    return resume.name.toLowerCase().includes(search);
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedJob || !selectedResume) {
      setError("Please select both a job and a resume");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await jobApplicationService.createJobApplication({
        career_job_id: selectedJob.id,
        resume_id: selectedResume.id,
      });
      onCreated();
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to create job application"
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div className="fixed inset-0 bg-black/50" />
      <div
        className={`relative z-10 w-full bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-200 dark:border-gray-800 ${
          selectedJob || selectedResume ? "max-w-3xl" : "max-w-lg"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Create Job Application
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <HiXMark className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg">
              {error}
            </div>
          )}

          <div ref={jobRef}>
            <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
              Job
            </label>
            <div className="relative">
              <input
                type="text"
                value={selectedJob ? formatJobOption(selectedJob) : jobSearch}
                onChange={(e) => {
                  setJobSearch(e.target.value);
                  setSelectedJob(null);
                  setJobDropdownOpen(true);
                }}
                onFocus={() => setJobDropdownOpen(true)}
                placeholder="Search jobs..."
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              {selectedJob && (
                <button
                  type="button"
                  onClick={() => {
                    setSelectedJob(null);
                    setJobSearch("");
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <HiXMark className="w-4 h-4" />
                </button>
              )}
              {jobDropdownOpen && (
                <div className="absolute z-10 w-full mt-1 max-h-48 overflow-y-auto bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
                  {jobsLoading ? (
                    <div className="p-4 text-sm text-gray-500">Loading...</div>
                  ) : filteredJobs.length === 0 ? (
                    <div className="p-4 text-sm text-gray-500">
                      No jobs found
                    </div>
                  ) : (
                    filteredJobs.map((job) => (
                      <button
                        key={job.id}
                        type="button"
                        onClick={() => {
                          setSelectedJob(job);
                          setJobSearch("");
                          setJobDropdownOpen(false);
                        }}
                        className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      >
                        {formatJobOption(job)}
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>

          <div ref={resumeRef}>
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
                  <HiXMark className="w-4 h-4" />
                </button>
              )}
              {resumeDropdownOpen && (
                <div className="absolute z-10 w-full mt-1 max-h-48 overflow-y-auto bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
                  {resumesLoading ? (
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

          {(selectedJob || selectedResume) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-gray-200 dark:border-gray-800">
              {selectedJob && (
                <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-800/50">
                  <div className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
                    Job Details
                  </div>
                  <h3 className="font-semibold text-gray-900 dark:text-white text-sm mb-2 line-clamp-2">
                    {selectedJob.title}
                  </h3>
                  {selectedJob.career_client_name && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                      {selectedJob.career_client_name}
                    </p>
                  )}
                  {selectedJob.job_site_name && (
                    <p className="text-xs text-gray-500 dark:text-gray-500 mb-2">
                      {selectedJob.job_site_name}
                    </p>
                  )}
                  {selectedJob.description && (
                    <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-4 mt-2">
                      {selectedJob.description}
                    </p>
                  )}
                  {selectedJob.parsed_data?.location && (
                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                      {selectedJob.parsed_data.location}
                    </p>
                  )}
                  {selectedJob.url && (
                    <a
                      href={selectedJob.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary-600 dark:text-primary-400 hover:underline truncate block mt-1"
                    >
                      View job
                    </a>
                  )}
                </div>
              )}
              {selectedResume && (
                <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-800/50">
                  <div className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
                    Resume Details
                  </div>
                  <h3 className="font-semibold text-gray-900 dark:text-white text-sm mb-2">
                    {selectedResume.name}
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-500 mb-2">
                    {selectedResume.extension.toUpperCase()} ·{" "}
                    {selectedResume.size < 1024
                      ? `${selectedResume.size} B`
                      : `${(selectedResume.size / 1024).toFixed(1)} KB`}
                  </p>
                  {selectedResume.content && (
                    <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap line-clamp-6 overflow-hidden font-sans">
                      {selectedResume.content}
                    </pre>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !selectedJob || !selectedResume}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

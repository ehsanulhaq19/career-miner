"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import axios from "axios";
import {
  HiOutlineChevronDown,
  HiOutlinePlus,
  HiOutlineTrash,
  HiXMark,
} from "react-icons/hi2";
import { jobApplicationService } from "@/services/jobApplicationService";
import { resumeService } from "@/services/resumeService";
import { Resume } from "@/types";

interface LiveJobApplicationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export default function LiveJobApplicationModal({
  isOpen,
  onClose,
  onCreated,
}: LiveJobApplicationModalProps) {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [resumesLoading, setResumesLoading] = useState(false);
  const [selectedResume, setSelectedResume] = useState<Resume | null>(null);
  const [resumeSearch, setResumeSearch] = useState("");
  const [resumeDropdownOpen, setResumeDropdownOpen] = useState(false);
  const [jobDetails, setJobDetails] = useState("");
  const [action, setAction] = useState<
    | "create_job_application"
    | "create_and_send_job_application"
    | "prepare_job_application_form"
  >("create_job_application");
  const [formQuestions, setFormQuestions] = useState<string[]>([""]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duplicateInfo, setDuplicateInfo] = useState<{
    title: string;
    description: string | null;
  } | null>(null);
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
    setJobDetails("");
    setError(null);
    setDuplicateInfo(null);
    setSelectedResume(null);
    setResumeSearch("");
    setAction("create_job_application");
    setFormQuestions([""]);
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
        resumeRef.current &&
        !resumeRef.current.contains(e.target as Node)
      ) {
        setResumeDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredResumes = resumes.filter((resume) => {
    const search = resumeSearch.toLowerCase();
    return resume.name.toLowerCase().includes(search);
  });

  const parseAxiosDetail = useCallback((err: unknown): string => {
    if (axios.isAxiosError(err)) {
      const d = err.response?.data?.detail;
      if (typeof d === "string") {
        return d;
      }
      if (Array.isArray(d) && d[0] && typeof d[0] === "object" && "msg" in d[0]) {
        return String((d[0] as { msg: string }).msg);
      }
    }
    return "Request failed";
  }, []);

  const runLiveCreate = async () => {
    if (!selectedResume) return;
    const normalizedQuestions = formQuestions.map((q) => q.trim()).filter(Boolean);
    if (action === "prepare_job_application_form" && normalizedQuestions.length === 0) {
      setError("Please add at least one application question");
      return;
    }
    await jobApplicationService.createLiveJobApplication({
      job_details: jobDetails.trim(),
      resume_id: selectedResume.id,
      action,
      ...(action === "prepare_job_application_form"
        ? { application_form_questions: normalizedQuestions }
        : {}),
    });
    onCreated();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedResume) {
      setError("Please select a resume");
      return;
    }
    if (!jobDetails.trim()) {
      setError("Please enter job details");
      return;
    }
    if (action === "prepare_job_application_form") {
      const nq = formQuestions.map((q) => q.trim()).filter(Boolean);
      if (nq.length === 0) {
        setError("Please add at least one application question");
        return;
      }
    }
    setError(null);
    setSubmitting(true);
    try {
      const dup = await jobApplicationService.checkLiveJobDuplicate(
        jobDetails.trim()
      );
      if (dup.exists) {
        setDuplicateInfo({
          title: dup.title?.trim() ? dup.title : "—",
          description:
            dup.description != null && dup.description !== ""
              ? dup.description
              : null,
        });
        setSubmitting(false);
        return;
      }
      setDuplicateInfo(null);
      await runLiveCreate();
    } catch (err: unknown) {
      setError(parseAxiosDetail(err));
    } finally {
      setSubmitting(false);
    }
  };

  const proceedDespiteDuplicate = async () => {
    if (!selectedResume || !jobDetails.trim()) return;
    setDuplicateInfo(null);
    setError(null);
    setSubmitting(true);
    try {
      await runLiveCreate();
    } catch (err: unknown) {
      setError(parseAxiosDetail(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-hidden flex flex-col border border-gray-200 dark:border-gray-800">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-800">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Create Live Application
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <HiXMark className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Job details
            </label>
            <textarea
              value={jobDetails}
              onChange={(e) => {
                setJobDetails(e.target.value);
                setDuplicateInfo(null);
              }}
              rows={8}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white"
              placeholder="Paste the job posting or listing text"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Resume
            </label>
            <div className="relative" ref={resumeRef}>
              <button
                type="button"
                onClick={() => setResumeDropdownOpen((o) => !o)}
                className="w-full flex items-center justify-between rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-left text-gray-900 dark:text-white"
              >
                <span className="truncate">
                  {selectedResume ? selectedResume.name : resumesLoading ? "Loading…" : "Select resume"}
                </span>
                <HiOutlineChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
              </button>
              {resumeDropdownOpen && (
                <div className="absolute z-10 mt-1 w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg max-h-48 overflow-y-auto">
                  <input
                    type="search"
                    value={resumeSearch}
                    onChange={(e) => setResumeSearch(e.target.value)}
                    className="w-full px-3 py-2 text-sm border-b border-gray-200 dark:border-gray-700 bg-transparent text-gray-900 dark:text-white"
                    placeholder="Search"
                  />
                  {filteredResumes.map((r) => (
                    <button
                      key={r.id}
                      type="button"
                      onClick={() => {
                        setSelectedResume(r);
                        setResumeDropdownOpen(false);
                      }}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-900 dark:text-white"
                    >
                      {r.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          {duplicateInfo && (
            <div
              className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/40 p-3 space-y-2 text-sm text-gray-900 dark:text-gray-100"
              role="status"
            >
              <p className="font-medium text-amber-900 dark:text-amber-200">
                A career job you already saved matches this job text
              </p>
              <p>
                <span className="text-gray-600 dark:text-gray-400">Title: </span>
                <span className="font-medium">{duplicateInfo.title}</span>
              </p>
              {duplicateInfo.description ? (
                <div>
                  <p className="text-gray-600 dark:text-gray-400 mb-1">
                    Stored description:
                  </p>
                  <pre className="text-xs whitespace-pre-wrap break-words max-h-36 overflow-y-auto bg-white/60 dark:bg-black/30 p-2 rounded border border-amber-100 dark:border-amber-900">
                    {duplicateInfo.description}
                  </pre>
                </div>
              ) : (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  No description stored on the existing record.
                </p>
              )}
              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setDuplicateInfo(null)}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Edit job text
                </button>
                <button
                  type="button"
                  onClick={() => void proceedDespiteDuplicate()}
                  disabled={submitting}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-700 text-white hover:bg-amber-800 disabled:opacity-50"
                >
                  {submitting ? "Working…" : "Create application anyway"}
                </button>
              </div>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Action
            </label>
            <select
              value={action}
              onChange={(e) =>
                setAction(
                  e.target.value as
                    | "create_job_application"
                    | "create_and_send_job_application"
                    | "prepare_job_application_form"
                )
              }
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white"
            >
              <option value="create_job_application">Create only</option>
              <option value="create_and_send_job_application">
                Create and send email
              </option>
              <option value="prepare_job_application_form">
                Prepare job application form
              </option>
            </select>
          </div>
          {action === "prepare_job_application_form" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Application questions
              </label>
              <div className="space-y-2">
                {formQuestions.map((q, idx) => (
                  <div key={idx} className="flex gap-2 items-start">
                    <input
                      type="text"
                      value={q}
                      onChange={(e) => {
                        const next = [...formQuestions];
                        next[idx] = e.target.value;
                        setFormQuestions(next);
                      }}
                      className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white"
                      placeholder="Question from the employer or form"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        if (formQuestions.length <= 1) return;
                        setFormQuestions(formQuestions.filter((_, i) => i !== idx));
                      }}
                      disabled={formQuestions.length <= 1}
                      className="shrink-0 p-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
                      aria-label="Remove question"
                    >
                      <HiOutlineTrash className="w-5 h-5" />
                    </button>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setFormQuestions([...formQuestions, ""])}
                className="mt-2 inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <HiOutlinePlus className="w-4 h-4" />
                Add question
              </button>
            </div>
          )}
          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {submitting ? "Working…" : "Proceed"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

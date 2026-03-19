"use client";

import { useEffect, useState, useRef } from "react";
import { HiXMark, HiOutlineBriefcase, HiOutlineUserGroup } from "react-icons/hi2";
import { jobApplicationService } from "@/services/jobApplicationService";
import { careerJobService } from "@/services/careerJobService";
import { JobApplication, CareerJob } from "@/types";
import JobDetailModal from "@/components/JobDetailModal";
import ClientDetailModal from "@/components/ClientDetailModal";

interface JobApplicationDetailModalProps {
  applicationId: number | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function JobApplicationDetailModal({
  applicationId,
  isOpen,
  onClose,
}: JobApplicationDetailModalProps) {
  const [application, setApplication] = useState<JobApplication | null>(null);
  const [loading, setLoading] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [jobModalOpen, setJobModalOpen] = useState(false);
  const [clientModalOpen, setClientModalOpen] = useState(false);
  const [job, setJob] = useState<CareerJob | null>(null);
  const blobUrlRef = useRef<string | null>(null);

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
    if (!isOpen || !applicationId) {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
      setApplication(null);
      setPdfUrl(null);
      setJob(null);
      setJobModalOpen(false);
      setClientModalOpen(false);
      return;
    }
    setLoading(true);
    jobApplicationService
      .getJobApplicationById(applicationId)
      .then((data) => {
        setApplication(data);
        if (data.output_resume_path) {
          return jobApplicationService
            .getJobApplicationFileBlobUrl(applicationId)
            .then((url) => {
              if (blobUrlRef.current) {
                URL.revokeObjectURL(blobUrlRef.current);
              }
              blobUrlRef.current = url;
              setPdfUrl(url);
            })
            .catch(() => setPdfUrl(null));
        }
      })
      .catch(() => setApplication(null))
      .finally(() => setLoading(false));

    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
    };
  }, [isOpen, applicationId]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div className="fixed inset-0 bg-black/50" />
      <div
        className="relative z-10 w-full max-w-6xl max-h-[90vh] flex flex-col bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-200 dark:border-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 flex items-center justify-between p-6 pb-4 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 shrink-0">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white pr-8 truncate">
            {loading
              ? "Loading..."
              : application?.career_job_title || "Job Application"}
          </h2>
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <HiXMark className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 min-h-0 flex overflow-hidden">
          <div className="w-1/2 min-w-0 border-r border-gray-200 dark:border-gray-800 overflow-y-auto p-6">
            {loading ? (
              <div className="animate-pulse space-y-4">
                <div className="h-4 w-3/4 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-4 w-1/2 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
            ) : application ? (
              <div className="space-y-5">
                <div>
                  <div className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
                    Job
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      careerJobService
                        .getCareerJob(application.career_job_id)
                        .then((data) => {
                          setJob(data);
                          setJobModalOpen(true);
                        });
                    }}
                    className="flex items-center gap-2 w-full text-left p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                  >
                    <HiOutlineBriefcase className="w-4 h-4 text-primary-600 dark:text-primary-400 shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {application.career_job_title}
                      </p>
                      {application.job_site_name && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {application.job_site_name}
                        </p>
                      )}
                    </div>
                  </button>
                </div>

                {application.similarity_score != null && (
                  <div>
                    <div className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                      Job Fit
                    </div>
                    <span
                      className={`inline-block text-sm px-3 py-1.5 rounded font-medium ${
                        (application.similarity_score ?? 0) >= 70
                          ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                          : (application.similarity_score ?? 0) >= 50
                            ? "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                      }`}
                    >
                      {Math.round(application.similarity_score)}% match
                    </span>
                  </div>
                )}

                {application.career_client_id && (
                  <div>
                    <div className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
                      Client
                    </div>
                    <button
                      type="button"
                      onClick={() => setClientModalOpen(true)}
                      className="flex items-center gap-2 w-full text-left p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <HiOutlineUserGroup className="w-4 h-4 text-primary-600 dark:text-primary-400 shrink-0" />
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {application.career_client_name || "View Client"}
                      </p>
                    </button>
                  </div>
                )}

                <div>
                  <div className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                    Resume
                  </div>
                  <p className="text-sm text-gray-900 dark:text-white">
                    {application.resume_name}
                  </p>
                </div>

                {application.subject && (
                  <div>
                    <div className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                      Subject
                    </div>
                    <p className="text-sm text-gray-900 dark:text-white">
                      {application.subject}
                    </p>
                  </div>
                )}

                {application.cover_letter && (
                  <div>
                    <div className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                      Cover Letter
                    </div>
                    <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {application.cover_letter}
                    </p>
                  </div>
                )}

                {application.to_emails && application.to_emails.length > 0 && (
                  <div>
                    <div className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                      To Emails
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {application.to_emails.map((email) => (
                        <a
                          key={email}
                          href={`mailto:${email}`}
                          className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
                        >
                          {email}
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                <div className="pt-3 border-t border-gray-200 dark:border-gray-800 text-xs text-gray-500 dark:text-gray-400">
                  Created: {new Date(application.created_at).toLocaleString()}
                </div>
              </div>
            ) : (
              !loading && (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Application not found.
                </p>
              )
            )}
          </div>

          <div className="w-1/2 min-w-0 flex flex-col p-6">
            <div className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
              Output Resume
            </div>
            {loading ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="animate-pulse w-full h-96 bg-gray-200 dark:bg-gray-700 rounded-lg" />
              </div>
            ) : pdfUrl ? (
              <iframe
                src={pdfUrl}
                title="Application Resume"
                className="flex-1 min-h-[500px] rounded-lg border border-gray-200 dark:border-gray-700"
              />
            ) : (
              <div className="flex-1 flex items-center justify-center rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No resume preview available
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      <JobDetailModal
        job={job}
        isOpen={jobModalOpen}
        onClose={() => {
          setJobModalOpen(false);
          setJob(null);
        }}
      />
      <ClientDetailModal
        clientId={application?.career_client_id ?? null}
        isOpen={clientModalOpen}
        onClose={() => setClientModalOpen(false)}
      />
    </div>
  );
}

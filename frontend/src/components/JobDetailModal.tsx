"use client";

import { useEffect } from "react";
import { HiXMark } from "react-icons/hi2";
import { CareerJob } from "@/types";

interface JobDetailModalProps {
  job: CareerJob | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function JobDetailModal({ job, isOpen, onClose }: JobDetailModalProps) {
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

  if (!isOpen || !job) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div className="fixed inset-0 bg-black/50" />
      <div
        className="relative z-10 w-full max-w-2xl max-h-[80vh] overflow-y-auto bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-200 dark:border-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 flex items-center justify-between p-6 pb-4 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white pr-8">
            {job.title}
          </h2>
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <HiXMark className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {job.job_site_name && (
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Job Site
              </span>
              <p className="mt-1 text-sm text-gray-900 dark:text-white">
                {job.job_site_name}
              </p>
            </div>
          )}

          {job.description && (
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Description
              </span>
              <p className="mt-1 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {job.description}
              </p>
            </div>
          )}

          {job.url && (
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                URL
              </span>
              <p className="mt-1">
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary-600 dark:text-primary-400 hover:underline break-all"
                >
                  {job.url}
                </a>
              </p>
            </div>
          )}

          {job.parsed_data &&
            (job.parsed_data.location ||
              job.parsed_data.salary ||
              job.parsed_data.company_name ||
              job.parsed_data.job_posted_datetime ||
              (job.parsed_data.company_emails?.length ?? 0) > 0 ||
              (job.parsed_data.company_numbers?.length ?? 0) > 0 ||
              (job.parsed_data.skills?.length ?? 0) > 0) && (
            <div className="space-y-4">
              {job.parsed_data.location && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Location
                  </span>
                  <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
                    {job.parsed_data.location}
                  </p>
                </div>
              )}
              {job.parsed_data.salary && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Salary
                  </span>
                  <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
                    {job.parsed_data.salary}
                  </p>
                </div>
              )}
              {job.parsed_data.company_name && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Company
                  </span>
                  <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
                    {job.parsed_data.company_name}
                  </p>
                </div>
              )}
              {job.parsed_data.job_posted_datetime && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Posted
                  </span>
                  <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
                    {job.parsed_data.job_posted_datetime}
                  </p>
                </div>
              )}
              {(job.parsed_data.company_emails?.length ?? 0) > 0 && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Company Emails
                  </span>
                  <div className="mt-1 space-y-1">
                    {(job.parsed_data.company_emails ?? []).map((email) => (
                      <a
                        key={email}
                        href={`mailto:${email}`}
                        className="block text-sm text-primary-600 dark:text-primary-400 hover:underline"
                      >
                        {email}
                      </a>
                    ))}
                  </div>
                </div>
              )}
              {(job.parsed_data.company_numbers?.length ?? 0) > 0 && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Company Numbers
                  </span>
                  <div className="mt-1 space-y-1">
                    {(job.parsed_data.company_numbers ?? []).map((num) => (
                      <a
                        key={num}
                        href={`tel:${num}`}
                        className="block text-sm text-primary-600 dark:text-primary-400 hover:underline"
                      >
                        {num}
                      </a>
                    ))}
                  </div>
                </div>
              )}
              {(job.parsed_data.skills?.length ?? 0) > 0 && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Skills
                  </span>
                  <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
                    {(job.parsed_data.skills ?? []).join(", ")}
                  </p>
                </div>
              )}
            </div>
          )}

          {job.meta_data && Object.keys(job.meta_data).length > 0 && (
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Metadata
              </span>
              <div className="mt-2 space-y-1">
                {Object.entries(job.meta_data).map(([key, value]) => (
                  <div key={key} className="flex gap-2 text-sm">
                    <span className="font-medium text-gray-600 dark:text-gray-400 capitalize">
                      {key.replace(/_/g, " ")}:
                    </span>
                    <span className="text-gray-700 dark:text-gray-300">
                      {String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="pt-3 border-t border-gray-200 dark:border-gray-800">
            <span className="text-xs text-gray-400">
              Created {new Date(job.created_at).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

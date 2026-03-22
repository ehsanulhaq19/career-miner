"use client";

import { useEffect, useState, useRef } from "react";
import { HiXMark } from "react-icons/hi2";
import { emailService, JobEmailLogDetail } from "@/services/emailService";

interface EmailLogDetailModalProps {
  emailLogId: number | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function EmailLogDetailModal({
  emailLogId,
  isOpen,
  onClose,
}: EmailLogDetailModalProps) {
  const [detail, setDetail] = useState<JobEmailLogDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [attachmentUrl, setAttachmentUrl] = useState<string | null>(null);
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
    if (!isOpen || !emailLogId) {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
      setDetail(null);
      setAttachmentUrl(null);
      return;
    }
    setLoading(true);
    setDetail(null);
    setAttachmentUrl(null);
    emailService
      .getJobEmailLogDetail(emailLogId)
      .then((data) => {
        setDetail(data);
        if (data.file_attachment) {
          return emailService.getAttachmentBlobUrl(emailLogId).then((url) => {
            if (blobUrlRef.current) {
              URL.revokeObjectURL(blobUrlRef.current);
            }
            blobUrlRef.current = url ?? null;
            setAttachmentUrl(url ?? null);
          });
        }
      })
      .finally(() => setLoading(false));

    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
    };
  }, [isOpen, emailLogId]);

  if (!isOpen) return null;

  const isPdf = detail?.file_attachment?.toLowerCase().endsWith(".pdf");

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
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800 shrink-0">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white truncate pr-4">
            {loading ? "Loading..." : detail?.subject ?? "Email Log"}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors shrink-0"
          >
            <HiXMark className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 min-h-0 flex overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6 space-y-6 border-r border-gray-200 dark:border-gray-800">
            {loading ? (
              <div className="animate-pulse space-y-4">
                <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-4 w-5/6 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-4 w-4/5 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
            ) : detail ? (
              <>
                <div>
                  <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                    Subject
                  </label>
                  <p className="text-sm text-gray-900 dark:text-white">
                    {detail.subject}
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                    To
                  </label>
                  <p className="text-sm text-gray-900 dark:text-white">
                    {detail.to_email}
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                    Status
                  </label>
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      detail.status === "success"
                        ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                        : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                    }`}
                  >
                    {detail.status}
                  </span>
                </div>
                {detail.content && (
                  <div>
                    <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                      Content
                    </label>
                    <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-sans bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 max-h-48 overflow-y-auto">
                      {detail.content}
                    </pre>
                  </div>
                )}
                <div>
                  <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                    Linked Job
                  </label>
                  <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-2">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {detail.career_job.title}
                    </p>
                    {detail.career_job.description && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                        {detail.career_job.description}
                      </p>
                    )}
                    {detail.career_job.url && (
                      <a
                        href={detail.career_job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
                      >
                        {detail.career_job.url}
                      </a>
                    )}
                  </div>
                </div>
                {detail.career_client && (
                  <div>
                    <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                      Linked Client
                    </label>
                    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-2">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {detail.career_client.name || `Client #${detail.career_client.id}`}
                      </p>
                      {detail.career_client.official_website && (
                        <a
                          href={detail.career_client.official_website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-primary-600 dark:text-primary-400 hover:underline block"
                        >
                          {detail.career_client.official_website}
                        </a>
                      )}
                      {detail.career_client.emails?.length > 0 && (
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          {detail.career_client.emails.join(", ")}
                        </p>
                      )}
                    </div>
                  </div>
                )}
                {detail.job_application && (
                  <div>
                    <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                      Application
                    </label>
                    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-2">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {detail.job_application.application_name}
                      </p>
                      {detail.job_application.subject && (
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          Subject: {detail.job_application.subject}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </>
            ) : null}
          </div>
          {detail?.file_attachment && (
            <div className="w-96 shrink-0 flex flex-col border-l border-gray-200 dark:border-gray-800">
              <div className="p-4 border-b border-gray-200 dark:border-gray-800">
                <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
                  Attachment
                </label>
                <p className="text-sm text-gray-900 dark:text-white truncate">
                  {detail.file_attachment}
                </p>
              </div>
              <div className="flex-1 min-h-0 p-4 overflow-hidden">
                {attachmentUrl ? (
                  isPdf ? (
                    <iframe
                      src={attachmentUrl}
                      title="Attachment preview"
                      className="w-full h-full min-h-[400px] rounded-lg border border-gray-200 dark:border-gray-700"
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
                      <p className="text-sm mb-2">Preview not available</p>
                      <a
                        href={attachmentUrl}
                        download={detail.file_attachment}
                        className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
                      >
                        Download attachment
                      </a>
                    </div>
                  )
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Loading attachment...
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

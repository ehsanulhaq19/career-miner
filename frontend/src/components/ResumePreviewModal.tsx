"use client";

import { useEffect, useState, useRef } from "react";
import { HiXMark } from "react-icons/hi2";
import { resumeService } from "@/services/resumeService";
import { Resume } from "@/types";

interface ResumePreviewModalProps {
  resumeId: number | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function ResumePreviewModal({
  resumeId,
  isOpen,
  onClose,
}: ResumePreviewModalProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [fallbackContent, setFallbackContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [resumeName, setResumeName] = useState<string>("Resume Preview");
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
    if (!isOpen || !resumeId) {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
      setPdfUrl(null);
      setFallbackContent(null);
      return;
    }
    setLoading(true);
    setFallbackContent(null);
    resumeService
      .getResumeById(resumeId)
      .then((resume: Resume) => {
        setResumeName(resume.name);
        return resumeService
          .getResumeFileBlobUrl(resumeId)
          .then((blobUrl) => {
            if (blobUrlRef.current) {
              URL.revokeObjectURL(blobUrlRef.current);
            }
            blobUrlRef.current = blobUrl;
            setPdfUrl(blobUrl);
          })
          .catch(() => {
            setFallbackContent(resume.content);
          });
      })
      .catch(() => {
        setFallbackContent("");
      })
      .finally(() => setLoading(false));

    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
    };
  }, [isOpen, resumeId]);

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
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800 shrink-0">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white truncate pr-4">
            {loading ? "Loading..." : resumeName}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors shrink-0"
          >
            <HiXMark className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 min-h-0 flex flex-col p-6 overflow-hidden">
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="animate-pulse space-y-4 w-full max-w-md">
                <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-4 w-5/6 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-4 w-4/5 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
            </div>
          ) : pdfUrl ? (
            <iframe
              src={pdfUrl}
              title={resumeName}
              className="w-full flex-1 min-h-[500px] rounded-lg border border-gray-200 dark:border-gray-700"
            />
          ) : fallbackContent !== null ? (
            fallbackContent ? (
              <pre className="flex-1 overflow-y-auto whitespace-pre-wrap font-sans text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                {fallbackContent}
              </pre>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No content available for this resume.
              </p>
            )
          ) : null}
        </div>
      </div>
    </div>
  );
}

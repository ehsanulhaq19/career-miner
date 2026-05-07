"use client";

import { useEffect, useState, useRef } from "react";
import {
  HiOutlineChevronLeft,
  HiOutlineChevronRight,
  HiOutlineDocumentArrowUp,
  HiOutlineDocumentText,
  HiOutlineMagnifyingGlass,
} from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import {
  fetchResumes,
  setPage,
  setNameFilter,
} from "@/store/slices/resumeSlice";
import { resumeService } from "@/services/resumeService";
import { Resume } from "@/types";
import ResumePreviewModal from "@/components/ResumePreviewModal";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ResumesPage() {
  const dispatch = useAppDispatch();
  const {
    items,
    total,
    page,
    limit,
    nameFilter,
    loading,
  } = useAppSelector((state) => state.resume);
  const [selectedResume, setSelectedResume] = useState<Resume | null>(null);
  const [uploading, setUploading] = useState(false);
  const [toast, setToast] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refetch = () => {
    const skip = (page - 1) * limit;
    dispatch(
      fetchResumes({
        skip,
        limit,
        name: nameFilter.trim() || undefined,
      })
    );
  };

  useEffect(() => {
    const skip = (page - 1) * limit;
    dispatch(
      fetchResumes({
        skip,
        limit,
        name: nameFilter.trim() || undefined,
      })
    );
  }, [dispatch, page, limit, nameFilter]);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setToast({ type: "error", text: "Only PDF files are allowed" });
      return;
    }
    setUploading(true);
    e.target.value = "";
    try {
      await resumeService.uploadResume(file);
      setToast({ type: "success", text: "Resume uploaded successfully" });
      dispatch(setPage(1));
      refetch();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to upload resume";
      setToast({ type: "error", text: msg });
    } finally {
      setUploading(false);
    }
  };

  const handleToggleActive = async (resume: Resume) => {
    try {
      await resumeService.updateResume(resume.id, {
        is_active: !resume.is_active,
      });
      setToast({
        type: "success",
        text: `Resume ${resume.is_active ? "deactivated" : "activated"}`,
      });
      refetch();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to update resume";
      setToast({ type: "error", text: msg });
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6">
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all ${
            toast.type === "success"
              ? "bg-green-50 dark:bg-green-900/80 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800"
              : "bg-red-50 dark:bg-red-900/80 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800"
          }`}
        >
          {toast.text}
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Resumes
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            className="hidden"
          />
          <button
            onClick={handleUploadClick}
            disabled={uploading}
            className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <HiOutlineDocumentArrowUp className="w-4 h-4" />
            {uploading ? "Uploading..." : "Upload Resume"}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-0 w-full sm:min-w-[200px] sm:max-w-sm">
          <HiOutlineMagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={nameFilter}
            onChange={(e) => {
              dispatch(setNameFilter(e.target.value));
              dispatch(setPage(1));
            }}
            placeholder="Search by name..."
            className="w-full pl-9 pr-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
          />
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
          <HiOutlineDocumentText className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-500 dark:text-gray-400 mb-2">
            No resumes found.
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mb-4">
            Upload a PDF resume to get started.
          </p>
          <button
            onClick={handleUploadClick}
            disabled={uploading}
            className="inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50"
          >
            <HiOutlineDocumentArrowUp className="w-4 h-4" />
            Upload Resume
          </button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {items.map((resume) => (
              <div
                key={resume.id}
                className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-5 cursor-pointer hover:border-primary-300 dark:hover:border-primary-600 transition-colors"
                role="button"
                tabIndex={0}
                onClick={() => setSelectedResume(resume)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelectedResume(resume);
                  }
                }}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="font-semibold text-gray-900 dark:text-white line-clamp-1 flex-1 min-w-0">
                    {resume.name}
                  </h3>
                  <span
                    className={`shrink-0 text-xs px-2 py-0.5 rounded ${
                      resume.is_active
                        ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                    }`}
                  >
                    {resume.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                  {formatFileSize(resume.size)} · {resume.extension.toUpperCase()}
                </p>
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  {new Date(resume.created_at).toLocaleDateString()}
                </p>
                {resume.extra_detail && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mt-1">
                    {resume.extra_detail}
                  </p>
                )}
                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 flex gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleToggleActive(resume);
                    }}
                    className="text-xs font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                  >
                    {resume.is_active ? "Deactivate" : "Activate"}
                  </button>
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
                  onClick={() => dispatch(setPage(page - 1))}
                  disabled={page <= 1}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <HiOutlineChevronLeft className="w-4 h-4" />
                  Previous
                </button>
                <button
                  onClick={() => dispatch(setPage(page + 1))}
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

      <ResumePreviewModal
        resumeId={selectedResume?.id ?? null}
        isOpen={!!selectedResume}
        onClose={() => setSelectedResume(null)}
        onUpdated={refetch}
      />
    </div>
  );
}

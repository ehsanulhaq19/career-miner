"use client";

import { useEffect, useState } from "react";
import { HiXMark } from "react-icons/hi2";
import { careerClientService } from "@/services/careerClientService";

interface ScanClientsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpdated?: () => void;
}

export default function ScanClientsModal({
  isOpen,
  onClose,
  onUpdated,
}: ScanClientsModalProps) {
  const [minDescription, setMinDescription] = useState("");
  const [matchingWords, setMatchingWords] = useState("");
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<number | null>(null);

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
    if (!isOpen) {
      setMinDescription("");
      setMatchingWords("");
      setResult(null);
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const minDesc = minDescription.trim() ? parseInt(minDescription, 10) : null;
    const words = matchingWords.trim() || null;
    if (!minDesc && !words) return;
    if (minDesc !== null && (isNaN(minDesc) || minDesc < 0)) return;
    setSaving(true);
    setResult(null);
    try {
      const data = await careerClientService.scanCareerClients({
        min_description: minDesc ?? undefined,
        matching_words: words ?? undefined,
      });
      setResult(data.deactivated_count);
      onUpdated?.();
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  const hasValidCriteria =
    (minDescription.trim() && !isNaN(parseInt(minDescription, 10))) ||
    matchingWords.trim();

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div className="fixed inset-0 bg-black/50" />
      <div
        className="relative z-10 w-full max-w-md bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-200 dark:border-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-6 pb-4 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Scan Clients
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <HiXMark className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
              Min Description Length
            </label>
            <input
              type="number"
              min={0}
              placeholder="e.g. 100"
              value={minDescription}
              onChange={(e) => setMinDescription(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Deactivate clients with description shorter than this
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
              Matching Words (comma separated)
            </label>
            <input
              type="text"
              placeholder="e.g. test, dummy, sample"
              value={matchingWords}
              onChange={(e) => setMatchingWords(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Deactivate clients whose name contains any of these words
            </p>
          </div>

          {result !== null && (
            <div className="p-3 rounded-lg bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 text-sm">
              {result} client{result !== 1 ? "s" : ""} deactivated
            </div>
          )}

          <div className="pt-3 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            >
              {result !== null ? "Close" : "Cancel"}
            </button>
            <button
              type="submit"
              disabled={saving || !hasValidCriteria}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
            >
              {saving ? "Scanning..." : "Scan"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

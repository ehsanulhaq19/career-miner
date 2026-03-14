"use client";

import { useEffect, useState } from "react";
import { HiXMark } from "react-icons/hi2";
import {
  careerClientService,
  CareerClientUpdatePayload,
} from "@/services/careerClientService";
import { CareerClient } from "@/types";

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

  const handleChange = (
    field: keyof CareerClientUpdatePayload,
    value: string | string[] | boolean | null
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
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
            {loading ? "Loading..." : client?.name || "Edit Client"}
          </h2>
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <HiXMark className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {loading ? (
            <div className="animate-pulse space-y-4">
              <div className="h-4 w-3/4 bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="h-4 w-1/2 bg-gray-200 dark:bg-gray-700 rounded" />
            </div>
          ) : client ? (
            <>
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
    </div>
  );
}

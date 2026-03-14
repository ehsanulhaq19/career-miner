"use client";

import { useEffect, useState } from "react";
import { HiXMark } from "react-icons/hi2";
import { careerClientService } from "@/services/careerClientService";
import { CareerClient } from "@/types";

interface ClientDetailModalProps {
  clientId: number | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function ClientDetailModal({
  clientId,
  isOpen,
  onClose,
}: ClientDetailModalProps) {
  const [client, setClient] = useState<CareerClient | null>(null);
  const [loading, setLoading] = useState(false);

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
      return;
    }
    setLoading(true);
    careerClientService
      .getCareerClientById(clientId)
      .then(setClient)
      .finally(() => setLoading(false));
  }, [isOpen, clientId]);

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
            {loading ? "Loading..." : client?.name || "Client Details"}
          </h2>
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <HiXMark className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {loading ? (
            <div className="animate-pulse space-y-4">
              <div className="h-4 w-3/4 bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="h-4 w-1/2 bg-gray-200 dark:bg-gray-700 rounded" />
            </div>
          ) : client ? (
            <>
              {client.name && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Name
                  </span>
                  <p className="mt-1 text-sm text-gray-900 dark:text-white">
                    {client.name}
                  </p>
                </div>
              )}

              {client.location && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Location
                  </span>
                  <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
                    {client.location}
                  </p>
                </div>
              )}

              {client.size && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Size
                  </span>
                  <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
                    {client.size}
                  </p>
                </div>
              )}

              {client.detail && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Detail
                  </span>
                  <p className="mt-1 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                    {client.detail}
                  </p>
                </div>
              )}

              {client.emails && client.emails.length > 0 && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Emails
                  </span>
                  <div className="mt-1 space-y-1">
                    {client.emails.map((email) => (
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

              {client.official_website && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Official Website
                  </span>
                  <p className="mt-1">
                    <a
                      href={client.official_website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary-600 dark:text-primary-400 hover:underline break-all"
                    >
                      {client.official_website}
                    </a>
                  </p>
                </div>
              )}

              {client.link && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Link
                  </span>
                  <p className="mt-1">
                    <a
                      href={client.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary-600 dark:text-primary-400 hover:underline break-all"
                    >
                      {client.link}
                    </a>
                  </p>
                </div>
              )}

              <div className="pt-3 border-t border-gray-200 dark:border-gray-800">
                <span className="text-xs text-gray-400">
                  Created{" "}
                  {new Date(client.created_at).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            </>
          ) : (
            !loading && (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Client not found.
              </p>
            )
          )}
        </div>
      </div>
    </div>
  );
}

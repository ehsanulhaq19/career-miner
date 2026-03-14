"use client";

import { useEffect, useState } from "react";
import {
  HiOutlineChevronLeft,
  HiOutlineChevronRight,
  HiOutlineUserGroup,
} from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import {
  fetchCareerClients,
  setHasEmailInformation,
  setPage,
} from "@/store/slices/careerClientSlice";
import { CareerClient } from "@/types";
import ClientDetailModal from "@/components/ClientDetailModal";

export default function ClientsPage() {
  const dispatch = useAppDispatch();
  const { items, total, page, limit, hasEmailInformation, loading } =
    useAppSelector((state) => state.careerClient);
  const [selectedClient, setSelectedClient] = useState<CareerClient | null>(
    null
  );

  useEffect(() => {
    const skip = (page - 1) * limit;
    dispatch(
      fetchCareerClients({
        skip,
        limit,
        hasEmailInformation: hasEmailInformation || undefined,
      })
    );
  }, [dispatch, page, limit, hasEmailInformation]);

  const totalPages = Math.ceil(total / limit);

  const handleHasEmailFilterChange = (checked: boolean) => {
    dispatch(setHasEmailInformation(checked));
    dispatch(setPage(1));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Clients
        </h2>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={hasEmailInformation}
            onChange={(e) => handleHasEmailFilterChange(e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">
            With emails only
          </span>
        </label>
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
          <HiOutlineUserGroup className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-500 dark:text-gray-400">No clients found.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {items.map((client) => (
              <ClientCard
                key={client.id}
                client={client}
                onClick={() => setSelectedClient(client)}
              />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 px-6 py-3">
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

      <ClientDetailModal
        clientId={selectedClient?.id ?? null}
        isOpen={!!selectedClient}
        onClose={() => setSelectedClient(null)}
      />
    </div>
  );
}

function ClientCard({
  client,
  onClick,
}: {
  client: CareerClient;
  onClick: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-5 cursor-pointer hover:border-primary-300 dark:hover:border-primary-600 transition-colors"
    >
      <h3 className="font-semibold text-gray-900 dark:text-white line-clamp-1 mb-2">
        {client.name || "Unnamed Client"}
      </h3>
      {client.location && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
          {client.location}
        </p>
      )}
      {client.size && (
        <p className="text-xs text-gray-400 dark:text-gray-500 mb-2">
          {client.size}
        </p>
      )}
      {client.emails && client.emails.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {client.emails.slice(0, 2).map((email) => (
            <a
              key={email}
              href={`mailto:${email}`}
              className="text-xs text-primary-600 dark:text-primary-400 hover:underline truncate max-w-full"
            >
              {email}
            </a>
          ))}
          {client.emails.length > 2 && (
            <span className="text-xs text-gray-400">
              +{client.emails.length - 2}
            </span>
          )}
        </div>
      )}
      {client.official_website && (
        <a
          href={client.official_website}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 block text-xs text-primary-600 dark:text-primary-400 hover:underline truncate"
        >
          {client.official_website}
        </a>
      )}
      {client.link && (
        <a
          href={client.link}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 block text-xs text-primary-600 dark:text-primary-400 hover:underline truncate"
        >
          {client.link}
        </a>
      )}
    </div>
  );
}

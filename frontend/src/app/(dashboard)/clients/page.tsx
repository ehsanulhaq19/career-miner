"use client";

import { useEffect, useRef, useState } from "react";
import {
  HiOutlineChevronDown,
  HiOutlineChevronLeft,
  HiOutlineChevronRight,
  HiOutlineMagnifyingGlassCircle,
  HiOutlinePencilSquare,
  HiOutlineUserGroup,
  HiOutlineTrash,
  HiOutlineEnvelope,
} from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import {
  fetchCareerClients,
  type ClientListFilter,
  type SourceFilter,
  setListFilter,
  setPage,
  setSourceFilter,
} from "@/store/slices/careerClientSlice";
import { CareerClient } from "@/types";
import ClientDetailModal from "@/components/ClientDetailModal";
import BulkEditModal from "@/components/BulkEditModal";
import ScanClientsModal from "@/components/ScanClientsModal";
import CleanEmailsModal from "@/components/CleanEmailsModal";
import BulkCareerClientEmailModal from "@/components/BulkCareerClientEmailModal";
import ImportClientsModal from "@/components/ImportClientsModal";

export default function ClientsPage() {
  const dispatch = useAppDispatch();
  const { items, total, page, limit, listFilter, sourceFilter, loading } =
    useAppSelector((state) => state.careerClient);
  const [selectedClient, setSelectedClient] = useState<CareerClient | null>(
    null
  );
  const [bulkEditOpen, setBulkEditOpen] = useState(false);
  const [scanModalOpen, setScanModalOpen] = useState(false);
  const [cleanEmailsOpen, setCleanEmailsOpen] = useState(false);
  const [bulkEmailOpen, setBulkEmailOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [openMenu, setOpenMenu] = useState<
    null | "bulk" | "actions" | "import"
  >(null);
  const bulkRef = useRef<HTMLDivElement>(null);
  const actionsRef = useRef<HTMLDivElement>(null);
  const importRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!openMenu) return;
    const onDoc = (e: MouseEvent) => {
      const n = e.target as Node;
      if (
        bulkRef.current?.contains(n) ||
        actionsRef.current?.contains(n) ||
        importRef.current?.contains(n)
      ) {
        return;
      }
      setOpenMenu(null);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [openMenu]);

  const refetch = () => {
    const skip = (page - 1) * limit;
    dispatch(
      fetchCareerClients({
        skip,
        limit,
        listFilter,
        sourceFilter,
      })
    );
  };

  useEffect(() => {
    const skip = (page - 1) * limit;
    dispatch(
      fetchCareerClients({
        skip,
        limit,
        listFilter,
        sourceFilter,
      })
    );
  }, [dispatch, page, limit, listFilter, sourceFilter]);

  const totalPages = Math.ceil(total / limit);

  const handleListFilterChange = (value: ClientListFilter) => {
    dispatch(setListFilter(value));
    dispatch(setPage(1));
  };

  const handleSourceFilterChange = (value: SourceFilter) => {
    dispatch(setSourceFilter(value));
    dispatch(setPage(1));
  };

  const menuBtn =
    "flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors";
  const menuPanel =
    "absolute right-0 mt-1 min-w-[11rem] py-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20";
  const menuItem =
    "w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/80";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Clients
        </h2>
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative" ref={bulkRef}>
            <button
              type="button"
              className={menuBtn}
              onClick={() =>
                setOpenMenu((m) => (m === "bulk" ? null : "bulk"))
              }
            >
              Bulk actions
              <HiOutlineChevronDown className="w-4 h-4 opacity-70" />
            </button>
            {openMenu === "bulk" && (
              <div className={menuPanel}>
                <button
                  type="button"
                  className={menuItem}
                  onClick={() => {
                    setOpenMenu(null);
                    setBulkEmailOpen(true);
                  }}
                >
                  <span className="inline-flex items-center gap-2">
                    <HiOutlineEnvelope className="w-4 h-4" />
                    Bulk email
                  </span>
                </button>
                <button
                  type="button"
                  className={menuItem}
                  onClick={() => {
                    setOpenMenu(null);
                    setBulkEditOpen(true);
                  }}
                >
                  <span className="inline-flex items-center gap-2">
                    <HiOutlinePencilSquare className="w-4 h-4" />
                    Bulk edit
                  </span>
                </button>
              </div>
            )}
          </div>

          <div className="relative" ref={actionsRef}>
            <button
              type="button"
              className={menuBtn}
              onClick={() =>
                setOpenMenu((m) => (m === "actions" ? null : "actions"))
              }
            >
              Actions
              <HiOutlineChevronDown className="w-4 h-4 opacity-70" />
            </button>
            {openMenu === "actions" && (
              <div className={menuPanel}>
                <button
                  type="button"
                  className={menuItem}
                  onClick={() => {
                    setOpenMenu(null);
                    setScanModalOpen(true);
                  }}
                >
                  <span className="inline-flex items-center gap-2">
                    <HiOutlineMagnifyingGlassCircle className="w-4 h-4" />
                    Scan clients
                  </span>
                </button>
                <button
                  type="button"
                  className={menuItem}
                  onClick={() => {
                    setOpenMenu(null);
                    setCleanEmailsOpen(true);
                  }}
                >
                  <span className="inline-flex items-center gap-2">
                    <HiOutlineTrash className="w-4 h-4" />
                    Clean emails
                  </span>
                </button>
              </div>
            )}
          </div>

          <div className="relative" ref={importRef}>
            <button
              type="button"
              className={menuBtn}
              onClick={() =>
                setOpenMenu((m) => (m === "import" ? null : "import"))
              }
            >
              Import
              <HiOutlineChevronDown className="w-4 h-4 opacity-70" />
            </button>
            {openMenu === "import" && (
              <div className={menuPanel}>
                <button
                  type="button"
                  className={menuItem}
                  onClick={() => {
                    setOpenMenu(null);
                    setImportOpen(true);
                  }}
                >
                  CSV
                </button>
              </div>
            )}
          </div>

          <select
            value={listFilter}
            onChange={(e) =>
              handleListFilterChange(e.target.value as ClientListFilter)
            }
            className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
          >
            <option value="all">All clients</option>
            <option value="with_email">With emails</option>
            <option value="without_email">Without emails</option>
            <option value="scrape_failed">Email scrape failed</option>
            <option value="scrape_ok">Email scrape OK</option>
          </select>

          <select
            value={sourceFilter}
            onChange={(e) =>
              handleSourceFilterChange(e.target.value as SourceFilter)
            }
            className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
          >
            <option value="all">All sources</option>
            <option value="with_source">Has import source</option>
          </select>
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
        onUpdated={refetch}
      />
      <BulkEditModal
        isOpen={bulkEditOpen}
        onClose={() => setBulkEditOpen(false)}
        onUpdated={refetch}
      />
      <ScanClientsModal
        isOpen={scanModalOpen}
        onClose={() => setScanModalOpen(false)}
        onUpdated={refetch}
      />
      <CleanEmailsModal
        isOpen={cleanEmailsOpen}
        onClose={() => setCleanEmailsOpen(false)}
        onUpdated={refetch}
      />
      <BulkCareerClientEmailModal
        isOpen={bulkEmailOpen}
        onClose={() => setBulkEmailOpen(false)}
      />
      <ImportClientsModal
        isOpen={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={refetch}
        initialFileType="csv"
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
  const src =
    typeof client.meta_data?.source === "string"
      ? client.meta_data.source.trim()
      : "";

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
      {src ? (
        <p className="text-xs font-medium text-primary-700 dark:text-primary-300 mb-2">
          Source: {src}
        </p>
      ) : null}
      {client.meta_data?.email_found_error === true && (
        <p className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-2">
          Email fetch failed
        </p>
      )}
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
              onClick={(e) => e.stopPropagation()}
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
          onClick={(e) => e.stopPropagation()}
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
          onClick={(e) => e.stopPropagation()}
          className="mt-2 block text-xs text-primary-600 dark:text-primary-400 hover:underline truncate"
        >
          {client.link}
        </a>
      )}
    </div>
  );
}

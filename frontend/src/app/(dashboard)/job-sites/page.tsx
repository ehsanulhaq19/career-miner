"use client";

import { useEffect, useState, FormEvent, KeyboardEvent } from "react";
import {
  HiOutlinePencilSquare,
  HiOutlineTrash,
  HiOutlinePlus,
  HiXMark,
} from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import {
  fetchJobSites,
  addJobSite,
  editJobSite,
  removeJobSite,
} from "@/store/slices/jobSiteSlice";
import { JobSite } from "@/types";

interface JobSiteFormData {
  name: string;
  url: string;
  is_active: boolean;
  scrap_duration: number;
  categories: string[];
}

const emptyForm: JobSiteFormData = {
  name: "",
  url: "",
  is_active: true,
  scrap_duration: 60,
  categories: [],
};

function timeAgo(date: string | null): string {
  if (!date) return "Never";
  const seconds = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function JobSitesPage() {
  const dispatch = useAppDispatch();
  const { items, loading } = useAppSelector((state) => state.jobSite);

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<JobSiteFormData>(emptyForm);
  const [categoryInput, setCategoryInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    dispatch(fetchJobSites());
  }, [dispatch]);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const openAddForm = () => {
    setForm(emptyForm);
    setEditingId(null);
    setCategoryInput("");
    setShowForm(true);
  };

  const openEditForm = (site: JobSite) => {
    setForm({
      name: site.name,
      url: site.url,
      is_active: site.is_active,
      scrap_duration: site.scrap_duration,
      categories: [...site.categories],
    });
    setEditingId(site.id);
    setCategoryInput("");
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingId(null);
    setForm(emptyForm);
  };

  const addCategory = (value: string) => {
    const trimmed = value.trim();
    if (trimmed && !form.categories.includes(trimmed)) {
      setForm({ ...form, categories: [...form.categories, trimmed] });
    }
    setCategoryInput("");
  };

  const handleCategoryKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addCategory(categoryInput);
    }
  };

  const removeCategory = (cat: string) => {
    setForm({ ...form, categories: form.categories.filter((c) => c !== cat) });
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingId) {
        await dispatch(editJobSite({ id: editingId, data: form })).unwrap();
        setToast({ type: "success", text: "Job site updated successfully." });
      } else {
        await dispatch(addJobSite(form)).unwrap();
        setToast({ type: "success", text: "Job site added successfully." });
      }
      closeForm();
      dispatch(fetchJobSites());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Operation failed.";
      setToast({ type: "error", text: msg });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await dispatch(removeJobSite(id)).unwrap();
      setToast({ type: "success", text: "Job site deleted successfully." });
      setDeleteConfirm(null);
      dispatch(fetchJobSites());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Delete failed.";
      setToast({ type: "error", text: msg });
    }
  };

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

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Job Sites</h2>
        <button
          onClick={openAddForm}
          className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          <HiOutlinePlus className="w-4 h-4" />
          Add Job Site
        </button>
      </div>

      {showForm && (
        <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-gray-900 dark:text-white">
              {editingId ? "Edit Job Site" : "New Job Site"}
            </h3>
            <button
              onClick={closeForm}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <HiXMark className="w-5 h-5" />
            </button>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                  className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
                  placeholder="e.g. LinkedIn"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  URL
                </label>
                <input
                  type="url"
                  value={form.url}
                  onChange={(e) => setForm({ ...form, url: e.target.value })}
                  required
                  className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
                  placeholder="https://example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Scrap Interval (minutes)
                </label>
                <input
                  type="number"
                  value={form.scrap_duration}
                  onChange={(e) => setForm({ ...form, scrap_duration: Number(e.target.value) })}
                  min={1}
                  required
                  className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
                />
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                    className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Active
                  </span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Categories
              </label>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                {form.categories.map((cat) => (
                  <span
                    key={cat}
                    className="inline-flex items-center gap-1 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full px-2.5 py-1 text-xs font-medium"
                  >
                    {cat}
                    <button
                      type="button"
                      onClick={() => removeCategory(cat)}
                      className="hover:text-primary-900 dark:hover:text-primary-100"
                    >
                      <HiXMark className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
              <input
                type="text"
                value={categoryInput}
                onChange={(e) => setCategoryInput(e.target.value)}
                onKeyDown={handleCategoryKeyDown}
                className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
                placeholder="Type a category and press Enter"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={submitting}
                className="bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
              >
                {submitting ? "Saving..." : editingId ? "Update" : "Create"}
              </button>
              <button
                type="button"
                onClick={closeForm}
                className="border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden">
        {loading && items.length === 0 ? (
          <div className="p-6 space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="animate-pulse flex items-center gap-4">
                <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-4 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-4 w-16 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-500 dark:text-gray-400">
              No job sites yet. Click &quot;Add Job Site&quot; to create one.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/50 text-gray-600 dark:text-gray-400">
                  <th className="text-left px-6 py-3 font-medium">Name</th>
                  <th className="text-left px-6 py-3 font-medium">URL</th>
                  <th className="text-left px-6 py-3 font-medium">Interval</th>
                  <th className="text-left px-6 py-3 font-medium">Categories</th>
                  <th className="text-left px-6 py-3 font-medium">Status</th>
                  <th className="text-left px-6 py-3 font-medium">Last Scrapped</th>
                  <th className="text-right px-6 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {items.map((site) => (
                  <tr
                    key={site.id}
                    className="text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors"
                  >
                    <td className="px-6 py-4 font-medium text-gray-900 dark:text-white">
                      {site.name}
                    </td>
                    <td className="px-6 py-4 max-w-[200px] truncate">{site.url}</td>
                    <td className="px-6 py-4">{site.scrap_duration}m</td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {site.categories.slice(0, 3).map((cat) => (
                          <span
                            key={cat}
                            className="bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-full px-2 py-0.5 text-xs"
                          >
                            {cat}
                          </span>
                        ))}
                        {site.categories.length > 3 && (
                          <span className="text-xs text-gray-400">
                            +{site.categories.length - 3}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`rounded-full px-2 py-1 text-xs font-medium ${
                          site.is_active
                            ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                            : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                        }`}
                      >
                        {site.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-500 dark:text-gray-400">
                      {timeAgo(site.last_scrapped as string | null)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => openEditForm(site)}
                          className="p-1.5 text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                          title="Edit"
                        >
                          <HiOutlinePencilSquare className="w-4 h-4" />
                        </button>
                        {deleteConfirm === site.id ? (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleDelete(site.id)}
                              className="px-2 py-1 text-xs bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                            >
                              Confirm
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(null)}
                              className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setDeleteConfirm(site.id)}
                            className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                            title="Delete"
                          >
                            <HiOutlineTrash className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import {
  HiOutlineMagnifyingGlass,
  HiOutlineFunnel,
  HiOutlineXMark,
  HiOutlineChevronLeft,
  HiOutlineChevronRight,
} from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import {
  fetchCareerJobs,
  setFilters,
  clearFilters,
  setPage,
} from "@/store/slices/careerJobSlice";
import { fetchJobSites } from "@/store/slices/jobSiteSlice";
import { CareerJob } from "@/types";
import JobDetailModal from "@/components/JobDetailModal";

export default function JobsPage() {
  const dispatch = useAppDispatch();
  const { items, total, page, limit, loading, filters } = useAppSelector(
    (state) => state.careerJob
  );
  const { items: jobSites } = useAppSelector((state) => state.jobSite);

  const [selectedJob, setSelectedJob] = useState<CareerJob | null>(null);
  const [searchInput, setSearchInput] = useState(filters.search ?? "");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    dispatch(fetchJobSites());
  }, [dispatch]);

  useEffect(() => {
    const skip = (page - 1) * limit;
    dispatch(
      fetchCareerJobs({
        skip,
        limit,
        job_site_id: filters.job_site_id,
        category: filters.category,
        search: filters.search,
      })
    );
  }, [dispatch, page, limit, filters]);

  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchInput(value);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        dispatch(setFilters({ search: value || undefined }));
        dispatch(setPage(1));
      }, 300);
    },
    [dispatch]
  );

  const handleJobSiteFilter = (value: string) => {
    dispatch(setFilters({ job_site_id: value ? Number(value) : undefined }));
    dispatch(setPage(1));
  };

  const handleCategoryFilter = (value: string) => {
    dispatch(setFilters({ category: value || undefined }));
    dispatch(setPage(1));
  };

  const handleClearFilters = () => {
    setSearchInput("");
    dispatch(clearFilters());
    dispatch(setPage(1));
  };

  const totalPages = Math.ceil(total / limit);
  const hasFilters = filters.search || filters.job_site_id || filters.category;

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <HiOutlineMagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search jobs by title..."
              className="w-full pl-9 pr-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
            />
          </div>
          <select
            value={filters.job_site_id ?? ""}
            onChange={(e) => handleJobSiteFilter(e.target.value)}
            className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
          >
            <option value="">All Job Sites</option>
            {jobSites.map((site) => (
              <option key={site.id} value={site.id}>
                {site.name}
              </option>
            ))}
          </select>
          <input
            type="text"
            value={filters.category ?? ""}
            onChange={(e) => handleCategoryFilter(e.target.value)}
            placeholder="Category"
            className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors sm:w-40"
          />
          {hasFilters && (
            <button
              onClick={handleClearFilters}
              className="flex items-center gap-1.5 border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
            >
              <HiOutlineXMark className="w-4 h-4" />
              Clear
            </button>
          )}
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
          <HiOutlineFunnel className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-500 dark:text-gray-400">
            {hasFilters ? "No jobs match your filters." : "No jobs found."}
          </p>
          {hasFilters && (
            <button
              onClick={handleClearFilters}
              className="mt-3 text-sm text-primary-600 dark:text-primary-400 hover:underline"
            >
              Clear all filters
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {items.map((job) => (
              <button
                key={job.id}
                onClick={() => setSelectedJob(job)}
                className="text-left bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-5 hover:border-primary-300 dark:hover:border-primary-700 hover:shadow-md transition-all"
              >
                <h3 className="font-semibold text-gray-900 dark:text-white line-clamp-1 mb-2">
                  {job.title}
                </h3>
                {job.description && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2 mb-3">
                    {job.description}
                  </p>
                )}
                <div className="flex items-center justify-between text-xs text-gray-400 dark:text-gray-500">
                  <span>{job.job_site_name ?? `Site #${job.job_site_id}`}</span>
                  <span>{new Date(job.created_at).toLocaleDateString()}</span>
                </div>
                {job.contact_details && (
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 truncate">
                    {job.contact_details}
                  </p>
                )}
              </button>
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

      <JobDetailModal
        job={selectedJob}
        isOpen={!!selectedJob}
        onClose={() => setSelectedJob(null)}
      />
    </div>
  );
}

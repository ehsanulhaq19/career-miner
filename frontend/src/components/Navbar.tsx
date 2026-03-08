"use client";

import { usePathname } from "next/navigation";
import { HiOutlineSun, HiOutlineMoon } from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { toggleTheme } from "@/store/slices/themeSlice";

const routeTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/job-sites": "Job Sites",
  "/jobs": "Jobs",
  "/profile": "Profile",
};

export default function Navbar() {
  const pathname = usePathname();
  const dispatch = useAppDispatch();
  const { mode } = useAppSelector((state) => state.theme);
  const { user } = useAppSelector((state) => state.auth);

  const title =
    routeTitles[pathname] ||
    Object.entries(routeTitles).find(([route]) => pathname.startsWith(route))?.[1] ||
    "Dashboard";

  return (
    <header className="h-16 flex items-center justify-between px-6 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
      <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
        {title}
      </h1>

      <div className="flex items-center gap-4">
        {user && (
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {user.first_name} {user.last_name}
          </span>
        )}
        <button
          onClick={() => dispatch(toggleTheme())}
          className="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          aria-label="Toggle theme"
        >
          {mode === "dark" ? (
            <HiOutlineSun className="w-5 h-5" />
          ) : (
            <HiOutlineMoon className="w-5 h-5" />
          )}
        </button>
      </div>
    </header>
  );
}

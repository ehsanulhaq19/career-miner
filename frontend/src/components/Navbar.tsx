"use client";

import { usePathname } from "next/navigation";
import { HiOutlineSun, HiOutlineMoon, HiBars3 } from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { toggleTheme } from "@/store/slices/themeSlice";

const routeTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/job-sites": "Job Sites",
  "/client-sites": "Client Sites",
  "/jobs": "Jobs",
  "/clients": "Clients",
  "/scrap": "Scrap",
  "/scrap-jobs": "Scrap Jobs",
  "/scrap-clients": "Scrap Clients",
  "/resumes": "Resumes",
  "/job-applications": "Job Applications",
  "/workflow": "Workflows",
  "/email-logs": "Email Logs",
  "/profile": "Profile",
  "/analytics": "Analytics",
};

type NavbarProps = {
  onMenuClick?: () => void;
};

export default function Navbar({ onMenuClick }: NavbarProps) {
  const pathname = usePathname();
  const dispatch = useAppDispatch();
  const { mode } = useAppSelector((state) => state.theme);
  const { user } = useAppSelector((state) => state.auth);

  const title =
    routeTitles[pathname] ||
    Object.entries(routeTitles).find(([route]) => pathname.startsWith(route))?.[1] ||
    "Dashboard";

  return (
    <header className="h-14 sm:h-16 shrink-0 flex items-center justify-between gap-3 px-4 sm:px-6 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
      <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
        <button
          type="button"
          className="md:hidden -ml-1 p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          onClick={onMenuClick}
          aria-label="Open navigation menu"
        >
          <HiBars3 className="w-6 h-6" />
        </button>
        <h1 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white truncate">
          {title}
        </h1>
      </div>

      <div className="flex items-center gap-2 sm:gap-4 shrink-0">
        {user && (
          <span className="hidden sm:inline text-sm text-gray-600 dark:text-gray-400 max-w-[10rem] lg:max-w-none truncate">
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

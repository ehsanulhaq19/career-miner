"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { IconType } from "react-icons";
import {
  HiOutlineHome,
  HiOutlineGlobeAlt,
  HiOutlineBuildingOffice2,
  HiOutlineBriefcase,
  HiOutlineCpuChip,
  HiOutlineUser,
  HiOutlineUserGroup,
  HiOutlineEnvelope,
  HiOutlineDocumentText,
  HiOutlineArrowRightOnRectangle,
  HiOutlinePaperAirplane,
  HiOutlineRectangleStack,
  HiOutlineSquares2X2,
  HiOutlineChevronDown,
} from "react-icons/hi2";
import { useAppDispatch } from "@/store/store";
import { logoutUser } from "@/store/slices/authSlice";

type NavItem = { label: string; href: string; icon: IconType };

const resourceItems: NavItem[] = [
  { label: "Job Sites", href: "/job-sites", icon: HiOutlineGlobeAlt },
  { label: "Client Sites", href: "/client-sites", icon: HiOutlineBuildingOffice2 },
  { label: "Scrap", href: "/scrap", icon: HiOutlineCpuChip },
  { label: "Jobs", href: "/jobs", icon: HiOutlineBriefcase },
  { label: "Clients", href: "/clients", icon: HiOutlineUserGroup },
];

const dashboardItem: NavItem = {
  label: "Dashboard",
  href: "/dashboard",
  icon: HiOutlineHome,
};

const mainNavItems: NavItem[] = [
  { label: "Resumes", href: "/resumes", icon: HiOutlineDocumentText },
  { label: "Job Applications", href: "/job-applications", icon: HiOutlinePaperAirplane },
  { label: "Workflows", href: "/workflow", icon: HiOutlineRectangleStack },
  { label: "Email Logs", href: "/email-logs", icon: HiOutlineEnvelope },
  { label: "Profile", href: "/profile", icon: HiOutlineUser },
];

function pathMatches(href: string, pathname: string) {
  if (pathname === href || pathname.startsWith(href + "/")) return true;
  if (
    href === "/scrap" &&
    (pathname.startsWith("/scrap-jobs") || pathname.startsWith("/scrap-clients"))
  ) {
    return true;
  }
  return false;
}

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const dispatch = useAppDispatch();

  const resourceActive = resourceItems.some((item) => pathMatches(item.href, pathname));
  const [resourcesOpen, setResourcesOpen] = useState(resourceActive);

  useEffect(() => {
    if (resourceActive) setResourcesOpen(true);
  }, [resourceActive, pathname]);

  const handleLogout = async () => {
    await dispatch(logoutUser());
    router.push("/login");
  };

  const linkClass = (active: boolean) =>
    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      active
        ? "bg-primary-50 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400"
        : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
    }`;

  const DashboardIcon = dashboardItem.icon;

  return (
    <aside className="w-64 h-screen flex flex-col bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800">
      <div className="px-6 py-5">
        <Link href="/dashboard" className="flex items-center gap-2">
          <HiOutlineBriefcase className="w-7 h-7 text-primary-600 dark:text-primary-400" />
          <span className="text-xl font-bold text-primary-600 dark:text-primary-400">
            CareerMiner
          </span>
        </Link>
      </div>

      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        <Link
          href={dashboardItem.href}
          className={linkClass(pathMatches(dashboardItem.href, pathname))}
        >
          <DashboardIcon className="w-5 h-5 shrink-0" />
          {dashboardItem.label}
        </Link>

        <div className="pt-0.5">
          <button
            type="button"
            onClick={() => setResourcesOpen((o) => !o)}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors w-full text-left ${
              resourceActive
                ? "bg-primary-50/80 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300"
                : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
            }`}
            aria-expanded={resourcesOpen}
          >
            <HiOutlineSquares2X2 className="w-5 h-5 shrink-0" />
            <span className="flex-1">Resources</span>
            <HiOutlineChevronDown
              className={`w-4 h-4 shrink-0 transition-transform ${resourcesOpen ? "rotate-180" : ""}`}
            />
          </button>
          {resourcesOpen && (
            <div className="mt-1 ml-2 pl-2 border-l border-gray-200 dark:border-gray-700 space-y-0.5">
              {resourceItems.map((item) => {
                const isActive = pathMatches(item.href, pathname);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`${linkClass(isActive)} pl-5 ml-1.5`}
                  >
                    <item.icon className="w-4 h-4 shrink-0" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {mainNavItems.map((item) => {
          const isActive = pathMatches(item.href, pathname);
          return (
            <Link key={item.href} href={item.href} className={linkClass(isActive)}>
              <item.icon className="w-5 h-5 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 pb-4">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium w-full text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
        >
          <HiOutlineArrowRightOnRectangle className="w-5 h-5" />
          Logout
        </button>
      </div>
    </aside>
  );
}

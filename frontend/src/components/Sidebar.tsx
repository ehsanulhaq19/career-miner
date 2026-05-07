"use client";

import { useEffect, useRef, useState } from "react";
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
  HiOutlineXMark,
  HiOutlineChevronDoubleLeft,
  HiOutlineChevronDoubleRight,
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

type SidebarProps = {
  mobileOpen?: boolean;
  onClose?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
};

export default function Sidebar({
  mobileOpen = false,
  onClose,
  collapsed = false,
  onToggleCollapse,
}: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const dispatch = useAppDispatch();
  const resourcesFlyoutRef = useRef<HTMLDivElement>(null);

  const resourceActive = resourceItems.some((item) => pathMatches(item.href, pathname));
  const [resourcesOpen, setResourcesOpen] = useState(resourceActive);
  const [resourcesFlyoutOpen, setResourcesFlyoutOpen] = useState(false);

  useEffect(() => {
    if (resourceActive) setResourcesOpen(true);
  }, [resourceActive, pathname]);

  useEffect(() => {
    onClose?.();
  }, [pathname, onClose]);

  useEffect(() => {
    if (!collapsed) setResourcesFlyoutOpen(false);
  }, [collapsed]);

  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileOpen, onClose]);

  useEffect(() => {
    if (!resourcesFlyoutOpen) return;
    const onDoc = (e: MouseEvent) => {
      if (resourcesFlyoutRef.current?.contains(e.target as Node)) return;
      setResourcesFlyoutOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [resourcesFlyoutOpen]);

  const handleLogout = async () => {
    await dispatch(logoutUser());
    router.push("/login");
  };

  const linkClass = (active: boolean) =>
    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      collapsed ? "md:justify-center md:gap-0 md:px-2" : ""
    } ${
      active
        ? "bg-primary-50 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400"
        : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
    }`;

  const resourceLinkClass = (active: boolean) =>
    `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
      active
        ? "bg-primary-50 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400"
        : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
    }`;

  const DashboardIcon = dashboardItem.icon;

  return (
    <>
      {mobileOpen ? (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => onClose?.()}
        />
      ) : null}

      <aside
        className={`fixed md:static inset-y-0 left-0 z-50 md:z-auto flex h-full md:h-screen shrink-0 flex-col border-r border-gray-200 bg-white transition-[width,transform] duration-200 ease-out dark:border-gray-800 dark:bg-gray-900 ${
          collapsed ? "md:w-16" : "md:w-64"
        } w-full max-w-full md:max-w-none ${
          mobileOpen ? "translate-x-0 shadow-xl md:shadow-none" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <div
          className={`flex items-center gap-2 border-b border-gray-100 px-4 py-4 dark:border-gray-800 md:border-0 md:py-4 ${
            collapsed ? "md:justify-center md:px-2" : "md:px-4"
          }`}
        >
          <Link
            href="/dashboard"
            className={`flex min-w-0 flex-1 items-center gap-2 md:flex-none ${
              collapsed ? "md:justify-center" : ""
            }`}
            onClick={() => onClose?.()}
            aria-label="Dashboard home"
          >
            <HiOutlineBriefcase className="h-7 w-7 shrink-0 text-primary-600 dark:text-primary-400" />
            <span
              className={`truncate text-xl font-bold text-primary-600 dark:text-primary-400 ${
                collapsed ? "md:hidden" : ""
              }`}
            >
              CareerMiner
            </span>
          </Link>
          <button
            type="button"
            className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 md:hidden"
            onClick={() => onClose?.()}
            aria-label="Close menu"
          >
            <HiOutlineXMark className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex flex-1 flex-col space-y-1 overflow-y-auto overscroll-contain px-3 pt-2">
          <Link
            href={dashboardItem.href}
            className={linkClass(pathMatches(dashboardItem.href, pathname))}
            onClick={() => onClose?.()}
            aria-label={collapsed ? dashboardItem.label : undefined}
          >
            <DashboardIcon className="h-5 w-5 shrink-0" />
            <span className={collapsed ? "md:hidden" : ""}>{dashboardItem.label}</span>
          </Link>

          <div className="pt-0.5">
            <div className={collapsed ? "md:hidden" : ""}>
              <button
                type="button"
                onClick={() => setResourcesOpen((o) => !o)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${
                  resourceActive
                    ? "bg-primary-50/80 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300"
                    : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
                }`}
                aria-expanded={resourcesOpen}
              >
                <HiOutlineSquares2X2 className="h-5 w-5 shrink-0" />
                <span className="flex-1">Resources</span>
                <HiOutlineChevronDown
                  className={`h-4 w-4 shrink-0 transition-transform ${resourcesOpen ? "rotate-180" : ""}`}
                />
              </button>
              {resourcesOpen && (
                <div className="ml-2 mt-1 space-y-0.5 border-l border-gray-200 pl-2 dark:border-gray-700">
                  {resourceItems.map((item) => {
                    const isActive = pathMatches(item.href, pathname);
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={`${linkClass(isActive)} ml-1.5 pl-5`}
                        onClick={() => onClose?.()}
                      >
                        <item.icon className="h-4 w-4 shrink-0" />
                        {item.label}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>

            {collapsed ? (
              <div className="relative hidden md:block" ref={resourcesFlyoutRef}>
                <button
                  type="button"
                  onClick={() => setResourcesFlyoutOpen((o) => !o)}
                  className={`flex w-full items-center justify-center rounded-lg px-2 py-2.5 text-sm font-medium transition-colors ${
                    resourceActive
                      ? "bg-primary-50/80 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300"
                      : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
                  }`}
                  aria-expanded={resourcesFlyoutOpen}
                  aria-label="Resources"
                  title="Resources"
                >
                  <HiOutlineSquares2X2 className="h-5 w-5 shrink-0" />
                </button>
                {resourcesFlyoutOpen ? (
                  <div className="absolute left-full top-0 z-50 ml-2 max-h-[min(70vh,24rem)] w-52 overflow-y-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-900">
                    {resourceItems.map((item) => {
                      const isActive = pathMatches(item.href, pathname);
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          className={`${resourceLinkClass(isActive)} mx-1`}
                          onClick={() => {
                            setResourcesFlyoutOpen(false);
                            onClose?.();
                          }}
                        >
                          <item.icon className="h-4 w-4 shrink-0" />
                          {item.label}
                        </Link>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          {mainNavItems.map((item) => {
            const isActive = pathMatches(item.href, pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={linkClass(isActive)}
                onClick={() => onClose?.()}
                aria-label={collapsed ? item.label : undefined}
                title={collapsed ? item.label : undefined}
              >
                <item.icon className="h-5 w-5 shrink-0" />
                <span className={collapsed ? "md:hidden" : ""}>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto border-t border-gray-100 px-3 pb-4 pt-2 dark:border-gray-800 md:border-0 md:pt-0">
          <button
            type="button"
            className="mb-2 hidden w-full items-center justify-center rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 md:flex"
            onClick={onToggleCollapse}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <HiOutlineChevronDoubleRight className="h-5 w-5" />
            ) : (
              <HiOutlineChevronDoubleLeft className="h-5 w-5" />
            )}
          </button>
          <button
            onClick={handleLogout}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-gray-600 transition-colors hover:bg-red-50 hover:text-red-600 dark:text-gray-400 dark:hover:bg-red-900/20 dark:hover:text-red-400 ${
              collapsed ? "md:justify-center md:px-2 md:gap-0" : ""
            }`}
            aria-label="Log out"
            title="Log out"
          >
            <HiOutlineArrowRightOnRectangle className="h-5 w-5 shrink-0" />
            <span className={collapsed ? "md:hidden" : ""}>Logout</span>
          </button>
        </div>
      </aside>
    </>
  );
}

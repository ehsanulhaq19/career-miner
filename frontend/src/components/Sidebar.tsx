"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  HiOutlineHome,
  HiOutlineGlobeAlt,
  HiOutlineBriefcase,
  HiOutlineCpuChip,
  HiOutlineUser,
  HiOutlineUserGroup,
  HiOutlineEnvelope,
  HiOutlineArrowRightOnRectangle,
} from "react-icons/hi2";
import { useAppDispatch } from "@/store/store";
import { logoutUser } from "@/store/slices/authSlice";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: HiOutlineHome },
  { label: "Job Sites", href: "/job-sites", icon: HiOutlineGlobeAlt },
  { label: "Scrap Jobs", href: "/scrap-jobs", icon: HiOutlineCpuChip },
  { label: "Scrap Clients", href: "/scrap-clients", icon: HiOutlineEnvelope },
  { label: "Jobs", href: "/jobs", icon: HiOutlineBriefcase },
  { label: "Clients", href: "/clients", icon: HiOutlineUserGroup },
  { label: "Profile", href: "/profile", icon: HiOutlineUser },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const dispatch = useAppDispatch();

  const handleLogout = async () => {
    await dispatch(logoutUser());
    router.push("/login");
  };

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

      <nav className="flex-1 px-3 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary-50 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              <item.icon className="w-5 h-5" />
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

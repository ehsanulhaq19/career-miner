"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { fetchCurrentUser } from "@/store/slices/authSlice";
import Sidebar from "@/components/Sidebar";
import Navbar from "@/components/Navbar";
import Loader from "@/components/Loader";
import WebSocketProvider from "@/components/WebSocketProvider";

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? match[2] : null;
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const { user, loading } = useAppSelector((state) => state.auth);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const closeMobileNav = useCallback(() => setMobileNavOpen(false), []);
  const openMobileNav = useCallback(() => setMobileNavOpen(true), []);

  useEffect(() => {
    try {
      if (localStorage.getItem("careerminer-sidebar-collapsed") === "1") {
        setSidebarCollapsed(true);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const toggleSidebarCollapsed = useCallback(() => {
    setSidebarCollapsed((c) => {
      const next = !c;
      try {
        localStorage.setItem("careerminer-sidebar-collapsed", next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  useEffect(() => {
    if (!mobileNavOpen) return;
    const mq = window.matchMedia("(max-width: 767px)");
    const applyScrollLock = () => {
      document.body.style.overflow = mq.matches ? "hidden" : "";
    };
    applyScrollLock();
    mq.addEventListener("change", applyScrollLock);
    return () => {
      mq.removeEventListener("change", applyScrollLock);
      document.body.style.overflow = "";
    };
  }, [mobileNavOpen]);

  useEffect(() => {
    const token = getCookie("token");
    if (!user && !token) {
      router.push("/login");
      return;
    }
    if (!user && token) {
      dispatch(fetchCurrentUser());
    }
  }, [user, dispatch, router]);

  if (loading && !user) {
    return <Loader size="md" />;
  }

  return (
    <WebSocketProvider>
      <div className="flex h-[100dvh] md:h-screen overflow-x-hidden bg-gray-50 dark:bg-gray-950">
        <Sidebar
          mobileOpen={mobileNavOpen}
          onClose={closeMobileNav}
          collapsed={sidebarCollapsed}
          onToggleCollapse={toggleSidebarCollapsed}
        />
        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          <Navbar onMenuClick={openMobileNav} />
          <main className="flex-1 overflow-y-auto overflow-x-hidden p-4 sm:p-6">
            {children}
          </main>
        </div>
      </div>
    </WebSocketProvider>
  );
}

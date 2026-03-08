"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { fetchCurrentUser } from "@/store/slices/authSlice";
import Sidebar from "@/components/Sidebar";
import Navbar from "@/components/Navbar";

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? match[2] : null;
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const { user, loading } = useAppSelector((state) => state.auth);

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
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-gray-500 dark:text-gray-400">Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}

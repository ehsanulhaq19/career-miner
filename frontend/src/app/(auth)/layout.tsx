"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();

  useEffect(() => {
    if (Cookies.get("token")) {
      router.replace("/dashboard");
    }
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900 px-4 py-8">
      <div className="w-full max-w-md">
        <div className="text-center mb-6 sm:mb-8">
          <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
            CareerMiner
          </h1>
          <p className="mt-2 text-sm sm:text-base text-primary-200">
            Discover opportunities, automated
          </p>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-6 sm:p-8">
          {children}
        </div>
      </div>
    </div>
  );
}

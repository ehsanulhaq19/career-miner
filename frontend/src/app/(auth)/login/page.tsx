"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { loginUser } from "@/store/slices/authSlice";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const dispatch = useAppDispatch();
  const { loading } = useAppSelector((state) => state.auth);
  const router = useRouter();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await dispatch(loginUser({ email, password })).unwrap();
      toast.success("Welcome back!");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(typeof err === "string" ? err : "Login failed");
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Sign in to your account
      </h2>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label
            htmlFor="email"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Email address
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition"
            placeholder="you@example.com"
          />
        </div>
        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition"
            placeholder="••••••••"
          />
        </div>
        <div className="flex items-center justify-end">
          <Link
            href="/forgot-password"
            className="text-sm text-primary-600 hover:text-primary-500 font-medium"
          >
            Forgot password?
          </Link>
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 px-4 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
              Signing in...
            </span>
          ) : (
            "Sign In"
          )}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
        Don&apos;t have an account?{" "}
        <Link
          href="/register"
          className="text-primary-600 hover:text-primary-500 font-semibold"
        >
          Create one
        </Link>
      </p>
    </div>
  );
}

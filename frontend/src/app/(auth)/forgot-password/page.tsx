"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { authService } from "@/services/authService";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { message } = await authService.forgotPassword(email);
      toast.success(message || "Reset link sent! Check your email.");
      setEmail("");
    } catch (err: any) {
      toast.error(
        err.response?.data?.detail || "Failed to send reset link"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
        Forgot your password?
      </h2>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
        Enter your email and we&apos;ll send you a reset link.
      </p>
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
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 px-4 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
              Sending...
            </span>
          ) : (
            "Send Reset Link"
          )}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
        Remember your password?{" "}
        <Link
          href="/login"
          className="text-primary-600 hover:text-primary-500 font-semibold"
        >
          Back to sign in
        </Link>
      </p>
    </div>
  );
}

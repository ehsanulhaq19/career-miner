"use client";

import { useState, FormEvent } from "react";
import { useAppSelector } from "@/store/store";
import { authService } from "@/services/authService";

export default function ProfilePage() {
  const { user } = useAppSelector((state) => state.auth);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handlePasswordUpdate = async (e: FormEvent) => {
    e.preventDefault();
    setMessage(null);

    if (newPassword !== confirmPassword) {
      setMessage({ type: "error", text: "New passwords do not match." });
      return;
    }
    if (newPassword.length < 6) {
      setMessage({ type: "error", text: "Password must be at least 6 characters." });
      return;
    }

    setLoading(true);
    try {
      await authService.updatePassword({ current_password: currentPassword, new_password: newPassword });
      setMessage({ type: "success", text: "Password updated successfully." });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update password.";
      setMessage({ type: "error", text: msg });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Profile Information
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              First Name
            </label>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {user?.first_name}
            </p>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Last Name
            </label>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {user?.last_name}
            </p>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Email
            </label>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {user?.email}
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Change Password
        </h2>

        {message && (
          <div
            className={`mb-4 px-4 py-3 rounded-lg text-sm ${
              message.type === "success"
                ? "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400"
                : "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400"
            }`}
          >
            {message.text}
          </div>
        )}

        <form onSubmit={handlePasswordUpdate} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Current Password
            </label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              New Password
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Confirm New Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          >
            {loading ? "Updating..." : "Update Password"}
          </button>
        </form>
      </div>
    </div>
  );
}

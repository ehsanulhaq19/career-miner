"use client";

import { useEffect } from "react";
import { useAppSelector, useAppDispatch } from "@/store/store";
import { setTheme } from "@/store/slices/themeSlice";

export default function ThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { mode } = useAppSelector((state) => state.theme);
  const dispatch = useAppDispatch();

  useEffect(() => {
    const saved = localStorage.getItem("theme") as "light" | "dark" | null;
    if (saved) {
      dispatch(setTheme(saved));
    } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      dispatch(setTheme("dark"));
    }
  }, [dispatch]);

  useEffect(() => {
    if (mode === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [mode]);

  return <>{children}</>;
}

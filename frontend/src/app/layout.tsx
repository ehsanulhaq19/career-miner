import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "react-hot-toast";
import StoreProvider from "@/store/provider";
import ThemeProvider from "@/components/ThemeProvider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CareerMiner",
  description: "Job scraping platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <StoreProvider>
          <ThemeProvider>
            {children}
            <Toaster position="top-right" />
          </ThemeProvider>
        </StoreProvider>
      </body>
    </html>
  );
}

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ScrapClientsRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/scrap?tab=clients");
  }, [router]);
  return null;
}

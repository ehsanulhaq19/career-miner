"use client";

import { useEffect, useRef } from "react";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { updateScrapJobFromSocket } from "@/store/slices/scrapJobSlice";
import {
  SCRAP_JOB_PENDING,
  SCRAP_JOB_IN_PROGRESS,
  SCRAP_JOB_COMPLETED,
  SCRAP_JOB_ERROR,
  SCRAP_JOB_TERMINATED,
  SCRAP_JOB_STOPPED,
} from "@/constants/socketMessageTypes";
import Cookies from "js-cookie";

const SCRAP_JOB_TYPES = [
  SCRAP_JOB_PENDING,
  SCRAP_JOB_IN_PROGRESS,
  SCRAP_JOB_COMPLETED,
  SCRAP_JOB_ERROR,
  SCRAP_JOB_TERMINATED,
  SCRAP_JOB_STOPPED,
];

function getWebSocketUrl(userId: number): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  const wsBase = baseUrl.replace(/^http/, "ws").replace("/api", "");
  const token = Cookies.get("token");
  return `${wsBase}/ws/scrap_job/${userId}?token=${encodeURIComponent(token || "")}`;
}

export default function WebSocketProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const dispatch = useAppDispatch();
  const { user, token } = useAppSelector((state) => state.auth);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const reconnectAttemptsRef = useRef(0);

  useEffect(() => {
    if (!user?.id || !token) return;

    const connect = () => {
      const url = getWebSocketUrl(user.id);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const { type, data } = message;
          if (!type || !data) return;
          if (!SCRAP_JOB_TYPES.includes(type)) return;

          const scrapJob = {
            id: data.id,
            name: data.name,
            job_site_id: data.job_site_id,
            status: data.status,
            created_at: data.created_at,
            updated_at: data.updated_at,
          };

          dispatch(updateScrapJobFromSocket(scrapJob));
        } catch {
          return;
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        const delay = Math.min(1000 * 2 ** reconnectAttemptsRef.current, 30000);
        reconnectAttemptsRef.current += 1;
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      };

      ws.onopen = () => {
        reconnectAttemptsRef.current = 0;
      };
    };

    connect();
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [user?.id, token, dispatch]);

  return <>{children}</>;
}

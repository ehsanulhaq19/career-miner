"use client";

import { useEffect, useRef } from "react";
import { useAppDispatch, useAppSelector } from "@/store/store";
import {
  updateScrapJobFromSocket,
  addScrapJobLogFromSocket,
} from "@/store/slices/scrapJobSlice";
import {
  updateScrapClientJobFromSocket,
  addScrapClientLogFromSocket,
} from "@/store/slices/scrapClientSlice";
import {
  SCRAP_JOB_PENDING,
  SCRAP_JOB_IN_PROGRESS,
  SCRAP_JOB_COMPLETED,
  SCRAP_JOB_ERROR,
  SCRAP_JOB_TERMINATED,
  SCRAP_JOB_STOPPED,
  SCRAP_JOB_LOG,
  SCRAP_CLIENT_PENDING,
  SCRAP_CLIENT_IN_PROGRESS,
  SCRAP_CLIENT_COMPLETED,
  SCRAP_CLIENT_ERROR,
  SCRAP_CLIENT_TERMINATED,
  SCRAP_CLIENT_STOPPED,
  SCRAP_CLIENT_LOG,
} from "@/constants/socketMessageTypes";
import Cookies from "js-cookie";

const SCRAP_JOB_TYPES = [
  SCRAP_JOB_PENDING,
  SCRAP_JOB_IN_PROGRESS,
  SCRAP_JOB_COMPLETED,
  SCRAP_JOB_ERROR,
  SCRAP_JOB_TERMINATED,
  SCRAP_JOB_STOPPED,
  SCRAP_JOB_LOG,
];

const SCRAP_CLIENT_TYPES = [
  SCRAP_CLIENT_PENDING,
  SCRAP_CLIENT_IN_PROGRESS,
  SCRAP_CLIENT_COMPLETED,
  SCRAP_CLIENT_ERROR,
  SCRAP_CLIENT_TERMINATED,
  SCRAP_CLIENT_STOPPED,
  SCRAP_CLIENT_LOG,
];

function getScrapJobWebSocketUrl(userId: number): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  const wsBase = baseUrl.replace(/^http/, "ws").replace("/api", "");
  const token = Cookies.get("token");
  return `${wsBase}/ws/scrap_job/${userId}?token=${encodeURIComponent(token || "")}`;
}

function getScrapClientWebSocketUrl(userId: number): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  const wsBase = baseUrl.replace(/^http/, "ws").replace("/api", "");
  const token = Cookies.get("token");
  return `${wsBase}/ws/scrap_client/${userId}?token=${encodeURIComponent(token || "")}`;
}

export default function WebSocketProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const dispatch = useAppDispatch();
  const { user, token } = useAppSelector((state) => state.auth);
  const scrapJobWsRef = useRef<WebSocket | null>(null);
  const scrapClientWsRef = useRef<WebSocket | null>(null);
  const scrapJobReconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const scrapClientReconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const scrapJobAttemptsRef = useRef(0);
  const scrapClientAttemptsRef = useRef(0);

  useEffect(() => {
    if (!user?.id || !token) return;

    const connectScrapJob = () => {
      const ws = new WebSocket(getScrapJobWebSocketUrl(user.id));
      scrapJobWsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const { type, data } = message;
          if (!type || !data) return;
          if (!SCRAP_JOB_TYPES.includes(type)) return;

          if (type === SCRAP_JOB_LOG) {
            dispatch(
              addScrapJobLogFromSocket({
                id: data.id,
                scrap_job_id: data.scrap_job_id,
                action: data.action,
                progress: data.progress,
                status: data.status,
                details: data.details,
                meta_data: data.meta_data || {},
                created_at: data.created_at,
              })
            );
            return;
          }

          dispatch(
            updateScrapJobFromSocket({
              id: data.id,
              name: data.name,
              job_site_id: data.job_site_id,
              status: data.status,
              created_at: data.created_at,
              updated_at: data.updated_at,
            })
          );
        } catch {
          return;
        }
      };

      ws.onclose = () => {
        scrapJobWsRef.current = null;
        const delay = Math.min(1000 * 2 ** scrapJobAttemptsRef.current, 30000);
        scrapJobAttemptsRef.current += 1;
        scrapJobReconnectRef.current = setTimeout(connectScrapJob, delay);
      };

      ws.onopen = () => {
        scrapJobAttemptsRef.current = 0;
      };
    };

    const connectScrapClient = () => {
      const ws = new WebSocket(getScrapClientWebSocketUrl(user.id));
      scrapClientWsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const { type, data } = message;
          if (!type || !data) return;
          if (!SCRAP_CLIENT_TYPES.includes(type)) return;

          if (type === SCRAP_CLIENT_LOG) {
            dispatch(
              addScrapClientLogFromSocket({
                id: data.id,
                scrap_client_job_id: data.scrap_client_job_id,
                action: data.action,
                progress: data.progress,
                status: data.status,
                details: data.details,
                meta_data: data.meta_data || {},
                created_at: data.created_at,
              })
            );
            return;
          }

          dispatch(
            updateScrapClientJobFromSocket({
              id: data.id,
              name: data.name,
              status: data.status,
              meta_data: data.meta_data || {},
              created_at: data.created_at,
              updated_at: data.updated_at,
            })
          );
        } catch {
          return;
        }
      };

      ws.onclose = () => {
        scrapClientWsRef.current = null;
        const delay = Math.min(1000 * 2 ** scrapClientAttemptsRef.current, 30000);
        scrapClientAttemptsRef.current += 1;
        scrapClientReconnectRef.current = setTimeout(connectScrapClient, delay);
      };

      ws.onopen = () => {
        scrapClientAttemptsRef.current = 0;
      };
    };

    connectScrapJob();
    connectScrapClient();

    return () => {
      if (scrapJobReconnectRef.current) {
        clearTimeout(scrapJobReconnectRef.current);
      }
      if (scrapClientReconnectRef.current) {
        clearTimeout(scrapClientReconnectRef.current);
      }
      if (scrapJobWsRef.current) {
        scrapJobWsRef.current.close();
        scrapJobWsRef.current = null;
      }
      if (scrapClientWsRef.current) {
        scrapClientWsRef.current.close();
        scrapClientWsRef.current = null;
      }
    };
  }, [user?.id, token, dispatch]);

  return <>{children}</>;
}

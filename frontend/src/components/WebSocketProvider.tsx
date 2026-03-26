"use client";

import { useEffect, useRef } from "react";
import { useAppDispatch, useAppSelector } from "@/store/store";
import {
  updateScrapJobFromSocket,
  addScrapJobLogFromSocket,
} from "@/store/slices/scrapJobSlice";
import { addBulkJobApplicationLogFromSocket } from "@/store/slices/bulkJobApplicationSlice";
import { addBulkEmailSendLogFromSocket } from "@/store/slices/bulkEmailSendSlice";
import { addBulkCareerClientEmailLogFromSocket } from "@/store/slices/bulkCareerClientEmailSlice";
import {
  updateScrapClientJobFromSocket,
  addScrapClientLogFromSocket,
} from "@/store/slices/scrapClientSlice";
import {
  clientEmailValidationCompletedFromSocket,
  clientEmailValidationErrorFromSocket,
  clientEmailValidationProgressFromSocket,
} from "@/store/slices/clientEmailValidationSlice";
import {
  BULK_JOB_APPLICATION_LOG,
  BULK_CAREER_CLIENT_EMAIL_SEND_LOG,
  BULK_JOB_APPLICATION_EMAIL_SEND_LOG,
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
  CLIENT_EMAIL_VALIDATION_PROGRESS,
  CLIENT_EMAIL_VALIDATION_COMPLETED,
  CLIENT_EMAIL_VALIDATION_ERROR,
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

function getBulkJobApplicationWebSocketUrl(userId: number): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  const wsBase = baseUrl.replace(/^http/, "ws").replace("/api", "");
  const token = Cookies.get("token");
  return `${wsBase}/ws/bulk_job_application/${userId}?token=${encodeURIComponent(token || "")}`;
}

function getBulkEmailSendWebSocketUrl(userId: number): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  const wsBase = baseUrl.replace(/^http/, "ws").replace("/api", "");
  const token = Cookies.get("token");
  return `${wsBase}/ws/bulk_job_application_email/${userId}?token=${encodeURIComponent(token || "")}`;
}

function getBulkCareerClientEmailWebSocketUrl(userId: number): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  const wsBase = baseUrl.replace(/^http/, "ws").replace("/api", "");
  const token = Cookies.get("token");
  return `${wsBase}/ws/bulk_career_client_email/${userId}?token=${encodeURIComponent(token || "")}`;
}

function getClientEmailValidationWebSocketUrl(userId: number): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  const wsBase = baseUrl.replace(/^http/, "ws").replace("/api", "");
  const token = Cookies.get("token");
  return `${wsBase}/ws/client_email_validation/${userId}?token=${encodeURIComponent(token || "")}`;
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
  const bulkJobApplicationWsRef = useRef<WebSocket | null>(null);
  const bulkEmailSendWsRef = useRef<WebSocket | null>(null);
  const bulkCareerClientEmailWsRef = useRef<WebSocket | null>(null);
  const clientEmailValidationWsRef = useRef<WebSocket | null>(null);
  const scrapJobReconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const scrapClientReconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const bulkJobApplicationReconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const bulkEmailSendReconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const bulkCareerClientEmailReconnectRef =
    useRef<ReturnType<typeof setTimeout>>();
  const clientEmailValidationReconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const scrapJobAttemptsRef = useRef(0);
  const scrapClientAttemptsRef = useRef(0);
  const bulkJobApplicationAttemptsRef = useRef(0);
  const bulkEmailSendAttemptsRef = useRef(0);
  const bulkCareerClientEmailAttemptsRef = useRef(0);

  useEffect(() => {
    if (!user?.id || !token) return;

    let clientEmailValidationReconnectAttempts = 0;

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

    const connectBulkJobApplication = () => {
      const ws = new WebSocket(getBulkJobApplicationWebSocketUrl(user.id));
      bulkJobApplicationWsRef.current = ws;
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const { type, data } = message;
          if (!type || !data) return;
          if (type !== BULK_JOB_APPLICATION_LOG) return;
          dispatch(
            addBulkJobApplicationLogFromSocket({
              id: data.id,
              bulk_job_application_id: data.bulk_job_application_id,
              action: data.action,
              progress: data.progress,
              status: data.status,
              details: data.details,
              meta_data: data.meta_data || {},
              created_at: data.created_at,
            })
          );
        } catch {
          return;
        }
      };
      ws.onclose = () => {
        bulkJobApplicationWsRef.current = null;
        const delay = Math.min(
          1000 * 2 ** bulkJobApplicationAttemptsRef.current,
          30000
        );
        bulkJobApplicationAttemptsRef.current += 1;
        bulkJobApplicationReconnectRef.current = setTimeout(
          connectBulkJobApplication,
          delay
        );
      };
      ws.onopen = () => {
        bulkJobApplicationAttemptsRef.current = 0;
      };
    };

    const connectBulkEmailSend = () => {
      const ws = new WebSocket(getBulkEmailSendWebSocketUrl(user.id));
      bulkEmailSendWsRef.current = ws;
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const { type, data } = message;
          if (!type || !data) return;
          if (type !== BULK_JOB_APPLICATION_EMAIL_SEND_LOG) return;
          dispatch(
            addBulkEmailSendLogFromSocket({
              id: data.id,
              bulk_job_application_email_send_id:
                data.bulk_job_application_email_send_id,
              action: data.action,
              progress: data.progress,
              status: data.status,
              details: data.details,
              meta_data: data.meta_data || {},
              created_at: data.created_at,
            })
          );
        } catch {
          return;
        }
      };
      ws.onclose = () => {
        bulkEmailSendWsRef.current = null;
        const delay = Math.min(
          1000 * 2 ** bulkEmailSendAttemptsRef.current,
          30000
        );
        bulkEmailSendAttemptsRef.current += 1;
        bulkEmailSendReconnectRef.current = setTimeout(
          connectBulkEmailSend,
          delay
        );
      };
      ws.onopen = () => {
        bulkEmailSendAttemptsRef.current = 0;
      };
    };

    const connectBulkCareerClientEmail = () => {
      const ws = new WebSocket(getBulkCareerClientEmailWebSocketUrl(user.id));
      bulkCareerClientEmailWsRef.current = ws;
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const { type, data } = message;
          if (!type || !data) return;
          if (type !== BULK_CAREER_CLIENT_EMAIL_SEND_LOG) return;
          dispatch(
            addBulkCareerClientEmailLogFromSocket({
              id: data.id,
              bulk_career_client_email_send_id:
                data.bulk_career_client_email_send_id,
              action: data.action,
              progress: data.progress,
              status: data.status,
              details: data.details,
              meta_data: data.meta_data || {},
              created_at: data.created_at,
            })
          );
        } catch {
          return;
        }
      };
      ws.onclose = () => {
        bulkCareerClientEmailWsRef.current = null;
        const delay = Math.min(
          1000 * 2 ** bulkCareerClientEmailAttemptsRef.current,
          30000
        );
        bulkCareerClientEmailAttemptsRef.current += 1;
        bulkCareerClientEmailReconnectRef.current = setTimeout(
          connectBulkCareerClientEmail,
          delay
        );
      };
      ws.onopen = () => {
        bulkCareerClientEmailAttemptsRef.current = 0;
      };
    };

    const connectClientEmailValidation = () => {
      const ws = new WebSocket(getClientEmailValidationWebSocketUrl(user.id));
      clientEmailValidationWsRef.current = ws;
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const { type, data } = message;
          if (!type || !data) return;
          if (type === CLIENT_EMAIL_VALIDATION_PROGRESS) {
            dispatch(
              clientEmailValidationProgressFromSocket({
                current: data.current,
                total: data.total,
                client_id: data.client_id,
                client_name: data.client_name,
              })
            );
            return;
          }
          if (type === CLIENT_EMAIL_VALIDATION_COMPLETED) {
            dispatch(
              clientEmailValidationCompletedFromSocket({
                invalid_clients: data.invalid_clients ?? [],
              })
            );
            return;
          }
          if (type === CLIENT_EMAIL_VALIDATION_ERROR) {
            dispatch(
              clientEmailValidationErrorFromSocket({
                message: data.message ?? "Validation failed",
              })
            );
          }
        } catch {
          return;
        }
      };
      ws.onclose = () => {
        clientEmailValidationWsRef.current = null;
        const delay = Math.min(
          1000 * 2 ** clientEmailValidationReconnectAttempts,
          30000
        );
        clientEmailValidationReconnectAttempts += 1;
        clientEmailValidationReconnectRef.current = setTimeout(
          connectClientEmailValidation,
          delay
        );
      };
      ws.onopen = () => {
        clientEmailValidationReconnectAttempts = 0;
      };
    };

    connectScrapJob();
    connectScrapClient();
    connectBulkJobApplication();
    connectBulkEmailSend();
    connectBulkCareerClientEmail();
    connectClientEmailValidation();

    return () => {
      if (scrapJobReconnectRef.current) {
        clearTimeout(scrapJobReconnectRef.current);
      }
      if (scrapClientReconnectRef.current) {
        clearTimeout(scrapClientReconnectRef.current);
      }
      if (bulkJobApplicationReconnectRef.current) {
        clearTimeout(bulkJobApplicationReconnectRef.current);
      }
      if (bulkEmailSendReconnectRef.current) {
        clearTimeout(bulkEmailSendReconnectRef.current);
      }
      if (bulkCareerClientEmailReconnectRef.current) {
        clearTimeout(bulkCareerClientEmailReconnectRef.current);
      }
      if (clientEmailValidationReconnectRef.current) {
        clearTimeout(clientEmailValidationReconnectRef.current);
      }
      if (bulkJobApplicationWsRef.current) {
        bulkJobApplicationWsRef.current.close();
        bulkJobApplicationWsRef.current = null;
      }
      if (bulkEmailSendWsRef.current) {
        bulkEmailSendWsRef.current.close();
        bulkEmailSendWsRef.current = null;
      }
      if (bulkCareerClientEmailWsRef.current) {
        bulkCareerClientEmailWsRef.current.close();
        bulkCareerClientEmailWsRef.current = null;
      }
      if (scrapJobWsRef.current) {
        scrapJobWsRef.current.close();
        scrapJobWsRef.current = null;
      }
      if (scrapClientWsRef.current) {
        scrapClientWsRef.current.close();
        scrapClientWsRef.current = null;
      }
      if (clientEmailValidationWsRef.current) {
        clientEmailValidationWsRef.current.close();
        clientEmailValidationWsRef.current = null;
      }
    };
  }, [user?.id, token, dispatch]);

  return <>{children}</>;
}

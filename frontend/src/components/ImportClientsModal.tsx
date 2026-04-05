"use client";

import { useEffect, useState } from "react";
import { HiXMark } from "react-icons/hi2";
import { careerClientService } from "@/services/careerClientService";
import type {
  CareerClientImportError,
  CareerClientImportResponse,
} from "@/types";

type ImportFileType = "csv";

const CHUNK = 100;

function parseCsvToMatrix(text: string): string[][] {
  const normalized = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let i = 0;
  let inQuotes = false;
  while (i < normalized.length) {
    const c = normalized[i];
    if (inQuotes) {
      if (c === '"') {
        if (normalized[i + 1] === '"') {
          field += '"';
          i += 2;
          continue;
        }
        inQuotes = false;
        i++;
        continue;
      }
      field += c;
      i++;
      continue;
    }
    if (c === '"') {
      inQuotes = true;
      i++;
      continue;
    }
    if (c === ",") {
      row.push(field);
      field = "";
      i++;
      continue;
    }
    if (c === "\n") {
      row.push(field);
      field = "";
      if (row.some((cell) => cell.trim() !== "")) rows.push(row);
      row = [];
      i++;
      continue;
    }
    field += c;
    i++;
  }
  if (field.length || row.length) {
    row.push(field);
    if (row.some((cell) => cell.trim() !== "")) rows.push(row);
  }
  return rows;
}

function normalizeHeader(h: string): string {
  return h.trim().toLowerCase().replace(/\s+/g, "_");
}

function splitList(s: string): string[] {
  const t = s.trim();
  if (!t) return [];
  return t
    .split(/[;\n]+/)
    .flatMap((p) => p.split(","))
    .map((p) => p.trim())
    .filter(Boolean);
}

function matrixToRowRecords(matrix: string[][]): Record<string, string>[] {
  if (matrix.length < 2) return [];
  const headers = matrix[0].map(normalizeHeader);
  const out: Record<string, string>[] = [];
  for (let r = 1; r < matrix.length; r++) {
    const cells = matrix[r];
    const obj: Record<string, string> = {};
    headers.forEach((h, j) => {
      obj[h] = (cells[j] ?? "").trim();
    });
    if (Object.values(obj).some((v) => v.length > 0)) out.push(obj);
  }
  return out;
}

function pick(row: Record<string, string>, keys: string[]): string {
  for (const k of keys) {
    if (row[k] !== undefined && row[k] !== "") return row[k];
  }
  return "";
}

function rowToImportClient(row: Record<string, string>): Record<string, unknown> {
  const emailRaw = pick(row, ["emails", "email"]);
  const phoneRaw = pick(row, ["phone_numbers", "phones", "phone", "phone_number"]);
  return {
    emails: splitList(emailRaw),
    official_website:
      pick(row, ["official_website", "offical_website", "website", "url"]) ||
      null,
    name: pick(row, ["name", "company", "company_name"]) || null,
    location: pick(row, ["location", "city"]) || null,
    detail: pick(row, ["detail", "description", "notes"]) || null,
    phone_numbers: splitList(phoneRaw),
  };
}

export interface ImportClientsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImported?: () => void;
  initialFileType?: ImportFileType;
}

export default function ImportClientsModal({
  isOpen,
  onClose,
  initialFileType = "csv",
  onImported,
}: ImportClientsModalProps) {
  const [fileType, setFileType] = useState<ImportFileType>(initialFileType);
  const [sourceName, setSourceName] = useState("");
  const [fileLabel, setFileLabel] = useState("");
  const [previewHeaders, setPreviewHeaders] = useState<string[]>([]);
  const [previewRows, setPreviewRows] = useState<string[][]>([]);
  const [clientsPayload, setClientsPayload] = useState<Record<string, unknown>[]>(
    []
  );
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [totalCreated, setTotalCreated] = useState(0);
  const [totalUpdated, setTotalUpdated] = useState(0);
  const [batchResults, setBatchResults] = useState<
    {
      batchIndex: number;
      res: CareerClientImportResponse;
    }[]
  >([]);

  useEffect(() => {
    if (!isOpen) return;
    setFileType(initialFileType);
    setSourceName("");
    setFileLabel("");
    setPreviewHeaders([]);
    setPreviewRows([]);
    setClientsPayload([]);
    setRunning(false);
    setProgress(0);
    setTotalCreated(0);
    setTotalUpdated(0);
    setBatchResults([]);
  }, [isOpen, initialFileType]);

  const handleClose = () => {
    onClose();
  };

  if (!isOpen) return null;

  const readFile = (file: File) => {
    setFileLabel(file.name);
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result ?? "");
      if (fileType === "csv") {
        const matrix = parseCsvToMatrix(text);
        if (matrix.length === 0) {
          setPreviewHeaders([]);
          setPreviewRows([]);
          setClientsPayload([]);
          return;
        }
        const headers = matrix[0].map((h) => h.trim());
        const body = matrix.slice(1);
        setPreviewHeaders(headers);
        setPreviewRows(body);
        const records = matrixToRowRecords(matrix);
        setClientsPayload(records.map(rowToImportClient));
      }
    };
    reader.readAsText(file);
  };

  const runImport = async () => {
    const src = sourceName.trim();
    if (!src || clientsPayload.length === 0 || running) return;
    setRunning(true);
    setProgress(0);
    setTotalCreated(0);
    setTotalUpdated(0);
    setBatchResults([]);
    const chunks: Record<string, unknown>[][] = [];
    for (let i = 0; i < clientsPayload.length; i += CHUNK) {
      chunks.push(clientsPayload.slice(i, i + CHUNK));
    }
    let createdAcc = 0;
    let updatedAcc = 0;
    const results: { batchIndex: number; res: CareerClientImportResponse }[] =
      [];
    for (let b = 0; b < chunks.length; b++) {
      const res = await careerClientService.importCareerClients(src, chunks[b]);
      createdAcc += res.created_count;
      updatedAcc += res.updated_count;
      results.push({ batchIndex: b, res });
      setBatchResults([...results]);
      setTotalCreated(createdAcc);
      setTotalUpdated(updatedAcc);
      setProgress(Math.round(((b + 1) / chunks.length) * 100));
    }
    setRunning(false);
    onImported?.();
  };

  const flatErrors: (CareerClientImportError & {
    globalRow: number;
    batchIndex: number;
  })[] = batchResults.flatMap(({ batchIndex, res }) =>
    res.errors.map((e) => ({
      ...e,
      batchIndex,
      globalRow: batchIndex * CHUNK + e.index,
    }))
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-200 dark:border-gray-800 max-w-5xl w-full max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-800">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Import clients
          </h3>
          <button
            type="button"
            onClick={handleClose}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
            aria-label="Close"
          >
            <HiXMark className="w-5 h-5" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4 overflow-y-auto flex-1">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Import file type
              </label>
              <select
                value={fileType}
                onChange={(e) =>
                  setFileType(e.target.value as ImportFileType)
                }
                className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
                <option value="csv">CSV</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Source name
              </label>
              <input
                type="text"
                value={sourceName}
                onChange={(e) => setSourceName(e.target.value)}
                placeholder="e.g. conference_2026"
                className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white"
              />
            </div>
          </div>

          <div>
            <input
              type="file"
              accept={fileType === "csv" ? ".csv,text/csv" : undefined}
              className="hidden"
              id="import-clients-file"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) readFile(f);
                e.target.value = "";
              }}
            />
            <label
              htmlFor="import-clients-file"
              className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Upload file
            </label>
            {fileLabel && (
              <span className="ml-3 text-sm text-gray-600 dark:text-gray-400">
                {fileLabel}
              </span>
            )}
          </div>

          {previewHeaders.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                File preview
              </p>
              <div className="overflow-auto max-h-56 rounded-lg border border-gray-200 dark:border-gray-800">
                <table className="min-w-full text-xs text-left">
                  <thead className="bg-gray-50 dark:bg-gray-800/80 sticky top-0">
                    <tr>
                      {previewHeaders.map((h) => (
                        <th
                          key={h}
                          className="px-2 py-2 font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((cells, ri) => (
                      <tr
                        key={ri}
                        className="border-t border-gray-100 dark:border-gray-800"
                      >
                        {previewHeaders.map((_, ci) => (
                          <td
                            key={ci}
                            className="px-2 py-1 text-gray-600 dark:text-gray-400 whitespace-nowrap max-w-[12rem] truncate"
                            title={cells[ci] ?? ""}
                          >
                            {cells[ci] ?? ""}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">
                {clientsPayload.length} row{clientsPayload.length !== 1 ? "s" : ""}{" "}
                ready
              </p>
            </div>
          )}

          {running || batchResults.length > 0 ? (
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400">
                <span>Progress</span>
                <span>{progress}%</span>
              </div>
              <div className="h-2 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                Created: {totalCreated.toLocaleString()} · Updated:{" "}
                {totalUpdated.toLocaleString()}
              </p>
              {flatErrors.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Errors by batch
                  </p>
                  <div className="overflow-auto max-h-48 rounded-lg border border-gray-200 dark:border-gray-800">
                    <table className="min-w-full text-xs">
                      <thead className="bg-gray-50 dark:bg-gray-800/80">
                        <tr>
                          <th className="px-2 py-2 text-left">Batch</th>
                          <th className="px-2 py-2 text-left">Row</th>
                          <th className="px-2 py-2 text-left">Message</th>
                          <th className="px-2 py-2 text-left">Record</th>
                        </tr>
                      </thead>
                      <tbody>
                        {flatErrors.map((err, i) => (
                          <tr
                            key={`${err.batchIndex}-${err.index}-${i}`}
                            className="border-t border-gray-100 dark:border-gray-800"
                          >
                            <td className="px-2 py-1 align-top">
                              {err.batchIndex + 1}
                            </td>
                            <td className="px-2 py-1 align-top">
                              {err.globalRow + 1}
                            </td>
                            <td className="px-2 py-1 align-top text-amber-700 dark:text-amber-300">
                              {err.message}
                            </td>
                            <td className="px-2 py-1 align-top font-mono text-[10px] max-w-xs truncate">
                              {JSON.stringify(err.record)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>

        <div className="px-5 py-4 border-t border-gray-200 dark:border-gray-800 flex justify-end gap-2">
          <button
            type="button"
            onClick={handleClose}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300"
          >
            Close
          </button>
          <button
            type="button"
            disabled={
              running ||
              !sourceName.trim() ||
              clientsPayload.length === 0
            }
            onClick={runImport}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Proceed with uploaded file
          </button>
        </div>
      </div>
    </div>
  );
}

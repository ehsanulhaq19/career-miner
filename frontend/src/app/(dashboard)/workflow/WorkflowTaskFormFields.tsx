"use client";

import type {
  CareerClient,
  CareerJob,
  ClientSite,
  JobApplication,
  JobSite,
  Resume,
} from "@/types";
import {
  WORKFLOW_TASK_MODELS,
  isTaskModelType,
  type WorkflowTaskRowForm,
  switchTaskModel,
} from "./workflowTaskForm";

const inputClass =
  "mt-1 w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm";
const labelClass = "block text-sm text-gray-600 dark:text-gray-400";
const hintClass = "text-xs text-gray-500 dark:text-gray-500 mt-0.5";

function MultiSelect({
  label,
  hint,
  options,
  selected,
  onChange,
}: {
  label: string;
  hint?: string;
  options: { value: number; label: string }[];
  selected: number[];
  onChange: (ids: number[]) => void;
}) {
  return (
    <label className="block text-sm">
      <span className={labelClass}>{label}</span>
      {hint ? <p className={hintClass}>{hint}</p> : null}
      <select
        multiple
        className={`${inputClass} min-h-[132px]`}
        value={selected.map(String)}
        onChange={(e) => {
          const vals = Array.from(e.target.selectedOptions, (o) =>
            Number(o.value)
          );
          onChange(vals);
        }}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export interface WorkflowTaskFormFieldsProps {
  row: WorkflowTaskRowForm;
  jobSites: JobSite[];
  clientSites: ClientSite[];
  resumes: Resume[];
  careerJobs: CareerJob[];
  careerClients: CareerClient[];
  jobApplications: JobApplication[];
  onChange: (row: WorkflowTaskRowForm) => void;
  onRemove?: () => void;
}

export default function WorkflowTaskFormFields({
  row,
  jobSites,
  clientSites,
  resumes,
  careerJobs,
  careerClients,
  jobApplications,
  onChange,
  onRemove,
}: WorkflowTaskFormFieldsProps) {
  const activeJobSites = jobSites.filter((s) => s.is_active);
  const activeClientSites = clientSites.filter((s) => s.is_active);
  const activeResumes = resumes.filter((r) => r.is_active);
  const activeCareerClients = careerClients.filter((c) => c.is_active);

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 space-y-3">
      <label className="block text-sm">
        <span className={labelClass}>Task type</span>
        <select
          className={inputClass}
          value={row.linked_task_model}
          onChange={(e) => {
            const v = e.target.value;
            if (isTaskModelType(v)) {
              onChange(switchTaskModel(row, v));
            }
          }}
        >
          {WORKFLOW_TASK_MODELS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-2 text-sm cursor-pointer">
        <input
          type="checkbox"
          checked={row.is_active}
          onChange={(e) =>
            onChange({ ...row, is_active: e.target.checked })
          }
        />
        <span className="text-gray-700 dark:text-gray-300">Task active</span>
      </label>

      <label className="block text-sm">
        <span className={labelClass}>Priority (higher runs first)</span>
        <input
          type="number"
          className={inputClass}
          value={row.priority}
          onChange={(e) =>
            onChange({ ...row, priority: Number(e.target.value) })
          }
        />
      </label>

      {row.linked_task_model === "ScrapJob" && (
        <div className="space-y-3 pt-1 border-t border-gray-100 dark:border-gray-800">
          <label className="block text-sm">
            <span className={labelClass}>Job site</span>
            <select
              className={inputClass}
              value={row.job_site_id === "" ? "" : String(row.job_site_id)}
              onChange={(e) =>
                onChange({
                  ...row,
                  job_site_id: e.target.value === "" ? "" : Number(e.target.value),
                })
              }
            >
              <option value="">Select job site…</option>
              {activeJobSites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className={labelClass}>Run name (optional)</span>
            <input
              className={inputClass}
              value={row.scrap_name}
              placeholder="Auto-generated if empty"
              onChange={(e) =>
                onChange({ ...row, scrap_name: e.target.value })
              }
            />
          </label>
          <label className="block text-sm">
            <span className={labelClass}>Categories (optional)</span>
            <p className={hintClass}>
              Comma-separated; leave empty to use the job site defaults.
            </p>
            <input
              className={inputClass}
              value={row.categories_input}
              placeholder="e.g. engineering, remote"
              onChange={(e) =>
                onChange({ ...row, categories_input: e.target.value })
              }
            />
          </label>
          <label className="block text-sm">
            <span className={labelClass}>Max pages per scrap (optional)</span>
            <input
              type="number"
              className={inputClass}
              value={row.max_pages_per_scrap}
              placeholder="Site default if empty"
              onChange={(e) =>
                onChange({ ...row, max_pages_per_scrap: e.target.value })
              }
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={row.process_with_llm}
              onChange={(e) =>
                onChange({ ...row, process_with_llm: e.target.checked })
              }
            />
            Process with LLM
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={row.load_more_on_scroll}
              onChange={(e) =>
                onChange({ ...row, load_more_on_scroll: e.target.checked })
              }
            />
            Load more on scroll
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm">
              <span className={labelClass}>Max scroll</span>
              <input
                type="number"
                className={inputClass}
                value={row.max_scroll}
                placeholder="10"
                onChange={(e) =>
                  onChange({ ...row, max_scroll: e.target.value })
                }
              />
            </label>
            <label className="block text-sm">
              <span className={labelClass}>Depth levels</span>
              <input
                type="number"
                className={inputClass}
                value={row.depth_levels}
                placeholder="0"
                onChange={(e) =>
                  onChange({ ...row, depth_levels: e.target.value })
                }
              />
            </label>
          </div>
        </div>
      )}

      {row.linked_task_model === "ScrapClientJob" && (
        <div className="space-y-3 pt-1 border-t border-gray-100 dark:border-gray-800">
          <label className="block text-sm">
            <span className={labelClass}>Mode</span>
            <select
              className={inputClass}
              value={row.scrap_client_mode}
              onChange={(e) =>
                onChange({
                  ...row,
                  scrap_client_mode: e.target.value as
                    | "site"
                    | "url"
                    | "email",
                })
              }
            >
              <option value="site">Client site (saved client site)</option>
              <option value="url">URL (single page)</option>
              <option value="email">Email discovery (career clients)</option>
            </select>
          </label>
          <label className="block text-sm">
            <span className={labelClass}>Job name (optional)</span>
            <input
              className={inputClass}
              value={row.scrap_client_name}
              onChange={(e) =>
                onChange({ ...row, scrap_client_name: e.target.value })
              }
            />
          </label>

          {row.scrap_client_mode === "site" && (
            <label className="block text-sm">
              <span className={labelClass}>Client site</span>
              <select
                className={inputClass}
                value={
                  row.client_site_id === "" ? "" : String(row.client_site_id)
                }
                onChange={(e) =>
                  onChange({
                    ...row,
                    client_site_id:
                      e.target.value === "" ? "" : Number(e.target.value),
                  })
                }
              >
                <option value="">Select client site…</option>
                {activeClientSites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          {row.scrap_client_mode === "url" && (
            <label className="block text-sm">
              <span className={labelClass}>URL</span>
              <input
                className={inputClass}
                value={row.scrap_client_url}
                placeholder="https://…"
                onChange={(e) =>
                  onChange({ ...row, scrap_client_url: e.target.value })
                }
              />
            </label>
          )}

          {row.scrap_client_mode === "email" && (
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={row.use_previous_career_clients}
                  onChange={(e) =>
                    onChange({
                      ...row,
                      use_previous_career_clients: e.target.checked,
                    })
                  }
                />
                Use career clients from previous workflow step
              </label>
              {!row.use_previous_career_clients && (
                <MultiSelect
                  label="Career clients"
                  hint="Hold Ctrl/Cmd to select multiple."
                  options={activeCareerClients.map((c) => ({
                    value: c.id,
                    label: `#${c.id} · ${c.name ?? "Unnamed"}`,
                  }))}
                  selected={row.client_ids_selected}
                  onChange={(ids) =>
                    onChange({ ...row, client_ids_selected: ids })
                  }
                />
              )}
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={row.only_clients_without_emails}
                  onChange={(e) =>
                    onChange({
                      ...row,
                      only_clients_without_emails: e.target.checked,
                    })
                  }
                />
                Only clients without emails
              </label>
              <label className="block text-sm">
                <span className={labelClass}>URL hint (optional)</span>
                <input
                  className={inputClass}
                  value={row.email_mode_url}
                  onChange={(e) =>
                    onChange({ ...row, email_mode_url: e.target.value })
                  }
                />
              </label>
            </div>
          )}
        </div>
      )}

      {row.linked_task_model === "BulkJobApplication" && (
        <div className="space-y-3 pt-1 border-t border-gray-100 dark:border-gray-800">
          <label className="block text-sm">
            <span className={labelClass}>Resume</span>
            <select
              className={inputClass}
              value={row.resume_id === "" ? "" : String(row.resume_id)}
              onChange={(e) =>
                onChange({
                  ...row,
                  resume_id: e.target.value === "" ? "" : Number(e.target.value),
                })
              }
            >
              <option value="">Select resume…</option>
              {activeResumes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={row.use_previous_career_jobs}
              onChange={(e) =>
                onChange({
                  ...row,
                  use_previous_career_jobs: e.target.checked,
                })
              }
            />
            Use career jobs from previous step (e.g. after Scrap Job)
          </label>
          {!row.use_previous_career_jobs && (
            <MultiSelect
              label="Career jobs"
              hint="Hold Ctrl/Cmd to select multiple."
              options={careerJobs.map((j) => ({
                value: j.id,
                label: `#${j.id} · ${j.title}`,
              }))}
              selected={row.career_job_ids_selected}
              onChange={(ids) =>
                onChange({ ...row, career_job_ids_selected: ids })
              }
            />
          )}
        </div>
      )}

      {row.linked_task_model === "BulkJobApplicationEmailSend" && (
        <div className="space-y-3 pt-1 border-t border-gray-100 dark:border-gray-800">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={row.use_previous_job_applications}
              onChange={(e) =>
                onChange({
                  ...row,
                  use_previous_job_applications: e.target.checked,
                })
              }
            />
            Use job applications from previous step
          </label>
          {!row.use_previous_job_applications && (
            <MultiSelect
              label="Job applications (active)"
              hint="Hold Ctrl/Cmd to select multiple."
              options={jobApplications.map((j) => ({
                value: j.id,
                label: `#${j.id} · ${j.career_job_title ?? "Application"} · ${j.application_name}`,
              }))}
              selected={row.job_application_ids_selected}
              onChange={(ids) =>
                onChange({ ...row, job_application_ids_selected: ids })
              }
            />
          )}
          <label className="block text-sm">
            <span className={labelClass}>Minimum similarity score (optional)</span>
            <p className={hintClass}>
              If set (0–100), only applications with this fit score or higher are
              emailed. Applications with no score are skipped.
            </p>
            <input
              type="number"
              min={0}
              max={100}
              step={1}
              className={inputClass}
              placeholder="No minimum"
              value={row.bulk_email_min_similarity_input}
              onChange={(e) =>
                onChange({
                  ...row,
                  bulk_email_min_similarity_input: e.target.value,
                })
              }
            />
          </label>
        </div>
      )}

      {onRemove ? (
        <button
          type="button"
          className="text-xs text-red-600 dark:text-red-400 pt-1"
          onClick={onRemove}
        >
          Remove task
        </button>
      ) : null}
    </div>
  );
}

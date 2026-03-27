export const WORKFLOW_TASK_MODELS = [
  "ScrapJob",
  "ScrapClientJob",
  "BulkJobApplication",
  "BulkJobApplicationEmailSend",
] as const;

export type TaskModelType = (typeof WORKFLOW_TASK_MODELS)[number];

export function isTaskModelType(s: string): s is TaskModelType {
  return (WORKFLOW_TASK_MODELS as readonly string[]).includes(s);
}

export interface WorkflowTaskRowForm {
  linked_task_model: TaskModelType;
  priority: number;
  is_active: boolean;
  job_site_id: number | "";
  scrap_name: string;
  categories_input: string;
  max_pages_per_scrap: string;
  process_with_llm: boolean;
  load_more_on_scroll: boolean;
  max_scroll: string;
  depth_levels: string;
  scrap_client_mode: "site" | "url" | "email";
  client_site_id: number | "";
  scrap_client_url: string;
  scrap_client_name: string;
  client_ids_selected: number[];
  use_previous_career_clients: boolean;
  only_clients_without_emails: boolean;
  email_mode_url: string;
  resume_id: number | "";
  career_job_ids_selected: number[];
  use_previous_career_jobs: boolean;
  job_application_ids_selected: number[];
  use_previous_job_applications: boolean;
  /** Only for BulkJobApplicationEmailSend; empty = no minimum filter (same as backend null). */
  bulk_email_min_similarity_input: string;
}

export function defaultRowForModel(model: TaskModelType): WorkflowTaskRowForm {
  return {
    linked_task_model: model,
    priority: 0,
    is_active: true,
    job_site_id: "",
    scrap_name: "",
    categories_input: "",
    max_pages_per_scrap: "",
    process_with_llm: true,
    load_more_on_scroll: false,
    max_scroll: "",
    depth_levels: "",
    scrap_client_mode: "site",
    client_site_id: "",
    scrap_client_url: "",
    scrap_client_name: "",
    client_ids_selected: [],
    use_previous_career_clients: false,
    only_clients_without_emails: false,
    email_mode_url: "",
    resume_id: "",
    career_job_ids_selected: [],
    use_previous_career_jobs: false,
    job_application_ids_selected: [],
    use_previous_job_applications: false,
    bulk_email_min_similarity_input: "",
  };
}

export function switchTaskModel(
  row: WorkflowTaskRowForm,
  model: TaskModelType
): WorkflowTaskRowForm {
  return {
    ...defaultRowForModel(model),
    priority: row.priority,
    is_active: row.is_active,
  };
}

export function rowToPayload(row: WorkflowTaskRowForm): Record<string, unknown> {
  switch (row.linked_task_model) {
    case "ScrapJob": {
      const out: Record<string, unknown> = {
        job_site_id: Number(row.job_site_id),
      };
      if (row.scrap_name.trim()) out.name = row.scrap_name.trim();
      const cats = row.categories_input
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      if (cats.length) out.categories = cats;
      if (row.max_pages_per_scrap !== "") {
        out.max_pages_per_scrap = Number(row.max_pages_per_scrap);
      }
      out.process_with_llm = row.process_with_llm;
      out.load_more_on_scroll = row.load_more_on_scroll;
      if (row.max_scroll !== "") out.max_scroll = Number(row.max_scroll);
      if (row.depth_levels !== "") out.depth_levels = Number(row.depth_levels);
      return out;
    }
    case "ScrapClientJob": {
      const mode = row.scrap_client_mode;
      const out: Record<string, unknown> = { mode };
      if (row.scrap_client_name.trim()) out.name = row.scrap_client_name.trim();
      if (mode === "site") {
        out.client_site_id = Number(row.client_site_id);
        return out;
      }
      if (mode === "url") {
        out.url = row.scrap_client_url.trim();
        return out;
      }
      out.client_ids = row.client_ids_selected;
      out.use_previous_career_clients = row.use_previous_career_clients;
      out.only_clients_without_emails = row.only_clients_without_emails;
      if (row.email_mode_url.trim()) out.url = row.email_mode_url.trim();
      return out;
    }
    case "BulkJobApplication": {
      const out: Record<string, unknown> = {
        resume_id: Number(row.resume_id),
      };
      if (row.use_previous_career_jobs) {
        out.use_previous_career_jobs = true;
      } else {
        out.career_job_ids = row.career_job_ids_selected;
      }
      return out;
    }
    case "BulkJobApplicationEmailSend": {
      const withMin = (base: Record<string, unknown>) => {
        const raw = row.bulk_email_min_similarity_input.trim();
        if (raw !== "") {
          const n = Number(raw);
          if (!Number.isNaN(n)) base.min_similarity_score = n;
        }
        return base;
      };
      if (row.use_previous_job_applications) {
        return withMin({ use_previous_job_applications: true });
      }
      return withMin({
        job_application_ids: row.job_application_ids_selected,
      });
    }
  }
}

export function validateRow(row: WorkflowTaskRowForm): string | null {
  switch (row.linked_task_model) {
    case "ScrapJob":
      if (row.job_site_id === "")
        return "Select a job site for each Scrap Job task.";
      return null;
    case "ScrapClientJob": {
      const mode = row.scrap_client_mode;
      if (mode === "site" && row.client_site_id === "")
        return "Select a client site for site mode.";
      if (mode === "url" && !row.scrap_client_url.trim())
        return "Enter a URL for URL mode.";
      return null;
    }
    case "BulkJobApplication":
      if (row.resume_id === "") return "Select a resume.";
      if (!row.use_previous_career_jobs && row.career_job_ids_selected.length === 0)
        return "Select career jobs or enable “Use career jobs from previous step”.";
      return null;
    case "BulkJobApplicationEmailSend": {
      if (
        !row.use_previous_job_applications &&
        row.job_application_ids_selected.length === 0
      )
        return "Select job applications or enable “Use job applications from previous step”.";
      const raw = row.bulk_email_min_similarity_input.trim();
      if (raw !== "") {
        const n = Number(raw);
        if (Number.isNaN(n) || n < 0 || n > 100)
          return "Minimum similarity must be a number between 0 and 100.";
      }
      return null;
    }
  }
}

function numArray(v: unknown): number[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is number => typeof x === "number");
}

export function hydrateRowFromPayload(
  linked_task_model: TaskModelType,
  data: Record<string, unknown> | null | undefined,
  priority: number,
  is_active: boolean
): WorkflowTaskRowForm {
  const d = data ?? {};
  const row = defaultRowForModel(linked_task_model);
  row.priority = priority;
  row.is_active = is_active;

  if (linked_task_model === "ScrapJob") {
    if (typeof d.job_site_id === "number") row.job_site_id = d.job_site_id;
    if (typeof d.name === "string") row.scrap_name = d.name;
    if (Array.isArray(d.categories))
      row.categories_input = (d.categories as string[]).join(", ");
    if (typeof d.max_pages_per_scrap === "number")
      row.max_pages_per_scrap = String(d.max_pages_per_scrap);
    if (typeof d.process_with_llm === "boolean")
      row.process_with_llm = d.process_with_llm;
    if (typeof d.load_more_on_scroll === "boolean")
      row.load_more_on_scroll = d.load_more_on_scroll;
    if (typeof d.max_scroll === "number") row.max_scroll = String(d.max_scroll);
    if (typeof d.depth_levels === "number")
      row.depth_levels = String(d.depth_levels);
    return row;
  }

  if (linked_task_model === "ScrapClientJob") {
    const modeRaw = d.mode;
    row.scrap_client_mode =
      modeRaw === "url" || modeRaw === "email" ? modeRaw : "site";
    if (typeof d.name === "string") row.scrap_client_name = d.name;
    if (row.scrap_client_mode === "site" && typeof d.client_site_id === "number")
      row.client_site_id = d.client_site_id;
    if (row.scrap_client_mode === "url" && typeof d.url === "string")
      row.scrap_client_url = d.url;
    if (row.scrap_client_mode === "email") {
      row.client_ids_selected = numArray(d.client_ids);
      row.use_previous_career_clients = Boolean(d.use_previous_career_clients);
      row.only_clients_without_emails = Boolean(d.only_clients_without_emails);
      if (typeof d.url === "string") row.email_mode_url = d.url;
    }
    return row;
  }

  if (linked_task_model === "BulkJobApplication") {
    if (typeof d.resume_id === "number") row.resume_id = d.resume_id;
    row.use_previous_career_jobs = Boolean(d.use_previous_career_jobs);
    row.career_job_ids_selected = numArray(d.career_job_ids);
    return row;
  }

  if (linked_task_model === "BulkJobApplicationEmailSend") {
    row.use_previous_job_applications = Boolean(d.use_previous_job_applications);
    row.job_application_ids_selected = numArray(d.job_application_ids);
    if (typeof d.min_similarity_score === "number")
      row.bulk_email_min_similarity_input = String(d.min_similarity_score);
    return row;
  }

  return row;
}

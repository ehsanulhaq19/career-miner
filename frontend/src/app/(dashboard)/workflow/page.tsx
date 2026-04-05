"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { HiOutlinePlayCircle, HiOutlineSquares2X2 } from "react-icons/hi2";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { fetchCareerClients } from "@/store/slices/careerClientSlice";
import { fetchCareerJobs } from "@/store/slices/careerJobSlice";
import { fetchClientSites } from "@/store/slices/clientSiteSlice";
import { fetchJobSites } from "@/store/slices/jobSiteSlice";
import { fetchResumes } from "@/store/slices/resumeSlice";
import {
  addWorkflowTask,
  clearExecutionDetail,
  clearWorkflowDetail,
  createWorkflow,
  fetchWorkflowDetail,
  fetchWorkflowExecutionDetail,
  fetchWorkflowExecutions,
  fetchWorkflows,
  patchWorkflowTask,
  removeWorkflowTask,
  runWorkflow,
  updateWorkflow,
} from "@/store/slices/workflowSlice";
import { jobApplicationService } from "@/services/jobApplicationService";
import type { JobApplication } from "@/types";
import WorkflowTaskFormFields from "./WorkflowTaskFormFields";
import {
  defaultRowForModel,
  hydrateRowFromPayload,
  isTaskModelType,
  rowToPayload,
  validateRow,
  type WorkflowTaskRowForm,
} from "./workflowTaskForm";

type WorkflowTab = "workflows" | "executions";

export default function WorkflowPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const dispatch = useAppDispatch();
  const {
    items: workflows,
    executions,
    loading,
    loadingExecutions,
    detailLoading,
    executionDetailLoading,
    workflowDetail: detail,
    executionDetail: execDetail,
  } = useAppSelector((state) => state.workflow);
  const jobSites = useAppSelector((state) => state.jobSite.items);
  const clientSites = useAppSelector((state) => state.clientSite.items);
  const resumes = useAppSelector((state) => state.resume.items);
  const careerClients = useAppSelector((state) => state.careerClient.items);
  const careerJobs = useAppSelector((state) => state.careerJob.items);

  const [activeTab, setActiveTab] = useState<WorkflowTab>("workflows");

  const setTab = (tab: WorkflowTab) => {
    setActiveTab(tab);
    router.replace(`/workflow?tab=${tab}`, { scroll: false });
  };

  useEffect(() => {
    if (tabParam === "workflows" || tabParam === "executions") {
      setActiveTab(tabParam);
    }
  }, [tabParam]);
  const [createOpen, setCreateOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);

  const [formName, setFormName] = useState("");
  const [formMinutes, setFormMinutes] = useState(60);
  const [formActive, setFormActive] = useState(true);
  const [taskRows, setTaskRows] = useState<WorkflowTaskRowForm[]>([
    defaultRowForModel("ScrapJob"),
  ]);
  const [jobApplicationsOptions, setJobApplicationsOptions] = useState<
    JobApplication[]
  >([]);
  const [createFormError, setCreateFormError] = useState<string | null>(null);
  const [taskEditError, setTaskEditError] = useState<string | null>(null);
  const [taskEditOpen, setTaskEditOpen] = useState(false);
  const [taskEditRow, setTaskEditRow] = useState<WorkflowTaskRowForm | null>(
    null
  );
  const [taskEditContext, setTaskEditContext] = useState<{
    workflowId: number;
    taskId: number;
  } | null>(null);
  const [taskAddOpen, setTaskAddOpen] = useState(false);
  const [taskAddRow, setTaskAddRow] = useState<WorkflowTaskRowForm | null>(
    null
  );
  const [taskAddError, setTaskAddError] = useState<string | null>(null);

  useEffect(() => {
    if (activeTab === "workflows") {
      dispatch(fetchWorkflows());
    } else {
      dispatch(fetchWorkflowExecutions());
    }
  }, [dispatch, activeTab]);

  useEffect(() => {
    if (!createOpen && !detail && editId == null) return;
    dispatch(fetchJobSites({ is_active: true, limit: 500 }));
    dispatch(fetchClientSites({ is_active: true, limit: 500 }));
    dispatch(fetchResumes({ skip: 0, limit: 300 }));
    dispatch(fetchCareerClients({ skip: 0, limit: 500 }));
    dispatch(fetchCareerJobs({ skip: 0, limit: 500 }));
    let cancelled = false;
    jobApplicationService
      .getJobApplications(0, 500, true)
      .then((data) => {
        if (!cancelled) setJobApplicationsOptions(data.items);
      })
      .catch(() => {
        if (!cancelled) setJobApplicationsOptions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [createOpen, detail, editId, dispatch]);

  const openDetail = (id: number) => {
    dispatch(fetchWorkflowDetail(id));
  };

  const openExecDetail = (id: number) => {
    dispatch(fetchWorkflowExecutionDetail(id));
  };

  const resetCreateForm = () => {
    setFormName("");
    setFormMinutes(60);
    setFormActive(true);
    setTaskRows([defaultRowForModel("ScrapJob")]);
    setCreateFormError(null);
  };

  const submitCreate = async () => {
    if (taskRows.length === 0) {
      setCreateFormError("Add at least one task.");
      return;
    }
    for (const row of taskRows) {
      const err = validateRow(row);
      if (err) {
        setCreateFormError(err);
        return;
      }
    }
    setCreateFormError(null);
    const tasks = taskRows.map((row) => ({
      linked_task_model: row.linked_task_model,
      linked_task_model_data: rowToPayload(row),
      priority: row.priority,
      is_active: row.is_active,
    }));
    await dispatch(
      createWorkflow({
        name: formName,
        next_execution_duration_minutes: formMinutes,
        is_active: formActive,
        meta_data: {},
        tasks,
      })
    ).unwrap();
    setCreateOpen(false);
    resetCreateForm();
    dispatch(fetchWorkflows());
  };

  const saveEdit = async () => {
    if (editId == null) return;
    await dispatch(
      updateWorkflow({
        id: editId,
        data: {
          name: formName,
          next_execution_duration_minutes: formMinutes,
          is_active: formActive,
        },
      })
    ).unwrap();
    setEditId(null);
    dispatch(clearWorkflowDetail());
    dispatch(fetchWorkflows());
  };

  const startEdit = (w: (typeof workflows)[number]) => {
    setEditId(w.id);
    setFormName(w.name);
    setFormMinutes(w.next_execution_duration_minutes);
    setFormActive(w.is_active);
  };

  const runNow = async (id: number) => {
    await dispatch(runWorkflow(id)).unwrap();
    dispatch(fetchWorkflows());
  };

  const deleteTask = async (workflowId: number, taskId: number) => {
    await dispatch(removeWorkflowTask({ workflowId, taskId })).unwrap();
  };

  const openTaskEdit = (task: {
    id: number;
    linked_task_model: string;
    linked_task_model_data: Record<string, unknown>;
    priority: number;
    is_active: boolean;
  }) => {
    if (!detail || !isTaskModelType(task.linked_task_model)) return;
    setTaskEditError(null);
    setTaskEditRow(
      hydrateRowFromPayload(
        task.linked_task_model,
        task.linked_task_model_data,
        task.priority,
        task.is_active
      )
    );
    setTaskEditContext({ workflowId: detail.id, taskId: task.id });
    setTaskEditOpen(true);
  };

  const saveTaskEdit = async () => {
    if (!detail || !taskEditRow || !taskEditContext) return;
    const err = validateRow(taskEditRow);
    if (err) {
      setTaskEditError(err);
      return;
    }
    setTaskEditError(null);
    await dispatch(
      patchWorkflowTask({
        workflowId: taskEditContext.workflowId,
        taskId: taskEditContext.taskId,
        data: {
          linked_task_model: taskEditRow.linked_task_model,
          linked_task_model_data: rowToPayload(taskEditRow),
          priority: taskEditRow.priority,
          is_active: taskEditRow.is_active,
        },
      })
    ).unwrap();
    setTaskEditOpen(false);
    setTaskEditRow(null);
    setTaskEditContext(null);
    setTaskEditError(null);
  };

  const taskAddWorkflowId = detail?.id ?? editId;

  const openTaskAdd = () => {
    if (taskAddWorkflowId == null) return;
    setTaskAddError(null);
    setTaskAddRow(defaultRowForModel("ScrapJob"));
    setTaskAddOpen(true);
  };

  const saveTaskAdd = async () => {
    if (taskAddWorkflowId == null || !taskAddRow) return;
    const err = validateRow(taskAddRow);
    if (err) {
      setTaskAddError(err);
      return;
    }
    setTaskAddError(null);
    await dispatch(
      addWorkflowTask({
        workflowId: taskAddWorkflowId,
        data: {
          linked_task_model: taskAddRow.linked_task_model,
          linked_task_model_data: rowToPayload(taskAddRow),
          priority: taskAddRow.priority,
          is_active: taskAddRow.is_active,
        },
      })
    ).unwrap();
    setTaskAddOpen(false);
    setTaskAddRow(null);
    setTaskAddError(null);
  };

  const listLoading = activeTab === "workflows" ? loading : loadingExecutions;

  const tabs: {
    id: WorkflowTab;
    label: string;
    icon: typeof HiOutlineSquares2X2;
  }[] = [
    { id: "workflows", label: "Workflows", icon: HiOutlineSquares2X2 },
    { id: "executions", label: "Executed Workflows", icon: HiOutlinePlayCircle },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Workflow
        </h2>
        <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 p-1 bg-gray-50 dark:bg-gray-800/50">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === tab.id
                  ? "bg-white dark:bg-gray-700 text-primary-600 dark:text-primary-400 shadow-sm"
                  : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "workflows" && (
        <div className="space-y-4">
          <button
            type="button"
            onClick={() => {
              resetCreateForm();
              setCreateOpen(true);
              setCreateFormError(null);
            }}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-primary-600 text-white hover:bg-primary-700"
          >
            New workflow
          </button>

          {listLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th className="text-left p-3">Name</th>
                    <th className="text-left p-3">Interval (min)</th>
                    <th className="text-left p-3">Active</th>
                    <th className="text-left p-3">Last run</th>
                    <th className="text-left p-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {workflows.map((w) => (
                    <tr key={w.id} className="border-t border-gray-100 dark:border-gray-800">
                      <td className="p-3">
                        <button
                          type="button"
                          className="text-primary-600 dark:text-primary-400 hover:underline"
                          onClick={() => openDetail(w.id)}
                        >
                          {w.name}
                        </button>
                      </td>
                      <td className="p-3">{w.next_execution_duration_minutes}</td>
                      <td className="p-3">{w.is_active ? "Yes" : "No"}</td>
                      <td className="p-3 text-xs text-gray-500">
                        {w.last_execution_at || "—"}
                      </td>
                      <td className="p-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="text-xs px-2 py-1 rounded border border-gray-300 dark:border-gray-600"
                          onClick={() => runNow(w.id)}
                        >
                          Run now
                        </button>
                        <button
                          type="button"
                          className="text-xs px-2 py-1 rounded border border-gray-300 dark:border-gray-600"
                          onClick={() => startEdit(w)}
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "executions" && (
        <div className="space-y-4">
          {listLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th className="text-left p-3">ID</th>
                    <th className="text-left p-3">Workflow</th>
                    <th className="text-left p-3">Status</th>
                    <th className="text-left p-3">Started</th>
                  </tr>
                </thead>
                <tbody>
                  {executions.map((e) => (
                    <tr key={e.id} className="border-t border-gray-100 dark:border-gray-800">
                      <td className="p-3">
                        <button
                          type="button"
                          className="text-primary-600 dark:text-primary-400 hover:underline"
                          onClick={() => openExecDetail(e.id)}
                        >
                          {e.id}
                        </button>
                      </td>
                      <td className="p-3">{e.workflow_id}</td>
                      <td className="p-3">{e.status}</td>
                      <td className="p-3 text-xs">{e.started_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <h2 className="font-semibold text-gray-900 dark:text-white">Create workflow</h2>
            <label className="block text-sm">
              <span className="text-gray-600 dark:text-gray-400">Name</span>
              <input
                className="mt-1 w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="text-gray-600 dark:text-gray-400">Interval (minutes)</span>
              <input
                type="number"
                className="mt-1 w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2"
                value={formMinutes}
                onChange={(e) => setFormMinutes(Number(e.target.value))}
              />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={formActive}
                onChange={(e) => setFormActive(e.target.checked)}
              />
              Active
            </label>
            {createFormError ? (
              <p className="text-sm text-red-600 dark:text-red-400">{createFormError}</p>
            ) : null}
            <div className="space-y-3">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Tasks</p>
              {taskRows.map((row, i) => (
                <WorkflowTaskFormFields
                  key={i}
                  row={row}
                  jobSites={jobSites}
                  clientSites={clientSites}
                  resumes={resumes}
                  careerJobs={careerJobs}
                  careerClients={careerClients}
                  jobApplications={jobApplicationsOptions}
                  onChange={(next) => {
                    const copy = [...taskRows];
                    copy[i] = next;
                    setTaskRows(copy);
                  }}
                  onRemove={() => {
                    setTaskRows(taskRows.filter((_, j) => j !== i));
                  }}
                />
              ))}
              <button
                type="button"
                className="text-sm text-primary-600 dark:text-primary-400"
                onClick={() => {
                  setTaskRows([...taskRows, defaultRowForModel("ScrapJob")]);
                }}
              >
                Add task
              </button>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 text-sm"
                onClick={() => {
                  setCreateOpen(false);
                  setCreateFormError(null);
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-3 py-2 rounded bg-primary-600 text-white text-sm"
                onClick={() => submitCreate()}
                disabled={!formName.trim()}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {taskAddOpen && taskAddRow && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <h2 className="font-semibold text-gray-900 dark:text-white">Add task</h2>
            {taskAddError ? (
              <p className="text-sm text-red-600 dark:text-red-400">{taskAddError}</p>
            ) : null}
            <WorkflowTaskFormFields
              row={taskAddRow}
              jobSites={jobSites}
              clientSites={clientSites}
              resumes={resumes}
              careerJobs={careerJobs}
              careerClients={careerClients}
              jobApplications={jobApplicationsOptions}
              onChange={setTaskAddRow}
            />
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 text-sm"
                onClick={() => {
                  setTaskAddOpen(false);
                  setTaskAddRow(null);
                  setTaskAddError(null);
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-3 py-2 rounded bg-primary-600 text-white text-sm"
                onClick={() => saveTaskAdd()}
              >
                Add task
              </button>
            </div>
          </div>
        </div>
      )}

      {taskEditOpen && taskEditRow && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <h2 className="font-semibold text-gray-900 dark:text-white">Edit task</h2>
            {taskEditError ? (
              <p className="text-sm text-red-600 dark:text-red-400">{taskEditError}</p>
            ) : null}
            <WorkflowTaskFormFields
              row={taskEditRow}
              jobSites={jobSites}
              clientSites={clientSites}
              resumes={resumes}
              careerJobs={careerJobs}
              careerClients={careerClients}
              jobApplications={jobApplicationsOptions}
              onChange={setTaskEditRow}
            />
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 text-sm"
                onClick={() => {
                  setTaskEditOpen(false);
                  setTaskEditRow(null);
                  setTaskEditContext(null);
                  setTaskEditError(null);
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-3 py-2 rounded bg-primary-600 text-white text-sm"
                onClick={() => saveTaskEdit()}
              >
                Save task
              </button>
            </div>
          </div>
        </div>
      )}

      {editId != null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl max-w-md w-full p-6 space-y-4">
            <h2 className="font-semibold text-gray-900 dark:text-white">Edit workflow</h2>
            <input
              className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-gray-100"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
            />
            <input
              type="number"
              className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-gray-100"
              value={formMinutes}
              onChange={(e) => setFormMinutes(Number(e.target.value))}
            />
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
              <input
                type="checkbox"
                checked={formActive}
                onChange={(e) => setFormActive(e.target.checked)}
              />
              Active
            </label>
            <button
              type="button"
              className="w-full text-sm px-3 py-2 rounded border border-gray-300 dark:border-gray-600 text-gray-800 dark:text-gray-200"
              onClick={() => openTaskAdd()}
            >
              Add task
            </button>
            <div className="flex gap-2 justify-end">
              <button type="button" className="px-3 py-2 border rounded text-sm" onClick={() => setEditId(null)}>
                Cancel
              </button>
              <button type="button" className="px-3 py-2 bg-primary-600 text-white rounded text-sm" onClick={saveEdit}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4">
            {detailLoading && (
              <p className="text-sm text-gray-500">Loading…</p>
            )}
            <h2 className="font-semibold text-lg">{detail.name}</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Interval: {detail.next_execution_duration_minutes} min · Active: {detail.is_active ? "yes" : "no"} · Total
              jobs executed: {detail.total_jobs_executed}
            </p>
            <p className="text-xs text-gray-500">
              Last execution: {detail.last_execution_started_at || "—"}
            </p>
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <h3 className="font-medium text-sm">Tasks</h3>
                <button
                  type="button"
                  className="text-xs px-2 py-1 rounded border border-gray-300 dark:border-gray-600"
                  onClick={() => openTaskAdd()}
                >
                  Add task
                </button>
              </div>
              <ul className="text-sm space-y-2">
                {detail.tasks.map((t) => (
                  <li key={t.id} className="border border-gray-100 dark:border-gray-800 rounded p-2 flex justify-between gap-2">
                    <div>
                      <span className="font-mono text-xs">{t.linked_task_model}</span> · priority {t.priority}
                      <pre className="text-xs mt-1 overflow-x-auto max-w-xl">
                        {JSON.stringify(t.linked_task_model_data, null, 2)}
                      </pre>
                    </div>
                    <div className="flex flex-col gap-1 shrink-0">
                      {isTaskModelType(t.linked_task_model) ? (
                        <button
                          type="button"
                          className="text-xs px-2 py-1 rounded border border-gray-300 dark:border-gray-600"
                          onClick={() => openTaskEdit(t)}
                        >
                          Edit
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="text-xs text-red-600 dark:text-red-400"
                        onClick={() => deleteTask(detail.id, t.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            <button
              type="button"
              className="px-3 py-2 rounded border text-sm"
              onClick={() => dispatch(clearWorkflowDetail())}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {execDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4">
            {executionDetailLoading && (
              <p className="text-sm text-gray-500">Loading…</p>
            )}
            <h2 className="font-semibold">
              Execution #{execDetail.id}{" "}
              {execDetail.workflow_name ? `(${execDetail.workflow_name})` : ""}
            </h2>
            <p className="text-sm">Status: {execDetail.status}</p>
            <div>
              <h3 className="font-medium text-sm mb-2">Jobs</h3>
              <ul className="text-xs space-y-1">
                {execDetail.jobs.map((j) => (
                  <li key={j.id} className="border rounded p-2">
                    Task {j.workflow_task_id} · {j.status}
                    {j.created_resource_type && (
                      <span>
                        {" "}
                        · {j.created_resource_type} #{j.created_resource_id}
                      </span>
                    )}
                    {j.error_detail && <span className="text-red-600"> · {j.error_detail}</span>}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-sm mb-2">Logs</h3>
              {execDetail.jobs.map((j) => (
                <div key={j.id} className="mb-3">
                  <p className="text-xs text-gray-500">Job {j.id}</p>
                  <ul className="text-xs space-y-1 pl-2">
                    {(execDetail.logs_by_job_id[String(j.id)] ?? []).map((lg) => (
                      <li key={lg.id}>
                        {lg.action}: {lg.detail}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <button
              type="button"
              className="px-3 py-2 rounded border text-sm"
              onClick={() => dispatch(clearExecutionDetail())}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

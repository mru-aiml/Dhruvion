import { useEffect, useState, useRef } from "react";
import { AlertCircle, CheckCircle, Loader2, X } from "lucide-react";
import { endpoints } from "../../services/api/endpoints";
import type { MissionCreateRequest, MissionRecord, MissionUpdateRequest } from "../../types";
import { saveMission } from "../../services/missionStore";
import PageHeader from "../../components/common/PageHeader";
import SectionCard from "../../components/common/SectionCard";
import { LoadingState, EmptyState, ErrorState } from "../../components/common/States";
import { FieldShell } from "../../components/common/Field";
import Button from "../../components/common/Button";

const REGIONS = ["gale_crater"];
const MISSION_TYPES = ["traverse", "reconnaissance", "science_exploration", "return"];
const STATUSES = ["draft", "planned", "active", "completed", "archived"];

interface FormState {
  name: string;
  description: string;
  region_id: string;
  mission_type: string;
  start_x: string;
  start_y: string;
  dest_x: string;
  dest_y: string;
  time_budget_min: string;
  objectives: string;
  notes: string;
  status: string;
}

const emptyForm: FormState = {
  name: "",
  description: "",
  region_id: "gale_crater",
  mission_type: "traverse",
  start_x: "137.2",
  start_y: "-4.5",
  dest_x: "137.3",
  dest_y: "-4.55",
  time_budget_min: "600",
  objectives: "",
  notes: "",
  status: "draft",
};

interface ValidationErrors {
  name?: string;
  start_x?: string;
  start_y?: string;
  dest_x?: string;
  dest_y?: string;
  time_budget_min?: string;
}

function validateForm(form: FormState): ValidationErrors {
  const errors: ValidationErrors = {};
  if (!form.name.trim()) {
    errors.name = "Mission name is required";
  }
  const startX = Number(form.start_x);
  const startY = Number(form.start_y);
  const destX = Number(form.dest_x);
  const destY = Number(form.dest_y);
  const timeBudget = Number(form.time_budget_min);
  if (!Number.isFinite(startX) || startX < -180 || startX > 180) {
    errors.start_x = "Start longitude must be between -180 and 180";
  }
  if (!Number.isFinite(startY) || startY < -90 || startY > 90) {
    errors.start_y = "Start latitude must be between -90 and 90";
  }
  if (!Number.isFinite(destX) || destX < -180 || destX > 180) {
    errors.dest_x = "Destination longitude must be between -180 and 180";
  }
  if (!Number.isFinite(destY) || destY < -90 || destY > 90) {
    errors.dest_y = "Destination latitude must be between -90 and 90";
  }
  if (!Number.isFinite(timeBudget) || timeBudget <= 0) {
    errors.time_budget_min = "Time budget must be greater than zero";
  }
  return errors;
}

interface MissionModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  form: FormState;
  setForm: React.Dispatch<React.SetStateAction<FormState>>;
  onSubmit: () => void;
  submitting: boolean;
  error: string | null;
}

function MissionModal({ isOpen, onClose, title, form, setForm, onSubmit, submitting, error }: MissionModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const firstInputRef = useRef<HTMLInputElement>(null);

  // Focus management
  useEffect(() => {
    if (!isOpen) return;
    
    const modal = modalRef.current;
    if (!modal) return;

    // Focus first input
    setTimeout(() => {
      firstInputRef.current?.focus();
    }, 0);

    // Trap focus
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "Tab") {
        const focusableElements = modal.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        
        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const errors = validateForm(form);
  const hasErrors = Object.keys(errors).length > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasErrors) {
      onSubmit();
    }
  };

  const handleInputChange = (field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="mission-modal-title"
    >
      <div
        ref={modalRef}
        className="w-full max-w-3xl max-h-[90vh] rounded-control border border-line bg-surface1 flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Fixed Header */}
        <div className="flex items-center justify-between border-b border-line p-4 shrink-0">
          <h2 id="mission-modal-title" className="font-heading text-lg text-text-primary">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-control text-text-muted hover:text-text-primary hover:bg-surface2 transition-colors"
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        {/* Scrollable Content */}
        <form id="mission-form" onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-4 md:p-6">
          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-control border border-critical-red/30 bg-critical-red/[0.05] p-3 text-sm text-critical-red" role="alert">
              <AlertCircle size={16} className="shrink-0" aria-hidden />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-5">
            {/* Section 1: Mission Identity */}
            <fieldset className="border border-line/50 rounded-control p-4">
              <legend className="text-[9px] uppercase tracking-[0.1em] text-text-muted px-2">Mission Identity</legend>
              <div className="grid gap-3 md:grid-cols-2">
                <FieldShell label="Mission name" error={errors.name}>
                  <input
                    ref={firstInputRef}
                    type="text"
                    className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                    value={form.name}
                    onChange={(e) => handleInputChange("name", e.target.value)}
                    aria-invalid={!!errors.name}
                    aria-describedby={errors.name ? "name-error" : undefined}
                    disabled={submitting}
                  />
                  {errors.name && <p id="name-error" className="mt-1 text-[10px] text-critical-red">{errors.name}</p>}
                </FieldShell>
                <FieldShell label="Description">
                  <textarea
                    className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                    rows={2}
                    value={form.description}
                    onChange={(e) => handleInputChange("description", e.target.value)}
                    disabled={submitting}
                  />
                </FieldShell>
                <FieldShell label="Mission type">
                  <select
                    className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                    value={form.mission_type}
                    onChange={(e) => handleInputChange("mission_type", e.target.value)}
                    disabled={submitting}
                  >
                    {MISSION_TYPES.map((type) => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </FieldShell>
                <FieldShell label="Status">
                  <select
                    className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                    value={form.status}
                    onChange={(e) => handleInputChange("status", e.target.value)}
                    disabled={submitting}
                  >
                    {STATUSES.map((status) => (
                      <option key={status} value={status}>{status}</option>
                    ))}
                  </select>
                </FieldShell>
              </div>
            </fieldset>

            {/* Section 2: Mission Location */}
            <fieldset className="border border-line/50 rounded-control p-4">
              <legend className="text-[9px] uppercase tracking-[0.1em] text-text-muted px-2">Mission Location</legend>
              <div className="grid gap-3 md:grid-cols-4">
                <FieldShell label="Start longitude (x)" error={errors.start_x}>
                  <input
                    type="number"
                    step="0.001"
                    className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                    value={form.start_x}
                    onChange={(e) => handleInputChange("start_x", e.target.value)}
                    aria-invalid={!!errors.start_x}
                    aria-describedby={errors.start_x ? "start-x-error" : undefined}
                    disabled={submitting}
                  />
                  {errors.start_x && <p id="start-x-error" className="mt-1 text-[10px] text-critical-red">{errors.start_x}</p>}
                </FieldShell>
                <FieldShell label="Start latitude (y)" error={errors.start_y}>
                  <input
                    type="number"
                    step="0.001"
                    className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                    value={form.start_y}
                    onChange={(e) => handleInputChange("start_y", e.target.value)}
                    aria-invalid={!!errors.start_y}
                    aria-describedby={errors.start_y ? "start-y-error" : undefined}
                    disabled={submitting}
                  />
                  {errors.start_y && <p id="start-y-error" className="mt-1 text-[10px] text-critical-red">{errors.start_y}</p>}
                </FieldShell>
                <FieldShell label="Destination longitude (x)" error={errors.dest_x}>
                  <input
                    type="number"
                    step="0.001"
                    className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                    value={form.dest_x}
                    onChange={(e) => handleInputChange("dest_x", e.target.value)}
                    aria-invalid={!!errors.dest_x}
                    aria-describedby={errors.dest_x ? "dest-x-error" : undefined}
                    disabled={submitting}
                  />
                  {errors.dest_x && <p id="dest-x-error" className="mt-1 text-[10px] text-critical-red">{errors.dest_x}</p>}
                </FieldShell>
                <FieldShell label="Destination latitude (y)" error={errors.dest_y}>
                  <input
                    type="number"
                    step="0.001"
                    className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                    value={form.dest_y}
                    onChange={(e) => handleInputChange("dest_y", e.target.value)}
                    aria-invalid={!!errors.dest_y}
                    aria-describedby={errors.dest_y ? "dest-y-error" : undefined}
                    disabled={submitting}
                  />
                  {errors.dest_y && <p id="dest-y-error" className="mt-1 text-[10px] text-critical-red">{errors.dest_y}</p>}
                </FieldShell>
              </div>
              <FieldShell label="Region">
                <select
                  className="w-full max-w-xs rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                  value={form.region_id}
                  onChange={(e) => handleInputChange("region_id", e.target.value)}
                  disabled={submitting}
                >
                  {REGIONS.map((region) => (
                    <option key={region} value={region}>{region}</option>
                  ))}
                </select>
              </FieldShell>
            </fieldset>

            {/* Section 3: Mission Constraints */}
            <fieldset className="border border-line/50 rounded-control p-4">
              <legend className="text-[9px] uppercase tracking-[0.1em] text-text-muted px-2">Mission Constraints</legend>
              <div className="grid gap-3 md:grid-cols-2">
                <FieldShell label="Time budget (minutes)" error={errors.time_budget_min}>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                    value={form.time_budget_min}
                    onChange={(e) => handleInputChange("time_budget_min", e.target.value)}
                    aria-invalid={!!errors.time_budget_min}
                    aria-describedby={errors.time_budget_min ? "time-budget-error" : undefined}
                    disabled={submitting}
                  />
                  {errors.time_budget_min && <p id="time-budget-error" className="mt-1 text-[10px] text-critical-red">{errors.time_budget_min}</p>}
                </FieldShell>
              </div>
            </fieldset>

            {/* Section 4: Mission Details */}
            <fieldset className="border border-line/50 rounded-control p-4">
              <legend className="text-[9px] uppercase tracking-[0.1em] text-text-muted px-2">Mission Details</legend>
              <FieldShell label="Objectives (one per line)">
                <textarea
                  className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                  rows={3}
                  value={form.objectives}
                  onChange={(e) => handleInputChange("objectives", e.target.value)}
                  disabled={submitting}
                />
              </FieldShell>
              <FieldShell label="Notes">
                <textarea
                  className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                  rows={3}
                  value={form.notes}
                  onChange={(e) => handleInputChange("notes", e.target.value)}
                  disabled={submitting}
                />
              </FieldShell>
            </fieldset>
          </div>
        </form>

        {/* Fixed Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-line p-4 shrink-0">
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button type="submit" form="mission-form" disabled={submitting || hasErrors} loading={submitting}>
            {submitting ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Saving…
              </>
            ) : (
              <>
                <CheckCircle size={14} />
                Save Mission
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function MissionsPage() {
  const [missions, setMissions] = useState<MissionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    if (!modalOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setModalOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [modalOpen]);
  const [editing, setEditing] = useState<MissionRecord | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [detail, setDetail] = useState<MissionRecord | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = { sort_by: sortBy, descending: "true" };
      if (statusFilter) params.status = statusFilter;
      if (search) params.search = search;
      const data = await endpoints.missions(params);
      setMissions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load missions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [statusFilter, sortBy]);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (mission: MissionRecord) => {
    setEditing(mission);
    setForm({
      name: mission.name,
      description: mission.description ?? "",
      region_id: mission.region_id,
      mission_type: mission.mission_type,
      start_x: String(mission.start.x),
      start_y: String(mission.start.y),
      dest_x: String(mission.destination.x),
      dest_y: String(mission.destination.y),
      time_budget_min: String(mission.time_budget_min),
      objectives: mission.objectives.join("\n"),
      notes: mission.notes ?? "",
      status: mission.status,
    });
    setModalOpen(true);
  };

  const submit = async () => {
    const payload: MissionCreateRequest = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      region_id: form.region_id,
      mission_type: form.mission_type,
      start: { x: Number(form.start_x), y: Number(form.start_y) },
      destination: { x: Number(form.dest_x), y: Number(form.dest_y) },
      time_budget_min: Number(form.time_budget_min),
      objectives: form.objectives
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean),
      notes: form.notes.trim() || null,
      status: form.status,
    };
    if (!payload.name) {
      setActionMessage("Mission name is required.");
      return;
    }
    if (!Number.isFinite(payload.start.x) || !Number.isFinite(payload.start.y)) {
      setActionMessage("Start coordinates must be numeric.");
      return;
    }
    if (!Number.isFinite(payload.destination.x) || !Number.isFinite(payload.destination.y)) {
      setActionMessage("Destination coordinates must be numeric.");
      return;
    }
    if (!Number.isFinite(payload.time_budget_min) || payload.time_budget_min <= 0) {
      setActionMessage("Time budget must be greater than zero.");
      return;
    }
    try {
      if (editing) {
        const update: MissionUpdateRequest = payload;
        await endpoints.missionUpdate(editing.id, update);
      } else {
        await endpoints.missionCreate(payload);
      }
      setModalOpen(false);
      setActionMessage(null);
      await load();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Failed to save mission");
    }
  };

  const remove = async (mission: MissionRecord) => {
    if (!window.confirm(`Delete mission ${mission.name}?`)) return;
    try {
      await endpoints.missionDelete(mission.id);
      if (detail?.id === mission.id) setDetail(null);
      await load();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Failed to delete mission");
    }
  };

  const planRoute = async (mission: MissionRecord) => {
    try {
      const plan = await endpoints.missionPlanRoute(mission.id, {});
      saveMission(plan);
      setDetail(mission);
      setActionMessage(`Route planned for ${mission.name}.`);
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Route planning failed");
    }
  };

  const generateReport = async (mission: MissionRecord) => {
    try {
      const report = await endpoints.missionReport(mission.id, {});
      setActionMessage(`Report generated: ${report.report_id}`);
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Report generation failed");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mission Management"
        description="Create, inspect, plan, and report on persistent Martian missions."
        actions={
          <Button onClick={openCreate}>+ ADD MISSION</Button>
        }
      />

      {actionMessage && (
        <div className="rounded-control border border-line bg-surface1 px-4 py-3 text-sm text-text-secondary">
          {actionMessage}
        </div>
      )}

      <SectionCard title="Mission Registry">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center">
          <input
            className="flex-1 rounded-control border border-line bg-surface1 px-3 py-2 text-sm text-text-primary"
            placeholder="Search missions"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void load();
            }}
          />
          <select
            className="rounded-control border border-line bg-surface1 px-3 py-2 text-sm text-text-primary"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All statuses</option>
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
          <select
            className="rounded-control border border-line bg-surface1 px-3 py-2 text-sm text-text-primary"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="created_at">Created date</option>
            <option value="name">Name</option>
            <option value="status">Status</option>
            <option value="mission_type">Type</option>
          </select>
          <Button variant="secondary" onClick={() => void load()}>
            Search
          </Button>
        </div>

        {loading && <LoadingState />}
        {error && <ErrorState message={error} />}
        {!loading && !error && missions.length === 0 && <EmptyState title="No missions found." />}

        {!loading && !error && missions.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-text-muted">
                  <th className="pb-2">ID</th>
                  <th className="pb-2">Name</th>
                  <th className="pb-2">Region</th>
                  <th className="pb-2">Type</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Created</th>
                  <th className="pb-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {missions.map((mission) => (
                  <tr key={mission.id} className="border-t border-line/60">
                    <td className="py-2 font-mono text-xs text-text-muted">{mission.id.slice(0, 8)}</td>
                    <td className="py-2">
                      <button
                        className="text-left text-text-primary hover:text-mars-orange"
                        onClick={() => setDetail(mission)}
                      >
                        {mission.name}
                      </button>
                    </td>
                    <td className="py-2 text-text-secondary">{mission.region_id}</td>
                    <td className="py-2 text-text-secondary">{mission.mission_type}</td>
                    <td className="py-2">
                      <span className="rounded-control border border-line px-2 py-1 text-xs uppercase text-text-secondary">
                        {mission.status}
                      </span>
                    </td>
                    <td className="py-2 text-text-secondary">
                      {new Date(mission.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2">
                      <div className="flex flex-wrap gap-2">
                        <Button variant="secondary" onClick={() => openEdit(mission)}>
                          Edit
                        </Button>
                        <Button variant="secondary" onClick={() => void planRoute(mission)}>
                          Plan
                        </Button>
                        <Button variant="secondary" onClick={() => void generateReport(mission)}>
                          Report
                        </Button>
                        <Button variant="danger" onClick={() => void remove(mission)}>
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      {detail && (
        <SectionCard title={`Mission Detail: ${detail.name}`}>
          <div className="grid gap-3 text-sm md:grid-cols-2">
            <div>
              <span className="text-text-muted">ID:</span> {detail.id}
            </div>
            <div>
              <span className="text-text-muted">Region:</span> {detail.region_id}
            </div>
            <div>
              <span className="text-text-muted">Type:</span> {detail.mission_type}
            </div>
            <div>
              <span className="text-text-muted">Status:</span> {detail.status}
            </div>
            <div>
              <span className="text-text-muted">Start:</span> {detail.start.x}, {detail.start.y}
            </div>
            <div>
              <span className="text-text-muted">Destination:</span> {detail.destination.x}, {detail.destination.y}
            </div>
            <div>
              <span className="text-text-muted">Time budget:</span> {detail.time_budget_min} min
            </div>
            <div>
              <span className="text-text-muted">Objectives:</span> {detail.objectives.join(", ") || "None"}
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              onClick={async () => {
                await endpoints.missionUpdate(detail.id, { status: "active" });
                setDetail({ ...detail, status: "active" });
                await load();
              }}
            >
              Mark Active
            </Button>
            <Button
              variant="secondary"
              onClick={async () => {
                await endpoints.missionUpdate(detail.id, { status: "completed" });
                setDetail({ ...detail, status: "completed" });
                await load();
              }}
            >
              Mark Completed
            </Button>
          </div>
        </SectionCard>
      )}

      {modalOpen && (
        <MissionModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          title={editing ? "Edit Mission" : "Add Mission"}
          form={form}
          setForm={setForm}
          onSubmit={submit}
          submitting={false}
          error={actionMessage}
        />
      )}
    </div>
  );
}
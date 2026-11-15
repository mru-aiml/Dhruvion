import { useEffect, useState } from "react";
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
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setModalOpen(false)}
        >
          <div
            className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-control border border-line bg-surface1 p-6"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 className="mb-4 font-heading text-lg text-text-primary">
              {editing ? "Edit Mission" : "Add Mission"}
            </h2>
            <div className="grid gap-3 md:grid-cols-2">
              <FieldShell label="Mission name">
                <input
                  className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </FieldShell>
              <FieldShell label="Region">
                <select
                  className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                  value={form.region_id}
                  onChange={(e) => setForm({ ...form, region_id: e.target.value })}
                >
                  {REGIONS.map((region) => (
                    <option key={region} value={region}>
                      {region}
                    </option>
                  ))}
                </select>
              </FieldShell>
              <FieldShell label="Mission type">
                <select
                  className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                  value={form.mission_type}
                  onChange={(e) => setForm({ ...form, mission_type: e.target.value })}
                >
                  {MISSION_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </FieldShell>
              <FieldShell label="Status">
                <select
                  className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value })}
                >
                  {STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </FieldShell>
              <FieldShell label="Start longitude (x)">
                <input
                  className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                  value={form.start_x}
                  onChange={(e) => setForm({ ...form, start_x: e.target.value })}
                />
              </FieldShell>
              <FieldShell label="Start latitude (y)">
                <input
                  className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                  value={form.start_y}
                  onChange={(e) => setForm({ ...form, start_y: e.target.value })}
                />
              </FieldShell>
              <FieldShell label="Destination longitude (x)">
                <input
                  className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                  value={form.dest_x}
                  onChange={(e) => setForm({ ...form, dest_x: e.target.value })}
                />
              </FieldShell>
              <FieldShell label="Destination latitude (y)">
                <input
                  className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                  value={form.dest_y}
                  onChange={(e) => setForm({ ...form, dest_y: e.target.value })}
                />
              </FieldShell>
              <FieldShell label="Time budget (minutes)">
                <input
                  className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                  value={form.time_budget_min}
                  onChange={(e) => setForm({ ...form, time_budget_min: e.target.value })}
                />
              </FieldShell>
              <FieldShell label="Description">
                <input
                  className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </FieldShell>
            </div>
            <FieldShell label="Objectives (one per line)">
              <textarea
                className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                rows={3}
                value={form.objectives}
                onChange={(e) => setForm({ ...form, objectives: e.target.value })}
              />
            </FieldShell>
            <FieldShell label="Notes">
              <textarea
                className="w-full rounded-control border border-line bg-surface2 px-3 py-2 text-sm text-text-primary"
                rows={3}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </FieldShell>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => void submit()}>Save Mission</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
import { useEffect, useRef, useState } from "react";
import { Bot, Loader2, Send, ShieldCheck, Wrench } from "lucide-react";
import PageHeader from "../../components/common/PageHeader";
import Panel from "../../components/common/Panel";
import StatusPill from "../../components/common/StatusPill";
import { ProvenanceBadge } from "../../components/common/StatusBadge";
import { endpoints } from "../../services/api/endpoints";
import { apiErrorMessage } from "../../services/api/client";
import { loadMission, subscribeMission } from "../../services/missionStore";
import type {
  AssistantHealthResponse,
  AssistantObservation,
  AssistantResponse,
  DatasetCatalogResponse,
  MissionPlanResponse,
} from "../../types";

const SUGGESTIONS = [
  "What is the terrain at longitude 137.4, latitude -4.6?",
  "Compare the shortest and safest routes to 137.3, -4.55.",
  "Can the planned mission reach the destination and return within its time limit?",
  "Summarise the historical REMS environment and RAD dose rates.",
  "An obstacle blocks my route — is the mission still feasible?",
];

interface Msg {
  role: "user" | "assistant";
  text: string;
  data?: AssistantResponse;
  failed?: boolean;
}

export default function AssistantPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<AssistantHealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [mission, setMission] = useState<MissionPlanResponse | null>(() => loadMission());
  const [datasets, setDatasets] = useState<DatasetCatalogResponse | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    endpoints
      .assistantHealth()
      .then((response) => active && setHealth(response))
      .catch((reason) => active && setHealthError(apiErrorMessage(reason)));
    endpoints
      .datasets()
      .then((response) => active && setDatasets(response))
      .catch(() => undefined);
    const unsubscribe = subscribeMission(setMission);
    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const latest = [...messages].reverse().find((message) => message.role === "assistant" && message.data)?.data;

  const send = async (msg: string) => {
    if (!msg.trim() || loading) return;
    setMessages((current) => [...current, { role: "user", text: msg }]);
    setInput("");
    setLoading(true);
    try {
      const result = await endpoints.assistantAsk({
        message: msg,
        mission_id: mission?.mission_id ?? null,
        context: {
          region_id: "gale_crater",
          selected_route_id: mission?.route.id ?? null,
          mission: mission
            ? {
                mission_id: mission.mission_id,
                feasibility_status: mission.feasibility_status,
                start: mission.start,
                destination: mission.destination,
                time_budget: mission.time_budget,
              }
            : null,
        },
      });
      setMessages((current) => [
        ...current,
        { role: "assistant", text: result.answer || result.message, data: result },
      ]);
    } catch (reason) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: `The assistant request failed: ${apiErrorMessage(reason)}. Deterministic terrain, route and environment endpoints remain available on the other workspaces.`,
          failed: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid h-full grid-cols-1 gap-4 lg:grid-cols-4">
      <div className="flex min-h-0 flex-col gap-4 lg:col-span-3">
        <PageHeader
          eyebrow="Decision support"
          title="AI Mission Assistant"
          description="The assistant interprets and explains. Every terrain, route, feasibility and environment value is computed by the backend services through allowlisted tools; the model never invents data."
          meta={
            <>
              <StatusPill tone={health?.available ? "observed" : "caution"}>
                {health?.available ? `Model ready · ${health.model}` : "Deterministic fallback"}
              </StatusPill>
              <StatusPill tone="derived">Real tool calls</StatusPill>
              <StatusPill tone="neutral" dot={false}>
                Historical measurements only
              </StatusPill>
            </>
          }
        />
        <Panel title="Conversation" className="flex min-h-0 flex-1 flex-col">
          <div ref={listRef} className="max-h-[58vh] min-h-[240px] flex-1 space-y-4 overflow-auto pr-1">
            {messages.length === 0 && (
              <div className="rounded-control border border-dashed border-line/70 p-4">
                <p className="text-sm text-text-secondary">
                  Ask a mission question. Requests call real backend tools first; if the local
                  language model is unavailable or slow, the deterministic tool results are
                  returned with a clear fallback flag.
                </p>
                <p className="mt-2 text-[11px] text-text-muted">
                  {mission
                    ? `Active mission ${mission.mission_id} (${mission.feasibility_status}) is attached as context.`
                    : "No mission is attached. Plan one in the Route Planner to enable mission feasibility questions."}
                </p>
              </div>
            )}
            {messages.map((message, index) => (
              <div key={index} className={`flex gap-3 ${message.role === "user" ? "justify-end" : ""}`}>
                {message.role === "assistant" && <Bot size={18} className="mt-1 shrink-0 text-cyan" />}
                <div
                  className={`max-w-[86%] rounded-md p-3 ${
                    message.role === "user"
                      ? "bg-mars-orange/20"
                      : message.failed
                        ? "border border-critical-red/35 bg-critical-red/[0.06]"
                        : "bg-surface2"
                  }`}
                >
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">{message.text}</div>
                  {message.data && <StructuredResult data={message.data} />}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-sm text-text-muted">
                <Loader2 size={14} className="animate-spin text-mars-orange" /> Running backend tools…
              </div>
            )}
          </div>
          <div className="mt-4 flex gap-2">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && void send(input)}
              placeholder="Ask about terrain, routes, feasibility, environment…"
              className="flex-1 rounded-md border border-line bg-surface2 px-3 py-2 text-sm"
              aria-label="Assistant message"
            />
            <button
              type="button"
              onClick={() => void send(input)}
              disabled={loading}
              className="flex items-center gap-1 rounded-md bg-mars-orange px-3 py-2 text-sm text-white disabled:opacity-60"
            >
              <Send size={14} /> Send
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => void send(suggestion)}
                disabled={loading}
                className="rounded-full border border-line px-2.5 py-1 text-xs text-text-secondary hover:bg-surface2 disabled:opacity-60"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </Panel>
      </div>

      <div className="space-y-4">
        <Panel title="Assistant status">
          {health ? (
            <dl className="space-y-1.5 text-xs">
              <SidebarRow label="Provider" value={health.provider} />
              <SidebarRow label="Model" value={health.model} />
              <SidebarRow label="Reachable" value={health.available ? "yes" : "no"} />
              <SidebarRow label="Fallback" value={health.fallback_available ? "available" : "unavailable"} />
              {health.error && <p className="pt-1 text-[10px] leading-relaxed text-warning-amber">{health.error}</p>}
            </dl>
          ) : healthError ? (
            <p className="text-xs text-warning-amber">{healthError}</p>
          ) : (
            <p className="text-xs text-text-muted">Checking model availability…</p>
          )}
        </Panel>

        <Panel title="Mission context">
          {mission ? (
            <dl className="space-y-1.5 text-xs">
              <SidebarRow label="Mission" value={mission.mission_id} />
              <SidebarRow label="Strategy" value={mission.route_strategy ?? "balanced"} />
              <SidebarRow label="Feasibility" value={mission.feasibility_status} />
              <SidebarRow label="Distance" value={`${(mission.route.distance_m / 1000).toFixed(2)} km`} />
              <SidebarRow label="Time budget" value={`${mission.time_budget.total_min ?? "—"} min`} />
              <SidebarRow label="Limit" value={`${mission.time_budget.limit_min ?? "—"} min`} />
              <div className="flex flex-wrap gap-1.5 pt-2">
                <ProvenanceBadge status="derived" />
                <span className="text-[10px] text-text-muted">Real backend mission</span>
              </div>
            </dl>
          ) : (
            <div className="space-y-2 text-xs text-text-secondary">
              <p>No active mission. Region: Gale Crater, Mars ({datasets?.datasets.length ?? 0} catalogued datasets).</p>
              <p className="text-text-muted">Route planning stores the mission id for assistant and report tools.</p>
            </div>
          )}
        </Panel>

        <Panel title="Tool transparency">
          <p className="text-xs leading-relaxed text-text-muted">
            Only calls that actually executed appear below. The model receives bounded tool output
            and explains it; it does not compute or fabricate values.
          </p>
          {latest ? (
            <div className="mt-2 space-y-1.5">
              {(latest.tool_activity.length ? latest.tool_activity : []).map((activity, index) => (
                <div key={`${activity.tool}-${index}`} className="flex items-start justify-between gap-2 text-[11px]">
                  <span className="flex min-w-0 items-center gap-1.5 text-text-secondary">
                    <Wrench size={11} className="shrink-0 text-cyan" />
                    <span className="truncate">{activity.tool}</span>
                  </span>
                  <span
                    className={
                      activity.status === "ok" || activity.status === "success"
                        ? "text-safe-green"
                        : "text-warning-amber"
                    }
                  >
                    {activity.status}
                  </span>
                </div>
              ))}
              {!latest.tool_activity.length && (
                <p className="text-[11px] text-text-muted">No tool executed for the latest answer.</p>
              )}
              <div className="border-t border-line/50 pt-2 text-[10px] text-text-muted">
                Confidence: {latest.confidence?.level ?? "unknown"} — {latest.confidence?.basis ?? "n/a"}
              </div>
            </div>
          ) : (
            <p className="mt-2 text-[11px] text-text-muted">Tool activity appears after the first request.</p>
          )}
          {health?.tools && (
            <details className="mt-2">
              <summary className="cursor-pointer text-[10px] uppercase tracking-[0.08em] text-text-muted">
                Allowlisted tools ({health.tools.length})
              </summary>
              <ul className="mt-1 space-y-0.5 text-[10px] text-text-muted">
                {health.tools.map((tool) => (
                  <li key={tool} className="truncate">
                    {tool}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </Panel>
      </div>
    </div>
  );
}

function StructuredResult({ data }: { data: AssistantResponse }) {
  const toolsUsed = data.tools_used?.length
    ? data.tools_used
    : (data.tool_activity ?? []).map((activity) => activity.tool);
  const observations = data.observations ?? [];
  const limitations = data.limitations ?? [];
  return (
    <div className="mt-3 space-y-2 border-t border-line pt-3">
      <div className="flex flex-wrap items-center gap-1.5">
        <ProvenanceBadge status={data.fallback ? "derived" : "observed"} />
        <span className="text-[9px] uppercase tracking-[0.08em] text-text-muted">intent: {data.intent}</span>
        {data.model && (
          <span className="text-[9px] uppercase tracking-[0.08em] text-text-muted">{data.model}</span>
        )}
        {data.fallback && <StatusPill tone="caution">Deterministic fallback</StatusPill>}
      </div>

      {toolsUsed.length > 0 && (
        <div>
          <div className="mb-1 text-micro text-text-muted">Tools called</div>
          <div className="flex flex-wrap gap-1">
            {toolsUsed.map((tool) => (
              <span key={tool} className="rounded border border-line bg-surface3 px-1.5 py-0.5 text-micro">
                {tool}
              </span>
            ))}
          </div>
        </div>
      )}

      {observations.length > 0 && (
        <div>
          <div className="mb-1 text-micro text-text-muted">Observations</div>
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="text-left text-text-muted">
                  <th className="py-0.5 pr-2 font-medium">Metric</th>
                  <th className="py-0.5 pr-2 font-medium">Value</th>
                  <th className="py-0.5 pr-2 font-medium">Unit</th>
                  <th className="py-0.5 font-medium">Provenance</th>
                </tr>
              </thead>
              <tbody>
                {observations.map((observation, index) => (
                  <tr key={`${observation.tool}-${index}`} className="border-t border-line/40">
                    <td className="py-1 pr-2 text-text-secondary">{observation.label}</td>
                    <td className="py-1 pr-2 tabular text-text-primary">{formatValue(observation)}</td>
                    <td className="py-1 pr-2 text-text-muted">{observation.unit ?? "—"}</td>
                    <td className="py-1 text-text-muted">{observation.provenance ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {observations.some((observation) => observation.coverage) && (
            <p className="mt-1 text-[9px] text-text-muted">
              Coverage: {unique(observations.map((observation) => observation.coverage).filter(Boolean)).join("; ")}
            </p>
          )}
        </div>
      )}

      {data.confidence && (
        <div>
          <div className="mb-1 text-micro text-text-muted">
            Confidence · <span className="text-text-secondary">{data.confidence.level}</span>
          </div>
          <p className="text-[10px] leading-relaxed text-text-secondary">{data.confidence.basis}</p>
        </div>
      )}

      {limitations.length > 0 && (
        <div>
          <div className="mb-1 text-micro text-text-muted">Limitations</div>
          <ul className="list-disc space-y-0.5 pl-4 text-[10px] leading-relaxed text-text-muted">
            {limitations.slice(0, 4).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {data.warnings.length > 0 && (
        <div>
          <div className="mb-1 text-micro text-warning-amber">Warnings</div>
          <ul className="list-disc space-y-0.5 pl-4 text-[10px] leading-relaxed text-text-secondary">
            {data.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {data.sources.length > 0 && (
        <div>
          <div className="mb-1 text-micro text-text-muted">Data sources</div>
          <ul className="space-y-0.5 text-[10px] text-text-secondary">
            {data.sources.map((source, index) => (
              <li key={index}>{formatValue({ label: "", tool: "", value: source } as AssistantObservation)}</li>
            ))}
          </ul>
        </div>
      )}

      {data.actions.length > 0 && (
        <div className="pt-1 text-[10px] text-text-muted">Suggested actions: {data.actions.join(", ")}</div>
      )}
      <div className="flex items-center gap-1.5 pt-1">
        <ShieldCheck size={11} className="text-safe-green" />
        <span className="text-[9px] uppercase tracking-[0.08em] text-text-muted">
          Values returned by backend tools
        </span>
      </div>
    </div>
  );
}

function formatValue(observation: AssistantObservation): string {
  const value = observation.value;
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(3);
  if (typeof value === "string" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function unique(values: Array<string | null | undefined>): string[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value))));
}

function SidebarRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <dt className="shrink-0 text-text-muted">{label}</dt>
      <dd className="max-w-[62%] truncate text-right tabular text-text-secondary" title={value}>
        {value}
      </dd>
    </div>
  );
}

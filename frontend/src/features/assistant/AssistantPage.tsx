import { useState } from "react";
import { Send, Bot } from "lucide-react";
import Panel from "../../components/common/Panel";
import { endpoints } from "../../services/api/endpoints";
import { SimulatedLabel, ProvenanceBadge } from "../../components/common/StatusBadge";
import type { AssistantResponse } from "../../types";

const SUGGESTIONS = [
  "Find the safest route to the geological target.",
  "Can I reach this target and return before my mission time expires?",
  "Which nearby geological formations are worth investigating?",
  "An obstacle has blocked my path. Find an alternative.",
];

interface Msg { role: "user" | "assistant"; text: string; data?: AssistantResponse }

export default function AssistantPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(false);

  const send = async (msg: string) => {
    if (!msg.trim()) return;
    setMessages((m) => [...m, { role: "user", text: msg }]);
    setInput("");
    setLoading(true);
    try {
      const res = await endpoints.assistantAsk({ message: msg, mission_id: null, context: { region_id: "gale_crater", selected_route_id: null } });
      setMessages((m) => [...m, { role: "assistant", text: res.message, data: res }]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", text: "AI assistant is unavailable. The backend endpoint is not implemented." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-full">
      <div className="lg:col-span-3 flex flex-col gap-4 min-h-0">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">AI Mission Assistant</h1>
          <SimulatedLabel />
        </div>
        <Panel title="Conversation">
          <div className="space-y-4 max-h-[60vh] overflow-auto">
            {messages.length === 0 && (
              <p className="text-sm text-text-muted">Ask a mission question. Responses are grounded in backend tool outputs when available.</p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                {m.role === "assistant" && <Bot size={18} className="text-cyan mt-1" />}
                <div className={`max-w-[80%] ${m.role === "user" ? "bg-mars-orange/20" : "bg-surface2"} rounded-md p-3`}>
                  <div className="text-sm">{m.text}</div>
                  {m.data && <StructuredResult data={m.data} />}
                </div>
              </div>
            ))}
            {loading && <div className="text-sm text-text-muted">Thinking…</div>}
          </div>
          <div className="mt-4 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send(input)}
              placeholder="Ask about terrain, routes, feasibility…"
              className="flex-1 bg-surface2 border border-line rounded-md px-3 py-2 text-sm"
            />
            <button onClick={() => send(input)} className="px-3 py-2 rounded-md bg-mars-orange text-white text-sm flex items-center gap-1">
              <Send size={14} /> Send
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)} className="text-xs px-2.5 py-1 rounded-full border border-line hover:bg-surface2 text-text-secondary">
                {s}
              </button>
            ))}
          </div>
        </Panel>
      </div>

      <div className="space-y-4">
        <Panel title="Mission context">
          <ul className="space-y-1 text-xs">
            <li><span className="text-text-muted">Mission:</span> Alpha-1</li>
            <li><span className="text-text-muted">Region:</span> Gale Crater, Mars</li>
            <li><span className="text-text-muted">Time remaining:</span> 90 min (SIMULATED)</li>
            <li><span className="text-text-muted">Active route:</span> Balanced</li>
            <li><span className="text-text-muted">Objective:</span> Geological sampling</li>
            <li><span className="text-text-muted">Hazards:</span> 1 identified (SIMULATED)</li>
            <li><span className="text-text-muted">Layers:</span> Optical, Science targets</li>
          </ul>
        </Panel>
        <Panel title="Tool transparency">
          <p className="text-xs text-text-muted">Tool activity is shown only when a tool call actually occurs.</p>
        </Panel>
      </div>
    </div>
  );
}

function StructuredResult({ data }: { data: AssistantResponse }) {
  return (
    <div className="mt-3 space-y-2 border-t border-line pt-3">
      {data.tool_activity.length > 0 && (
        <div>
          <div className="text-micro text-text-muted mb-1">Tool activity</div>
          <div className="flex flex-wrap gap-1">
            {data.tool_activity.map((t, i) => (
              <span key={i} className="text-micro px-1.5 py-0.5 rounded bg-surface3 border border-line">
                {t.tool} · {t.status}
              </span>
            ))}
          </div>
        </div>
      )}
      {Array.isArray(data.evidence) && data.evidence.length > 0 && (
        <div>
          <div className="text-micro text-text-muted mb-1">Supporting evidence</div>
          <ul className="text-xs text-text-secondary list-disc pl-4">
            {data.evidence.map((e, i) => <li key={i}>{String(e)}</li>)}
          </ul>
        </div>
      )}
      {data.warnings.length > 0 && (
        <div>
          <div className="text-micro text-warning-amber mb-1">Warnings</div>
          <ul className="text-xs text-text-secondary list-disc pl-4">
            {data.warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}
      {data.sources.length > 0 && (
        <div>
          <div className="text-micro text-text-muted mb-1">Data sources</div>
          <div className="text-xs text-text-secondary">{data.sources.map(String).join(", ")}</div>
        </div>
      )}
      {data.actions.length > 0 && (
        <div className="text-micro text-text-muted pt-1">
          Suggested actions: {data.actions.join(", ")}
        </div>
      )}
      <div className="pt-1"><ProvenanceBadge status="simulated" /></div>
    </div>
  );
}

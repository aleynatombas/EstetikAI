export type KnowledgeSource = {
  title: string;
  score: number | null;
};

export type Analysis = {
  id: string;
  created_at: string;
  request_type: string;
  category: string;
  priority: string;
  verified_information: string[];
  missing_information: string[];
  recommended_actions: string[];
  escalation_required: boolean;
  reason: string;
  knowledge_sources: KnowledgeSource[];
  anythingllm_error: boolean;
  direct_answer: string;
};

export type RequestSummary = {
  id: string;
  original_request: string;
  request_type: string;
  category: string;
  priority: string;
  escalation_required: boolean;
  anythingllm_error: boolean;
  created_at: string;
};

export type SavedRequest = Analysis & {
  original_request: string;
};

export type EscalationReport = {
  open_count: number;
  high_count: number;
  medium_count: number;
  items: SavedRequest[];
};

export type ActivityEvent = {
  id: string;
  event_type: string;
  request_id: string;
  request_preview: string;
  created_at: string;
};

export type KnowledgeDocument = {
  title: string;
  kind?: string;
  use_count: number;
  last_used_at: string | null;
  last_request_id: string | null;
  last_request_preview: string | null;
};

export type KnowledgeCatalog = {
  connected: boolean;
  workspace_name: string;
  workspace_slug: string;
  documents: KnowledgeDocument[];
};

const FRIENDLY_ERROR = "Analizi tamamlayamadık. Lütfen yeniden deneyin.";

export async function fetchHealth(): Promise<boolean> {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) return false;
    const body = (await response.json()) as { status?: string };
    return body.status === "ok";
  } catch {
    return false;
  }
}

export async function analyzeRequest(
  employeeRequest: string,
  audience: "employee" | "client" = "employee",
): Promise<Analysis> {
  return readJson(`/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ employee_request: employeeRequest, audience }),
  }, normalizeAnalysis);
}

export async function fetchRequests(): Promise<RequestSummary[]> {
  return readJson("/api/requests", undefined, (body) => (Array.isArray(body) ? body.map(summary) : []));
}

export async function fetchRequest(id: string): Promise<SavedRequest> {
  return readJson(`/api/requests/${encodeURIComponent(id)}`, undefined, savedRequest);
}

export async function fetchEscalations(): Promise<EscalationReport> {
  return readJson("/api/escalations", undefined, (body) => {
    const record = objectRecord(body);
    return {
      open_count: numberValue(record.open_count),
      high_count: numberValue(record.high_count),
      medium_count: numberValue(record.medium_count),
      items: Array.isArray(record.items) ? record.items.map(savedRequest) : [],
    };
  });
}

export async function fetchActivity(): Promise<ActivityEvent[]> {
  return readJson("/api/activity", undefined, (body) => (Array.isArray(body) ? body.flatMap(activityEvent) : []));
}

export async function fetchKnowledge(): Promise<KnowledgeCatalog> {
  return readJson("/api/knowledge/sources", undefined, (body) => {
    const record = objectRecord(body);
    return {
      connected: Boolean(record.connected),
      workspace_name: text(record.workspace_name, ""),
      workspace_slug: text(record.workspace_slug, ""),
      documents: Array.isArray(record.documents) ? record.documents.flatMap(documentItem) : [],
    };
  });
}

async function readJson<T>(url: string, init: RequestInit | undefined, parse: (body: unknown) => T): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch {
    throw new Error("EstetikAI servisine ulaşılamadı. Lütfen yeniden deneyin.");
  }
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return parse(await response.json());
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) return body.detail;
  } catch {
    return FRIENDLY_ERROR;
  }
  return FRIENDLY_ERROR;
}

function normalizeAnalysis(body: unknown): Analysis {
  const record = objectRecord(body);
  return {
    id: text(record.id, ""),
    created_at: text(record.created_at, ""),
    request_type: text(record.request_type, "Unknown"),
    category: text(record.category, "Unspecified"),
    priority: text(record.priority, "Medium"),
    verified_information: texts(record.verified_information),
    missing_information: texts(record.missing_information),
    recommended_actions: texts(record.recommended_actions),
    escalation_required: Boolean(record.escalation_required),
    reason: text(record.reason, ""),
    knowledge_sources: sources(record.knowledge_sources),
    anythingllm_error: Boolean(record.anythingllm_error),
    direct_answer: text(record.direct_answer, ""),
  };
}

function summary(body: unknown): RequestSummary {
  const record = objectRecord(body);
  return {
    id: text(record.id, ""),
    original_request: text(record.original_request, ""),
    request_type: text(record.request_type, ""),
    category: text(record.category, ""),
    priority: text(record.priority, ""),
    escalation_required: Boolean(record.escalation_required),
    anythingllm_error: Boolean(record.anythingllm_error),
    created_at: text(record.created_at, ""),
  };
}

function savedRequest(body: unknown): SavedRequest {
  return { ...normalizeAnalysis(body), original_request: text(objectRecord(body).original_request, "") };
}

function activityEvent(body: unknown): ActivityEvent[] {
  const record = objectRecord(body);
  const id = text(record.id, "");
  const eventType = text(record.event_type, "");
  if (!id || !eventType) return [];
  return [
    {
      id,
      event_type: eventType,
      request_id: text(record.request_id, ""),
      request_preview: text(record.request_preview, ""),
      created_at: text(record.created_at, ""),
    },
  ];
}

function documentItem(body: unknown): KnowledgeDocument[] {
  const record = objectRecord(body);
  const title = text(record.title, "");
  if (!title) return [];
  return [
    {
      title,
      kind: text(record.kind, "") || undefined,
      use_count: numberValue(record.use_count),
      last_used_at: typeof record.last_used_at === "string" ? record.last_used_at : null,
      last_request_id: typeof record.last_request_id === "string" ? record.last_request_id : null,
      last_request_preview: typeof record.last_request_preview === "string" ? record.last_request_preview : null,
    },
  ];
}

function objectRecord(body: unknown): Record<string, unknown> {
  if (!body || typeof body !== "object") throw new Error(FRIENDLY_ERROR);
  return body as Record<string, unknown>;
}

function text(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function texts(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.trim() !== "");
}

function sources(value: unknown): KnowledgeSource[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const record = item as Record<string, unknown>;
    const title = text(record.title, "");
    if (!title) return [];
    const score = typeof record.score === "number" ? record.score : null;
    return [{ title, score }];
  });
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

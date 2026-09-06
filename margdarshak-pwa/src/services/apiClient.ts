const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(path.startsWith("/admin") ? { Authorization: `Bearer ${import.meta.env.VITE_ADMIN_API_KEY ?? "local-admin-demo"}` } : {}),
      ...options.headers
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body)
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Margdarshak API ${response.status}: ${detail}`);
  }

  return response.json() as Promise<T>;
}

async function upload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE_URL}${path}`, { method: "POST", body: form, headers: { Authorization: `Bearer ${import.meta.env.VITE_ADMIN_API_KEY ?? "local-admin-demo"}` } });
  if (!response.ok) throw new Error(`Margdarshak API ${response.status}: ${await response.text()}`);
  return response.json() as Promise<T>;
}

export type ResourceRecommendation = {
  session_id: string;
  reasoning_snapshot: string;
  resource: {
    id: string;
    title: string;
    url: string;
    format: "video" | "sheet";
    pacing: "short" | "long";
    price_tier: "free" | "paid";
  };
};

export type VoiceSession = {
  session_id: string;
  ticket_id: string;
  agora_app_id: string;
  channel_name: string;
  uid: number;
  rtc_token: string;
  rtm_token: string;
  agent: Record<string, unknown>;
};

export type TranscriptTurn = {
  id: string;
  call_session_id: string;
  turn_index: number;
  speaker: "student" | "agent" | "human_coordinator";
  content: string;
  timestamp: string;
};

export type VoiceHistorySession = {
  session_id: string;
  started_at: string;
  ended_at: string | null;
  turns: TranscriptTurn[];
};

export type VoiceSessionStatus = {
  session_id: string;
  ended_at: string | null;
  escalated: boolean;
  poc_name: string | null;
  handoff_status: "queued_for_human_support" | null;
};

export type TicketWithCaseCard = {
  id: string;
  status: "open" | "escalated" | "resolved";
  display_status: string;
  display_status_detail: string;
  issue_summary: string;
  confidence_score: number;
  escalated_to: string;
  parent_ticket_id: string | null;
  similar_count: number;
  created_at: string;
  case_card: Record<string, unknown> | null;
};

export type MatchBridge = {
  matched: boolean;
  bridge_id: string | null;
  status: "active" | "expired" | "revealed" | "upgraded_to_voice" | null;
  created_at: string | null;
  expires_at: string | null;
};

export type ConsentResult = {
  status: "pending" | "revealed" | "upgraded_to_voice";
  linkedin_urls?: Array<string | null>;
  channel_name?: string;
  rtc_tokens?: string[];
};

export type AdminTicket = {
  id: string; status: "open" | "claimed" | "waiting" | "escalated" | "resolved"; issue_summary: string; confidence_score: number; created_at: string; updated_at: string;
  student: { name: string; enrollment_number: string; email: string };
  placement: { company: string | null; drive_id: string | null; role: string | null; round: string | null; deadline: string | null };
  intelligence: { urgency: "low" | "medium" | "high" | "critical"; language: string; category: string; assigned_coordinator: string | null; cluster_id: string | null };
  original_request: string | null; conversation_summary: string | null; source: string | null;
};
export type AdminOverview = { metrics: Record<AdminTicket["status"], number>; priority_tickets: AdminTicket[]; active_drives: Array<{ id: string; company: string; status: string; policy: string }>; recent_updates: Array<{ kind: string; text: string; at: string }> };
export type AdminCluster = { id: string; title: string; company_name: string | null; urgency: "low" | "medium" | "high" | "critical"; priority_score: number; status: string; affected_students: number; incident_update: string | null; response_draft: string | null; created_at: string };
export type AdminKnowledge = { id: string; title: string; type: string; company: string | null; version: string; status: "draft" | "published" | "expired"; source: string; content: Record<string, unknown>; created_at: string };

export function createMatchmakerSocket(bridgeId: string, studentId: string): WebSocket {
  const endpoint = new URL(API_BASE_URL);
  endpoint.protocol = endpoint.protocol === "https:" ? "wss:" : "ws:";
  endpoint.pathname = endpoint.pathname.replace(/\/api\/v1\/?$/, "");
  endpoint.pathname += `/ws/matchmaker/${encodeURIComponent(bridgeId)}`;
  endpoint.searchParams.set("student_id", studentId);
  return new WebSocket(endpoint);
}

export const apiClient = {
  adminOverview() { return request<AdminOverview>("/admin/overview"); },
  adminTickets(filters: Record<string, string | undefined> = {}) { const query = new URLSearchParams(Object.entries(filters).filter((entry): entry is [string, string] => Boolean(entry[1]))).toString(); return request<AdminTicket[]>(`/admin/tickets${query ? `?${query}` : ""}`); },
  updateAdminTicket(id: string, body: { status?: string; assigned_coordinator?: string; urgency?: string; language?: string; category?: string; original_request?: string; conversation_summary?: string; cluster_id?: string | null }) { return request(`/admin/tickets/${encodeURIComponent(id)}`, { method: "PATCH", body }); },
  adminStats() { return request<{ total_conversations: number; tickets_created: number; tickets_resolved: number; students_assisted: number; active_clusters: number; average_resolution_time_hours: number; most_common_issue_categories: Record<string, number>; most_requested_companies: Record<string, number>; most_common_languages: Record<string, number> }>("/admin/stats"); },
  adminClusters() { return request<AdminCluster[]>("/admin/clusters"); },
  createAdminCluster(body: { title: string; company_name?: string; urgency: string }) { return request<{ id: string }>("/admin/clusters", { method: "POST", body }); },
  startAdminAgoraSession() { return request<{ app_id: string; channel_name: string; uid: number; rtc_token: string }>("/admin/agora/session", { method: "POST" }); },
  draftCluster(id: string, notes: string) { return request<{ draft: string }>(`/admin/clusters/${encodeURIComponent(id)}/draft-response`, { method: "POST", body: { notes } }); },
  publishCluster(id: string, message: string) { return request(`/admin/clusters/${encodeURIComponent(id)}/publish-update`, { method: "POST", body: { message } }); },
  resolveCluster(id: string) { return request(`/admin/clusters/${encodeURIComponent(id)}/resolve`, { method: "POST" }); },
  adminKnowledge() { return request<AdminKnowledge[]>("/admin/knowledge"); },
  createKnowledge(body: { title: string; document_type: string; version_label: string; source_reference: string; company_name?: string; content?: Record<string, unknown> }) { return request("/admin/knowledge", { method: "POST", body }); },
  updateKnowledge(id: string, status: string) { return request(`/admin/knowledge/${encodeURIComponent(id)}?status=${encodeURIComponent(status)}`, { method: "PATCH" }); },
  previewShortlist(file: File) { return upload<{ valid: boolean; record_count: number; preview: Array<Record<string, string>>; rows: Array<Record<string, string>> }>("/admin/knowledge/shortlist-preview", file); },
  importShortlist(body: { title: string; source_reference: string; version_label: string; rows: Array<Record<string, string>> }) { return request("/admin/knowledge/shortlist-import", { method: "POST", body }); },
  startVoiceSession(studentId: string) {
    const uidValues = new Uint32Array(1);
    crypto.getRandomValues(uidValues);
    // Agora integer-mode RTC UIDs must be below 2^31 - 1. Reserve UID 1
    // for the conversational agent, so callers use the range 2..2147483646.
    const uid = (uidValues[0] % 2_147_483_645) + 2;
    return request<VoiceSession>("/voice/session/start", {
      method: "POST",
      body: {
        student_id: studentId,
        channel_name: `margdarshak-${crypto.randomUUID()}`,
        uid
      }
    });
  },

  endVoiceSession(sessionId: string) {
    return request<{ session_id: string; ended_at: string }>(
      `/voice/session/${encodeURIComponent(sessionId)}/end`,
      { method: "POST" }
    );
  },

  getVoiceSessionStatus(sessionId: string) {
    return request<VoiceSessionStatus>(
      `/voice/session/${encodeURIComponent(sessionId)}/status`
    );
  },

  getVoiceHistory(studentId: string) {
    return request<VoiceHistorySession[]>(
      `/voice/history/${encodeURIComponent(studentId)}`
    );
  },

  ingestTranscript(
    sessionId: string,
    turn: { speaker: TranscriptTurn["speaker"]; content: string; is_final?: boolean }
  ) {
    return request<{ accepted: boolean }>(
      `/voice/session/${encodeURIComponent(sessionId)}/transcript`,
      { method: "POST", body: { ...turn, is_final: turn.is_final ?? true } }
    );
  },

  getTicket(ticketId: string) {
    return request<TicketWithCaseCard>(`/tickets/${encodeURIComponent(ticketId)}`);
  },

  listTickets(params?: { studentId?: string; status?: TicketWithCaseCard["status"] }) {
    const query = new URLSearchParams();
    if (params?.studentId) query.set("student_id", params.studentId);
    if (params?.status) query.set("status", params.status);
    const suffix = query.size ? `?${query.toString()}` : "";
    return request<TicketWithCaseCard[]>(`/tickets${suffix}`);
  },

  requestMatch(studentId: string, tags: string[], campusResponsibility?: string) {
    return request<MatchBridge>("/matchmaker/request", {
      method: "POST",
      body: {
        student_id: studentId,
        tags,
        campus_responsibility: campusResponsibility || null
      }
    });
  },

  getMatchBridge(bridgeId: string) {
    return request<MatchBridge>(`/matchmaker/bridge/${encodeURIComponent(bridgeId)}`);
  },

  revealLinkedIn(bridgeId: string, studentId: string) {
    return request<ConsentResult>(
      `/matchmaker/bridge/${encodeURIComponent(bridgeId)}/reveal`,
      { method: "POST", body: { student_id: studentId } }
    );
  },

  upgradeMatchToVoice(bridgeId: string, studentId: string) {
    return request<ConsentResult>(
      `/matchmaker/bridge/${encodeURIComponent(bridgeId)}/upgrade-voice`,
      { method: "POST", body: { student_id: studentId } }
    );
  },

  getResourceRecommendation(sessionId: string) {
    return request<ResourceRecommendation>(
      `/resources/recommendations/${encodeURIComponent(sessionId)}`
    );
  },

  ensureResourceRecommendation(sessionId: string) {
    return request<ResourceRecommendation>(
      `/resources/recommendations/${encodeURIComponent(sessionId)}/ensure`,
      { method: "POST" }
    );
  }
};

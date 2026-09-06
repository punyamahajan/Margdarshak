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

export function createMatchmakerSocket(bridgeId: string, studentId: string): WebSocket {
  const endpoint = new URL(API_BASE_URL);
  endpoint.protocol = endpoint.protocol === "https:" ? "wss:" : "ws:";
  endpoint.pathname = endpoint.pathname.replace(/\/api\/v1\/?$/, "");
  endpoint.pathname += `/ws/matchmaker/${encodeURIComponent(bridgeId)}`;
  endpoint.searchParams.set("student_id", studentId);
  return new WebSocket(endpoint);
}

export const apiClient = {
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

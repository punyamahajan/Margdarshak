import type { VoiceHistorySession, TranscriptTurn } from "../services/apiClient";

export type ExtractedLink = {
  url: string;
  title: string;
  domain: string;
  source: "agent" | "recommendation" | "student" | "case_card";
  snippet?: string;
  category?: string;
};

export type SynthesizedSummary = {
  topic: string;
  overview: string;
  studentQuery: string;
  aiGuidance: string;
  keyPoints: string[];
  statusBadge: string;
};

const URL_REGEX = /https?:\/\/[^\s<>"'()]+(?:\([^\s<>"'()]+\)|[^\s`!()\[\]{};:'",<>?«»“”‘’])/gi;

function cleanUrl(raw: string): string {
  return raw.replace(/[.,;!?:)]+$/, "");
}

function getDomainLabel(domain: string): string {
  const d = domain.replace(/^www\./, "").toLowerCase();
  if (d.includes("takeuforward")) return "Striver's A2Z DSA Sheet";
  if (d.includes("leetcode")) return "LeetCode Platform";
  if (d.includes("geeksforgeeks")) return "GeeksforGeeks";
  if (d.includes("hackerrank")) return "HackerRank Practice";
  if (d.includes("github.com")) return "GitHub Repository";
  if (d.includes("youtube.com") || d.includes("youtu.be")) return "YouTube Video Tutorial";
  if (d.includes("drive.google.com")) return "Google Drive Document";
  if (d.includes("tcsion") || d.includes("tcs.com")) return "TCS iON National Qualifier";
  if (d.includes("infosys")) return "Infosys Springboard / Portal";
  if (d.includes("roadmap.sh")) return "Developer Roadmap";
  if (d.includes("college") || d.includes("univ") || d.includes("edu")) return "University Campus Portal";
  return d;
}

export function extractLinksFromSession(session: VoiceHistorySession): ExtractedLink[] {
  const links: ExtractedLink[] = [];
  const seenUrls = new Set<string>();

  for (const turn of session.turns) {
    const matches = turn.content.match(URL_REGEX);
    if (!matches) continue;

    for (const rawMatch of matches) {
      const url = cleanUrl(rawMatch);
      if (!url || seenUrls.has(url)) continue;
      seenUrls.add(url);

      try {
        const parsed = new URL(url);
        const domain = parsed.hostname.replace(/^www\./, "");
        let title = getDomainLabel(domain);

        // If path has a clean slug, enhance title
        if (parsed.pathname && parsed.pathname.length > 2 && title === domain) {
          const parts = parsed.pathname.split("/").filter(Boolean);
          if (parts.length > 0) {
            const lastPart = decodeURIComponent(parts[parts.length - 1])
              .replace(/[-_]/g, " ")
              .trim();
            if (lastPart.length > 2 && lastPart.length < 50) {
              title = `${lastPart.charAt(0).toUpperCase() + lastPart.slice(1)} (${domain})`;
            }
          }
        }

        const isAgent = turn.speaker === "agent";
        links.push({
          url,
          title,
          domain,
          source: isAgent ? "agent" : "student",
          snippet: turn.content.length > 130 ? `${turn.content.slice(0, 127)}…` : turn.content,
          category: isAgent ? "AI Resource" : "Shared in Call",
        });
      } catch {
        // invalid URL skip
      }
    }
  }

  return links;
}

export function generateClientSessionSummary(session: VoiceHistorySession): SynthesizedSummary {
  const studentTurns = session.turns.filter((t) => t.speaker === "student" && t.content.trim());
  const agentTurns = session.turns.filter((t) => t.speaker === "agent" && t.content.trim());

  const fullStudentText = studentTurns.map((t) => t.content.trim()).join(" ");
  const fullAgentText = agentTurns.map((t) => t.content.trim()).join(" ");

  // Extract topic
  let topic = "Voice Guidance Session";
  if (studentTurns.length > 0) {
    const firstTurn = studentTurns[0].content.trim();
    // Remove leading conversational fillers like "hey", "hi", "can you tell me"
    const cleaned = firstTurn.replace(/^(hi|hello|hey|excuse me|can you tell me|please help me with|i want to know about|tell me about)\s+/i, "");
    const capitalized = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
    topic = capitalized.length > 60 ? `${capitalized.slice(0, 57)}…` : capitalized;
  }

  // Key points extraction
  const keyPoints: string[] = [];

  // Detect specific topics
  const lower = (fullStudentText + " " + fullAgentText).toLowerCase();
  if (lower.includes("dsa") || lower.includes("sheet") || lower.includes("algorithm") || lower.includes("data structure")) {
    keyPoints.push("DSA and algorithmic interview preparation recommendations discussed.");
  }
  if (lower.includes("drive") || lower.includes("tcs") || lower.includes("infosys") || lower.includes("placement") || lower.includes("company")) {
    keyPoints.push("Campus placement drives, eligibility criteria, and application rules reviewed.");
  }
  if (lower.includes("resume") || lower.includes("project") || lower.includes("portfolio")) {
    keyPoints.push("Resume building and project portfolio alignment suggestions provided.");
  }
  if (lower.includes("backlog") || lower.includes("cgpa") || lower.includes("criteria") || lower.includes("policy")) {
    keyPoints.push("Academic criteria, backlog clearance, and placement cell policy clarified.");
  }
  if (lower.includes("escalat") || lower.includes("ticket") || lower.includes("coordinator")) {
    keyPoints.push("Grievance ticket created and assigned to placement coordination desk.");
  }

  // If no specific points caught, provide generic smart points
  if (keyPoints.length === 0) {
    if (studentTurns.length > 0) {
      keyPoints.push(`Student inquired: "${studentTurns[0].content.slice(0, 80)}…"`);
    }
    if (agentTurns.length > 0) {
      keyPoints.push("Margdarshak provided step-by-step guidance and answers.");
    }
  }

  // Status badge
  let statusBadge = "Guidance Completed";
  if (lower.includes("escalat") || lower.includes("coordinator")) {
    statusBadge = "Escalated to Desk";
  } else if (extractLinksFromSession(session).length > 0) {
    statusBadge = "Resources Recommended";
  } else if (session.turns.length > 0) {
    statusBadge = "AI Resolved";
  } else {
    statusBadge = "No Speech";
  }

  const overview = agentTurns.length > 0
    ? agentTurns[0].content.slice(0, 180) + (agentTurns[0].content.length > 180 ? "…" : "")
    : "Conversation session with Margdarshak conversational assistant.";

  return {
    topic,
    overview,
    studentQuery: fullStudentText || "No student audio was recorded during this call.",
    aiGuidance: fullAgentText || "No agent response was generated for this session.",
    keyPoints,
    statusBadge,
  };
}

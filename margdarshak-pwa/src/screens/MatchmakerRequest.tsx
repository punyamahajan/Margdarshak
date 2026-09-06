import { useState, type FormEvent } from "react";
import { apiClient } from "../services/apiClient";
import { useAuth } from "../context/AuthContext";

type MatchmakerRequestProps = {
  onBack: () => void;
  onMatched: (bridgeId: string) => void;
};

const DEFAULT_STUDENT_ID = import.meta.env.VITE_STUDENT_ID as string | undefined;

export function MatchmakerRequest({ onBack, onMatched }: MatchmakerRequestProps) {
  const { student } = useAuth();
  const activeStudentId = student?.id ?? DEFAULT_STUDENT_ID;

  const defaultTags = student?.tags?.join(", ") || "";
  const [tagsText, setTagsText] = useState(defaultTags);
  const [responsibility, setResponsibility] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const tags = tagsText.split(",").map((tag) => tag.trim()).filter(Boolean);
    if (!activeStudentId) {
      setStatus("Please sign in or set VITE_STUDENT_ID to a student UUID first.");
      return;
    }
    if (!tags.length && !responsibility.trim()) {
      setStatus("Add at least one skill, interest, or campus responsibility.");
      return;
    }

    setSubmitting(true);
    setStatus(null);
    try {
      const result = await apiClient.requestMatch(activeStudentId, tags, responsibility.trim());
      if (result.matched && result.bridge_id) {
        onMatched(result.bridge_id);
      } else {
        setStatus("You are opted in. We will create a bridge when a relevant match is available.");
      }
    } catch (cause) {
      setStatus(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="matchmaker-request">
      <button className="text-button" type="button" onClick={onBack}>← Back</button>
      <header className="matchmaker-request__header">
        <p className="section-kicker">48-hour matchmaker</p>
        <h1>Find someone who gets the work</h1>
        <p>Share only what you want to compare notes on. Your identity stays hidden.</p>
      </header>

      <form className="matchmaker-form" onSubmit={submit}>
        <label htmlFor="match-tags">
          Skills or interests
          <span>Separate a few with commas</span>
        </label>
        <input
          id="match-tags"
          value={tagsText}
          onChange={(event) => setTagsText(event.target.value)}
          placeholder="Python, backend, interview prep"
        />
        <label htmlFor="match-responsibility">
          Campus responsibility <span>Optional</span>
        </label>
        <input
          id="match-responsibility"
          value={responsibility}
          onChange={(event) => setResponsibility(event.target.value)}
          placeholder="Coding club, placement coordinator"
        />
        <button className="primary-button" type="submit" disabled={submitting}>
          {submitting ? "Looking…" : "Find my match"}
        </button>
        {status ? <p className="form-status" role="status">{status}</p> : null}
      </form>
    </main>
  );
}

import { useState, type KeyboardEvent } from "react";
import { useAuth } from "../context/AuthContext";

const QUICK_KNOWN_SUGGESTIONS = [
  "Data Structures",
  "Algorithms",
  "DBMS",
  "Operating Systems",
  "Computer Networks",
  "Python",
  "Java",
  "SQL",
];

const QUICK_EXPLORE_SUGGESTIONS = [
  "System Design",
  "Cloud Architecture",
  "Machine Learning",
  "Microservices",
  "DevOps / Docker",
  "Web Development",
  "Cybersecurity",
];

export function ProfileSection() {
  const { student, updateProfile, openAuthModal } = useAuth();

  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Edit state
  const [editCollege, setEditCollege] = useState(student?.college_name || "");
  const [editBranch, setEditBranch] = useState(student?.branch || "");
  const [knownSubjects, setKnownSubjects] = useState<string[]>(student?.known_subjects || []);
  const [subjectInput, setSubjectInput] = useState("");
  const [exploreTopics, setExploreTopics] = useState<string[]>(student?.explore_topics || []);
  const [exploreInput, setExploreInput] = useState("");

  const startEditing = () => {
    if (!student) {
      openAuthModal("login");
      return;
    }
    setEditCollege(student.college_name || "");
    setEditBranch(student.branch || "");
    setKnownSubjects(student.known_subjects || []);
    setExploreTopics(student.explore_topics || []);
    setErrorMessage(null);
    setSaveSuccess(false);
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
    setErrorMessage(null);
  };

  const handleAddSubject = (val: string) => {
    const trimmed = val.trim();
    if (trimmed && !knownSubjects.includes(trimmed)) {
      setKnownSubjects((prev) => [...prev, trimmed]);
    }
    setSubjectInput("");
  };

  const handleRemoveSubject = (val: string) => {
    setKnownSubjects((prev) => prev.filter((s) => s !== val));
  };

  const handleAddExplore = (val: string) => {
    const trimmed = val.trim();
    if (trimmed && !exploreTopics.includes(trimmed)) {
      setExploreTopics((prev) => [...prev, trimmed]);
    }
    setExploreInput("");
  };

  const handleRemoveExplore = (val: string) => {
    setExploreTopics((prev) => prev.filter((t) => t !== val));
  };

  const handleSave = async () => {
    setSaving(true);
    setErrorMessage(null);
    try {
      await updateProfile({
        college_name: editCollege.trim() || undefined,
        branch: editBranch.trim() || undefined,
        known_subjects: knownSubjects,
        explore_topics: exploreTopics,
      });
      setSaving(false);
      setEditing(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 5000);
    } catch (err) {
      setSaving(false);
      setErrorMessage(err instanceof Error ? err.message : String(err));
    }
  };

  if (!student) {
    return (
      <section className="profile-banner-card" aria-labelledby="profile-guest-title">
        <div className="profile-guest-content">
          <div className="profile-guest-icon" aria-hidden="true">🎓</div>
          <div>
            <h2 id="profile-guest-title">Student Profile & Academic Skills</h2>
            <p>
              Sign in or create your profile with your college name, student ID, and the subjects you know.
              Margdarshak shapes its advice around your academic background.
            </p>
          </div>
        </div>
        <div className="profile-guest-actions">
          <button
            type="button"
            className="home-path__button home-path__button--primary"
            onClick={() => openAuthModal("signup")}
          >
            Create Profile & Skills
          </button>
          <button
            type="button"
            className="home-path__button"
            onClick={() => openAuthModal("login")}
          >
            Sign In
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="profile-section-card" aria-labelledby="profile-section-title">
      <div className="profile-section-header">
        <div className="profile-header-meta">
          <span className="profile-section-badge">Student Profile</span>
          <h2 id="profile-section-title">{student.name}</h2>
          <p className="profile-section-sub">
            {student.college_name} · ID: {student.student_id} · {student.branch}
          </p>
        </div>
        {!editing && (
          <button
            type="button"
            className="profile-edit-btn"
            onClick={startEditing}
            aria-label="Edit subjects and college profile"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">
              <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" />
            </svg>
            Edit Profile & Subjects
          </button>
        )}
      </div>

      {saveSuccess && (
        <div className="profile-toast-success" role="status">
          ✓ Profile updated successfully! Margdarshak now references your updated subjects and learning goals.
        </div>
      )}

      {errorMessage && (
        <div className="profile-toast-error" role="alert">
          {errorMessage}
        </div>
      )}

      {!editing ? (
        <div className="profile-view-body">
          <div className="profile-skills-group">
            <div className="profile-skills-group__label">
              <span className="skill-dot skill-dot--known" />
              <strong>Subjects & Skills You Know ({student.known_subjects.length})</strong>
            </div>
            <div className="tag-chips-wrapper">
              {student.known_subjects.length ? (
                student.known_subjects.map((sub) => (
                  <span key={sub} className="tag-chip tag-chip--known tag-chip--static">
                    {sub}
                  </span>
                ))
              ) : (
                <span className="tag-chip--empty">No known subjects added yet. Click &ldquo;Edit Profile&rdquo; to add.</span>
              )}
            </div>
          </div>

          <div className="profile-skills-group">
            <div className="profile-skills-group__label">
              <span className="skill-dot skill-dot--explore" />
              <strong>Topics You Want to Explore ({student.explore_topics.length})</strong>
            </div>
            <div className="tag-chips-wrapper">
              {student.explore_topics.length ? (
                student.explore_topics.map((top) => (
                  <span key={top} className="tag-chip tag-chip--explore tag-chip--static">
                    {top}
                  </span>
                ))
              ) : (
                <span className="tag-chip--empty">No exploration topics added yet. Click &ldquo;Edit Profile&rdquo; to add.</span>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="profile-edit-body">
          <div className="profile-edit-grid-2">
            <div className="auth-field">
              <label htmlFor="edit-college">College / University Name</label>
              <input
                id="edit-college"
                type="text"
                value={editCollege}
                onChange={(e) => setEditCollege(e.target.value)}
                placeholder="e.g. Aarohan Demo University"
              />
            </div>
            <div className="auth-field">
              <label htmlFor="edit-branch">Branch / Department</label>
              <input
                id="edit-branch"
                type="text"
                value={editBranch}
                onChange={(e) => setEditBranch(e.target.value)}
                placeholder="e.g. Computer Science & Engineering"
              />
            </div>
          </div>

          {/* Known Subjects Editor */}
          <div className="auth-field">
            <label>
              <strong>Subjects You Know</strong>
              <span className="auth-label-sub">Add or remove core subjects and competencies</span>
            </label>
            <div className="tag-input-box">
              <input
                type="text"
                placeholder="Add subject (e.g. Algorithms, DBMS, Python)"
                value={subjectInput}
                onChange={(e) => setSubjectInput(e.target.value)}
                onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddSubject(subjectInput);
                  }
                }}
              />
              <button
                type="button"
                className="tag-add-btn"
                onClick={() => handleAddSubject(subjectInput)}
              >
                + Add
              </button>
            </div>
            <div className="tag-chips-wrapper">
              {knownSubjects.map((subject) => (
                <span key={subject} className="tag-chip tag-chip--known">
                  {subject}
                  <button
                    type="button"
                    className="tag-chip-remove"
                    onClick={() => handleRemoveSubject(subject)}
                    title={`Remove ${subject}`}
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
            <div className="tag-suggestions">
              <small>Suggestions: </small>
              {QUICK_KNOWN_SUGGESTIONS.filter((s) => !knownSubjects.includes(s)).slice(0, 6).map((s) => (
                <button
                  key={s}
                  type="button"
                  className="tag-pill-btn"
                  onClick={() => handleAddSubject(s)}
                >
                  + {s}
                </button>
              ))}
            </div>
          </div>

          {/* Explore Topics Editor */}
          <div className="auth-field">
            <label>
              <strong>Topics You Want to Explore</strong>
              <span className="auth-label-sub">Topics you want practice resources or guidance on</span>
            </label>
            <div className="tag-input-box">
              <input
                type="text"
                placeholder="Add topic (e.g. System Design, Cloud, ML)"
                value={exploreInput}
                onChange={(e) => setExploreInput(e.target.value)}
                onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddExplore(exploreInput);
                  }
                }}
              />
              <button
                type="button"
                className="tag-add-btn"
                onClick={() => handleAddExplore(exploreInput)}
              >
                + Add
              </button>
            </div>
            <div className="tag-chips-wrapper">
              {exploreTopics.map((topic) => (
                <span key={topic} className="tag-chip tag-chip--explore">
                  {topic}
                  <button
                    type="button"
                    className="tag-chip-remove"
                    onClick={() => handleRemoveExplore(topic)}
                    title={`Remove ${topic}`}
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
            <div className="tag-suggestions">
              <small>Suggestions: </small>
              {QUICK_EXPLORE_SUGGESTIONS.filter((t) => !exploreTopics.includes(t)).slice(0, 6).map((t) => (
                <button
                  key={t}
                  type="button"
                  className="tag-pill-btn"
                  onClick={() => handleAddExplore(t)}
                >
                  + {t}
                </button>
              ))}
            </div>
          </div>

          <div className="profile-edit-actions">
            <button
              type="button"
              className="profile-save-btn"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? "Saving Changes..." : "Save Changes"}
            </button>
            <button
              type="button"
              className="profile-cancel-btn"
              onClick={cancelEditing}
              disabled={saving}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

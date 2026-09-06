import { useState, useEffect, useId, type KeyboardEvent } from "react";
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

export function StudentProfileModal() {
  const {
    student,
    profileModalOpen,
    closeProfileModal,
    updateProfile,
    logout,
    openAuthModal,
  } = useAuth();

  const titleId = useId();

  // Editing state
  const [isEditingInfo, setIsEditingInfo] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Form states
  const [editCollege, setEditCollege] = useState("");
  const [editBranch, setEditBranch] = useState("");
  const [knownSubjects, setKnownSubjects] = useState<string[]>([]);
  const [subjectInput, setSubjectInput] = useState("");
  const [exploreTopics, setExploreTopics] = useState<string[]>([]);
  const [exploreInput, setExploreInput] = useState("");

  // Sync state whenever student data or modal opens
  useEffect(() => {
    if (student && profileModalOpen) {
      setEditCollege(student.college_name || "");
      setEditBranch(student.branch || "");
      setKnownSubjects(student.known_subjects || []);
      setExploreTopics(student.explore_topics || []);
      setIsEditingInfo(false);
      setErrorMessage(null);
      setSaveSuccess(false);
    }
  }, [student, profileModalOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && profileModalOpen) {
        closeProfileModal();
      }
    };
    window.addEventListener("keydown", handleKeyDown as unknown as EventListener);
    return () => window.removeEventListener("keydown", handleKeyDown as unknown as EventListener);
  }, [profileModalOpen, closeProfileModal]);

  if (!profileModalOpen) return null;

  const initials = student?.name
    ? student.name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()
    : "ST";

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
      setIsEditingInfo(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err) {
      setSaving(false);
      setErrorMessage(err instanceof Error ? err.message : String(err));
    }
  };

  const handleSignOut = () => {
    logout();
    closeProfileModal();
  };

  return (
    <div className="profile-modal-backdrop" onClick={closeProfileModal}>
      <div
        className="profile-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="profile-modal__header">
          <div className="profile-modal__user-badge">
            <span className="profile-modal__avatar" aria-hidden="true">
              {initials}
            </span>
            <div className="profile-modal__title-group">
              <div className="profile-modal__status-row">
                <span className="profile-modal__status-dot" />
                <span className="profile-modal__status-text">Active Student Profile</span>
              </div>
              <h2 id={titleId} className="profile-modal__title">
                {student ? student.name : "Guest Profile"}
              </h2>
              {student && (
                <p className="profile-modal__sub">
                  {student.college_name} · ID: {student.student_id}
                </p>
              )}
            </div>
          </div>

          <button
            type="button"
            className="profile-modal__close-btn"
            onClick={closeProfileModal}
            aria-label="Close profile window"
          >
            ✕
          </button>
        </div>

        {/* Alerts */}
        {saveSuccess && (
          <div className="profile-toast-success" role="status">
            ✓ Profile and subjects saved! Margdarshak AI now tailors guidance to these topics.
          </div>
        )}
        {errorMessage && (
          <div className="profile-toast-error" role="alert">
            {errorMessage}
          </div>
        )}

        {/* Body */}
        <div className="profile-modal__body">
          {!student ? (
            <div className="profile-modal__guest-view">
              <div className="profile-modal__guest-icon">🎓</div>
              <h3>Sign In to Customize Your Guidance</h3>
              <p>
                Sign in or register with your college, student ID, and known subjects so
                Margdarshak can personalize answers and recommend tailored resources.
              </p>
              <div className="profile-modal__guest-actions">
                <button
                  type="button"
                  className="profile-modal__btn profile-modal__btn--primary"
                  onClick={() => {
                    closeProfileModal();
                    openAuthModal("login");
                  }}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  className="profile-modal__btn profile-modal__btn--secondary"
                  onClick={() => {
                    closeProfileModal();
                    openAuthModal("signup");
                  }}
                >
                  Create Account
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Academic Details Card */}
              <div className="profile-modal__card">
                <div className="profile-modal__card-header">
                  <h4>Academic & Contact Details</h4>
                  <button
                    type="button"
                    className="profile-modal__link-btn"
                    onClick={() => setIsEditingInfo(!isEditingInfo)}
                  >
                    {isEditingInfo ? "Done Editing" : "Edit Info"}
                  </button>
                </div>

                {!isEditingInfo ? (
                  <div className="profile-modal__grid-2">
                    <div className="profile-info-item">
                      <span className="profile-info-item__label">College / University</span>
                      <strong className="profile-info-item__val">{student.college_name}</strong>
                    </div>
                    <div className="profile-info-item">
                      <span className="profile-info-item__label">Student ID</span>
                      <strong className="profile-info-item__val">{student.student_id}</strong>
                    </div>
                    <div className="profile-info-item">
                      <span className="profile-info-item__label">Branch / Department</span>
                      <strong className="profile-info-item__val">{student.branch}</strong>
                    </div>
                    <div className="profile-info-item">
                      <span className="profile-info-item__label">Email Address</span>
                      <strong className="profile-info-item__val">{student.email}</strong>
                    </div>
                  </div>
                ) : (
                  <div className="profile-modal__edit-fields">
                    <div className="auth-field">
                      <label htmlFor="modal-edit-college">College / University</label>
                      <input
                        id="modal-edit-college"
                        type="text"
                        value={editCollege}
                        onChange={(e) => setEditCollege(e.target.value)}
                        placeholder="e.g. Aarohan Demo University"
                      />
                    </div>
                    <div className="auth-field">
                      <label htmlFor="modal-edit-branch">Branch / Department</label>
                      <input
                        id="modal-edit-branch"
                        type="text"
                        value={editBranch}
                        onChange={(e) => setEditBranch(e.target.value)}
                        placeholder="e.g. Computer Science & Engineering"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Known Subjects Section */}
              <div className="profile-modal__card">
                <div className="profile-modal__card-header">
                  <div>
                    <h4>Subjects & Skills You Know ({knownSubjects.length})</h4>
                    <p className="profile-modal__card-sub">
                      Topics you are comfortable in. AI will build on these.
                    </p>
                  </div>
                </div>

                <div className="tag-input-box">
                  <input
                    type="text"
                    placeholder="Type subject (e.g. DSA, DBMS, Python) & press Enter"
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
                  {knownSubjects.length ? (
                    knownSubjects.map((sub) => (
                      <span key={sub} className="tag-chip tag-chip--known">
                        {sub}
                        <button
                          type="button"
                          className="tag-chip-remove"
                          onClick={() => handleRemoveSubject(sub)}
                          title={`Remove ${sub}`}
                        >
                          &times;
                        </button>
                      </span>
                    ))
                  ) : (
                    <span className="tag-chip--empty">No subjects added yet. Pick from suggestions below.</span>
                  )}
                </div>

                <div className="tag-suggestions">
                  <small>Quick suggestions: </small>
                  {QUICK_KNOWN_SUGGESTIONS.filter((s) => !knownSubjects.includes(s)).slice(0, 5).map((s) => (
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

              {/* Explore Topics Section */}
              <div className="profile-modal__card">
                <div className="profile-modal__card-header">
                  <div>
                    <h4>Topics You Want to Explore ({exploreTopics.length})</h4>
                    <p className="profile-modal__card-sub">
                      Subjects you want practice links or study roadmaps for.
                    </p>
                  </div>
                </div>

                <div className="tag-input-box">
                  <input
                    type="text"
                    placeholder="Type topic (e.g. System Design, Cloud) & press Enter"
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
                  {exploreTopics.length ? (
                    exploreTopics.map((top) => (
                      <span key={top} className="tag-chip tag-chip--explore">
                        {top}
                        <button
                          type="button"
                          className="tag-chip-remove"
                          onClick={() => handleRemoveExplore(top)}
                          title={`Remove ${top}`}
                        >
                          &times;
                        </button>
                      </span>
                    ))
                  ) : (
                    <span className="tag-chip--empty">No explore topics added yet. Pick from suggestions below.</span>
                  )}
                </div>

                <div className="tag-suggestions">
                  <small>Quick suggestions: </small>
                  {QUICK_EXPLORE_SUGGESTIONS.filter((t) => !exploreTopics.includes(t)).slice(0, 5).map((t) => (
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
            </>
          )}
        </div>

        {/* Footer */}
        {student && (
          <div className="profile-modal__footer">
            <button
              type="button"
              className="profile-modal__signout-btn"
              onClick={handleSignOut}
            >
              Sign Out
            </button>

            <div className="profile-modal__footer-right">
              <button
                type="button"
                className="profile-modal__btn profile-modal__btn--primary"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? "Saving Changes…" : "Save Profile & Subjects"}
              </button>
              <button
                type="button"
                className="profile-modal__btn profile-modal__btn--secondary"
                onClick={closeProfileModal}
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

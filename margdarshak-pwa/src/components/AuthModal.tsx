import { useState, type FormEvent, type KeyboardEvent } from "react";
import { useAuth } from "../context/AuthContext";

const COMMON_SUBJECT_SUGGESTIONS = [
  "Data Structures",
  "Algorithms",
  "DBMS",
  "Operating Systems",
  "Computer Networks",
  "Python",
  "Java",
  "SQL",
  "Object Oriented Programming",
];

const COMMON_EXPLORE_SUGGESTIONS = [
  "System Design",
  "Cloud Architecture",
  "Machine Learning",
  "DevOps / Docker",
  "Microservices",
  "Web Development",
  "Distributed Systems",
  "Cybersecurity",
];

export function AuthModal() {
  const { authModalOpen, authModalMode, closeAuthModal, openAuthModal, login, signup } = useAuth();

  const [tab, setTab] = useState<"login" | "signup">(authModalMode);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sign In fields
  const [loginIdentifier, setLoginIdentifier] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Sign Up fields
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [collegeName, setCollegeName] = useState("Aarohan Demo University");
  const [studentId, setStudentId] = useState("");
  const [branch, setBranch] = useState("Computer Science & Engineering");
  const [phone, setPhone] = useState("");

  // Tag inputs
  const [knownSubjects, setKnownSubjects] = useState<string[]>([
    "Data Structures",
    "Algorithms",
    "DBMS",
  ]);
  const [subjectInput, setSubjectInput] = useState("");

  const [exploreTopics, setExploreTopics] = useState<string[]>([
    "System Design",
    "Cloud Architecture",
  ]);
  const [exploreInput, setExploreInput] = useState("");

  if (!authModalOpen) return null;

  const handleAddSubject = (subject: string) => {
    const trimmed = subject.trim();
    if (trimmed && !knownSubjects.includes(trimmed)) {
      setKnownSubjects((prev) => [...prev, trimmed]);
    }
    setSubjectInput("");
  };

  const handleRemoveSubject = (subjectToRemove: string) => {
    setKnownSubjects((prev) => prev.filter((s) => s !== subjectToRemove));
  };

  const handleAddExplore = (topic: string) => {
    const trimmed = topic.trim();
    if (trimmed && !exploreTopics.includes(trimmed)) {
      setExploreTopics((prev) => [...prev, trimmed]);
    }
    setExploreInput("");
  };

  const handleRemoveExplore = (topicToRemove: string) => {
    setExploreTopics((prev) => prev.filter((t) => t !== topicToRemove));
  };

  const handleLoginSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!loginIdentifier.trim() || !loginPassword.trim()) {
      setError("Please enter your email or student ID, and your password.");
      return;
    }
    setLoading(true);
    try {
      await login({ email: loginIdentifier.trim(), password: loginPassword });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSignupSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!name.trim()) return setError("Please enter your full name.");
    if (!email.trim()) return setError("Please enter your email address.");
    if (password.length < 6) return setError("Password must be at least 6 characters.");
    if (!collegeName.trim()) return setError("Please enter your college or university name.");
    if (!studentId.trim()) return setError("Please enter your Student ID or Roll Number.");

    setLoading(true);
    try {
      await signup({
        name: name.trim(),
        email: email.trim(),
        password,
        college_name: collegeName.trim(),
        student_id: studentId.trim(),
        branch: branch.trim() || "Computer Science",
        phone: phone.trim(),
        known_subjects: knownSubjects,
        explore_topics: exploreTopics,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleFillDemoStudent = (emailToFill: string, pass: string) => {
    setLoginIdentifier(emailToFill);
    setLoginPassword(pass);
  };

  return (
    <div className="auth-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title">
      <div className="auth-modal-card">
        <button
          type="button"
          className="auth-modal-close"
          onClick={closeAuthModal}
          aria-label="Close authentication modal"
        >
          &times;
        </button>

        <div className="auth-modal-header">
          <div className="auth-modal-badge">M</div>
          <h2 id="auth-modal-title">Welcome to Margdarshak</h2>
          <p>Sign in to sync your university profile, test links, and voice guidance.</p>
        </div>

        <div className="auth-modal-tabs">
          <button
            type="button"
            className={`auth-tab-btn ${tab === "login" ? "auth-tab-btn--active" : ""}`}
            onClick={() => { setTab("login"); setError(null); }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`auth-tab-btn ${tab === "signup" ? "auth-tab-btn--active" : ""}`}
            onClick={() => { setTab("signup"); setError(null); }}
          >
            Create Account
          </button>
        </div>

        {error && (
          <div className="auth-modal-alert" role="alert">
            <span className="auth-alert-icon">!</span>
            <span>{error}</span>
          </div>
        )}

        {tab === "login" ? (
          <form className="auth-form" onSubmit={handleLoginSubmit}>
            <div className="auth-field">
              <label htmlFor="login-email">Email Address or Student ID</label>
              <input
                id="login-email"
                type="text"
                placeholder="e.g. mira.test@example.invalid or 230644"
                value={loginIdentifier}
                onChange={(e) => setLoginIdentifier(e.target.value)}
                autoComplete="username"
                required
              />
            </div>

            <div className="auth-field">
              <label htmlFor="login-password">Password</label>
              <input
                id="login-password"
                type="password"
                placeholder="Enter your password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>

            <button type="submit" className="auth-submit-btn" disabled={loading}>
              {loading ? "Signing in..." : "Sign In to Margdarshak"}
            </button>

            <div className="auth-demo-hint">
              <p>Quick Test Account:</p>
              <button
                type="button"
                className="auth-demo-btn"
                onClick={() => handleFillDemoStudent("mira.test@example.invalid", "Password@123")}
              >
                Use Seeded Student (Mira Test · ID: 230644)
              </button>
            </div>
          </form>
        ) : (
          <form className="auth-form" onSubmit={handleSignupSubmit}>
            <div className="auth-grid-2">
              <div className="auth-field">
                <label htmlFor="signup-name">Full Name *</label>
                <input
                  id="signup-name"
                  type="text"
                  placeholder="e.g. Aryan Mehta"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>

              <div className="auth-field">
                <label htmlFor="signup-id">Student ID / Roll No *</label>
                <input
                  id="signup-id"
                  type="text"
                  placeholder="e.g. 2026-CS-042"
                  value={studentId}
                  onChange={(e) => setStudentId(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="auth-grid-2">
              <div className="auth-field">
                <label htmlFor="signup-email">Email Address *</label>
                <input
                  id="signup-email"
                  type="email"
                  placeholder="e.g. aryan@university.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="auth-field">
                <label htmlFor="signup-password">Password (min 6 characters) *</label>
                <input
                  id="signup-password"
                  type="password"
                  placeholder="Create a strong password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                />
              </div>
            </div>

            <div className="auth-grid-2">
              <div className="auth-field">
                <label htmlFor="signup-college">College / University Name *</label>
                <input
                  id="signup-college"
                  type="text"
                  placeholder="e.g. Aarohan Demo University, IIT Delhi"
                  value={collegeName}
                  onChange={(e) => setCollegeName(e.target.value)}
                  required
                />
              </div>

              <div className="auth-field">
                <label htmlFor="signup-branch">Branch / Major</label>
                <input
                  id="signup-branch"
                  type="text"
                  placeholder="e.g. Computer Science & Engineering"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                />
              </div>
            </div>

            {/* Known Subjects Section */}
            <div className="auth-field">
              <label>
                <strong>Subjects & Skills You Know</strong>
                <span className="auth-label-sub">
                  (Topics you have already studied or feel comfortable discussing)
                </span>
              </label>
              <div className="tag-input-box">
                <input
                  type="text"
                  placeholder="Type a subject (e.g. DBMS, Python) and press Enter"
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
                {COMMON_SUBJECT_SUGGESTIONS.filter((s) => !knownSubjects.includes(s)).slice(0, 5).map((s) => (
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
            <div className="auth-field">
              <label>
                <strong>Things You Would Like to Explore</strong>
                <span className="auth-label-sub">
                  (New skills, advanced topics, or domains you want learning resources for)
                </span>
              </label>
              <div className="tag-input-box">
                <input
                  type="text"
                  placeholder="Type a topic (e.g. System Design, ML) and press Enter"
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
                {COMMON_EXPLORE_SUGGESTIONS.filter((t) => !exploreTopics.includes(t)).slice(0, 5).map((t) => (
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

            <button type="submit" className="auth-submit-btn" disabled={loading}>
              {loading ? "Creating Profile..." : "Create Account & Get Started"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

import { PlacementCard } from "../components/PlacementCard";
import { demoStudent, placementUpdate, studentPlacements } from "../data/studentData";

type HomeProps = { onStartCall: () => void; onFindMatch: () => void; onOpenPlacement: (id: string) => void };

function VoiceIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 15.5a3.5 3.5 0 0 0 3.5-3.5V6a3.5 3.5 0 1 0-7 0v6a3.5 3.5 0 0 0 3.5 3.5Zm-5.75-4a.75.75 0 0 1 .75.75 5 5 0 0 0 10 0 .75.75 0 0 1 1.5 0 6.5 6.5 0 0 1-5.75 6.45V21h2.5a.75.75 0 0 1 0 1.5h-6.5a.75.75 0 0 1 0-1.5h2.5v-2.3a6.5 6.5 0 0 1-5.75-6.45.75.75 0 0 1 .75-.75Z" /></svg>;
}

function ChatIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5.5 4A3.5 3.5 0 0 0 2 7.5v7A3.5 3.5 0 0 0 5.5 18H7v2.35a.75.75 0 0 0 1.2.6L12.13 18h6.37a3.5 3.5 0 0 0 3.5-3.5v-7A3.5 3.5 0 0 0 18.5 4h-13Zm1.75 6.25a1 1 0 1 1 0 2 1 1 0 0 1 0-2Zm4.75 0a1 1 0 1 1 0 2 1 1 0 0 1 0-2Zm4.75 0a1 1 0 1 1 0 2 1 1 0 0 1 0-2Z" /></svg>;
}

export function Home({ onStartCall, onFindMatch, onOpenPlacement }: HomeProps) {
  return (
    <main className="home-screen">
      <nav className="home-nav" aria-label="Main navigation">
        <a className="home-brand" href="/" aria-label="Margdarshak home"><span className="home-brand__mark" aria-hidden="true">M</span><span>Margdarshak</span></a>
        <div className="student-menu" aria-label="Signed-in student"><span className="student-menu__avatar" aria-hidden="true">AS</span><span><strong>{demoStudent.name}</strong><small>{demoStudent.university}</small></span></div>
      </nav>

      <section className="home-hero" aria-labelledby="home-title">
        <div className="home-hero__intro">
          <p className="home-eyebrow"><span aria-hidden="true" /> Your student guidance companion</p>
          <h1 id="home-title">Campus questions can feel complicated. <em>Let’s make them clearer.</em></h1>
          <p className="home-hero__lead">Talk through placements, university processes, or anything that is worrying you. Get practical next steps shaped around your student profile.</p>
          <div className="home-prompts" aria-label="Things you can ask about"><span>Eligibility</span><span>Placement guidance</span><span>Campus support</span></div>
        </div>
        <div className="home-paths" aria-label="Choose how to get support">
          <article className="home-path home-path--primary">
            <div className="home-path__icon"><VoiceIcon /></div><p className="home-path__label">AI guidance</p><h2>Talk to Margdarshak</h2>
            <p>Have a private voice conversation. Your guide remembers the details you share and builds a live summary.</p>
            <button className="home-path__button home-path__button--primary" type="button" onClick={onStartCall}>Start a voice conversation <span aria-hidden="true">→</span></button>
            <p className="home-path__meta">Available now · Usually 5–10 minutes</p>
          </article>
          <article className="home-path">
            <div className="home-path__icon home-path__icon--chat"><ChatIcon /></div><p className="home-path__label">Peer support</p><h2>Chat anonymously</h2>
            <p>Connect with another student without sharing your identity. You stay in control throughout the conversation.</p>
            <button className="home-path__button" type="button" onClick={onFindMatch}>Open anonymous chat <span aria-hidden="true">→</span></button>
            <p className="home-path__meta">48-hour private bridge · You stay in control</p>
          </article>
        </div>
      </section>

      <section className="student-update" aria-labelledby="placement-update-title">
        <div className="student-update__icon" aria-hidden="true">!</div><div><p className="section-kicker">Placement update</p><h2 id="placement-update-title">{placementUpdate.title}</h2><p>{placementUpdate.body}</p><small>{placementUpdate.affectedStudents} students reported this · Updated {placementUpdate.timestamp}</small></div>
      </section>

      <section className="placements-section" aria-labelledby="placements-title">
        <div className="section-heading"><div><p className="section-kicker">Your placement journey</p><h2 id="placements-title">Current opportunities</h2></div><p>Only drives connected to your student profile are shown.</p></div>
        <div className="placement-grid">{studentPlacements.map((placement) => <PlacementCard key={placement.id} placement={placement} onOpen={onOpenPlacement} />)}</div>
      </section>

      <footer className="home-footer"><p><span aria-hidden="true">●</span> A confidential space for Aarohan students</p><p>If something is urgent, Margdarshak can route it to the support desk.</p></footer>
    </main>
  );
}

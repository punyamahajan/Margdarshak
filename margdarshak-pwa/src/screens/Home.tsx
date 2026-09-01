import { FloatingCallButton } from "../components/FloatingCallButton";

type HomeProps = {
  onStartCall: () => void;
  onFindMatch: () => void;
};

export function Home({ onStartCall, onFindMatch }: HomeProps) {
  return (
    <main className="home-screen">
      <header className="home-screen__header">
        <p className="wordmark">Margdarshak</p>
        <p className="home-screen__note">Your campus guide, when you need one.</p>
      </header>

      <div className="home-screen__action">
        <FloatingCallButton onPress={onStartCall} />
        <p>Speak naturally. We’ll help find the next useful step.</p>
        <button className="quiet-action" type="button" onClick={onFindMatch}>
          Find a 48-hour anonymous match
        </button>
      </div>

      <p className="home-screen__privacy">Private by default · You stay in control</p>
    </main>
  );
}

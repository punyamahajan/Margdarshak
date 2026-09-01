type FloatingCallButtonProps = {
  onPress: () => void;
};

export function FloatingCallButton({ onPress }: FloatingCallButtonProps) {
  return (
    <button className="floating-call-button" type="button" onClick={onPress}>
      <span className="floating-call-button__mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" focusable="false">
          <path d="M8.2 3.8c.5-.1 1 .2 1.2.7l1.1 3.1c.2.5 0 1-.4 1.3l-1.5 1.2a13.8 13.8 0 0 0 5.3 5.3l1.2-1.5c.3-.4.8-.6 1.3-.4l3.1 1.1c.5.2.8.7.7 1.2l-.5 3.1c-.1.5-.5.9-1 .9C10.7 19.8 4.2 13.3 4.2 5.3c0-.5.4-.9.9-1l3.1-.5Z" />
        </svg>
      </span>
      <span>Talk to Margdarshak</span>
    </button>
  );
}

type WaveformProps = {
  active?: boolean;
  localLevel?: number;
  remoteLevel?: number;
};

export function Waveform({
  active = false,
  localLevel = 0,
  remoteLevel = 0
}: WaveformProps) {
  const bars = [18, 30, 44, 26, 52, 36, 22];
  const measuredLevel = Math.min(1, Math.max(localLevel, remoteLevel));

  return (
    <div
      className="waveform"
      data-active={active || measuredLevel > 0.02}
      aria-label="Live voice activity"
    >
      {bars.map((height, index) => (
        <span
          key={`${height}-${index}`}
          style={
            {
              "--bar-height": `${Math.max(8, height * (0.35 + measuredLevel * 1.3))}px`,
              "--bar-opacity": `${0.35 + measuredLevel * 0.65}`
            } as React.CSSProperties
          }
        />
      ))}
    </div>
  );
}

export const themeTokens = {
  color: {
    paper: "#FAF7F0",
    paperRaised: "#FFFDF8",
    sage: "#87977B",
    sageDark: "#66745E",
    sageSoft: "#DDE4D7",
    charcoal: "#2E2E2C",
    inkMuted: "#6F6D67",
    line: "#DED9CE",
    white: "#FFFFFF"
  },
  space: {
    1: "0.25rem",
    2: "0.5rem",
    3: "0.75rem",
    4: "1rem",
    5: "1.5rem",
    6: "2rem",
    7: "3rem",
    8: "4.5rem"
  },
  radius: {
    small: "0.75rem",
    medium: "1.25rem",
    large: "2rem",
    pill: "999px"
  },
  type: {
    body: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    display: 'Iowan Old Style, Baskerville, "Times New Roman", serif'
  },
  shadow: {
    soft: "0 1rem 2.5rem rgba(46, 46, 44, 0.10)",
    pressed: "0 0.35rem 1rem rgba(46, 46, 44, 0.12)"
  }
} as const;

export const themeCssVariables: Record<string, string> = {
  "--color-paper": themeTokens.color.paper,
  "--color-paper-raised": themeTokens.color.paperRaised,
  "--color-sage": themeTokens.color.sage,
  "--color-sage-dark": themeTokens.color.sageDark,
  "--color-sage-soft": themeTokens.color.sageSoft,
  "--color-charcoal": themeTokens.color.charcoal,
  "--color-ink-muted": themeTokens.color.inkMuted,
  "--color-line": themeTokens.color.line,
  "--color-white": themeTokens.color.white,
  "--space-1": themeTokens.space[1],
  "--space-2": themeTokens.space[2],
  "--space-3": themeTokens.space[3],
  "--space-4": themeTokens.space[4],
  "--space-5": themeTokens.space[5],
  "--space-6": themeTokens.space[6],
  "--space-7": themeTokens.space[7],
  "--space-8": themeTokens.space[8],
  "--radius-small": themeTokens.radius.small,
  "--radius-medium": themeTokens.radius.medium,
  "--radius-large": themeTokens.radius.large,
  "--radius-pill": themeTokens.radius.pill,
  "--font-body": themeTokens.type.body,
  "--font-display": themeTokens.type.display,
  "--shadow-soft": themeTokens.shadow.soft,
  "--shadow-pressed": themeTokens.shadow.pressed
};

export function applyThemeTokens(root: HTMLElement = document.documentElement): void {
  Object.entries(themeCssVariables).forEach(([name, value]) => {
    root.style.setProperty(name, value);
  });
}

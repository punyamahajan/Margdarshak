import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["margdarshak-mark.svg"],
      workbox: {
        // Voice calls require a network connection; don't make the large Agora
        // chunk part of the offline app-shell download.
        globIgnores: ["**/CallScreen-*.js"]
      },
      manifest: {
        name: "Margdarshak",
        short_name: "Margdarshak",
        description: "A calm, voice-first guide for students.",
        theme_color: "#FAF7F0",
        background_color: "#FAF7F0",
        display: "standalone",
        orientation: "portrait",
        icons: [
          {
            src: "margdarshak-mark.svg",
            sizes: "any",
            type: "image/svg+xml",
            purpose: "any maskable"
          }
        ]
      }
    })
  ]
});

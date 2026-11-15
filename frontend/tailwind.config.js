/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#090909",
        surface1: "#171411",
        surface2: "#201A16",
        surface3: "#2A221C",
        "mars-orange": "#F06B3D",
        amber: "#D9A06A",
        cyan: "#55C7D9",
        "safe-green": "#65B88A",
        "warning-amber": "#EAB45B",
        "critical-red": "#E45C5C",
        "text-primary": "#F3F0EC",
        "text-secondary": "#B1A39A",
        "text-muted": "#786C65",
        line: "#624536",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        heading: ["Space Grotesk", "Inter", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "JetBrains Mono", "monospace"],
      },
      borderRadius: {
        panel: "12px",
        control: "8px",
      },
      boxShadow: {
        panel: "0 4px 16px rgba(0,0,0,0.35)",
      },
    },
  },
  plugins: [],
};
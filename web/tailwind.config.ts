import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // McKinsey-inspired editorial palette
        page: "#fafaf7",      // warm off-white background
        ink: {
          DEFAULT: "#0b1f3a", // deep navy (not pure black)
          soft: "#1a2d4a",
          mid: "#525866",
          faint: "#8b91a0",
        },
        line: {
          DEFAULT: "#e6e4dd", // warm border
          soft: "#efece5",
        },
        accent: {
          DEFAULT: "#2251ff", // electric blue (action)
          soft: "#dde6ff",
          deep: "#1a3fbf",
        },
        signal: {
          gain: "#0e7a3e",
          loss: "#a6291f",
          flag: "#a36410",
          flagSoft: "#fcf4dc",
        },
      },
      fontFamily: {
        serif: [
          "var(--font-serif)",
          "Source Serif Pro",
          "Georgia",
          "Cambria",
          "Times New Roman",
          "serif",
        ],
        sans: [
          "var(--font-sans)",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      letterSpacing: {
        tightest: "-0.04em",
      },
      maxWidth: {
        prose: "70ch",
        article: "76ch",
      },
      typography: {
        DEFAULT: {
          css: {
            "--tw-prose-body": "#1a2d4a",
            "--tw-prose-headings": "#0b1f3a",
            "--tw-prose-links": "#2251ff",
            "--tw-prose-bold": "#0b1f3a",
            "--tw-prose-quotes": "#0b1f3a",
            "--tw-prose-bullets": "#8b91a0",
            "--tw-prose-counters": "#8b91a0",
            maxWidth: "70ch",
          },
        },
      },
    },
  },
  plugins: [],
};

export default config;

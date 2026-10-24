/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "#F5F3ED",
        ink: "#171717",
        lime: {
          DEFAULT: "#C6FF4D",
          hover: "#B4F234",
          light: "#E4FF9E",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          muted: "#ECE9E0",
          card: "#FAF9F5",
          dark: "#171717",
        },
        danger: {
          DEFAULT: "#FF5A52",
          light: "#FFEAE8",
        },
        warning: {
          DEFAULT: "#FFB020",
          light: "#FFF6E5",
        },
        success: {
          DEFAULT: "#00BA66",
          light: "#E6F8F0",
        },
        info: {
          DEFAULT: "#3874FF",
          light: "#EBF1FF",
        }
      },
      fontFamily: {
        display: ["Space Grotesk", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        brutal: "4px 4px 0 #171717",
        "brutal-sm": "2px 2px 0 #171717",
        "brutal-lg": "6px 6px 0 #171717",
        "brutal-lime": "4px 4px 0 #C6FF4D",
      },
      borderWidth: {
        brutal: "2.5px",
        3: "3px",
      }
    },
  },
  plugins: [],
}

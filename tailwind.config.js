/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          dark: '#00325A',
          light: '#0072BC',
        },
        secondary: {
          light: '#F2F2F2',
          medium: '#6E6E6E',
        },
        accent: '#E30613',
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
}
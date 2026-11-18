# UI Fix Notes

### 1. Diagnosis of Broken Layout
**Issue:** Tailwind CSS utility classes (like `flex`, `grid`, `w-full`, etc.) were not being applied to any of the components, causing everything to stack vertically. Fonts and some colors (defined in CSS variables directly in `:root` and manually assigned) were working.

**Root Cause:**
1. The `package.json` specifies `"dev": "next dev --webpack"`, forcing the application to build with Webpack instead of Turbopack.
2. The `next.config.ts` was exclusively configured to use `@tailwindcss/turbopack`. Because Webpack was running, this configuration was ignored entirely. 
3. There was no `postcss.config.mjs` file in the project. Since Webpack relies on PostCSS to process Tailwind CSS v4 directives (via `@import "tailwindcss"`), the CSS parser completely skipped generating utility classes from the source files.

### 2. The Fix
1. Installed `@tailwindcss/postcss` and `postcss` via npm to enable standard PostCSS support for Webpack.
2. Created `postcss.config.mjs` in the project root containing the `@tailwindcss/postcss` plugin.
3. Restarted the development server so Webpack registers the new PostCSS pipeline. This immediately generated the correct utility classes, restoring the flex/grid layouts and components on the page.

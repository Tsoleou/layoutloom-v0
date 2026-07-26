import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API base is read at runtime from VITE_API_BASE (see src/api.ts),
// defaulting to the uvicorn dev server on :8012.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});

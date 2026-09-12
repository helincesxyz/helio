/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Without this, Vite's dev server only binds the IPv6 loopback (::1),
  // so "localhost:5173" works but "127.0.0.1:5173" gets connection
  // refused — depending on the browser/OS's address-resolution order,
  // that can make the whole app look broken for no obvious reason.
  server: {
    host: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
  },
});

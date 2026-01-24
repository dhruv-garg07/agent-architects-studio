import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    // Proxy Flask backend requests
    proxy: {
      '/login': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/register': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/logout': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/auth/callback': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/auth/github': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/dashboard': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/profile': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/explore': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/agent': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/submit': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/harshit': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/ranaji': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/dhruv': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
  plugins: [
    react(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));

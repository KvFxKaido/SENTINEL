import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

export default defineConfig({
  // React islands for interactive components (world map)
  integrations: [react()],
  // Development server
  server: {
    port: 4321,
    host: true,
  },
  // Output static site by default
  output: 'static',
  // Build options
  build: {
    inlineStylesheets: 'auto',
  },
  // Vite config for dev experience
  vite: {
    server: {
      // Proxy API requests to the Deno bridge during development
      proxy: {
        '/api': {
          target: 'http://localhost:3333',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  },
});

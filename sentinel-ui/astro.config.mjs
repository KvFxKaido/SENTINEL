import { defineConfig } from 'astro/config';

export default defineConfig({
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

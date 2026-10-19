import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// Output goes into the Python package; the server serves it from there.
export default defineConfig({
  plugins: [svelte()],
  base: './',
  build: {
    outDir: '../src/threatwright/web',
    emptyOutDir: true,
    assetsInlineLimit: 0,
  },
})

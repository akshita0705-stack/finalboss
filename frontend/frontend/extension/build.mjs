import { build } from 'esbuild'
import { cpSync, mkdirSync, rmSync } from 'node:fs'

rmSync('dist', { recursive: true, force: true })
mkdirSync('dist', { recursive: true })

// Every script is bundled as a self-contained IIFE: content scripts cannot use ES module imports.
await build({
  entryPoints: {
    background: 'src/background/index.ts',
    content: 'src/content/banner.ts',
    popup: 'src/popup/popup.ts',
    options: 'src/options/options.ts',
  },
  outdir: 'dist',
  bundle: true,
  format: 'iife',
  target: 'chrome110',
  minify: true,
  logLevel: 'info',
})

cpSync('public', 'dist', { recursive: true })
cpSync('src/popup/popup.html', 'dist/popup.html')
cpSync('src/options/options.html', 'dist/options.html')
cpSync('src/shared/ui.css', 'dist/ui.css')
console.log('Extension built -> dist/')

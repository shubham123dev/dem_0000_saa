import { readdir, readFile } from 'node:fs/promises';
import { relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = new URL('../src/app/', import.meta.url);
const rootPath = fileURLToPath(root);
const allowedHttpFiles = new Set(['core/api/validated-http.service.ts', 'core/agent-run/agent-run-stream.service.ts']);
const violations = [];

async function walk(url) {
  for (const entry of await readdir(url, { withFileTypes: true })) {
    const child = new URL(`${entry.name}${entry.isDirectory() ? '/' : ''}`, url);
    if (entry.isDirectory()) {
      await walk(child);
      continue;
    }
    if (!entry.name.endsWith('.ts') || entry.name.endsWith('.spec.ts')) continue;
    const path = relative(rootPath, fileURLToPath(child)).replaceAll('\\', '/');
    const text = await readFile(child, 'utf8');
    if ((/\bHttpClient\b/.test(text) || /\bfetch\s*\(/.test(text)) && !allowedHttpFiles.has(path) && !path.startsWith('core/config/')) {
      violations.push(`${path}: raw HTTP boundary`);
    }
    if (/(:\s*any\b|<any>)/.test(text)) violations.push(`${path}: explicit any`);
  }
}

await walk(root);
if (violations.length) {
  console.error(violations.join('\n'));
  process.exit(1);
}
console.log('Angular architecture boundaries are valid.');

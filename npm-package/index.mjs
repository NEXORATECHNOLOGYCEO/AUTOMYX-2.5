#!/usr/bin/env node

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Pass all arguments to the Python script
const args = process.argv.slice(2);

// Find the Python automyx script (ollama_launch.py is always in the parent dir of npm-package)
const projectRoot = join(__dirname, '..');
const ollamaLaunchPy = join(projectRoot, 'ollama_launch.py');
const automyxPy = join(projectRoot, 'automix.py');

let scriptToRun = null;

if (existsSync(ollamaLaunchPy)) {
  scriptToRun = ollamaLaunchPy;
} else if (existsSync(automyxPy)) {
  scriptToRun = automyxPy;
} else {
  console.error('❌ Automyx scripts not found!');
  process.exit(1);
}

console.log('🚀 Launching Automyx...');

// Run the Python script with all provided arguments, from the project root
const pythonProcess = spawn('python', [scriptToRun, ...args], {
  stdio: 'inherit',
  cwd: projectRoot
});

pythonProcess.on('error', (err) => {
  console.error('❌ Failed to start Automyx:', err);
  process.exit(1);
});

pythonProcess.on('exit', (code) => {
  if (code !== 0) {
    console.error(`❌ Automyx exited with code ${code}`);
  }
  process.exit(code);
});

#!/usr/bin/env node
/**
 * Batch spawner for benchmark agents.
 * Reads wave JSON files and spawns via OpenClaw API.
 * Usage: node spawner.js <wave_dir> [concurrency]
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const waveDir = process.argv[2] || '/data/workspace/lap-benchmark-docs/results/wave1';
const concurrency = parseInt(process.argv[3] || '10');

const files = fs.readdirSync(waveDir).filter(f => f.endsWith('.json'));
console.log(`Found ${files.length} runs in ${waveDir}`);

const results = {};
const resultFile = path.join(waveDir, '_sessions.json');

// Load existing results if any
if (fs.existsSync(resultFile)) {
  Object.assign(results, JSON.parse(fs.readFileSync(resultFile, 'utf8')));
  console.log(`Loaded ${Object.keys(results).length} existing results`);
}

async function spawnAgent(label, prompt) {
  // Use openclaw CLI to spawn
  const tmpFile = `/tmp/bench_prompt_${label}.txt`;
  fs.writeFileSync(tmpFile, prompt);
  
  try {
    const out = execSync(
      `openclaw session spawn --label "${label}" --model "anthropic/claude-sonnet-4-5-20250514" --timeout 180 --file "${tmpFile}"`,
      { encoding: 'utf8', timeout: 30000 }
    );
    return out.trim();
  } catch (e) {
    return `ERROR: ${e.message}`;
  } finally {
    try { fs.unlinkSync(tmpFile); } catch {}
  }
}

async function main() {
  const pending = files.filter(f => {
    const label = f.replace('.json', '');
    return !results[label];
  });
  
  console.log(`Pending: ${pending.length} (${files.length - pending.length} already done)`);
  
  for (let i = 0; i < pending.length; i += concurrency) {
    const batch = pending.slice(i, i + concurrency);
    console.log(`\nBatch ${Math.floor(i/concurrency) + 1}: spawning ${batch.length} agents...`);
    
    const promises = batch.map(async (f) => {
      const data = JSON.parse(fs.readFileSync(path.join(waveDir, f), 'utf8'));
      const result = await spawnAgent(data.label, data.prompt);
      results[data.label] = result;
      console.log(`  ✓ ${data.label}`);
    });
    
    await Promise.all(promises);
    
    // Save intermediate results
    fs.writeFileSync(resultFile, JSON.stringify(results, null, 2));
  }
  
  console.log(`\nDone! ${Object.keys(results).length} sessions spawned`);
}

main().catch(console.error);

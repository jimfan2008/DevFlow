const fs = require('fs');
const content = fs.readFileSync('deploy-wsl.sh', 'utf-8');

function countMatches(pattern) {
  return (content.match(pattern) || []).length;
}

const pairs = {
  'if / fi':      { open: countMatches(/\bif\b/g), close: countMatches(/\bfi\b/g) },
  'case / esac':  { open: countMatches(/\bcase\b/g), close: countMatches(/\besac\b/g) },
  'for / done':   { open: countMatches(/\bfor\b/g), close: countMatches(/\bdone\b/g) },
  'while / done': { open: countMatches(/\bwhile\b/g), close: countMatches(/\bdone\b/g) },
  'do / done':    { open: countMatches(/\bdo\b/g), close: countMatches(/\bdone\b/g) },
  'then / fi':    { open: countMatches(/\bthen\b/g), close: countMatches(/\bfi\b/g) },
};

console.log('=== Bash Keyword Pairing Check ===');
let allOk = true;
for (const [name, counts] of Object.entries(pairs)) {
  const status = counts.open === counts.close ? 'PASS' : 'FAIL';
  if (status === 'FAIL') allOk = false;
  console.log(status + ': ' + name.padEnd(16) + ' open=' + counts.open + ' close=' + counts.close);
}

// function definitions
const funcDefs = (content.match(/^\s*[\w_]+\s*\(\)\s*\{/gm) || []).length;
console.log('INFO: function definitions=' + funcDefs);

// case branches
const caseBranches = (content.match(/^\s+[\w\|\*\"\']+\)/gm) || []).length;
console.log('INFO: case branches=' + caseBranches);

// heredocs
const heredocs = (content.match(/<<\s*['"]?\w+['"]?/g) || []).length;
console.log('INFO: heredocs=' + heredocs);

console.log('');
if (allOk) {
  console.log('PASS: All bash keywords properly paired');
} else {
  console.log('FAIL: Unpaired keywords detected');
}
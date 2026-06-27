/**
 * PreToolUse Hook: 分支保护
 *
 * 拦截 Edit/Write 工具在 main 分支上对代码文件的执行，强制使用隔离工作区。
 * 配置/文档/规则文件放行。
 */

const fs = require('fs');
const { execSync } = require('child_process');

// 允许在 main 上直接编辑的文件（不受分支保护限制）
const ALLOWED_PATTERNS = [
  /AGENTS\.md$/i,
  /CLAUDE\.md$/i,
  /MEMORY\.md$/i,
  /\.claude[/\\]/,
  /\.githooks[/\\]/,
  /\.agents[/\\]/,
  /\.gitignore$/i,
  /\.env\.example$/i,
  /\.env\.docker$/i,
  /docs[/\\]/,
  /README\.md$/i,
  /VERSION$/i,
  /pyproject\.toml$/i,
  /Dockerfile/i,
  /docker-compose/i,
  /\.dockerignore$/i,
];

function normalizePath(p) {
  // 统一分隔符 + 小写（Windows 驱动器号大小写不一致）
  return p.replace(/\\/g, '/').toLowerCase();
}

function getCurrentBranch() {
  try {
    return execSync('git branch --show-current 2>nul', {
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: 5000,
    }).trim();
  } catch {
    return null;
  }
}

function isInWorktree() {
  try {
    const gitDir = execSync('git rev-parse --git-dir 2>nul', {
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: 5000,
    }).trim();
    const commonDir = execSync('git rev-parse --git-common-dir 2>nul', {
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: 5000,
    }).trim();
    return gitDir !== commonDir;
  } catch {
    return false;
  }
}

function isAllowedFile(filePath) {
  if (!filePath) return false;
  return ALLOWED_PATTERNS.some(p => p.test(filePath));
}

// 判断是否为代码文件（main 分支上不允许直接编辑）
function isCodeFile(filePath) {
  if (!filePath) return false;
  const normalized = normalizePath(filePath);

  // Python 代码：指定目录下的 .py
  const codeDirs = ['app/', 'tradingagents/', 'cli/', 'web/', 'scripts/', 'tests/', 'utils/'];
  if (normalized.endsWith('.py')) {
    return codeDirs.some(d => normalized.includes('/' + d) || normalized.startsWith(d));
  }

  // 前端代码：frontend/src/ 下的 .vue/.ts/.js/.tsx/.jsx
  if (normalized.includes('/frontend/src/') || normalized.startsWith('frontend/src/')) {
    return /\.(vue|ts|js|tsx|jsx)$/i.test(normalized);
  }

  return false;
}

// --- 主逻辑 ---

let inputRaw = '';
try {
  const buf = Buffer.alloc(65536);
  const bytes = fs.readSync(0, buf, 0, 65536, null);
  inputRaw = buf.toString('utf-8', 0, bytes);
} catch {
  process.exit(0);
}

if (!inputRaw.trim()) {
  process.exit(0);
}

let input;
try {
  input = JSON.parse(inputRaw);
} catch {
  process.exit(0);
}

const toolName = input.tool_name;
const toolInput = input.tool_input || {};

// 只拦截 Edit 和 Write
if (toolName !== 'Edit' && toolName !== 'Write') {
  process.exit(0);
}

const filePath = normalizePath(toolInput.file_path || '');
const cwd = normalizePath(process.cwd());

// 允许列表中的文件放行（配置/文档/规则类）
if (isAllowedFile(toolInput.file_path || '')) {
  process.exit(0);
}

// 不在项目目录内的文件放行
if (!filePath.startsWith(cwd)) {
  process.exit(0);
}

// 非代码文件放行（如 markdown、json 配置等未在 isCodeFile 命中的）
if (!isCodeFile(toolInput.file_path || '')) {
  process.exit(0);
}

const branch = getCurrentBranch();
if (!branch) {
  process.exit(0);
}

// 在 worktree 中放行
if (isInWorktree()) {
  process.exit(0);
}

// 在 main/master 分支上编辑代码文件 → 拦截
if (branch === 'main' || branch === 'master') {
  const message = [
    '🚫 分支保护：禁止在 main 分支直接编辑代码文件',
    '',
    '文件：' + toolInput.file_path,
    '分支：' + branch,
    '',
    '请使用隔离工作区开发：',
    '  1. git worktree add .worktrees/<task-name> -b feat/<task-name> main',
    '  2. cd .worktrees/<task-name>',
    '  3. 在分支内完成开发',
    '  4. 合并回 main 并推送，然后删除 worktree',
    '',
    '（配置/文档/规则文件可在 main 上直接编辑，代码文件不行）',
  ].join('\n');

  console.log(JSON.stringify({ decision: 'block', reason: message }));
  process.exit(0);
}

// 功能分支放行
process.exit(0);

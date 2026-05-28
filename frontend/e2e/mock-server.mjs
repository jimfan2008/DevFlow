/**
 * DevFlow Mock Server
 * - 提供前端静态文件 (dist/)
 * - 模拟所有 API 响应
 * - 支持 SPA 路由回退
 *
 * 使用: node e2e/mock-server.mjs
 * 端口: 8080
 */

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DIST_DIR = path.resolve(__dirname, '..', 'dist');
const PORT = 8080;

// 内置测试用户
const MOCK_USER = {
  id: 'mock-user-001',
  username: 'e2e_tester',
  email: 'e2e@devflow.io',
  role: 'admin',
  display_name: 'E2E 测试员',
  avatar_url: '',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const MOCK_TOKENS = {
  access_token: 'mock-jwt-access-token-for-e2e-testing',
  refresh_token: 'mock-jwt-refresh-token-for-e2e-testing',
  token_type: 'bearer',
  expires_in: 3600,
};

let nextId = 100;
function genId() { return `mock-id-${nextId++}`; }
function currentTime() { return new Date().toISOString(); }

function ok(data) {
  return JSON.stringify({ code: 0, data });
}

function error(message, code = -1) {
  return JSON.stringify({ code, message });
}

// MIME types
const MIME_MAP = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript; charset=utf-8',
  '.mjs':  'application/javascript; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml; charset=utf-8',
  '.ico':  'image/x-icon',
  '.woff': 'font/woff',
  '.woff2':'font/woff2',
};

function serveStatic(res, filePath) {
  try {
    const content = fs.readFileSync(filePath);
    const ext = path.extname(filePath).toLowerCase();
    const mime = MIME_MAP[ext] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': mime });
    res.end(content);
  } catch (e) {
    res.writeHead(404);
    res.end('Not Found');
  }
}

function serveIndex(res) {
  const indexPath = path.join(DIST_DIR, 'index.html');
  try {
    const content = fs.readFileSync(indexPath, 'utf-8');
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(content);
  } catch (e) {
    res.writeHead(500);
    res.end('index.html not found. Run npm run build first.');
  }
}

// ---- API Mock Data Stores ----
const stores = {
  projects: [],
  boards: [],
  tasks: [],
  agents: [],
  skills: [],
  swarms: [],
  qa_records: [],
  security_audits: [],
};

// ---- API Route Handlers ----
function handleApiRoute(method, urlPath, body) {
  // Auth
  if (urlPath === '/api/auth/login' && method === 'POST') {
    return ok({ user: MOCK_USER, tokens: MOCK_TOKENS });
  }
  if (urlPath === '/api/auth/register' && method === 'POST') {
    return ok({ user: { ...MOCK_USER, id: genId(), username: body?.username || 'newuser' }, tokens: MOCK_TOKENS });
  }
  if (urlPath === '/api/auth/me' && method === 'GET') {
    return ok({ ...MOCK_USER });
  }
  if (urlPath === '/api/auth/refresh' && method === 'GET') {
    return ok(MOCK_TOKENS);
  }
  if (urlPath === '/api/auth/logout' && method === 'POST') {
    return ok(null);
  }
  if (urlPath === '/api/auth/change-password' && method === 'POST') {
    return ok(null);
  }
  if (urlPath === '/api/auth/me' && method === 'PATCH') {
    return ok({ ...MOCK_USER, ...body });
  }

  // Projects
  if (urlPath === '/api/projects' && method === 'GET') {
    return ok({ projects: stores.projects, total: stores.projects.length });
  }
  if (urlPath === '/api/projects' && method === 'POST') {
    const project = {
      id: genId(),
      name: body?.name || 'New Project',
      slug: (body?.name || 'new-project').toLowerCase().replace(/\s+/g, '-'),
      description: body?.description || '',
      status: 'active',
      tech_stack: body?.tech_stack || {},
      current_step: 1,
      created_at: currentTime(),
      updated_at: currentTime(),
    };
    stores.projects.push(project);
    return ok({ project });
  }

  const projectMatch = urlPath.match(/^\/api\/projects\/([\w-]+)(?:\/(.+))?$/);
  if (projectMatch) {
    const projectId = projectMatch[1];
    const subPath = projectMatch[2];
    const project = stores.projects.find(p => p.id === projectId);

    if (method === 'GET' && !subPath) {
      return project ? ok(project) : error('项目不存在');
    }
    if (method === 'DELETE' && !subPath) {
      stores.projects = stores.projects.filter(p => p.id !== projectId);
      return ok({ deleted: true });
    }
    if (method === 'PATCH' && !subPath) {
      if (project) Object.assign(project, body);
      return ok(project || {});
    }
    if (subPath === 'tasks' && method === 'GET') {
      return ok({ tasks: stores.tasks.filter(t => t.project_id === projectId), total: stores.tasks.filter(t => t.project_id === projectId).length });
    }
    if (subPath === 'tasks' && method === 'POST') {
      const task = { id: genId(), project_id: projectId, ...body, created_at: currentTime() };
      stores.tasks.push(task);
      return ok({ task });
    }
    if (subPath === 'decompose' && method === 'POST') {
      return ok({ tasks: [], total: 0 });
    }
    if (subPath === 'notifications' && method === 'GET') {
      return ok({ notifications: [], total: 0, unread_count: 0 });
    }
    if (subPath === 'complete' && method === 'POST') {
      if (project) project.status = 'completed';
      return ok({ project_id: projectId, status: 'completed', summary: '项目已完成' });
    }
  }

  // Boards
  if (urlPath === '/api/boards' && method === 'GET') {
    return ok({ boards: stores.boards, total: stores.boards.length });
  }
  if (urlPath === '/api/boards' && method === 'POST') {
    const board = { id: genId(), name: body?.name || 'New Board', created_at: currentTime() };
    stores.boards.push(board);
    return ok({ board });
  }
  const boardMatch = urlPath.match(/^\/api\/boards\/([\w-]+)(?:\/(.+))?$/);
  if (boardMatch) {
    const boardId = boardMatch[1];
    const board = stores.boards.find(b => b.id === boardId);
    if (method === 'GET' && !boardMatch[2]) return ok(board || {});
    if (method === 'DELETE') {
      stores.boards = stores.boards.filter(b => b.id !== boardId);
      return ok({ deleted: true });
    }
  }

  // Tasks
  const taskDetailMatch = urlPath.match(/^\/api\/tasks\/([\w-]+)(?:\/(.+))?$/);
  if (taskDetailMatch) {
    const taskId = taskDetailMatch[1];
    const task = stores.tasks.find(t => t.id === taskId);
    if (method === 'GET') return ok(task || {});
    if (method === 'PATCH') {
      if (task) Object.assign(task, body);
      return ok(task || {});
    }
    if (method === 'DELETE') {
      stores.tasks = stores.tasks.filter(t => t.id !== taskId);
      return ok({ deleted: true });
    }
    if (taskDetailMatch[2] === 'comments' && method === 'POST') {
      return ok({ id: genId(), task_id: taskId, content: body?.content, created_at: currentTime() });
    }
    if (taskDetailMatch[2] === 'attachments' && method === 'POST') {
      return ok({ id: genId(), task_id: taskId, filename: body?.filename || 'file.txt' });
    }
    if (taskDetailMatch[2] === 'dependencies' && method === 'POST') {
      return ok({ id: genId(), ...body });
    }
  }

  // Agents
  if (urlPath === '/api/agents' && method === 'GET') {
    return ok({ agents: stores.agents, total: stores.agents.length });
  }
  if (urlPath === '/api/agents' && method === 'POST') {
    const agent = { id: genId(), name: body?.name || 'New Agent', agent_type: body?.agent_type || 'claude', status: 'idle', created_at: currentTime() };
    stores.agents.push(agent);
    return ok({ agent });
  }
  const agentMatch = urlPath.match(/^\/api\/agents\/([\w-]+)(?:\/(.+))?$/);
  if (agentMatch) {
    const agentId = agentMatch[1];
    const agent = stores.agents.find(a => a.id === agentId);
    if (method === 'GET') return ok(agent || {});
    if (method === 'DELETE') {
      stores.agents = stores.agents.filter(a => a.id !== agentId);
      return ok({ deleted: true });
    }
    if (agentMatch[2] === 'webhooks' && method === 'POST') {
      return ok({ id: genId(), agent_id: agentId, url: body?.url });
    }
  }

  // Skills
  if (urlPath === '/api/skills' && method === 'GET') {
    return ok({ skills: stores.skills, total: stores.skills.length });
  }
  if (urlPath === '/api/skills' && method === 'POST') {
    const skill = { id: genId(), name: body?.name || 'New Skill', created_at: currentTime() };
    stores.skills.push(skill);
    return ok({ skill });
  }
  const skillMatch = urlPath.match(/^\/api\/skills\/([\w-]+)$/);
  if (skillMatch) {
    if (method === 'DELETE') {
      stores.skills = stores.skills.filter(s => s.id !== skillMatch[1]);
      return ok({ deleted: true });
    }
  }

  // Chat / Groups
  if (urlPath === '/api/groups' && method === 'GET') {
    return ok({ groups: [], total: 0 });
  }
  if (urlPath === '/api/groups' && method === 'POST') {
    return ok({ group: { id: genId(), name: body?.name || 'New Group', created_at: currentTime() } });
  }
  if (urlPath === '/api/chat/messages' && method === 'GET') {
    return ok({ messages: [], total: 0 });
  }
  if (urlPath === '/api/chat/messages' && method === 'POST') {
    return ok({ id: genId(), content: body?.content, created_at: currentTime() });
  }

  // Repos
  if (urlPath === '/api/repos' && method === 'GET') {
    return ok({ repos: [], total: 0 });
  }
  if (urlPath === '/api/repos' && method === 'POST') {
    return ok({ id: genId(), name: body?.name, url: `https://gitea.local/${body?.name}` });
  }

  // Acceptance
  if (urlPath.match(/^\/api\/acceptance/) && method === 'GET') {
    return ok({ reports: [], total: 0 });
  }
  if (urlPath.match(/^\/api\/acceptance/) && method === 'POST') {
    return ok({ id: genId(), status: 'generated' });
  }

  // Requirements
  if (urlPath === '/api/requirements' && method === 'GET') {
    return ok({ requirements: [], total: 0 });
  }
  if (urlPath === '/api/requirements' && method === 'POST') {
    return ok({ id: genId(), title: body?.title, status: 'draft' });
  }

  // Inbox
  if (urlPath === '/api/inbox' && method === 'GET') {
    return ok({ notifications: [], total: 0, unread_count: 0 });
  }
  if (urlPath.match(/^\/api\/inbox\/read/) && method === 'POST') {
    return ok({ read: true });
  }

  // Workload
  if (urlPath === '/api/workload' && method === 'GET') {
    return ok({ workloads: [], total: 0 });
  }

  // User
  if (urlPath === '/api/user/profile' && method === 'GET') {
    return ok(MOCK_USER);
  }
  if (urlPath === '/api/users' && method === 'GET') {
    return ok({ users: [MOCK_USER], total: 1 });
  }

  // Notifications
  if (urlPath === '/api/notifications' && method === 'GET') {
    return ok({ notifications: [], total: 0, unread_count: 0 });
  }

  // ---- v4.0 新接口 ----

  // Workflow
  const workflowStepMatch = urlPath.match(/^\/api\/v1\/workflow\/([\w-]+)\/step(\d{1,2})$/);
  if (workflowStepMatch && method === 'POST') {
    const stepNum = parseInt(workflowStepMatch[2]);
    return ok({
      project_id: workflowStepMatch[1],
      step_number: stepNum,
      status: 'completed',
      message: `第${stepNum}步执行成功`,
    });
  }
  const workflowQAMatch = urlPath.match(/^\/api\/v1\/workflow\/([\w-]+)\/step(\d{1,2})\/qa$/);
  if (workflowQAMatch && method === 'POST') {
    return ok({
      project_id: workflowQAMatch[1],
      step_number: parseInt(workflowQAMatch[2]),
      qa_status: body?.result || 'passed',
      message: body?.result === 'failed' ? 'QA检验未通过' : 'QA检验通过',
    });
  }
  if (urlPath.match(/^\/api\/v1\/workflow\/[\w-]+\/status$/) && method === 'GET') {
    return ok({ current_step: 1, total_steps: 16, status: 'in_progress' });
  }

  // QA
  if (urlPath === '/api/v1/qa/inspect' && method === 'POST') {
    const record = { id: genId(), ...body, created_at: currentTime() };
    stores.qa_records.push(record);
    return ok(record);
  }
  const qaRecordsMatch = urlPath.match(/^\/api\/v1\/qa\/([\w-]+)\/records$/);
  if (qaRecordsMatch && method === 'GET') {
    return ok({ records: stores.qa_records.filter(r => r.project_id === qaRecordsMatch[1]), total: stores.qa_records.length });
  }
  if (urlPath === '/api/v1/qa/rollback' && method === 'POST') {
    return ok({ ...body, status: 'failed', created_at: currentTime() });
  }
  if (urlPath.match(/^\/api\/v1\/qa\/status/) && method === 'GET') {
    return ok({ status: 'pending', records_count: stores.qa_records.length });
  }

  // Swarms
  if (urlPath === '/api/v1/swarms' && method === 'GET') {
    return ok({ swarms: stores.swarms, total: stores.swarms.length });
  }
  if (urlPath === '/api/v1/swarms' && method === 'POST') {
    const swarm = { id: genId(), ...body, status: 'active', created_at: currentTime() };
    stores.swarms.push(swarm);
    return ok({ swarm });
  }
  const swarmMatch = urlPath.match(/^\/api\/v1\/swarms\/([\w-]+)(?:\/(.+))?$/);
  if (swarmMatch) {
    const swarmId = swarmMatch[1];
    const sub = swarmMatch[2];
    const swarm = stores.swarms.find(s => s.id === swarmId);
    if (method === 'GET' && !sub) return ok(swarm || {});
    if (method === 'DELETE' && !sub) {
      stores.swarms = stores.swarms.filter(s => s.id !== swarmId);
      return ok({ status: 'disbanded', disbanded_at: currentTime() });
    }
    if (sub === 'members' && method === 'POST') {
      if (!swarm) return error('蜂群不存在');
      swarm.members = swarm.members || [];
      swarm.members.push(body);
      return ok({ ...swarm });
    }
    if (sub && sub.startsWith('members/') && method === 'DELETE') {
      const agentId = sub.replace('members/', '');
      if (swarm?.members) swarm.members = swarm.members.filter(m => m.agent_id !== agentId);
      return ok({ removed: true });
    }
    if (sub === 'dispatch' && method === 'POST') {
      const tasks = body?.tasks || [];
      const assignments = tasks.map((t, i) => ({
        task_id: t.task_id,
        assigned_agent_id: i % 2 === 0 ? 'claude_code' : 'opencode',
      }));
      return ok({ assignments, total: assignments.length });
    }
    if (sub === 'progress' && method === 'GET') {
      return ok({ total_tasks: 5, completed_tasks: 2, progress: '40%', members: swarm?.members || [] });
    }
  }

  // Security
  const secMatch = urlPath.match(/^\/api\/v1\/security\/([\w-]+)\/audit$/);
  if (secMatch && method === 'POST') {
    const audit = { id: genId(), project_id: secMatch[1], ...body, created_at: currentTime() };
    stores.security_audits.push(audit);
    return ok(audit);
  }
  const secStatusMatch = urlPath.match(/^\/api\/v1\/security\/([\w-]+)\/audit\/status$/);
  if (secStatusMatch && method === 'GET') {
    const audits = stores.security_audits.filter(a => a.project_id === secStatusMatch[1]);
    return ok({ status: audits.length ? 'in_progress' : 'not_started', audits_count: audits.length });
  }
  const secReportMatch = urlPath.match(/^\/api\/v1\/security\/([\w-]+)\/audit\/report$/);
  if (secReportMatch && method === 'GET') {
    return ok({ compliance: 'pass', vulnerabilities_found: 0, last_audit: currentTime() });
  }

  // Health
  if (urlPath === '/health' || urlPath === '/api/health') {
    return ok({ status: 'healthy', version: '4.0-mock' });
  }

  // Default API fallback
  if (urlPath.startsWith('/api/')) {
    return ok({ mock: true, path: urlPath, method, note: 'Mock API - endpoint auto-generated' });
  }

  return null;
}

// ---- HTTP Server ----
const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const urlPath = url.pathname;

  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // Parse body
  const isApiPath = urlPath.startsWith('/api/') || urlPath === '/health';
  if (isApiPath && ['POST', 'PUT', 'PATCH'].includes(req.method)) {
    let bodyChunks = [];
    req.on('data', c => bodyChunks.push(c));
    req.on('end', () => {
      let body = {};
      try {
        body = JSON.parse(Buffer.concat(bodyChunks).toString());
      } catch (e) {}
      const result = handleApiRoute(req.method, urlPath, body);
      if (result) {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(result);
      } else {
        serveFile(urlPath, res);
      }
    });
    return;
  }

  if (isApiPath) {
    const result = handleApiRoute(req.method, urlPath);
    if (result) {
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(result);
      return;
    }
  }

  serveFile(urlPath, res);
});

function serveFile(urlPath, res) {
  // 安全检查：防止目录遍历
  const safePath = path.normalize(urlPath).replace(/^(\.\.(\/|\\|$))+/, '');
  let filePath = path.join(DIST_DIR, safePath);

  // 检查是否是文件
  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    serveStatic(res, filePath);
    return;
  }

  // SPA fallback: 非文件路径都返回 index.html
  serveIndex(res);
}

server.listen(PORT, () => {
  console.log(`
============================================================
  🎭 DevFlow Mock Server v4.0
============================================================
  📂 Static files: ${DIST_DIR}
  🌐 URL:          http://localhost:${PORT}
  🔌 API Prefix:   /api/*   (所有接口自动 mock)
  🎯 SPA Mode:     非文件路径 → index.html
============================================================

  可直接用于 Playwright E2E 测试:
    baseURL: 'http://localhost:${PORT}'

  按 Ctrl+C 停止服务
============================================================
`);
});

// 优雅关闭
process.on('SIGINT', () => {
  console.log('\n🛑 Mock Server 已停止');
  process.exit(0);
});
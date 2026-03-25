const statusEl = document.getElementById('status');
const runCountEl = document.getElementById('runCount');
const eventCountEl = document.getElementById('eventCount');

const limitInput = document.getElementById('limitInput');
const questionInput = document.getElementById('questionInput');
const askBtn = document.getElementById('askBtn');
const refreshBtn = document.getElementById('refreshBtn');
const pollBtn = document.getElementById('pollBtn');
const clearBtn = document.getElementById('clearBtn');
const pollStateEl = document.getElementById('pollState');

const taskStatusEl = document.getElementById('taskStatus');
const answerViewEl = document.getElementById('answerView');

const runsListEl = document.getElementById('runsList');
const timelineEl = document.getElementById('timeline');
const jsonTreeEl = document.getElementById('jsonTree');

const expandAllBtn = document.getElementById('expandAllBtn');
const collapseAllBtn = document.getElementById('collapseAllBtn');

const state = {
  polling: true,
  runs: [],
  selectedRunId: null,
  selectedEventIndex: null,
  activeTaskId: null,
  dataSignature: '',
  followLatestOnNextUpdate: false,
};

const EVENT_TYPE_LABELS = {
  user: 'USER',
  llm_request: 'LLM REQ',
  llm_response: 'LLM RES',
  tool: 'TOOL',
  agent: 'AGENT',
};

function emptyState(title, desc) {
  return '<div class="empty-state"><div class="empty-glyph"></div><div class="empty-title">' +
    title + '</div><div class="empty-desc">' + desc + '</div></div>';
}

function createEventTypeBadge(type) {
  const badge = document.createElement('span');
  const normalized = type || 'unknown';
  badge.className = 'event-type-badge type-' + normalized;
  badge.textContent = EVENT_TYPE_LABELS[normalized] || normalized.toUpperCase();
  return badge;
}

function updatePollingUi() {
  pollBtn.classList.toggle('is-paused', !state.polling);
  if (pollStateEl) {
    pollStateEl.classList.toggle('is-on', state.polling);
    pollStateEl.classList.toggle('is-off', !state.polling);
    pollStateEl.title = state.polling ? '自动刷新运行中' : '自动刷新已暂停';
  }
}

function summarizeEvent(event) {
  const type = event.type;
  if (type === 'user') return event.content || '(empty user message)';
  if (type === 'llm_request') {
    const msgLen = (event.messages || []).length;
    const toolLen = (event.tools || []).length;
    return 'send_to_llm messages=' + msgLen + ' tools=' + toolLen;
  }
  if (type === 'llm_response') {
    const toolCalls = event.tool_calls || [];
    if (toolCalls.length) {
      const names = toolCalls.map((call) => call.name).join(', ');
      return 'tool_calls(' + toolCalls.length + '): ' + names;
    }
    return event.content || '(empty llm response)';
  }
  if (type === 'tool') {
    const result = String(event.result || '').replace(/\s+/g, ' ').slice(0, 72);
    return (event.tool_name || 'tool') + ' => ' + result;
  }
  if (type === 'agent') {
    if (event.tool_calls) return 'agent plan tool_calls=' + event.tool_calls.length;
    return event.content || '(empty agent message)';
  }
  return JSON.stringify(event).slice(0, 80);
}

function renderRunList() {
  const runs = state.runs;
  const selectedRunId = state.selectedRunId;
  runsListEl.innerHTML = '';

  if (!runs.length) {
    runsListEl.innerHTML = emptyState('暂无问题轮次', '提交一个问题后，这里会展示运行历史。');
    runCountEl.textContent = '';
    return;
  }

  runCountEl.textContent = String(runs.length) + ' 轮';

  [...runs].reverse().forEach((run) => {
    const item = document.createElement('div');
    item.className = 'run-item ' + (run.id === selectedRunId ? 'active' : '');

    const title = document.createElement('div');
    title.className = 'run-title';
    title.textContent = run.question || '(empty question)';

    const meta = document.createElement('div');
    meta.className = 'run-meta';
    const t = run.type_counts || {};
    const llmCount = (t.llm_request || 0) + (t.llm_response || 0);
    meta.textContent = 'events=' + (run.event_count || 0) + ' | user=' + (t.user || 0) + ' llm=' + llmCount + ' tool=' + (t.tool || 0);

    item.append(title, meta);
    item.addEventListener('click', () => {
      state.selectedRunId = run.id;
      state.selectedEventIndex = null;
      renderTimeline();
    });

    runsListEl.appendChild(item);
  });
}

function getSelectedRun() {
  return state.runs.find((run) => run.id === state.selectedRunId) || null;
}

function renderTimeline() {
  const run = getSelectedRun();
  timelineEl.innerHTML = '';

  if (!run) {
    timelineEl.innerHTML = emptyState('没有可展示的事件', '选择左侧轮次后，可查看完整时间线。');
    eventCountEl.textContent = '';
    jsonTreeEl.innerHTML = emptyState('等待事件详情', '点击中间时间线卡片查看结构化数据。');
    return;
  }

  const events = run.events || [];
  eventCountEl.textContent = String(events.length) + ' 条事件';

  events.forEach((event, idx) => {
    const card = document.createElement('div');
    card.className = 'event ' + (event.type || 'unknown') + ' ' + (state.selectedEventIndex === idx ? 'active' : '');

    const head = document.createElement('div');
    head.className = 'event-head';
    const headLeft = document.createElement('span');
    headLeft.className = 'event-head-left';
    headLeft.textContent = '#' + String(idx + 1);
    headLeft.appendChild(createEventTypeBadge(event.type));

    const headRight = document.createElement('span');
    const iteration = event.iteration == null ? '-' : String(event.iteration);
    headRight.textContent = 'iter=' + iteration;
    head.append(headLeft, headRight);

    const summary = document.createElement('div');
    summary.className = 'event-summary';
    summary.textContent = summarizeEvent(event);

    card.append(head, summary);
    card.addEventListener('click', () => {
      state.selectedEventIndex = idx;
      renderTimeline();
      renderEventDetail(event);
    });

    timelineEl.appendChild(card);
  });

  if (state.selectedEventIndex === null && events.length) {
    state.selectedEventIndex = events.length - 1;
    renderTimeline();
    renderEventDetail(events[state.selectedEventIndex]);
  } else if (events[state.selectedEventIndex]) {
    renderEventDetail(events[state.selectedEventIndex]);
  }
}

function makeValueNode(value) {
  const span = document.createElement('span');
  if (typeof value === 'string') {
    span.className = 'val-string';
    span.textContent = JSON.stringify(value);
  } else if (typeof value === 'number') {
    span.className = 'val-number';
    span.textContent = String(value);
  } else if (typeof value === 'boolean') {
    span.className = 'val-bool';
    span.textContent = String(value);
  } else if (value === null) {
    span.className = 'val-null';
    span.textContent = 'null';
  } else {
    span.textContent = JSON.stringify(value);
  }
  return span;
}

function buildJsonTree(value, key) {
  const hasKey = key !== undefined && key !== null;
  const isArray = Array.isArray(value);
  const isObject = value && typeof value === 'object';

  if (!isObject) {
    const line = document.createElement('div');
    line.className = 'json-leaf';
    if (hasKey) {
      const keyNode = document.createElement('span');
      keyNode.className = 'json-key';
      keyNode.textContent = key + ': ';
      line.appendChild(keyNode);
    }
    line.appendChild(makeValueNode(value));
    return line;
  }

  const details = document.createElement('details');
  details.className = 'json-block';
  details.open = true;

  const summary = document.createElement('summary');
  const size = isArray ? value.length : Object.keys(value).length;
  const label = isArray ? 'Array(' + size + ')' : 'Object(' + size + ')';
  summary.textContent = hasKey ? key + ': ' + label : label;
  details.appendChild(summary);

  const node = document.createElement('div');
  node.className = 'json-node';
  details.appendChild(node);

  if (isArray) {
    value.forEach((item, index) => {
      node.appendChild(buildJsonTree(item, '[' + index + ']'));
    });
  } else {
    Object.keys(value).forEach((k) => {
      node.appendChild(buildJsonTree(value[k], k));
    });
  }

  return details;
}

function renderEventDetail(event) {
  jsonTreeEl.innerHTML = '';
  jsonTreeEl.appendChild(buildJsonTree(event, null));
}

function render() {
  if (!state.runs.length) {
    runsListEl.innerHTML = '';
    timelineEl.innerHTML = '';
    jsonTreeEl.innerHTML = emptyState('暂无数据', '系统还没有收到新的追踪记录。');
    runCountEl.textContent = '';
    eventCountEl.textContent = '';
    return;
  }

  const hasSelectedRun = state.runs.some((run) => run.id === state.selectedRunId);
  if (!hasSelectedRun) {
    state.selectedRunId = state.runs[state.runs.length - 1].id;
    state.selectedEventIndex = null;
  }

  renderRunList();
  renderTimeline();
}

function buildSignature(runs) {
  return JSON.stringify(
    runs.map((run) => [run.id, run.question, run.event_count, (run.events || []).length]),
  );
}

async function loadRuns() {
  const limit = Number(limitInput.value || 500);
  const response = await fetch('/api/runs?limit=' + encodeURIComponent(limit));
  if (!response.ok) throw new Error('HTTP ' + response.status);

  const data = await response.json();
  const runs = data.runs || [];
  const signature = buildSignature(runs);

  if (signature !== state.dataSignature) {
    state.runs = runs;
    state.dataSignature = signature;
    if (state.followLatestOnNextUpdate && state.runs.length) {
      state.selectedRunId = state.runs[state.runs.length - 1].id;
      state.selectedEventIndex = null;
      state.followLatestOnNextUpdate = false;
    }
    render();
  }

  const totalEvents = state.runs.reduce((sum, run) => sum + (run.event_count || 0), 0);
  statusEl.textContent = '轮次 ' + state.runs.length + ' | 事件 ' + totalEvents + ' | ' + new Date().toLocaleTimeString();
}

async function refresh() {
  try {
    await loadRuns();
  } catch (error) {
    statusEl.textContent = '加载失败: ' + error.message;
  }
}

async function submitQuestion() {
  const question = (questionInput.value || '').trim();
  if (!question) return;

  askBtn.disabled = true;
  taskStatusEl.textContent = '任务提交中...';

  try {
    const response = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    if (!response.ok) throw new Error('HTTP ' + response.status);

    const data = await response.json();
    state.activeTaskId = data.task_id;
    state.followLatestOnNextUpdate = true;
    taskStatusEl.textContent = '运行中: ' + state.activeTaskId.slice(0, 8) + '...';
    questionInput.value = '';
    await refresh();
  } catch (error) {
    taskStatusEl.textContent = '提交失败: ' + error.message;
  } finally {
    askBtn.disabled = false;
  }
}

async function refreshTaskStatus() {
  if (!state.activeTaskId) return;

  try {
    const response = await fetch('/api/tasks/' + encodeURIComponent(state.activeTaskId));
    if (!response.ok) throw new Error('HTTP ' + response.status);

    const task = await response.json();
    if (task.status === 'done') {
      taskStatusEl.textContent = '任务完成';
      answerViewEl.textContent = task.result || '(empty result)';
      state.activeTaskId = null;
      await refresh();
      return;
    }

    if (task.status === 'error') {
      taskStatusEl.textContent = '任务失败';
      answerViewEl.textContent = 'Error: ' + (task.error || 'unknown error');
      state.activeTaskId = null;
      await refresh();
      return;
    }

    taskStatusEl.textContent = '任务状态: ' + task.status;
  } catch (error) {
    taskStatusEl.textContent = '任务查询失败: ' + error.message;
  }
}

function clearLocalState() {
  state.runs = [];
  state.dataSignature = '';
  state.selectedRunId = null;
  state.selectedEventIndex = null;
  state.activeTaskId = null;
  runCountEl.textContent = '';
  eventCountEl.textContent = '';
  answerViewEl.textContent = '暂无回答';
  taskStatusEl.textContent = '';
  render();
}

refreshBtn.addEventListener('click', refresh);
askBtn.addEventListener('click', submitQuestion);
questionInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') submitQuestion();
});

pollBtn.addEventListener('click', () => {
  state.polling = !state.polling;
  pollBtn.textContent = state.polling ? '暂停自动刷新' : '恢复自动刷新';
  updatePollingUi();
});

clearBtn.addEventListener('click', async () => {
  try {
    const response = await fetch('/api/clear', { method: 'POST' });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    clearLocalState();
    await refresh();
  } catch (error) {
    statusEl.textContent = '清空失败: ' + error.message;
  }
});

collapseAllBtn.addEventListener('click', () => {
  jsonTreeEl.querySelectorAll('details.json-block').forEach((item) => {
    item.open = false;
  });
});

expandAllBtn.addEventListener('click', () => {
  jsonTreeEl.querySelectorAll('details.json-block').forEach((item) => {
    item.open = true;
  });
});

refresh();
updatePollingUi();
setInterval(() => {
  if (!state.polling) return;
  refresh();
  refreshTaskStatus();
}, 1500);

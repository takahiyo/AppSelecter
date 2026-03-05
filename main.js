/**
 * AppSelecter Main Logic
 * [SSOT]: Settings are managed in LocalStorage and reflected in the UI.
 */

// =====================================
// Constants & State
// =====================================
const STORAGE_KEY = 'appSelecter_Settings';
const AUTO_CLOSE_MS = 4000;
const GRID_SIZE = 9;

const DEFAULT_SETTINGS = Array.from({ length: GRID_SIZE }, (_, i) => ({
  id: i,
  name: `アプリ ${i + 1}`,
  path: '',
  icon: '🚀' // デフォルトアイコン
}));

let state = {
  apps: [],
  timerId: null,
  editingIndex: null
};

// =====================================
// Initialization
// =====================================
function init() {
  loadSettings();
  renderGrid();
  setupEventListeners();
  resetTimer();
}

// =====================================
// Settings Management
// =====================================
function loadSettings() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    try {
      state.apps = JSON.parse(saved);
    } catch (e) {
      console.error('Failed to parse settings:', e);
      state.apps = [...DEFAULT_SETTINGS];
    }
  } else {
    state.apps = [...DEFAULT_SETTINGS];
    saveSettings();
  }
}

function saveSettings() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.apps));
}

// =====================================
// UI Rendering
// =====================================
function renderGrid() {
  const grid = document.getElementById('launcherGrid');
  grid.innerHTML = '';

  state.apps.forEach((app, index) => {
    const button = document.createElement('div');
    button.className = 'app-button staggered-in';
    button.style.animationDelay = `${index * 0.05}s`;
    
    button.innerHTML = `
      <div class="app-icon">${app.icon || '📦'}</div>
      <div class="app-name">${app.name}</div>
    `;

    button.addEventListener('click', (e) => handleButtonClick(e, index));
    grid.appendChild(button);
  });
}

// =====================================
// Event Handlers
// =====================================
function handleButtonClick(e, index) {
  pauseTimer();

  if (e.shiftKey) {
    // Shift + Click: 詳細編集 (Path / Name)
    openEditModal(index);
  } else if (e.ctrlKey) {
    // Ctrl + Click: 名前のみ変更 (簡易版)
    const newName = prompt('新しい名前を入力してください:', state.apps[index].name);
    if (newName) {
      updateApp(index, { name: newName });
    }
    resumeTimer();
  } else {
    // Standard Click: アプリ / URL 起動
    openApp(index);
  }
}

function openApp(index) {
  const app = state.apps[index];
  if (!app.path) {
    alert('パスが設定されていません。Shift+Clickで設定してください。');
    resumeTimer();
    return;
  }

  console.log(`Launching: ${app.name} (${app.path})`);
  
  // Web版ではURLを開くか、または将来的にデスクトップラッパー経由で起動
  if (app.path.startsWith('http')) {
    window.open(app.path, '_blank');
  } else {
    // ブラウザ環境では実際のEXE実行は不可だが、デバッグ用に出力
    alert(`[ブラウザ制限] ローカルアプリを起動しようとしました:\n${app.path}\n\n※この機能にはPython/Electron等のラッパーが必要です。`);
  }
  
  // 起動後は終了（シミュレーション）
  closeApp();
}

function openEditModal(index) {
  state.editingIndex = index;
  const app = state.apps[index];
  
  document.getElementById('appName').value = app.name;
  document.getElementById('appPath').value = app.path;
  document.getElementById('configOverlay').classList.remove('hidden');
}

function closeEditModal() {
  document.getElementById('configOverlay').classList.add('hidden');
  state.editingIndex = null;
  resumeTimer();
}

function updateApp(index, data) {
  state.apps[index] = { ...state.apps[index], ...data };
  saveSettings();
  renderGrid();
}

// =====================================
// Timer Logic
// =====================================
function resetTimer() {
  pauseTimer();
  resumeTimer();
}

function pauseTimer() {
  if (state.timerId) {
    clearTimeout(state.timerId);
    state.timerId = null;
    updateTimerDisplay('Timer Paused');
  }
}

function resumeTimer() {
  state.timerId = setTimeout(() => {
    closeApp();
  }, AUTO_CLOSE_MS);
  
  // カウントダウン表示（オプション）
  let remaining = AUTO_CLOSE_MS / 1000;
  updateTimerDisplay(`Closing in ${remaining}s...`);
  
  const countdownInterval = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0 || !state.timerId) {
      clearInterval(countdownInterval);
    } else {
      updateTimerDisplay(`Closing in ${remaining}s...`);
    }
  }, 1000);
}

function updateTimerDisplay(text) {
  const el = document.getElementById('timerDisplay');
  if (el) el.textContent = text;
}

function closeApp() {
  console.log('App auto-closing...');
  // 実際のウィンドウを閉じる (Electron/Python環境用)
  // window.close();
  
  // ブラウザシミュレーション: UIを暗转させるなど
  document.body.style.opacity = '0.3';
  document.body.style.pointerEvents = 'none';
  updateTimerDisplay('App Closed');
}

// =====================================
// Global Events
// =====================================
function setupEventListeners() {
  document.getElementById('saveBtn').addEventListener('click', () => {
    const name = document.getElementById('appName').value;
    const path = document.getElementById('appPath').value;
    if (state.editingIndex !== null) {
      updateApp(state.editingIndex, { name, path });
    }
    closeEditModal();
  });

  document.getElementById('cancelBtn').addEventListener('click', closeEditModal);

  // ユーザーの何らかの操作でタイマーリセット
  window.addEventListener('mousemove', resetTimer);
  window.addEventListener('keydown', resetTimer);
}

// Start
init();

const app = document.querySelector("#app");
const toastRoot = document.querySelector("#toast-root");
const dropIndicator = document.createElement("div");
dropIndicator.className = "drop-marker";

const state = {
  apiBase: "",
  token: localStorage.getItem("kju.token") || "",
  authMode: "login",
  user: null,
  boards: [],
  boardId: Number(localStorage.getItem("kju.boardId")) || null,
  board: null,
  columns: [],
  cardsByColumn: {},
  commentsByCard: {},
  loading: false,
  search: "",
  drag: null,
  drop: null,
  modal: null,
  auditLogs: null,
};

const priorityLabel = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
};

const roleLabel = {
  owner: "Владелец",
  member: "Участник",
  reader: "Читатель",
};

function icon(name) {
  return `<svg class="icon" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function initials(user) {
  const name = user?.username || user?.email || "?";
  return name.trim().slice(0, 2).toUpperCase();
}

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
  }).format(new Date(`${value}T00:00:00`));
}
function formatDateTime(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function getErrorMessage(payload) {
  if (!payload) return "Что-то пошло не так";
  if (typeof payload.detail === "string") return payload.detail;
  if (payload.detail?.message) return payload.detail.message;
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => item.msg).join(", ");
  }
  return payload.message || "Что-то пошло не так";
}

function normalizeApiBase(value) {
  const base = String(value || "").trim().replace(/\/$/, "");
  if (!base) return "";
  if (/^https?:\/\//i.test(base)) return base;
  return `http://${base}`;
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (state.token) headers.set("Authorization", `Bearer ${state.token}`);

  state.apiBase = normalizeApiBase(state.apiBase);

  let response;
  try {
    response = await fetch(`${state.apiBase}${path}`, {
      ...options,
      headers,
      body:
        options.body && typeof options.body !== "string"
          ? JSON.stringify(options.body)
          : options.body,
    });
  } catch {
    throw new Error(
      `Не удалось подключиться к API ${state.apiBase}. Проверь, что backend запущен на этом адресе.`,
    );
  }

  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { message: text };
  }
  if (!response.ok) {
    if (response.status === 401) logout(false);
    throw new Error(getErrorMessage(data));
  }
  return data;
}

function toast(message, type = "ok") {
  const node = document.createElement("div");
  node.className = `toast ${type === "error" ? "is-error" : ""}`;
  node.textContent = message;
  toastRoot.appendChild(node);
  setTimeout(() => node.remove(), 3600);
}

function setLoading(loading) {
  state.loading = loading;
  render();
}

async function bootstrap() {
  if (!state.token) {
    render();
    return;
  }

  try {
    setLoading(true);
    state.user = await api("/api/auth/users/me");
    await loadBoards(false);
    const firstBoard =
      state.boards.find((board) => board.id === state.boardId) || state.boards[0];
    if (firstBoard) await selectBoard(firstBoard.id, false);
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(false);
  }
}

async function loadBoards(shouldRender = true) {
  state.boards = await api("/api/boards/");
  if (shouldRender) render();
}

async function selectBoard(boardId, shouldRender = true) {
  state.boardId = Number(boardId);
  localStorage.setItem("kju.boardId", String(state.boardId));
  state.board = await api(`/api/boards/${state.boardId}`);
  state.columns = await api(`/api/columns/boards/${state.boardId}/columns`);
  state.columns.sort((a, b) => a.position - b.position || a.id - b.id);
  const entries = await Promise.all(
    state.columns.map(async (column) => {
      const cards = await api(`/api/cards/columns/${column.id}/cards`);
      cards.sort((a, b) => a.position - b.position || a.id - b.id);
      return [column.id, cards];
    }),
  );
  state.cardsByColumn = Object.fromEntries(entries);
  state.auditLogs = null;
  if (shouldRender) render();
}

function logout(showMessage = true) {
  localStorage.removeItem("kju.token");
  localStorage.removeItem("kju.boardId");
  state.token = "";
  state.user = null;
  state.boards = [];
  state.board = null;
  state.boardId = null;
  state.columns = [];
  state.cardsByColumn = {};
  state.commentsByCard = {};
  state.modal = null;
  if (showMessage) toast("Сессия завершена");
  render();
}

function normalizeRole(role) {
  const value = String(role || "")
    .toLowerCase()
    .split(".")
    .pop();
  return ["owner", "member", "reader"].includes(value) ? value : null;
}

function getCurrentMember() {
  if (!state.board || !state.user) return null;
  return (
    state.board.members?.find(
      (member) => Number(member.user_id) === Number(state.user.id),
    ) || null
  );
}

function getCurrentRole() {
  if (!state.board || !state.user) return null;
  const memberRole = normalizeRole(getCurrentMember()?.role);
  if (memberRole) return memberRole;
  if (Number(state.board.owner_id) === Number(state.user.id)) return "owner";
  return null;
}

function isOwner() {
  return getCurrentRole() === "owner";
}

function canManageBoard() {
  return getCurrentRole() === "owner";
}

function canManageColumns() {
  return canManageBoard();
}

function canManageMembers() {
  return canManageBoard();
}

function canCreateCards() {
  return ["owner", "member"].includes(getCurrentRole());
}

function isOwnCard(card) {
  return Number(card?.created_by) === Number(state.user?.id);
}

function canEditCard(card) {
  const role = getCurrentRole();
  return role === "owner" || (role === "member" && isOwnCard(card));
}

function canMoveCard(card) {
  return canEditCard(card);
}

function canDeleteCard(card) {
  return canEditCard(card);
}

function canAddComment() {
  return Boolean(getCurrentRole());
}

function canEditComment(comment) {
  return Number(comment?.user_id) === Number(state.user?.id);
}

function canDeleteComment(comment) {
  const role = getCurrentRole();
  return role === "owner" || (role === "member" && canEditComment(comment));
}

function guardPermission(allowed, message) {
  if (allowed) return true;
  toast(message, "error");
  return false;
}

function render() {
  if (!state.token) {
    app.innerHTML = renderAuth();
    return;
  }
  app.innerHTML = renderApp();
  if (state.modal) app.insertAdjacentHTML("beforeend", renderModal());
}

function renderAuth() {
  const isLogin = state.authMode === "login";
  return `
    <main class="auth-shell">
      <section class="auth-brand">
        <div class="brand-lockup">
          <span class="logo-mark logo-mark-auth" role="img" aria-label="KJU"></span>
          <span>kanban workspace</span>
        </div>
        <div class="auth-copy">
          <h1>KJU</h1>
          <p>Тёмная канбан-доска для командных задач, дедлайнов, исполнителей и быстрых комментариев.</p>
        </div>
      </section>
      <section class="auth-panel-wrap">
        <form class="auth-panel" data-form="auth">
          <div class="segmented">
            <button type="button" class="${isLogin ? "is-active" : ""}" data-action="auth-mode" data-mode="login">Вход</button>
            <button type="button" class="${!isLogin ? "is-active" : ""}" data-action="auth-mode" data-mode="register">Регистрация</button>
          </div>
          <div class="form-grid">
            <label class="field">
              <span>API</span>
              <input class="input" name="apiBase" value="${escapeHtml(state.apiBase)}" placeholder="http://127.0.0.1:8000" />
            </label>
            ${
              isLogin
                ? ""
                : `<label class="field">
                    <span>Имя</span>
                    <input class="input" name="username" minlength="3" maxlength="50" required autocomplete="username" />
                  </label>`
            }
            <label class="field">
              <span>Email</span>
              <input class="input" name="email" type="email" required autocomplete="email" />
            </label>
            <label class="field">
              <span>Пароль</span>
              <input class="input" name="password" type="password" minlength="6" required autocomplete="${isLogin ? "current-password" : "new-password"}" />
            </label>
            <button class="primary-btn" type="submit">${icon("check")} ${isLogin ? "Войти" : "Создать аккаунт"}</button>
          </div>
        </form>
      </section>
    </main>
  `;
}

function renderApp() {
  const roleClass = `role-${getCurrentRole() || "none"}`;
  return `
    <div class="app-shell ${roleClass}">
      <aside class="sidebar">
        <div class="sidebar-brand">
          <span class="logo-mark logo-mark-sidebar" role="img" aria-label="KJU"></span>
          <button class="icon-btn" data-action="new-board" title="Создать доску" aria-label="Создать доску">${icon("plus")}</button>
        </div>
        <div class="nav-title">
          <span>Доски</span>
          <span>${state.boards.length}</span>
        </div>
        <div class="board-list">
          ${renderBoardLinks()}
        </div>
      </aside>
      <main class="main">
        <header class="topbar">
          <label class="search">
            ${icon("search")}
            <input class="input" data-field="search" value="${escapeHtml(state.search)}" placeholder="Поиск по доскам и карточкам" />
          </label>
          <div></div>
          <div class="user-chip">
            <span class="avatar">${escapeHtml(initials(state.user))}</span>
            <span>${escapeHtml(state.user?.username || "")}</span>
            <button class="icon-btn" data-action="logout" title="Выйти" aria-label="Выйти">${icon("log-out")}</button>
          </div>
        </header>
        <section class="workspace">
          ${state.loading ? `<span class="loader">Загрузка</span>` : renderWorkspace()}
        </section>
      </main>
    </div>
  `;
}

function renderBoardLinks() {
  const query = state.search.trim().toLowerCase();
  const boards = state.boards.filter((board) => board.title.toLowerCase().includes(query));
  if (!boards.length) return `<div class="empty-note">Нет досок</div>`;
  return boards
    .map(
      (board) => `
        <button class="board-link ${board.id === state.boardId ? "is-active" : ""}" data-action="select-board" data-board-id="${board.id}">
          ${icon("board")}
          <span>${escapeHtml(board.title)}</span>
        </button>
      `,
    )
    .join("");
}

function renderWorkspace() {
  if (!state.boards.length) {
    return `
      <div class="empty-state">
        <div class="empty-state-inner">
          <h1>Первая доска</h1>
          <p>Создай рабочее пространство, а стартовые колонки появятся автоматически.</p>
          <button class="primary-btn" data-action="new-board">${icon("plus")} Создать доску</button>
        </div>
      </div>
    `;
  }

  if (!state.board) {
    return `
      <div class="empty-state">
        <div class="empty-state-inner">
          <h2>Выбери доску</h2>
          <p>Список доступных досок находится слева.</p>
        </div>
      </div>
    `;
  }

  const role = getCurrentRole();
  const canCreateCard = canCreateCards();
  const canManageColumn = canManageColumns();
  const canManage = canManageBoard();

  return `
    <div class="board-stage">
      <div>
        <div class="board-head">
          <div class="board-title">
            <h1>${escapeHtml(state.board.title)}</h1>
            <p class="board-meta">
              <span>${state.columns.length} колонок, ${countCards()} карточек, ${state.board.members.length} участников</span>
              <span class="role-pill role-pill-current">${roleLabel[role] || role || "Нет доступа"}</span>
            </p>
          </div>
          <div class="board-actions">
            ${canCreateCard ? `<button class="primary-btn" data-action="new-card-any">${icon("plus")} Карточка</button>` : ""}
            ${canManageColumn ? `<button class="ghost-btn" data-action="new-column">${icon("plus")} Колонка</button>` : ""}
            ${canManage ? `<button class="icon-btn" data-action="edit-board" title="Переименовать доску" aria-label="Переименовать доску">${icon("edit")}</button>` : ""}
            ${canManage ? `<button class="icon-btn danger" data-action="delete-board" title="Удалить доску" aria-label="Удалить доску">${icon("trash")}</button>` : ""}
          </div>
        </div>
        <div class="kanban">
          ${state.columns.map(renderColumn).join("")}
          ${canManageColumn ? renderAddColumnTile() : ""}
        </div>
      </div>
      ${renderMembers()}
    </div>
  `;
}

function countCards() {
  return Object.values(state.cardsByColumn).reduce((sum, cards) => sum + cards.length, 0);
}

function renderColumn(column, index) {
  const cards = state.cardsByColumn[column.id] || [];
  const canManageColumn = canManageColumns();
  const canCreateCard = canCreateCards();
  const query = state.search.trim().toLowerCase();
  const filteredCards = cards.filter(
    (card) =>
      card.title.toLowerCase().includes(query) ||
      (card.description || "").toLowerCase().includes(query),
  );
  return `
    <section class="column" data-column-id="${column.id}" style="animation-delay: ${index * 35}ms">
      <div class="column-head">
        <div class="column-title">
          <h2>${escapeHtml(column.title)}</h2>
          <span class="count-pill">${cards.length}</span>
        </div>
        <div class="column-tools">
          ${
            canManageColumn
              ? `<button class="icon-btn" data-action="edit-column" data-column-id="${column.id}" title="Редактировать колонку" aria-label="Редактировать колонку">${icon("edit")}</button>
                <button class="icon-btn danger" data-action="delete-column" data-column-id="${column.id}" title="Удалить колонку" aria-label="Удалить колонку">${icon("trash")}</button>`
              : ""
          }
        </div>
      </div>
      <div class="card-list" data-drop-zone data-column-id="${column.id}">
        ${filteredCards.map((card) => renderCard(card, column.id)).join("")}
      </div>
      ${
        canCreateCard
          ? `<div class="column-foot">
              <button class="ghost-btn add-card-btn" data-action="new-card" data-column-id="${column.id}">${icon("plus")} Добавить</button>
            </div>`
          : ""
      }
    </section>
  `;
}

function renderAddColumnTile() {
  return `
    <section class="column">
      <div class="empty-state-inner">
        <h2>Новая колонка</h2>
        <p>Добавь этап для процесса команды.</p>
        <button class="primary-btn" data-action="new-column">${icon("plus")} Создать</button>
      </div>
    </section>
  `;
}

function renderCard(card, columnId) {
  const assignee = card.assignee || findMemberUser(card.assignee_id);
  const movable = canMoveCard(card);
  return `
    <article class="task-card ${card.is_overdue ? "is-overdue" : ""} ${movable ? "" : "is-locked"}" draggable="${movable ? "true" : "false"}" data-card-id="${card.id}" data-column-id="${columnId}">
      <div class="task-top">
        <span class="priority-pill priority-${card.priority}">${priorityLabel[card.priority] || card.priority}</span>
        ${movable ? `<span title="Переместить">${icon("grip")}</span>` : ""}
      </div>
      <h3 class="task-title">${escapeHtml(card.title)}</h3>
      ${card.description ? `<p class="task-desc">${escapeHtml(card.description)}</p>` : ""}
      <div class="task-meta">
        ${
          assignee
            ? `<span class="meta-chip"><span class="avatar" style="width:20px;height:20px;font-size:10px">${escapeHtml(initials(assignee))}</span><span>${escapeHtml(assignee.username)}</span></span>`
            : ""
        }
        ${
          card.deadline
            ? `<span class="meta-chip">${icon("calendar")}<span>${formatDate(card.deadline)}</span></span>`
            : ""
        }
      </div>
    </article>
  `;
}

function renderMembers() {
  const canManage = canManageMembers();
  const showAuditButton = isOwner();

  const auditHtml = state.auditLogs ? `
  <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #2a2a4a;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
      <h3 style="color: #e94560; font-size: 14px;">📋 История изменений</h3>
      <button class="ghost-btn" data-action="close-audit" style="font-size: 12px; padding: 4px 8px;">✕ Закрыть</button>
    </div>
    ${renderAuditLogs()}
  </div>
` : '';

  return `
    <aside class="members-panel">
      <div class="panel-head">
        <h2>${icon("users")} Участники</h2>
        <span class="count-pill">${state.board.members.length}</span>
      </div>
      ${
        canManage
          ? `<form class="form-grid" data-form="member">
              <label class="field">
                <span>Email</span>
                <input class="input" name="email" type="email" placeholder="name@example.com" required />
              </label>
              <button class="ghost-btn" type="submit">${icon("plus")} Добавить</button>
            </form>`
          : ""
      }
      ${
  showAuditButton && !state.auditLogs ? `
    <button class="ghost-btn" data-action="show-audit" style="margin-top: 12px; width: 100%;">
      ${icon("clock")} История изменений
    </button>
  ` : ''
}
      <div class="member-list">
        ${state.board.members.map((member) => renderMember(member, canManage)).join("")}
      </div>
    ${auditHtml}
    </aside>
  `;
}

function renderAuditLogs() {
  if (!state.auditLogs || state.auditLogs.logs.length === 0) {
    return `
      <div class="empty-state-inner">
        <p style="color: #888;">История изменений пуста</p>
      </div>
    `;
  }

  const logsHtml = state.auditLogs.logs.map((log, index) => {
    const actionText = formatAuditMessage(log);
    return `
      <div class="audit-log-item" style="
        padding: 12px;
        border-bottom: 1px solid #2a2a4a;
        display: flex;
        gap: 12px;
        align-items: flex-start;
      ">
        <span style="
          background: #2a2a5e;
          border-radius: 50%;
          width: 28px;
          height: 28px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: bold;
          flex-shrink: 0;
          color: #aaa;
        ">${index + 1}</span>
        <div style="flex: 1;">
          <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
            <strong style="color: #e94560;">${escapeHtml(log.user || "Пользователь")}</strong>
            <span style="color: #666; font-size: 12px;">${escapeHtml(formatDateTime(log.created_at))}</span>
          </div>
          <div style="margin-top: 4px; color: #ddd; font-size: 14px;">${actionText}</div>
        </div>
      </div>
    `;
  }).join("");

  return `
    <div class="audit-logs-list" style="max-height: 400px; overflow-y: auto;">
      ${logsHtml}
    </div>
  `;
}

function formatAuditMessage(log) {
  let oldValues = null;
  let newValues = null;
  try {
    oldValues = typeof log.old_values === 'string' ? JSON.parse(log.old_values) : log.old_values;
  } catch {}
  try {
    newValues = typeof log.new_values === 'string' ? JSON.parse(log.new_values) : log.new_values;
  } catch {}

  const actionMap = {
    'create': 'создал',
    'update': 'обновил',
    'delete': 'удалил',
    'move': 'переместил',
    'login': 'вошёл в систему',
    'register': 'зарегистрировался',
    'add_member': 'добавил участника',
    'remove_member': 'удалил участника',
    'change_role': 'изменил роль',
    'assign': 'назначил исполнителя',
  };

  const actionVerb = actionMap[log.action] || log.action;


  if (log.entity_type === 'card') {

    const cardTitle = newValues?.card_name || newValues?.title || oldValues?.card_name || oldValues?.title || `#${log.entity_id}`;
    const oldColumn = oldValues?.column_name || '';
    const newColumn = newValues?.column_name || '';

    if (log.action === 'move') {
      if (oldColumn && newColumn) {
        return `${actionVerb} карточку "${cardTitle}" из колонки "${oldColumn}" в колонку "${newColumn}"`;
      } else if (newColumn) {
        return `${actionVerb} карточку "${cardTitle}" в колонку "${newColumn}"`;
      } else if (oldColumn) {
        return `${actionVerb} карточку "${cardTitle}" из колонки "${oldColumn}"`;
      }
      return `${actionVerb} карточку "${cardTitle}"`;
    }

    if (log.action === 'update') {
      const changes = [];
      const oldTitle = oldValues?.title || '';
      const newTitle = newValues?.title || '';
      if (oldTitle && newTitle && oldTitle !== newTitle) {
        changes.push(`название "${oldTitle}" → "${newTitle}"`);
      }
      const oldAssignee = oldValues?.assignee_name || oldValues?.assignee_id || '';
      const newAssignee = newValues?.assignee_name || newValues?.assignee_id || '';
      if (oldAssignee && newAssignee && oldAssignee !== newAssignee) {
        changes.push(`исполнитель "${oldAssignee}" → "${newAssignee}"`);
      }
      if (oldValues?.priority && newValues?.priority && oldValues.priority !== newValues.priority) {
        const priorityMap = { 'low': 'Низкий', 'medium': 'Средний', 'high': 'Высокий', 'critical': 'Критический' };
        changes.push(`приоритет "${priorityMap[oldValues.priority] || oldValues.priority}" → "${priorityMap[newValues.priority] || newValues.priority}"`);
      }
      if (changes.length === 0) {
        return `${actionVerb} карточку "${cardTitle}" (без изменений)`;
      }
      return `${actionVerb} карточку "${cardTitle}": ${changes.join(', ')}`;
    }

    return `${actionVerb} карточку "${cardTitle}"`;
  }

  if (log.entity_type === 'board') {
    const name = newValues?.title || oldValues?.title || `#${log.entity_id}`;
    return `${actionVerb} доску "${name}"`;
  }

  if (log.entity_type === 'column') {
    const name = newValues?.title || oldValues?.title || `#${log.entity_id}`;
    const boardName = newValues?.board_name || oldValues?.board_name || '';
    if (boardName) {
      return `${actionVerb} колонку "${name}" в доске "${boardName}"`;
    }
    return `${actionVerb} колонку "${name}"`;
  }

  if (log.entity_type === 'comment') {
    const content = newValues?.content || oldValues?.content || '';
    const snippet = content.length > 40 ? content.slice(0, 40) + '…' : content;
    const cardTitle = newValues?.card_name || oldValues?.card_name || '';
    if (cardTitle) {
      return `${actionVerb} комментарий "${snippet}" в карточке "${cardTitle}"`;
    }
    return `${actionVerb} комментарий "${snippet}"`;
  }

    if (log.entity_type === 'board_member') {
      const boardName = newValues?.board_name || oldValues?.board_name || '';
      const email = newValues?.email || oldValues?.email || '';
      const userName = newValues?.user_name || oldValues?.user_name || '';
      const user = userName || email || `#${log.entity_id}`;

      if (log.action === 'add_member') {
        const boardPart = boardName ? ` в доску "${boardName}"` : '';
        return `добавил участника ${user}${boardPart}`;
      }
      if (log.action === 'remove_member') {
        const boardPart = boardName ? ` из доски "${boardName}"` : '';
        return `удалил участника ${user}${boardPart}`;
      }
      if (log.action === 'change_role') {
        const fromRole = oldValues?.role || 'неизвестно';
        const toRole = newValues?.role || 'неизвестно';
        const boardPart = boardName ? ` в доске "${boardName}"` : '';
        return `изменил роль участника ${user} с "${fromRole}" на "${toRole}"${boardPart}`;
      }
    }

  // --- Вход / регистрация ---
  if (log.entity_type === 'user') {
    if (log.action === 'login') {
      const email = newValues?.email || '';
      const username = newValues?.user_name || '';
      return `вошёл в систему ${username || email}`;
    }
    if (log.action === 'register') {
      const username = newValues?.username || '';
      return `зарегистрировался как ${username}`;
    }
  }

  // --- Если ничего не подошло ---
  return `${actionVerb} ${log.entity_type} #${log.entity_id}`;
}

function renderMember(member, canManage) {
  const owner = member.role === "owner";
  return `
    <div class="member-row">
      <span class="avatar">${escapeHtml(initials(member))}</span>
      <div class="member-main">
        <strong>${escapeHtml(member.username)}</strong>
        <span>${escapeHtml(member.email)}</span>
      </div>
      <div class="member-actions">
        ${
          canManage && !owner
            ? `<select class="select" data-action="change-role" data-user-id="${member.user_id}">
                <option value="reader" ${member.role === "reader" ? "selected" : ""}>Читатель</option>
                <option value="member" ${member.role === "member" ? "selected" : ""}>Участник</option>
              </select>
              <button class="icon-btn danger" data-action="remove-member" data-user-id="${member.user_id}" title="Удалить участника" aria-label="Удалить участника">${icon("trash")}</button>`
            : `<span class="role-pill">${roleLabel[member.role] || member.role}</span>`
        }
      </div>
    </div>
  `;
}

function renderModal() {
  const { type, payload = {} } = state.modal;
  const titles = {
    board: payload.id ? "Доска" : "Новая доска",
    column: payload.id ? "Колонка" : "Новая колонка",
    card: payload.id ? "Карточка" : "Новая карточка",
  };

  return `
    <div class="modal-backdrop" data-action="close-modal">
      <section class="modal" role="dialog" aria-modal="true" aria-label="${titles[type]}">
        <div class="modal-head">
          <h2>${titles[type]}</h2>
          <button class="icon-btn" data-action="close-modal" aria-label="Закрыть">${icon("close")}</button>
        </div>
        <div class="modal-body">
          ${type === "board" ? renderBoardForm(payload) : ""}
          ${type === "column" ? renderColumnForm(payload) : ""}
          ${type === "card" ? renderCardForm(payload) : ""}
        </div>
      </section>
    </div>
  `;
}

function renderBoardForm(board) {
  return `
    <form class="form-grid" data-form="board">
      <label class="field">
        <span>Название</span>
        <input class="input" name="title" maxlength="100" required value="${escapeHtml(board.title || "")}" autofocus />
      </label>
      <div class="modal-actions">
        <button class="ghost-btn" type="button" data-action="close-modal">Отмена</button>
        <button class="primary-btn" type="submit">${icon("check")} Сохранить</button>
      </div>
    </form>
  `;
}

function renderColumnForm(column) {
  return `
    <form class="form-grid" data-form="column">
      <label class="field">
        <span>Название</span>
        <input class="input" name="title" maxlength="100" required value="${escapeHtml(column.title || "")}" autofocus />
      </label>
      <div class="modal-actions">
        <button class="ghost-btn" type="button" data-action="close-modal">Отмена</button>
        <button class="primary-btn" type="submit">${icon("check")} Сохранить</button>
      </div>
    </form>
  `;
}

function renderCardForm(card) {
  const comments = state.commentsByCard[card.id] || [];
  const editable = card.id ? canEditCard(card) : canCreateCards();
  const disabled = editable ? "" : "disabled";
  return `
    <form class="form-grid" ${editable ? `data-form="card"` : ""}>
      <label class="field">
        <span>Заголовок</span>
        <input class="input" name="title" maxlength="200" required value="${escapeHtml(card.title || "")}" ${editable ? "autofocus" : ""} ${disabled} />
      </label>
      <label class="field">
        <span>Описание</span>
        <textarea class="textarea" name="description" ${disabled}>${escapeHtml(card.description || "")}</textarea>
      </label>
      <div class="form-grid card-fields">
        <label class="field">
          <span>Приоритет</span>
          <select class="select" name="priority" ${disabled}>
            <option value="low" ${card.priority === "low" ? "selected" : ""}>Низкий</option>
            <option value="medium" ${!card.priority || card.priority === "medium" ? "selected" : ""}>Средний</option>
            <option value="high" ${card.priority === "high" ? "selected" : ""}>Высокий</option>
          </select>
        </label>
        <label class="field">
          <span>Исполнитель</span>
          <select class="select" name="assignee_id" ${disabled}>
            <option value="">Без исполнителя</option>
            ${state.board.members
              .map(
                (member) =>
                  `<option value="${member.user_id}" ${member.user_id === card.assignee_id ? "selected" : ""}>${escapeHtml(member.username)}</option>`,
              )
              .join("")}
          </select>
        </label>
        <label class="field">
          <span>Дедлайн</span>
          <input class="input" name="deadline" type="date" value="${escapeHtml(card.deadline || "")}" ${disabled} />
        </label>
      </div>
      <div class="modal-actions">
        ${card.id && canDeleteCard(card) ? `<button class="danger-btn" type="button" data-action="delete-card" data-card-id="${card.id}">${icon("trash")} Удалить</button>` : ""}
        <button class="ghost-btn" type="button" data-action="close-modal">Отмена</button>
        ${editable ? `<button class="primary-btn" type="submit">${icon("check")} Сохранить</button>` : ""}
      </div>
    </form>
    ${
      card.id
        ? `<section class="comments">
            <div class="panel-head">
              <h2>${icon("message")} Комментарии</h2>
              <span class="count-pill">${comments.length}</span>
            </div>
            ${
              canAddComment()
                ? `<form class="form-grid" data-form="comment" data-card-id="${card.id}">
                    <textarea class="textarea" name="content" required placeholder="Комментарий"></textarea>
                    <button class="ghost-btn" type="submit">${icon("plus")} Добавить комментарий</button>
                  </form>`
                : ""
            }
            ${comments.map(renderComment).join("") || `<p class="task-desc">Пока пусто</p>`}
          </section>`
        : ""
    }
  `;
}

function renderComment(comment) {
  const canEdit = canEditComment(comment);
  const canDelete = canDeleteComment(comment);
  return `
    <article class="comment">
      <span class="avatar">${escapeHtml(initials(comment.user))}</span>
      <div>
        <strong>${escapeHtml(comment.user?.username || "Участник")}</strong>
        <p>${escapeHtml(comment.content)}</p>
      </div>
      <div class="member-actions">
        ${canEdit ? `<button class="icon-btn" data-action="edit-comment" data-comment-id="${comment.id}" title="Редактировать" aria-label="Редактировать">${icon("edit")}</button>` : ""}
        ${canDelete ? `<button class="icon-btn danger" data-action="delete-comment" data-comment-id="${comment.id}" title="Удалить" aria-label="Удалить">${icon("trash")}</button>` : ""}
      </div>
    </article>
  `;
}

function findMemberUser(userId) {
  if (!userId || !state.board) return null;
  return state.board.members.find((member) => member.user_id === userId);
}

function findColumn(columnId) {
  return state.columns.find((column) => column.id === Number(columnId));
}

function findCard(cardId) {
  for (const [columnId, cards] of Object.entries(state.cardsByColumn)) {
    const card = cards.find((item) => item.id === Number(cardId));
    if (card) return { card, columnId: Number(columnId) };
  }
  return null;
}

function openModal(type, payload = {}) {
  state.modal = { type, payload };
  render();
}

function closeModal() {
  state.modal = null;
  render();
}

function clearRemovalAnimations() {
  document.querySelectorAll(".is-shattering").forEach((node) => {
    node.classList.remove("is-shattering");
    node.removeAttribute("aria-hidden");
  });
}

function animateRemoval(targets) {
  const nodes = [...new Set(targets.filter(Boolean))];
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!nodes.length || reduceMotion) return Promise.resolve();

  nodes.forEach((node) => {
    node.classList.add("is-shattering");
    node.setAttribute("aria-hidden", "true");
  });

  return new Promise((resolve) => {
    window.setTimeout(resolve, 460);
  });
}

function closeServiceDialog(dialog) {
  dialog.classList.add("is-closing");
  window.setTimeout(() => dialog.remove(), 140);
}

function confirmAction({ title, message, confirmText = "Удалить" }) {
  return new Promise((resolve) => {
    const dialog = document.createElement("div");
    dialog.className = "service-dialog-backdrop";
    dialog.innerHTML = `
      <section class="service-dialog" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}">
        <div class="service-dialog-head">
          <h2>${escapeHtml(title)}</h2>
          <button class="icon-btn" type="button" data-dialog-action="cancel" aria-label="Закрыть">${icon("close")}</button>
        </div>
        <div class="service-dialog-body">
          <p>${escapeHtml(message)}</p>
          <div class="modal-actions">
            <button class="ghost-btn" type="button" data-dialog-action="cancel">Отмена</button>
            <button class="danger-btn" type="button" data-dialog-action="confirm">${icon("trash")} ${escapeHtml(confirmText)}</button>
          </div>
        </div>
      </section>
    `;

    const finish = (value) => {
      document.removeEventListener("keydown", onKeydown);
      closeServiceDialog(dialog);
      resolve(value);
    };
    const onKeydown = (event) => {
      if (event.key === "Escape") finish(false);
    };

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) finish(false);
      const action = event.target.closest("[data-dialog-action]")?.dataset.dialogAction;
      if (action === "cancel") finish(false);
      if (action === "confirm") finish(true);
    });

    document.addEventListener("keydown", onKeydown);
    document.body.appendChild(dialog);
    dialog.querySelector("[data-dialog-action='cancel']")?.focus();
  });
}

function promptAction({ title, label, value = "", confirmText = "Сохранить" }) {
  return new Promise((resolve) => {
    const dialog = document.createElement("div");
    dialog.className = "service-dialog-backdrop";
    dialog.innerHTML = `
      <section class="service-dialog" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}">
        <div class="service-dialog-head">
          <h2>${escapeHtml(title)}</h2>
          <button class="icon-btn" type="button" data-dialog-action="cancel" aria-label="Закрыть">${icon("close")}</button>
        </div>
        <form class="service-dialog-body" data-dialog-form>
          <label class="field">
            <span>${escapeHtml(label)}</span>
            <textarea class="textarea" name="value" required>${escapeHtml(value)}</textarea>
          </label>
          <div class="modal-actions">
            <button class="ghost-btn" type="button" data-dialog-action="cancel">Отмена</button>
            <button class="primary-btn" type="submit">${icon("check")} ${escapeHtml(confirmText)}</button>
          </div>
        </form>
      </section>
    `;

    const finish = (value) => {
      document.removeEventListener("keydown", onKeydown);
      closeServiceDialog(dialog);
      resolve(value);
    };
    const onKeydown = (event) => {
      if (event.key === "Escape") finish(null);
    };

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) finish(null);
      const action = event.target.closest("[data-dialog-action]")?.dataset.dialogAction;
      if (action === "cancel") finish(null);
    });
    dialog.querySelector("[data-dialog-form]").addEventListener("submit", (event) => {
      event.preventDefault();
      finish(new FormData(event.currentTarget).get("value"));
    });

    document.addEventListener("keydown", onKeydown);
    document.body.appendChild(dialog);
    dialog.querySelector("textarea")?.focus();
  });
}

async function openCard(cardId, columnId) {
  if (!cardId && !guardPermission(canCreateCards(), "Читатель не может создавать карточки")) {
    return;
  }
  const found = cardId ? findCard(cardId) : null;
  const payload = found
    ? { ...found.card, columnId: found.columnId }
    : { columnId: Number(columnId), priority: "medium" };
  state.modal = { type: "card", payload };
  render();

  if (payload.id) {
    try {
      state.commentsByCard[payload.id] = await api(`/api/comments/cards/${payload.id}/comments`);
      render();
    } catch (error) {
      toast(error.message, "error");
    }
  }
}

async function createDefaultColumns(boardId) {
  const names = ["Бэклог", "В работе", "Ревью", "Готово"];
  await Promise.all(
    names.map((title, position) =>
      api(`/api/columns/boards/${boardId}/columns`, {
        method: "POST",
        body: { title, position },
      }),
    ),
  );
}

function applyLocalMove(cardId, targetColumnId, targetIndex) {
  const found = findCard(cardId);
  if (!found) return;
  const sourceCards = state.cardsByColumn[found.columnId] || [];
  const targetCards = state.cardsByColumn[targetColumnId] || [];
  const sourceIndex = sourceCards.findIndex((card) => card.id === Number(cardId));
  const [card] = sourceCards.splice(sourceIndex, 1);
  const normalizedIndex = Math.max(0, Math.min(targetIndex, targetCards.length));
  card.column_id = targetColumnId;
  targetCards.splice(normalizedIndex, 0, card);
  [sourceCards, targetCards].forEach((cards) => {
    cards.forEach((item, index) => {
      item.position = index;
    });
  });
}

function placeDropIndicator(zone, event) {
  const cards = [...zone.querySelectorAll(".task-card:not(.is-dragging)")];
  let index = cards.length;
  for (let i = 0; i < cards.length; i += 1) {
    const rect = cards[i].getBoundingClientRect();
    if (event.clientY < rect.top + rect.height / 2) {
      index = i;
      break;
    }
  }
  zone.classList.add("is-over");
  zone.insertBefore(dropIndicator, cards[index] || null);
  state.drop = { columnId: Number(zone.dataset.columnId), index };
}

function clearDropState() {
  document.querySelectorAll(".card-list.is-over").forEach((node) => node.classList.remove("is-over"));
  dropIndicator.remove();
  state.drop = null;
}

app.addEventListener("submit", async (event) => {
  const form = event.target.closest("form[data-form]");
  if (!form) return;
  event.preventDefault();
  const formData = new FormData(form);
  const type = form.dataset.form;

  try {
    if (type === "auth") {
      state.apiBase = "";
      localStorage.removeItem("kju.apiBase");
      const payload = {
        email: formData.get("email"),
        password: formData.get("password"),
      };
      if (state.authMode === "register") payload.username = formData.get("username");
      const result = await api(`/api/auth/${state.authMode === "login" ? "login" : "register"}`, {
        method: "POST",
        body: payload,
      });
      state.token = result.access_token;
      state.user = result.user;
      localStorage.setItem("kju.token", state.token);
      toast("Добро пожаловать");
      await bootstrap();
      return;
    }

    if (type === "board") {
      if (
        state.modal.payload.id &&
        !guardPermission(canManageBoard(), "Только владелец может менять доску")
      ) {
        return;
      }
      const title = formData.get("title");
      if (state.modal.payload.id) {
        await api(`/api/boards/${state.modal.payload.id}`, {
          method: "PUT",
          body: { title, version: state.modal.payload.version },
        });
      } else {
        const board = await api("/api/boards/", { method: "POST", body: { title } });
        await createDefaultColumns(board.id);
        state.boardId = board.id;
      }
      closeModal();
      await loadBoards(false);
      await selectBoard(state.boardId || state.boards[0]?.id);
      toast("Доска сохранена");
      return;
    }

    if (type === "column") {
      if (!guardPermission(canManageColumns(), "Только владелец может менять колонки")) {
        return;
      }
      const title = formData.get("title");
      if (state.modal.payload.id) {
        await api(`/api/columns/${state.modal.payload.id}`, {
          method: "PUT",
          body: { title, version: state.modal.payload.version },
        });
      } else {
        await api(`/api/columns/boards/${state.boardId}/columns`, {
          method: "POST",
          body: { title, position: state.columns.length },
        });
      }
      closeModal();
      await selectBoard(state.boardId);
      toast("Колонка сохранена");
      return;
    }

    if (type === "card") {
      const allowed = state.modal.payload.id
        ? canEditCard(state.modal.payload)
        : canCreateCards();
      if (!guardPermission(allowed, "Недостаточно прав для изменения карточки")) {
        return;
      }
      const payload = {
        title: formData.get("title"),
        description: formData.get("description") || null,
        assignee_id: formData.get("assignee_id") ? Number(formData.get("assignee_id")) : null,
        deadline: formData.get("deadline") || null,
        priority: formData.get("priority") || "medium",
      };
      if (state.modal.payload.id) {
        await api(`/api/cards/${state.modal.payload.id}`, {
          method: "PUT",
          body: { ...payload, version: state.modal.payload.version },
        });
      } else {
        await api(`/api/cards/columns/${state.modal.payload.columnId}/cards`, {
          method: "POST",
          body: payload,
        });
      }
      closeModal();
      await selectBoard(state.boardId);
      toast("Карточка сохранена");
      return;
    }

    if (type === "member") {
      if (!guardPermission(canManageMembers(), "Только владелец может менять участников")) {
        return;
      }
      await api(`/api/boards/${state.boardId}/members`, {
        method: "POST",
        body: { email: formData.get("email") },
      });
      await selectBoard(state.boardId);
      toast("Участник добавлен");
      return;
    }

    if (type === "comment") {
      if (!guardPermission(canAddComment(), "Нет доступа к комментариям этой доски")) {
        return;
      }
      const cardId = Number(form.dataset.cardId);
      await api(`/api/comments/cards/${cardId}/comments`, {
        method: "POST",
        body: { content: formData.get("content") },
      });
      state.commentsByCard[cardId] = await api(`/api/comments/cards/${cardId}/comments`);
      render();
      toast("Комментарий добавлен");
    }
  } catch (error) {
    toast(error.message, "error");
  }
});

app.addEventListener("click", async (event) => {
  const actionNode = event.target.closest("[data-action]");
  if (!actionNode) {
    const card = event.target.closest(".task-card");
    if (card) openCard(Number(card.dataset.cardId), Number(card.dataset.columnId));
    return;
  }

  const action = actionNode.dataset.action;
  if (action === "close-modal") {
    if (actionNode.classList.contains("modal-backdrop") && event.target !== actionNode) return;
    closeModal();
    return;
  }

  try {
    if (action === "auth-mode") {
      state.authMode = actionNode.dataset.mode;
      render();
    }
    if (action === "show-audit") {
      try {
        const response = await api(`/api/audit/board/${state.boardId}?limit=20`);
        state.auditLogs = response;
        render();
      } catch (error) {
        toast(error.message, "error");
      }
    }

    if (action === "close-audit") {
      state.auditLogs = null;
      render();
    }
    if (action === "logout") logout();
    if (action === "select-board") {
      setLoading(true);
      await selectBoard(actionNode.dataset.boardId);
      setLoading(false);
    }
    if (action === "new-board") openModal("board", {});
    if (action === "edit-board") {
      if (!guardPermission(canManageBoard(), "Только владелец может менять доску")) return;
      openModal("board", state.board);
    }
    if (action === "delete-board") {
      if (!guardPermission(canManageBoard(), "Только владелец может удалить доску")) return;
      const confirmed = await confirmAction({
        title: "Удаление доски",
        message: `Доска "${state.board.title}" будет удалена вместе с колонками и карточками.`,
      });
      if (!confirmed) return;
      await animateRemoval([
        document.querySelector(".board-stage"),
        document.querySelector(`.board-link[data-board-id="${state.boardId}"]`),
      ]);
      await api(`/api/boards/${state.boardId}`, { method: "DELETE" });
      state.boardId = null;
      await loadBoards(false);
      const next = state.boards[0];
      state.board = null;
      if (next) await selectBoard(next.id, false);
      render();
      toast("Доска удалена");
    }
    if (action === "new-column") {
      if (!guardPermission(canManageColumns(), "Только владелец может создавать колонки")) return;
      openModal("column", {});
    }
    if (action === "edit-column") {
      if (!guardPermission(canManageColumns(), "Только владелец может менять колонки")) return;
      openModal("column", findColumn(actionNode.dataset.columnId));
    }
    if (action === "delete-column") {
      if (!guardPermission(canManageColumns(), "Только владелец может удалить колонку")) return;
      const column = findColumn(actionNode.dataset.columnId);
      const confirmed = await confirmAction({
        title: "Удаление колонки",
        message: `Колонка "${column.title}" и все карточки внутри неё будут удалены.`,
      });
      if (!confirmed) return;
      await animateRemoval([actionNode.closest(".column")]);
      await api(`/api/columns/${column.id}`, { method: "DELETE" });
      await selectBoard(state.boardId);
      toast("Колонка удалена");
    }
    if (action === "new-card") {
      if (!guardPermission(canCreateCards(), "Читатель не может создавать карточки")) return;
      openCard(null, actionNode.dataset.columnId);
    }
    if (action === "new-card-any") {
      if (!guardPermission(canCreateCards(), "Читатель не может создавать карточки")) return;
      const column = state.columns[0];
      if (!column && !guardPermission(canManageColumns(), "Сначала владелец должен создать колонку")) {
        return;
      }
      if (!column) openModal("column", {});
      else openCard(null, column.id);
    }
    if (action === "delete-card") {
      const cardId = actionNode.dataset.cardId;
      const found = findCard(cardId) || { card: state.modal?.payload };
      if (!guardPermission(canDeleteCard(found.card), "Недостаточно прав для удаления карточки")) {
        return;
      }
      const confirmed = await confirmAction({
        title: "Удаление карточки",
        message: "Карточка и её комментарии будут удалены.",
      });
      if (!confirmed) return;
      await animateRemoval([
        document.querySelector(`.task-card[data-card-id="${cardId}"]`),
        actionNode.closest(".modal"),
      ]);
      await api(`/api/cards/${cardId}`, { method: "DELETE" });
      closeModal();
      await selectBoard(state.boardId);
      toast("Карточка удалена");
    }
    if (action === "remove-member") {
      if (!guardPermission(canManageMembers(), "Только владелец может менять участников")) return;
      const confirmed = await confirmAction({
        title: "Удаление участника",
        message: "Участник потеряет доступ к этой доске.",
        confirmText: "Удалить",
      });
      if (!confirmed) return;
      await animateRemoval([actionNode.closest(".member-row")]);
      await api(`/api/boards/${state.boardId}/members/${actionNode.dataset.userId}`, {
        method: "DELETE",
      });
      await selectBoard(state.boardId);
      toast("Участник удалён");
    }
    if (action === "edit-comment") {
      const commentId = Number(actionNode.dataset.commentId);
      const cardId = state.modal.payload.id;
      const comment = (state.commentsByCard[cardId] || []).find((item) => item.id === commentId);
      if (!guardPermission(canEditComment(comment), "Можно редактировать только свой комментарий")) {
        return;
      }
      const content = await promptAction({
        title: "Редактирование комментария",
        label: "Комментарий",
        value: comment?.content || "",
      });
      if (content === null) return;
      if (!String(content).trim()) {
        toast("Комментарий не может быть пустым", "error");
        return;
      }
      await api(`/api/comments/${commentId}`, {
        method: "PUT",
        body: { content: String(content).trim(), version: comment.version },
      });
      state.commentsByCard[cardId] = await api(`/api/comments/cards/${cardId}/comments`);
      render();
      toast("Комментарий обновлён");
    }
    if (action === "delete-comment") {
      const cardId = state.modal.payload.id;
      const comment = (state.commentsByCard[cardId] || []).find(
        (item) => item.id === Number(actionNode.dataset.commentId),
      );
      if (!guardPermission(canDeleteComment(comment), "Недостаточно прав для удаления комментария")) {
        return;
      }
      const confirmed = await confirmAction({
        title: "Удаление комментария",
        message: "Комментарий будет удалён из карточки.",
      });
      if (!confirmed) return;
      await animateRemoval([actionNode.closest(".comment")]);
      await api(`/api/comments/${actionNode.dataset.commentId}`, { method: "DELETE" });
      state.commentsByCard[cardId] = await api(`/api/comments/cards/${cardId}/comments`);
      render();
      toast("Комментарий удалён");
    }
  } catch (error) {
    clearRemovalAnimations();
    setLoading(false);
    toast(error.message, "error");
  }
});

app.addEventListener("input", (event) => {
  if (event.target.matches("[data-field='search']")) {
    state.search = event.target.value;
    render();
  }
});

app.addEventListener("change", async (event) => {
  const select = event.target.closest("[data-action='change-role']");
  if (!select) return;
  if (!guardPermission(canManageMembers(), "Только владелец может менять роли")) {
    render();
    return;
  }
  try {
    await api(`/api/boards/${state.boardId}/members/${select.dataset.userId}/role`, {
      method: "PATCH",
      body: { role: select.value },
    });
    await selectBoard(state.boardId);
    toast("Роль обновлена");
  } catch (error) {
    toast(error.message, "error");
  }
});

app.addEventListener("dragstart", (event) => {
  const card = event.target.closest(".task-card");
  if (!card) return;
  const found = findCard(card.dataset.cardId);
  if (!found || !canMoveCard(found.card)) {
    event.preventDefault();
    state.drag = null;
    return;
  }
  state.drag = {
    cardId: Number(card.dataset.cardId),
    fromColumnId: Number(card.dataset.columnId),
  };
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", card.dataset.cardId);
  requestAnimationFrame(() => card.classList.add("is-dragging"));
});

app.addEventListener("dragover", (event) => {
  const zone = event.target.closest("[data-drop-zone]");
  if (!zone || !state.drag) return;
  event.preventDefault();
  placeDropIndicator(zone, event);
});

app.addEventListener("dragleave", (event) => {
  const zone = event.target.closest("[data-drop-zone]");
  if (!zone || zone.contains(event.relatedTarget)) return;
  zone.classList.remove("is-over");
});

app.addEventListener("drop", async (event) => {
  const zone = event.target.closest("[data-drop-zone]");
  if (!zone || !state.drag || !state.drop) return;
  event.preventDefault();
  const { cardId } = state.drag;
  const { columnId, index } = state.drop;
  clearDropState();

  try {
    const found = findCard(cardId);
    if (!found || !guardPermission(canMoveCard(found.card), "Недостаточно прав для перемещения карточки")) {
      await selectBoard(state.boardId);
      return;
    }
    applyLocalMove(cardId, columnId, index);
    render();
    await api(`/api/cards/${cardId}/move`, {
      method: "PATCH",
      body: { target_column_id: columnId, position: index },
    });
    await selectBoard(state.boardId);
    toast("Карточка перемещена");
  } catch (error) {
    toast(error.message, "error");
    await selectBoard(state.boardId);
  } finally {
    state.drag = null;
  }
});

app.addEventListener("dragend", () => {
  state.drag = null;
  document.querySelectorAll(".task-card.is-dragging").forEach((node) => {
    node.classList.remove("is-dragging");
  });
  clearDropState();
});

bootstrap();

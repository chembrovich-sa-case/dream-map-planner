/**
 * API-клиент сервиса «Горизонт»
 * Связывает интерфейс фронтенда с бэкендом на FastAPI (http://127.0.0.1:8000/api).
 * Предоставляет методы для работы со сферами, целями, чек-листами и курсами валют.
 * Включает мягкий фолбэк на локальное хранилище (MockAPI), если бэкенд не запущен.
 */

(function(window) {
  'use strict';

  const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/api';
  const TOKEN_STORAGE_KEY = 'horizont_auth_token';
  const USER_STORAGE_KEY = 'horizont_current_user';

  class HorizontApiClient {
    constructor() {
      this.baseUrl = window.API_BASE_URL || localStorage.getItem('horizont_api_url') || DEFAULT_API_BASE_URL;
      this.isOnline = null; // null = неизвестно, true = FastAPI доступен, false = fallback
      this.authToken = localStorage.getItem(TOKEN_STORAGE_KEY) || null;
      this.hasShownOfflineNotice = false;
      this.cachedSpheres = [];
    }

    /**
     * Проверка доступности FastAPI бэкенда (Health Check)
     */
    async checkHealth() {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1500);

        const resp = await fetch(`${this.baseUrl}/health`, {
          method: 'GET',
          headers: { 'Accept': 'application/json' },
          signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (resp.ok) {
          const data = await resp.json();
          this.isOnline = true;
          console.log(`🟢 [Horizont API] FastAPI бэкенд успешно подключен (${this.baseUrl}):`, data);
          return true;
        }
      } catch (err) {
        // Ошибка подключения (сервер выключен)
      }

      this.isOnline = false;
      if (!this.hasShownOfflineNotice) {
        this.hasShownOfflineNotice = true;
        console.info(
          `ℹ️ [Horizont API] Сервер FastAPI (${this.baseUrl}) недоступен.\n` +
          `Автоматически активирован автономный локальный режим с кэшированием в localStorage.`
        );
      }
      return false;
    }

    /**
     * Базовый HTTP-запрос к FastAPI бэкенду с поддержкой RBAC авторизации
     */
    async request(endpoint, options = {}) {
      if (this.isOnline === null) {
        await this.checkHealth();
      }

      if (!this.isOnline) {
        return null; // Сигнал для использования MockAPI
      }

      const url = `${this.baseUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
      const headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...(options.headers || {})
      };

      // Передаем заголовок авторизации Bearer (для прав администратора CMS)
      const token = this.authToken || (this.getCurrentUser() ? this.getCurrentUser().email : null);
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);

        const resp = await fetch(url, {
          ...options,
          headers,
          signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (resp.status === 204) {
          return { success: true };
        }

        if (!resp.ok) {
          const errData = await resp.json().catch(() => ({}));
          throw new Error(errData.detail || `Ошибка сервера (${resp.status}): ${resp.statusText}`);
        }

        return await resp.json();
      } catch (err) {
        console.warn(`⚠️ [Horizont API] Сбой запроса к ${endpoint}:`, err.message);
        if (err.name === 'AbortError' || err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
          this.isOnline = false;
        }
        return null;
      }
    }

    // ============================================================================
    // 1. АВТОРИЗАЦИЯ И ПОЛЬЗОВАТЕЛИ (RBAC)
    // ============================================================================

    isAuthenticated() {
      const session = localStorage.getItem('horizont_auth_session');
      const token = localStorage.getItem(TOKEN_STORAGE_KEY) || this.authToken;
      const user = this.getCurrentUser();
      return Boolean(session === 'true' && token && user && user.role !== 'guest');
    }

    getCurrentUser() {
      if (window.MockAPI) {
        return window.MockAPI.getCurrentUser();
      }
      try {
        const raw = localStorage.getItem(USER_STORAGE_KEY);
        if (raw) {
          const u = JSON.parse(raw);
          if (u && u.role && u.role !== 'guest') return u;
        }
      } catch (e) {
        console.warn("Ошибка чтения пользователя:", e);
      }
      return null;
    }

    async login(usernameOrEmail, password = "admin") {
      let identifier = (usernameOrEmail || "").trim().toLowerCase();
      if (identifier === 'admin') identifier = 'admin@horizon.app';
      if (identifier === 'user') identifier = 'user@horizon.app';

      const data = await this.request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: identifier, username: usernameOrEmail, password })
      });

      if (data && data.user) {
        this.authToken = data.access_token || identifier;
        localStorage.setItem(TOKEN_STORAGE_KEY, this.authToken);
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user));
        localStorage.setItem('horizont_auth_session', 'true');
        return {
          token: this.authToken,
          user: data.user
        };
      }

      // Фолбэк на MockAPI
      if (window.MockAPI) {
        const res = await window.MockAPI.login(usernameOrEmail, password);
        this.authToken = res.token;
        localStorage.setItem(TOKEN_STORAGE_KEY, this.authToken);
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(res.user));
        localStorage.setItem('horizont_auth_session', 'true');
        return res;
      }

      throw new Error(`Пользователь «${usernameOrEmail}» не найден`);
    }

    async logout() {
      this.authToken = null;
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(USER_STORAGE_KEY);
      localStorage.removeItem('horizont_auth_session');
      if (window.MockAPI) {
        return await window.MockAPI.logout();
      }
      return {
        id: "a0000000-0000-0000-0000-000000000002",
        email: "guest@horizon.app",
        name: "Гость",
        role: "guest",
        avatar_url: null
      };
    }

    getDemoUsers() {
      if (window.MockAPI) {
        return window.MockAPI.getDemoUsers();
      }
      return [
        {
          id: "a0000000-0000-0000-0000-000000000000",
          name: "Алексей Администраторов",
          email: "admin@horizon.app",
          role: "admin",
          avatar_url: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=300&q=80"
        },
        {
          id: "a0000000-0000-0000-0000-000000000001",
          name: "Иван Горизонтов",
          email: "user@horizon.app",
          role: "user",
          avatar_url: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80"
        }
      ];
    }

    // ============================================================================
    // 2. СФЕРЫ ЖИЗНИ (КОЛЕСО БАЛАНСА)
    // ============================================================================

    async getSpheres() {
      const data = await this.request('/spheres');
      if (Array.isArray(data)) {
        this.cachedSpheres = data;
        return data.map(s => ({
          ...s,
          target_score: Number(s.target_score) || 10.0,
          current_score: Number(s.current_score) || 0.0
        }));
      }

      if (window.MockAPI) {
        const fallback = await window.MockAPI.getSpheres();
        this.cachedSpheres = fallback;
        return fallback;
      }
      return [];
    }

    async createSphere(sphereData) {
      const data = await this.request('/spheres', {
        method: 'POST',
        body: JSON.stringify(sphereData)
      });
      if (data && data.id) {
        return data;
      }
      if (window.MockAPI) {
        return await window.MockAPI.createSphere(sphereData);
      }
      throw new Error("Не удалось создать сферу");
    }

    async updateSphere(id, updateData) {
      const data = await this.request(`/spheres/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updateData)
      });
      if (data && data.id) {
        return data;
      }
      if (window.MockAPI) {
        return await window.MockAPI.updateSphere(id, updateData);
      }
      throw new Error("Не удалось обновить сферу");
    }

    async deleteSphere(id) {
      const data = await this.request(`/spheres/${id}`, {
        method: 'DELETE'
      });
      if (data) {
        return { success: true };
      }
      if (window.MockAPI) {
        return await window.MockAPI.deleteSphere(id);
      }
      throw new Error("Не удалось удалить сферу");
    }

    // ============================================================================
    // 3. КАРТОЧКИ ЦЕЛЕЙ И ЧЕК-ЛИСТЫ
    // ============================================================================

    async getGoals({ sphereId = null, status = null } = {}) {
      let query = [];
      if (sphereId) query.push(`sphere_id=${encodeURIComponent(sphereId)}`);
      if (status && status !== 'all') query.push(`status=${encodeURIComponent(status)}`);
      const endpoint = `/goals${query.length ? '?' + query.join('&') : ''}`;

      const data = await this.request(endpoint);
      if (Array.isArray(data)) {
        if (!this.cachedSpheres || this.cachedSpheres.length === 0) {
          await this.getSpheres();
        }
        // Обогащаем данными сфер (название, цвет, иконка)
        const spheresMap = {};
        this.cachedSpheres.forEach(s => { spheresMap[s.id] = s; });

        return data.map(g => {
          const s = spheresMap[g.sphere_id];
          return {
            ...g,
            sphere_title: s ? s.title : "Без сферы",
            sphere_color: s ? s.color : "#94a3b8",
            sphere_icon: s ? s.icon : "circle",
            cost_amount: Number(g.cost_amount) || 0,
            progress_percent: Number(g.progress_percent) || 0,
            steps_count: g.steps_count !== undefined ? g.steps_count : (g.steps ? g.steps.length : 0),
            completed_steps_count: g.completed_steps_count !== undefined ? g.completed_steps_count : (g.steps ? g.steps.filter(st => st.is_completed).length : 0),
            steps: g.steps || []
          };
        });
      }

      if (window.MockAPI) {
        return await window.MockAPI.getGoals({ sphereId, status });
      }
      return [];
    }

    async getGoalById(id) {
      const data = await this.request(`/goals/${id}`);
      if (data && data.id) {
        if (!this.cachedSpheres || this.cachedSpheres.length === 0) {
          await this.getSpheres();
        }
        const spheresMap = {};
        this.cachedSpheres.forEach(s => { spheresMap[s.id] = s; });
        const s = data.sphere || spheresMap[data.sphere_id];

        return {
          ...data,
          sphere_title: s ? s.title : "Без сферы",
          sphere_color: s ? s.color : "#94a3b8",
          sphere_icon: s ? s.icon : "circle",
          cost_amount: Number(data.cost_amount) || 0,
          progress_percent: Number(data.progress_percent) || 0,
          steps_count: data.steps ? data.steps.length : 0,
          completed_steps_count: data.steps ? data.steps.filter(st => st.is_completed).length : 0,
          steps: data.steps || []
        };
      }

      if (window.MockAPI) {
        return await window.MockAPI.getGoalById(id);
      }
      return null;
    }

    async createGoal(goalData) {
      const data = await this.request('/goals', {
        method: 'POST',
        body: JSON.stringify(goalData)
      });
      if (data && data.id) {
        return data;
      }
      if (window.MockAPI) {
        return await window.MockAPI.createGoal(goalData);
      }
      throw new Error("Не удалось создать цель");
    }

    async updateGoal(id, updateData) {
      const data = await this.request(`/goals/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updateData)
      });
      if (data && data.id) {
        return data;
      }
      if (window.MockAPI) {
        return await window.MockAPI.updateGoal(id, updateData);
      }
      throw new Error("Не удалось обновить цель");
    }

    async deleteGoal(id) {
      const data = await this.request(`/goals/${id}`, {
        method: 'DELETE'
      });
      if (data) {
        return { success: true, message: "Карточка цели удалена" };
      }
      if (window.MockAPI) {
        return await window.MockAPI.deleteGoal(id);
      }
      throw new Error("Не удалось удалить цель");
    }

    async toggleStep(goalId, stepId, explicitStatus = undefined) {
      const data = await this.request(`/goals/${goalId}/steps/${stepId}/toggle`, {
        method: 'PATCH'
      });

      if (data && data.id) {
        // Подтягиваем обновленную цель для получения нового прогресса
        const updatedGoal = await this.getGoalById(goalId);
        const progress = updatedGoal ? updatedGoal.progress_percent : 0;
        const isCompleted = progress === 100;

        return {
          step: data,
          goal: updatedGoal,
          goal_title: updatedGoal ? updatedGoal.title : "",
          goal_progress_percent: progress,
          goal_status: updatedGoal ? updatedGoal.status : "in_progress",
          sphere_metrics: {
            sphere_id: updatedGoal ? updatedGoal.sphere_id : null,
            sphere_title: updatedGoal ? updatedGoal.sphere_title : "",
            previous_score: 0,
            new_score: 0,
            score_delta: 0
          },
          celebration: isCompleted
        };
      }

      if (window.MockAPI) {
        return await window.MockAPI.toggleStep(goalId, stepId, explicitStatus);
      }
      throw new Error("Не удалось переключить шаг");
    }

    async addStep(goalId, title, weight = 1) {
      const data = await this.request(`/goals/${goalId}/steps`, {
        method: 'POST',
        body: JSON.stringify({ title, weight: parseInt(weight, 10) || 1 })
      });
      if (data && data.id) {
        return data;
      }
      if (window.MockAPI) {
        return await window.MockAPI.addStep(goalId, title, weight);
      }
      throw new Error("Не удалось добавить шаг");
    }

    async deleteStep(goalId, stepId) {
      const data = await this.request(`/goals/${goalId}/steps/${stepId}`, {
        method: 'DELETE'
      });
      if (data) {
        return { success: true };
      }
      if (window.MockAPI) {
        return await window.MockAPI.deleteStep(goalId, stepId);
      }
      throw new Error("Не удалось удалить шаг");
    }

    // ============================================================================
    // 4. КУРСЫ ВАЛЮТ (НБРБ)
    // ============================================================================

    async getNbrbRate(forceRefresh = false) {
      const endpoint = forceRefresh ? '/currency/refresh' : '/currency/rates';
      const method = forceRefresh ? 'POST' : 'GET';
      const data = await this.request(endpoint, { method });

      if (data && data.rate) {
        return {
          rate: Number(data.rate),
          rate_date: data.rate_date,
          scale: data.scale || 1,
          source: data.source || "Официальный курс Нацбанка РБ (FastAPI)"
        };
      }

      if (window.MockAPI) {
        return await window.MockAPI.getNbrbRate(forceRefresh);
      }
      return {
        rate: 2.9543,
        rate_date: new Date().toISOString().split('T')[0],
        scale: 1,
        source: "Резервный курс (оффлайн)"
      };
    }

    // ============================================================================
    // 5. РАДАРНАЯ ДИАГРАММА И CMS ИМПОРТ/ЭКСПОРТ
    // ============================================================================

    async getRadarChartData() {
      if (window.MockAPI) {
        return await window.MockAPI.getRadarChartData();
      }
      const spheres = await this.getSpheres();
      return {
        overall_harmony_index: 0.85,
        evaluated_at: new Date().toISOString(),
        sectors: spheres.map(s => ({
          sphere_id: s.id,
          title: s.title,
          color: s.color,
          icon: s.icon,
          target_score: s.target_score,
          current_score: s.current_score
        }))
      };
    }

    exportJSON() {
      if (window.MockAPI) return window.MockAPI.exportJSON();
      return JSON.stringify({ app: "Horizont", exported_at: new Date().toISOString() });
    }

    importJSON(jsonString) {
      if (window.MockAPI) return window.MockAPI.importJSON(jsonString);
      return { success: true, spheres_count: 0, goals_count: 0 };
    }

    generateSQLInserts() {
      if (window.MockAPI) return window.MockAPI.generateSQLInserts();
      return "-- SQL INSERT generation";
    }

    resetToDefaults() {
      if (window.MockAPI) return window.MockAPI.resetToDefaults();
    }

    // ============================================================================
    // 6. СРЕЗЫ БАЛАНСА И ИСТОРИЧЕСКАЯ АНАЛИТИКА (BALANCE SNAPSHOTS & TRENDS)
    // ============================================================================

    async getSnapshots({ period = null, days = null, limit = 50 } = {}) {
      let query = [];
      if (period) query.push(`period=${encodeURIComponent(period)}`);
      if (days) query.push(`days=${encodeURIComponent(days)}`);
      if (limit) query.push(`limit=${encodeURIComponent(limit)}`);
      const endpoint = `/snapshots${query.length ? '?' + query.join('&') : ''}`;

      const data = await this.request(endpoint);
      if (Array.isArray(data)) {
        return data;
      }

      if (window.MockAPI) {
        return await window.MockAPI.getSnapshots({ period, days, limit });
      }
      return [];
    }

    async getAnalyticsTrend({ period = null, days = null } = {}) {
      let query = [];
      if (period) query.push(`period=${encodeURIComponent(period)}`);
      if (days) query.push(`days=${encodeURIComponent(days)}`);
      const endpoint = `/snapshots/trend${query.length ? '?' + query.join('&') : ''}`;

      const data = await this.request(endpoint);
      if (data && data.harmony_series && Array.isArray(data.labels)) {
        return data;
      }

      if (window.MockAPI) {
        return await window.MockAPI.getAnalyticsTrend({ period, days });
      }
      return {
        labels: [],
        dates: [],
        harmony_series: [],
        spheres_series: [],
        snapshots_count: 0,
        current_harmony_index: 0.5,
        earliest_harmony_index: 0.5,
        improvement_delta: 0,
        improvement_percent: 0
      };
    }

    async createSnapshot({ notes = null, items = null } = {}) {
      const data = await this.request('/snapshots', {
        method: 'POST',
        body: JSON.stringify({ notes, items })
      });

      if (data && data.id) {
        return data;
      }

      if (window.MockAPI) {
        return await window.MockAPI.createSnapshot({ notes, items });
      }
      throw new Error("Не удалось создать срез баланса");
    }

    async deleteSnapshot(id) {
      const data = await this.request(`/snapshots/${id}`, {
        method: 'DELETE'
      });

      if (data) {
        return { success: true };
      }

      if (window.MockAPI) {
        return await window.MockAPI.deleteSnapshot(id);
      }
      throw new Error("Не удалось удалить срез");
    }
  }

  // Экспортируем глобальный экземпляр клиента
  window.API = new HorizontApiClient();

})(window);

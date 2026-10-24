/**
 * Главный скрипт веб-приложения «Горизонт»
 * Компактный эргономичный дашборд в чистом стиле Google for Developers
 * Полностью совместим с открытием через протокол file:// без ES-модулей
 */

const appState = {
  selectedSphereId: null,
  selectedStatus: 'all',
  searchQuery: '',
  chartInstance: null,
  activeCurrency: localStorage.getItem('horizont_currency') || 'BYN',
  fxRate: 2.9543,
  fxRateData: null,
  currentUser: window.MockAPI ? window.MockAPI.getCurrentUser() : null,
  currentMode: 'dashboard',
  isDarkMode: localStorage.getItem('horizont_theme') === 'dark' || 
              (!('horizont_theme' in localStorage) && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
};

// Безопасный вызов иконок Lucide
function safeLucideIcons() {
  if (typeof lucide !== 'undefined' && lucide && typeof lucide.createIcons === 'function') {
    try {
      lucide.createIcons();
    } catch (e) {
      console.warn("Lucide icons error:", e);
    }
  }
}

/**
 * Инициализация при старте приложения
 */
async function startApp() {
  setupTheme();
  setupEventListeners();
  applyRBAC();
  await initExchangeRate();
  await refreshAll();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startApp);
} else {
  startApp();
}

/**
 * Сервис курсов валют и интеграция с Нацбанком РБ (НБРБ)
 */
async function initExchangeRate() {
  try {
    const fx = await window.MockAPI.getNbrbRate(false);
    appState.fxRateData = fx;
    appState.fxRate = fx.rate || 2.9543;

    const rateValEl = document.getElementById('nbrb-rate-val');
    const ratePillEl = document.getElementById('nbrb-rate-pill');
    const switcherWrap = document.getElementById('currency-switcher-wrap');

    if (rateValEl) {
      rateValEl.textContent = Number(appState.fxRate).toFixed(4);
    }
    if (ratePillEl) {
      ratePillEl.title = `Официальный курс НБРБ на ${fx.rate_date || 'сегодня'}: 1 USD = ${appState.fxRate} BYN (${fx.source})`;
    }
    if (switcherWrap) {
      switcherWrap.title = `Курс НБРБ (${fx.rate_date || 'сегодня'}): 1 USD = ${Number(appState.fxRate).toFixed(4)} BYN`;
    }
  } catch (e) {
    console.warn("Ошибка инициализации курса НБРБ:", e);
  }
  updateCurrencySwitcherUI();
  updateTotalGoalsBudget();
}

/**
 * Переключение активной валюты отображения (BYN ⇄ USD)
 */
window.setAppCurrency = function(currency) {
  if (currency !== 'BYN' && currency !== 'USD') return;
  appState.activeCurrency = currency;
  localStorage.setItem('horizont_currency', currency);
  updateCurrencySwitcherUI();
  renderGoals();
  updateTotalGoalsBudget();
  if (typeof renderCMSGoals === 'function') {
    renderCMSGoals();
  }
};

function updateCurrencySwitcherUI() {
  const bynBtn = document.getElementById('currency-byn-btn');
  const usdBtn = document.getElementById('currency-usd-btn');
  if (!bynBtn || !usdBtn) return;

  if (appState.activeCurrency === 'BYN') {
    bynBtn.className = "px-2.5 py-1 rounded-full text-xs font-bold transition-all bg-[#1A73E8] text-white shadow-sm";
    usdBtn.className = "px-2.5 py-1 rounded-full text-xs font-medium text-[#5F6368] dark:text-[#94A3B8] hover:text-[#202124] dark:hover:text-white transition-all";
  } else {
    usdBtn.className = "px-2.5 py-1 rounded-full text-xs font-bold transition-all bg-[#1A73E8] text-white shadow-sm";
    bynBtn.className = "px-2.5 py-1 rounded-full text-xs font-medium text-[#5F6368] dark:text-[#94A3B8] hover:text-[#202124] dark:hover:text-white transition-all";
  }
}

/**
 * Конвертация и форматирование бюджета карточки цели
 */
function formatGoalBudget(amount, fromCur, toCur, rate) {
  if (!amount || amount <= 0) return 'Без бюджета';
  const fx = rate || appState.fxRate || 2.9543;
  let converted = amount;
  if (fromCur === 'USD' && toCur === 'BYN') {
    converted = amount * fx;
  } else if (fromCur === 'BYN' && toCur === 'USD') {
    converted = amount / fx;
  }
  const formatted = Math.round(converted).toLocaleString('ru-RU');
  return `${formatted} ${toCur}`;
}

/**
 * Подсчет и отображение суммарного бюджета всех целей
 */
async function updateTotalGoalsBudget() {
  const budgetEl = document.getElementById('total-goals-budget');
  if (!budgetEl) return;

  try {
    const goals = await window.MockAPI.getGoals();
    const fx = appState.fxRate || 2.9543;
    let totalInActiveCur = 0;

    goals.forEach(g => {
      const amount = parseFloat(g.cost_amount) || 0;
      if (amount <= 0) return;
      const gCur = g.currency === 'USD' ? 'USD' : 'BYN';
      if (gCur === appState.activeCurrency) {
        totalInActiveCur += amount;
      } else if (gCur === 'USD' && appState.activeCurrency === 'BYN') {
        totalInActiveCur += amount * fx;
      } else if (gCur === 'BYN' && appState.activeCurrency === 'USD') {
        totalInActiveCur += amount / fx;
      }
    });

    budgetEl.textContent = `${Math.round(totalInActiveCur).toLocaleString('ru-RU')} ${appState.activeCurrency}`;
  } catch (e) {
    console.warn("Ошибка подсчета бюджета:", e);
  }
}

/**
 * Настройка переключения светлой и темной темы
 */
function setupTheme() {
  const html = document.documentElement;
  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  const themeIcon = document.getElementById('theme-icon');

  function applyTheme(isDark) {
    if (isDark) {
      html.classList.add('dark');
      localStorage.setItem('horizont_theme', 'dark');
      if (themeIcon) themeIcon.setAttribute('data-lucide', 'sun');
    } else {
      html.classList.remove('dark');
      localStorage.setItem('horizont_theme', 'light');
      if (themeIcon) themeIcon.setAttribute('data-lucide', 'moon');
    }
    safeLucideIcons();
    if (appState.chartInstance) {
      updateChartTheme();
    }
  }

  applyTheme(appState.isDarkMode);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      appState.isDarkMode = !appState.isDarkMode;
      applyTheme(appState.isDarkMode);
    });
  }
}

/**
 * Настройка глобальных обработчиков событий
 */
function setupEventListeners() {
  // Поиск по целям в реальном времени
  const searchInput = document.getElementById('global-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      appState.searchQuery = e.target.value.toLowerCase().trim();
      renderGoals();
    });
  }

  // Модальное окно "+ Новая цель"
  const openModalBtn = document.getElementById('open-create-goal-modal');
  const closeModalBtn = document.getElementById('close-goal-modal');
  const cancelModalBtn = document.getElementById('cancel-goal-modal');
  const goalModal = document.getElementById('goal-modal');

  if (openModalBtn) {
    openModalBtn.addEventListener('click', () => window.openCreateGoalModal());
  }

  const hideCreateModal = () => {
    if (goalModal) goalModal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  };

  if (closeModalBtn) closeModalBtn.addEventListener('click', hideCreateModal);
  if (cancelModalBtn) cancelModalBtn.addEventListener('click', hideCreateModal);

  if (goalModal) {
    goalModal.addEventListener('click', (e) => {
      if (e.target === goalModal) hideCreateModal();
    });
  }

  // Сабмит формы создания цели
  const goalForm = document.getElementById('goal-form');
  if (goalForm) {
    goalForm.addEventListener('submit', handleCreateGoalSubmit);
  }

  // Кнопка добавления шага в форме создания
  const addStepBtn = document.getElementById('modal-add-step-btn');
  if (addStepBtn) {
    addStepBtn.addEventListener('click', () => addStepInputToModal());
  }

  // Фильтры статуса (Все / В работе / Достигнуто)
  const statusFilterBtns = document.querySelectorAll('.status-filter-btn');
  statusFilterBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      statusFilterBtns.forEach(b => {
        b.classList.remove('bg-[#1A73E8]', 'text-white', 'font-semibold');
        b.classList.add('text-[#5F6368]', 'dark:text-[#94A3B8]', 'font-medium');
      });
      const target = e.currentTarget;
      target.classList.add('bg-[#1A73E8]', 'text-white', 'font-semibold');
      target.classList.remove('text-[#5F6368]', 'dark:text-[#94A3B8]', 'font-medium');
      
      appState.selectedStatus = target.dataset.status;
      renderGoals();
    });
  });

  // Переключение режима «Дашборд / CMS Управление»
  const modeDashboardBtn = document.getElementById('nav-mode-dashboard-btn');
  const modeCmsBtn = document.getElementById('nav-mode-cms-btn');
  const mobileModeToggleBtn = document.getElementById('mobile-mode-toggle-btn');
  const dashboardView = document.getElementById('dashboard-view');
  const cmsView = document.getElementById('cms-view');

  function setAppMode(mode) {
    if (mode === 'cms') {
      const user = appState.currentUser || window.MockAPI.getCurrentUser();
      if (!user || user.role !== 'admin') {
        showToast('⚠️ Доступ ограничен: панель CMS доступна только администраторам (admin@horizon.app)', 'error');
        setAppMode('dashboard');
        return;
      }

      appState.currentMode = 'cms';
      dashboardView.classList.add('hidden');
      cmsView.classList.remove('hidden');

      if (modeCmsBtn) {
        modeCmsBtn.classList.add('bg-[#1A73E8]', 'text-white', 'shadow-sm', 'font-semibold');
        modeCmsBtn.classList.remove('text-[#5F6368]', 'dark:text-[#94A3B8]', 'font-medium');
      }
      if (modeDashboardBtn) {
        modeDashboardBtn.classList.remove('bg-[#1A73E8]', 'text-white', 'shadow-sm', 'font-semibold');
        modeDashboardBtn.classList.add('text-[#5F6368]', 'dark:text-[#94A3B8]', 'font-medium');
      }
      renderCMSSpheres();
      renderCMSGoals();
    } else {
      appState.currentMode = 'dashboard';
      cmsView.classList.add('hidden');
      dashboardView.classList.remove('hidden');

      if (modeDashboardBtn) {
        modeDashboardBtn.classList.add('bg-[#1A73E8]', 'text-white', 'shadow-sm', 'font-semibold');
        modeDashboardBtn.classList.remove('text-[#5F6368]', 'dark:text-[#94A3B8]', 'font-medium');
      }
      if (modeCmsBtn) {
        modeCmsBtn.classList.remove('bg-[#1A73E8]', 'text-white', 'shadow-sm', 'font-semibold');
        modeCmsBtn.classList.add('text-[#5F6368]', 'dark:text-[#94A3B8]', 'font-medium');
      }
      refreshAll();
    }
    safeLucideIcons();
  }

  window.setAppMode = setAppMode;

  if (modeDashboardBtn) modeDashboardBtn.addEventListener('click', () => setAppMode('dashboard'));
  if (modeCmsBtn) modeCmsBtn.addEventListener('click', () => setAppMode('cms'));
  if (mobileModeToggleBtn) {
    mobileModeToggleBtn.addEventListener('click', () => {
      const isCms = !cmsView.classList.contains('hidden');
      setAppMode(isCms ? 'dashboard' : 'cms');
    });
  }

  // Вкладки внутри CMS (Сферы / Цели / База данных)
  const cmsTabSpheresBtn = document.getElementById('cms-tab-spheres-btn');
  const cmsTabGoalsBtn = document.getElementById('cms-tab-goals-btn');
  const cmsTabDatabaseBtn = document.getElementById('cms-tab-database-btn');

  const cmsTabSpheresContent = document.getElementById('cms-tab-spheres-content');
  const cmsTabGoalsContent = document.getElementById('cms-tab-goals-content');
  const cmsTabDatabaseContent = document.getElementById('cms-tab-database-content');

  function setCMSTab(tab) {
    const tabs = [
      { id: 'spheres', btn: cmsTabSpheresBtn, content: cmsTabSpheresContent },
      { id: 'goals', btn: cmsTabGoalsBtn, content: cmsTabGoalsContent },
      { id: 'database', btn: cmsTabDatabaseBtn, content: cmsTabDatabaseContent }
    ];

    tabs.forEach(t => {
      if (!t.btn || !t.content) return;
      if (t.id === tab) {
        t.btn.classList.add('bg-white', 'dark:bg-[#1F2937]', 'text-[#1A73E8]', 'shadow-sm', 'font-semibold');
        t.btn.classList.remove('text-[#5F6368]', 'dark:text-[#94A3B8]', 'font-medium');
        t.content.classList.remove('hidden');
      } else {
        t.btn.classList.remove('bg-white', 'dark:bg-[#1F2937]', 'text-[#1A73E8]', 'shadow-sm', 'font-semibold');
        t.btn.classList.add('text-[#5F6368]', 'dark:text-[#94A3B8]', 'font-medium');
        t.content.classList.add('hidden');
      }
    });

    if (tab === 'spheres') renderCMSSpheres();
    if (tab === 'goals') renderCMSGoals();
    safeLucideIcons();
  }

  if (cmsTabSpheresBtn) cmsTabSpheresBtn.addEventListener('click', () => setCMSTab('spheres'));
  if (cmsTabGoalsBtn) cmsTabGoalsBtn.addEventListener('click', () => setCMSTab('goals'));
  if (cmsTabDatabaseBtn) cmsTabDatabaseBtn.addEventListener('click', () => setCMSTab('database'));

  // CMS: Кнопка "+ Добавить сферу"
  const openCreateSphereBtn = document.getElementById('cms-open-create-sphere-btn');
  if (openCreateSphereBtn) {
    openCreateSphereBtn.addEventListener('click', () => window.openSphereModal());
  }

  // Модалка сферы (закрытие)
  const sphereModal = document.getElementById('sphere-modal');
  const closeSphereModalBtn = document.getElementById('close-sphere-modal');
  const cancelSphereModalBtn = document.getElementById('cancel-sphere-modal');

  const hideSphereModal = () => {
    if (sphereModal) sphereModal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  };

  if (closeSphereModalBtn) closeSphereModalBtn.addEventListener('click', hideSphereModal);
  if (cancelSphereModalBtn) cancelSphereModalBtn.addEventListener('click', hideSphereModal);

  // Синхронизация color picker и поля текста цвета
  const sphereColorPicker = document.getElementById('sphere-color-picker');
  const sphereColorText = document.getElementById('sphere-color-text');
  if (sphereColorPicker && sphereColorText) {
    sphereColorPicker.addEventListener('input', (e) => {
      sphereColorText.value = e.target.value.toUpperCase();
    });
    sphereColorText.addEventListener('input', (e) => {
      if (/^#[0-9A-Fa-f]{6}$/.test(e.target.value)) {
        sphereColorPicker.value = e.target.value;
      }
    });
  }

  // Сабмит формы сферы (Создание / Редактирование)
  const sphereForm = document.getElementById('sphere-form');
  if (sphereForm) {
    sphereForm.addEventListener('submit', handleSphereFormSubmit);
  }

  // Фильтр статуса в CMS таблице целей
  const cmsGoalsStatusFilter = document.getElementById('cms-goals-status-filter');
  if (cmsGoalsStatusFilter) {
    cmsGoalsStatusFilter.addEventListener('change', () => renderCMSGoals());
  }

  // Экспорт JSON
  const exportJsonBtn = document.getElementById('cms-export-json-btn');
  if (exportJsonBtn) {
    exportJsonBtn.addEventListener('click', () => {
      const json = window.MockAPI.exportJSON();
      const blob = new Blob([json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `horizont-backup-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast('Резервная копия JSON успешно скачана', 'success');
    });
  }

  // Импорт JSON
  const triggerImportBtn = document.getElementById('cms-trigger-import-btn');
  const importFileInput = document.getElementById('cms-import-file-input');

  if (triggerImportBtn && importFileInput) {
    triggerImportBtn.addEventListener('click', () => importFileInput.click());

    importFileInput.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = async (evt) => {
        try {
          const res = window.MockAPI.importJSON(evt.target.result);
          showToast(`Импорт успешен: ${res.spheres_count} сфер, ${res.goals_count} целей`, 'success');
          await refreshAll();
          renderCMSSpheres();
          renderCMSGoals();
        } catch (err) {
          showToast('Ошибка импорта JSON: ' + err.message, 'error');
        }
      };
      reader.readAsText(file);
      e.target.value = '';
    });
  }

  // Генератор SQL INSERT
  const generateSqlBtn = document.getElementById('cms-generate-sql-btn');
  const sqlOutput = document.getElementById('cms-sql-output');
  const copySqlBtn = document.getElementById('cms-copy-sql-btn');

  if (generateSqlBtn && sqlOutput) {
    generateSqlBtn.addEventListener('click', () => {
      const sql = window.MockAPI.generateSQLInserts();
      sqlOutput.value = sql;
      showToast('SQL INSERT скрипт сгенерирован', 'info');
    });
  }

  if (copySqlBtn && sqlOutput) {
    copySqlBtn.addEventListener('click', () => {
      if (!sqlOutput.value) {
        sqlOutput.value = window.MockAPI.generateSQLInserts();
      }
      navigator.clipboard.writeText(sqlOutput.value).then(() => {
        showToast('SQL скопирован в буфер обмена', 'success');
      }).catch(() => {
        sqlOutput.select();
        document.execCommand('copy');
        showToast('SQL скопирован в буфер обмена', 'success');
      });
    });
  }

  // Кнопка сброса к демо-данным
  const resetBtn = document.getElementById('reset-demo-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', async () => {
      if (confirm('Сбросить данные к исходным демо-значениям из базы данных?')) {
        window.MockAPI.resetToDefaults();
        showToast('Данные успешно сброшены к начальным значениям', 'info');
        await refreshAll();
      }
    });
  }

  setupPresetImages();
}

function setupPresetImages() {
  const presetBtns = document.querySelectorAll('.image-preset-btn');
  const imageUrlInput = document.getElementById('goal-image-url');
  presetBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const url = btn.dataset.url;
      if (imageUrlInput) {
        imageUrlInput.value = url;
        showToast('Обложка выбрана из пресета', 'info');
      }
    });
  });
}

/**
 * Полное обновление всех секций
 */
async function refreshAll() {
  try {
    await Promise.all([
      renderRadarAndAnalytics(),
      renderSpheresFilterBar(),
      renderGoals(),
      updateTotalGoalsBudget()
    ]);
  } catch (err) {
    console.error("Ошибка при обновлении:", err);
  }
  safeLucideIcons();
}

/**
 * Рендеринг радарной диаграммы и аналитики
 */
async function renderRadarAndAnalytics() {
  const radarData = await window.MockAPI.getRadarChartData();

  // Обновление индекса гармонии
  const harmonyElem = document.getElementById('harmony-index-value');
  const harmonyDescElem = document.getElementById('harmony-index-desc');
  const harmonyProgressElem = document.getElementById('harmony-index-progress');

  if (harmonyElem) {
    const percent = Math.round(radarData.overall_harmony_index * 100);
    harmonyElem.textContent = `${percent}%`;
    if (harmonyProgressElem) {
      harmonyProgressElem.style.width = `${percent}%`;
    }

    if (harmonyDescElem) {
      if (percent >= 80) {
        harmonyDescElem.textContent = "Высокая гармония: сферы жизни развиваются сбалансированно.";
      } else if (percent >= 60) {
        harmonyDescElem.textContent = "Умеренный баланс: есть 1-2 сферы, требующие внимания.";
      } else {
        harmonyDescElem.textContent = "Обнаружен перекос: часть сфер сильно проседает относительно других.";
      }
    }
  }

  // Рендеринг мини-сетки 2x3 сфер
  renderSpheresMiniGrid(radarData.sectors);

  // Отрисовка Chart.js
  renderRadarChart(radarData.sectors);
}

/**
 * Рендеринг компактной сетки 2x3 сфер жизни (как в Версии 1)
 */
function renderSpheresMiniGrid(sectors) {
  const container = document.getElementById('spheres-mini-grid');
  if (!container) return;

  container.innerHTML = sectors.map(sector => {
    const isSelected = appState.selectedSphereId === sector.sphere_id;
    const progressPercent = Math.min(100, Math.round((sector.current_score / sector.target_score) * 100));

    return `
      <div class="p-2.5 rounded-xl border ${isSelected ? 'border-[#1A73E8] bg-[#E8F0FE]/40 dark:bg-blue-950/30' : 'border-[#E8EAED] dark:border-[#1F2937] bg-white dark:bg-[#111827]'} hover:border-[#BDC1C6] dark:hover:border-[#374151] transition-all cursor-pointer"
           onclick="window.selectSphereFilter('${sector.sphere_id}')">
        <div class="flex items-center justify-between mb-1">
          <div class="flex items-center gap-1.5 min-w-0">
            <span class="w-2.5 h-2.5 rounded-full shrink-0" style="background-color: ${sector.color};"></span>
            <span class="text-xs font-semibold text-[#202124] dark:text-[#F8FAFC] truncate max-w-[120px]">
              ${escapeHTML(sector.title)}
            </span>
          </div>
          <span class="text-xs font-bold font-mono shrink-0" style="color: ${sector.color};">
            ${sector.current_score.toFixed(1)} <span class="text-[10px] text-[#5F6368] dark:text-[#94A3B8] font-normal">/ 10</span>
          </span>
        </div>
        <div class="w-full bg-[#E8EAED] dark:bg-[#1F2937] h-1.5 rounded-full overflow-hidden">
          <div class="h-full rounded-full transition-all duration-500" 
               style="width: ${progressPercent}%; background-color: ${sector.color};"></div>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Отрисовка радарной диаграммы Chart.js с цветными вершинами
 */
function renderRadarChart(sectors) {
  const canvas = document.getElementById('radarChartCanvas');
  if (!canvas) return;

  if (typeof Chart === 'undefined') {
    console.warn("Chart.js библиотека не обнаружена.");
    return;
  }

  const labels = sectors.map(s => s.title);
  const currentScores = sectors.map(s => s.current_score);
  const targetScores = sectors.map(s => s.target_score);
  const isDark = document.documentElement.classList.contains('dark');

  const gridColor = isDark ? 'rgba(148, 163, 184, 0.15)' : 'rgba(218, 220, 224, 0.6)';
  const angleLineColor = isDark ? 'rgba(148, 163, 184, 0.2)' : 'rgba(218, 220, 224, 0.8)';
  const labelColor = isDark ? '#E2E8F0' : '#202124';

  if (appState.chartInstance) {
    appState.chartInstance.data.labels = labels;
    appState.chartInstance.data.datasets[0].data = targetScores;
    appState.chartInstance.data.datasets[1].data = currentScores;
    appState.chartInstance.data.datasets[1].pointBackgroundColor = sectors.map(s => s.color);
    appState.chartInstance.update();
    return;
  }

  const ctx = canvas.getContext('2d');
  appState.chartInstance = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Целевой ориентир',
          data: targetScores,
          backgroundColor: isDark ? 'rgba(148, 163, 184, 0.04)' : 'rgba(218, 220, 224, 0.15)',
          borderColor: isDark ? 'rgba(148, 163, 184, 0.4)' : '#9AA0A6',
          borderWidth: 1.5,
          borderDash: [4, 4],
          pointRadius: 2,
          pointBackgroundColor: '#9AA0A6'
        },
        {
          label: 'Текущий баланс',
          data: currentScores,
          backgroundColor: isDark ? 'rgba(99, 102, 241, 0.25)' : 'rgba(26, 115, 232, 0.18)',
          borderColor: '#1A73E8',
          borderWidth: 2.5,
          pointBackgroundColor: sectors.map(s => s.color), // Цветные вершины по цветам сфер!
          pointBorderColor: '#FFFFFF',
          pointBorderWidth: 2,
          pointRadius: 5.5,
          pointHoverRadius: 8
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 0,
          max: 10,
          ticks: {
            stepSize: 2,
            display: true,
            backdropColor: 'transparent',
            color: isDark ? '#94A3B8' : '#5F6368',
            font: { size: 10, family: 'Inter' }
          },
          grid: {
            color: gridColor
          },
          angleLines: {
            color: angleLineColor
          },
          pointLabels: {
            color: labelColor,
            font: {
              size: 11,
              weight: '600',
              family: 'Plus Jakarta Sans'
            }
          }
        }
      },
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          backgroundColor: isDark ? '#1E293B' : '#202124',
          titleFont: { family: 'Plus Jakarta Sans', weight: 'bold' },
          bodyFont: { family: 'Inter' },
          padding: 10,
          cornerRadius: 8,
          callbacks: {
            label: function(context) {
              const val = context.raw || 0;
              return ` ${context.dataset.label}: ${val.toFixed(1)} / 10`;
            }
          }
        }
      },
      animation: {
        duration: 350,
        easing: 'easeOutQuart'
      }
    }
  });
}

function updateChartTheme() {
  if (!appState.chartInstance) return;
  const isDark = document.documentElement.classList.contains('dark');
  const gridColor = isDark ? 'rgba(148, 163, 184, 0.15)' : 'rgba(218, 220, 224, 0.6)';
  const angleLineColor = isDark ? 'rgba(148, 163, 184, 0.2)' : 'rgba(218, 220, 224, 0.8)';
  const labelColor = isDark ? '#E2E8F0' : '#202124';

  appState.chartInstance.options.scales.r.grid.color = gridColor;
  appState.chartInstance.options.scales.r.angleLines.color = angleLineColor;
  appState.chartInstance.options.scales.r.pointLabels.color = labelColor;
  appState.chartInstance.options.scales.r.ticks.color = isDark ? '#94A3B8' : '#5F6368';
  appState.chartInstance.update();
}

/**
 * Чипсы фильтрации по сферам жизни (Material 3)
 */
async function renderSpheresFilterBar() {
  const container = document.getElementById('spheres-filter-container');
  if (!container) return;

  const spheres = await window.MockAPI.getSpheres();

  const allActive = !appState.selectedSphereId;
  let html = `
    <button class="google-chip ${allActive ? 'active' : ''}"
            onclick="window.selectSphereFilter(null)">
      <span>Все сферы</span>
    </button>
  `;

  spheres.forEach(sphere => {
    const isSelected = appState.selectedSphereId === sphere.id;
    html += `
      <button class="google-chip ${isSelected ? 'active' : ''}"
              onclick="window.selectSphereFilter('${sphere.id}')">
        <span class="w-2 h-2 rounded-full" style="background-color: ${sphere.color};"></span>
        <span>${escapeHTML(sphere.title)}</span>
      </button>
    `;
  });

  container.innerHTML = html;
}

window.selectSphereFilter = (sphereId) => {
  appState.selectedSphereId = (appState.selectedSphereId === sphereId) ? null : sphereId;
  renderSpheresFilterBar();
  renderGoals();
};

/**
 * Рендеринг карточек целей: дизайн Google Developers + компактный чек-лист шагов прямо на карточке!
 */
async function renderGoals() {
  const container = document.getElementById('goals-grid');
  const countBadge = document.getElementById('goals-count-badge');
  if (!container) return;

  let goals = await window.MockAPI.getGoals({
    sphereId: appState.selectedSphereId,
    status: appState.selectedStatus
  });

  // Поиск
  if (appState.searchQuery) {
    goals = goals.filter(g => 
      g.title.toLowerCase().includes(appState.searchQuery) ||
      (g.description && g.description.toLowerCase().includes(appState.searchQuery))
    );
  }

  if (countBadge) {
    countBadge.textContent = `Показано ${goals.length} целей`;
  }

  if (goals.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-16 text-center google-card p-12">
        <div class="w-12 h-12 mx-auto mb-3 rounded-full bg-[#E8F0FE] text-[#1A73E8] flex items-center justify-center">
          <i data-lucide="compass" class="w-5 h-5"></i>
        </div>
        <h4 class="text-base font-bold font-heading text-[#202124] dark:text-white">Цели не найдены</h4>
        <p class="text-xs text-[#5F6368] dark:text-[#94A3B8] mt-1 max-w-sm mx-auto">
          В выбранной категории нет карточек. Создайте новую цель или измените фильтр.
        </p>
      </div>
    `;
    safeLucideIcons();
    return;
  }

  container.innerHTML = goals.map(goal => {
    const isAchieved = goal.status === 'achieved';
    const deadlineText = formatDeadline(goal.deadline);
    const priorityBadge = getPriorityBadge(goal.priority);
    const budgetDisplay = formatGoalBudget(goal.cost_amount, goal.currency, appState.activeCurrency, appState.fxRate);

    // Компактные шаги чек-листа прямо внутри карточки
    const stepsHTML = goal.steps.map(step => `
      <div class="flex items-center justify-between py-1 group/step">
        <label class="flex items-center gap-2 cursor-pointer min-w-0 flex-1">
          <input type="checkbox" 
                 class="material-checkbox" 
                 ${step.is_completed ? 'checked' : ''} 
                 onchange="window.handleToggleStep('${goal.id}', '${step.id}')">
          <span class="text-xs ${step.is_completed ? 'line-through text-[#9AA0A6] dark:text-[#64748B]' : 'text-[#202124] dark:text-[#F8FAFC]'} truncate transition-all">
            ${escapeHTML(step.title)}
          </span>
        </label>
        <div class="flex items-center gap-1.5 shrink-0 pl-1">
          ${step.weight > 1 ? `<span class="text-[9px] font-semibold px-1 rounded bg-[#F1F3F4] dark:bg-[#1F2937] text-[#5F6368]">в${step.weight}</span>` : ''}
          <button onclick="window.handleDeleteStep('${goal.id}', '${step.id}')" 
                  title="Удалить шаг" 
                  class="opacity-0 group-hover/step:opacity-100 text-[#9AA0A6] hover:text-[#D93025] transition-opacity p-0.5">
            <i data-lucide="trash-2" class="w-3 h-3"></i>
          </button>
        </div>
      </div>
    `).join('');

    return `
      <div class="google-card overflow-hidden flex flex-col justify-between">
        <div>
          <!-- Иллюстрация 16:9 с бейджами -->
          <div class="relative w-full aspect-video bg-[#F1F3F4] dark:bg-[#1E293B] overflow-hidden">
            ${goal.image_url 
              ? `<img src="${goal.image_url}" alt="${escapeHTML(goal.title)}" class="w-full h-full object-cover transition-transform duration-500 hover:scale-105" loading="lazy">` 
              : `<div class="w-full h-full flex items-center justify-center text-[#5F6368]"><i data-lucide="image" class="w-8 h-8"></i></div>`
            }
            
            <!-- Бейдж сферы слева вверху -->
            <div class="absolute top-2.5 left-2.5">
              <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-white/95 dark:bg-[#111827]/95 text-[#202124] dark:text-white shadow-sm backdrop-blur-sm">
                <span class="w-2 h-2 rounded-full" style="background-color: ${goal.sphere_color};"></span>
                ${escapeHTML(goal.sphere_title)}
              </span>
            </div>

            <!-- Бейдж приоритета или удаление справа вверху -->
            <div class="absolute top-2.5 right-2.5 flex items-center gap-1">
              ${isAchieved ? `
                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#1E8E3E] text-white">Достигнуто</span>
              ` : ''}
              <button onclick="window.handleDeleteGoal('${goal.id}')" 
                      class="p-1 rounded-full bg-black/40 hover:bg-[#D93025] text-white transition-all backdrop-blur-sm"
                      title="Удалить карточку">
                <i data-lucide="x" class="w-3.5 h-3.5"></i>
              </button>
            </div>
          </div>

          <!-- Контент карточки -->
          <div class="p-5">
            <h3 class="goal-card-title text-base font-semibold leading-snug line-clamp-2 mb-1.5">
              ${escapeHTML(goal.title)}
            </h3>
            
            ${goal.description ? `
              <p class="text-xs text-[#5F6368] dark:text-[#94A3B8] line-clamp-2 leading-relaxed mb-3">
                ${escapeHTML(goal.description)}
              </p>
            ` : '<div class="mb-2"></div>'}

            <!-- Тонкий прогресс-бар карточки и бюджет (мультивалютность) -->
            <div class="mb-3">
              <div class="flex items-center justify-between text-[11px] font-medium text-[#5F6368] dark:text-[#94A3B8] mb-1">
                <span>Прогресс: <strong class="font-bold font-mono text-[#1A73E8] dark:text-[#60A5FA]">${goal.progress_percent}%</strong></span>
                <span class="inline-flex items-center gap-1 font-mono font-bold text-xs ${goal.cost_amount > 0 ? 'text-[#0D9488] dark:text-[#2DD4BF]' : 'text-[#9AA0A6]'}" title="Бюджет цели: ${goal.cost_amount || 0} ${goal.currency || 'BYN'}">
                  <i data-lucide="coins" class="w-3.5 h-3.5"></i>
                  ${budgetDisplay}
                </span>
              </div>
              <div class="google-progress-track">
                <div class="google-progress-bar ${isAchieved ? 'bg-[#1E8E3E]' : 'bg-[#1A73E8]'}" 
                     style="width: ${goal.progress_percent}%;"></div>
              </div>
            </div>

            <!-- Интерактивный чек-лист шагов прямо в карточке -->
            <div class="border-t border-[#E8EAED] dark:border-[#1F2937] pt-2.5">
              <div class="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-[#5F6368] dark:text-[#94A3B8] mb-1.5">
                <span>Шаги (${goal.completed_steps_count}/${goal.steps_count})</span>
                <button onclick="window.promptAddStep('${goal.id}')" 
                        class="text-[#1A73E8] dark:text-[#60A5FA] hover:underline font-semibold flex items-center gap-0.5 normal-case">
                  <i data-lucide="plus" class="w-3 h-3"></i> шаг
                </button>
              </div>
              
              <div class="space-y-0.5 max-h-40 overflow-y-auto pr-1">
                ${stepsHTML}
              </div>
            </div>

          </div>
        </div>

        <!-- Подвал карточки: статус и дедлайн -->
        <div class="px-5 pb-4 pt-1 border-t border-[#E8EAED] dark:border-[#1F2937] flex items-center justify-between text-[11px] text-[#5F6368] dark:text-[#94A3B8]">
          <span class="flex items-center gap-1">
            <i data-lucide="calendar" class="w-3 h-3"></i>
            ${deadlineText}
          </span>
          ${priorityBadge}
        </div>

      </div>
    `;
  }).join('');

  safeLucideIcons();
}

function getPriorityBadge(priority) {
  switch (priority) {
    case 'critical':
      return `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#FCE8E6] text-[#D93025]">Критический</span>`;
    case 'high':
      return `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#FEF7E0] text-[#B06000]">Высокий</span>`;
    case 'medium':
      return `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#E8F0FE] text-[#1A73E8]">Средний</span>`;
    case 'low':
      return `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#F1F3F4] text-[#5F6368]">Низкий</span>`;
    default:
      return `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#F1F3F4] text-[#5F6368]">Обычный</span>`;
  }
}

function formatDeadline(dateString) {
  if (!dateString) return 'Без дедлайна';
  const date = new Date(dateString);
  const now = new Date();
  const diffDays = Math.ceil((date - now) / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return 'Просрочено';
  if (diffDays === 0) return 'Сегодня';
  if (diffDays === 1) return 'Завтра';
  if (diffDays < 30) return `${diffDays} дн.`;
  return date.toLocaleDateString('ru-RU', { month: 'short', year: 'numeric' });
}

/**
 * Обработка переключения шага чек-листа прямо на карточке (UC-2)
 */
window.handleToggleStep = async (goalId, stepId) => {
  try {
    const result = await window.MockAPI.toggleStep(goalId, stepId);

    if (result.celebration && typeof confetti === 'function') {
      confetti({
        particleCount: 80,
        spread: 60,
        origin: { y: 0.6 }
      });
      showToast('🎉 Поздравляем! Цель выполнена на 100%!', 'celebration');
    } else {
      const deltaSign = result.sphere_metrics.score_delta > 0 ? '+' : '';
      const deltaText = result.sphere_metrics.score_delta !== 0 
        ? ` (${result.sphere_metrics.sphere_title}: ${deltaSign}${result.sphere_metrics.score_delta})`
        : '';
      showToast(`Прогресс цели: ${result.goal_progress_percent}%${deltaText}`, 'success');
    }

    await refreshAll();
  } catch (error) {
    console.error(error);
    showToast('Ошибка обновления шага: ' + error.message, 'error');
  }
};

window.promptAddStep = async (goalId) => {
  const title = prompt('Введите название шага чек-листа:');
  if (!title || !title.trim()) return;

  const weightStr = prompt('Вес шага (по умолчанию 1, или укажите 2, 3):', '1');
  const weight = parseInt(weightStr, 10) || 1;

  try {
    await window.MockAPI.addStep(goalId, title, weight);
    showToast('Шаг добавлен в чек-лист', 'success');
    await refreshAll();
  } catch (e) {
    showToast('Ошибка: ' + e.message, 'error');
  }
};

window.handleDeleteStep = async (goalId, stepId) => {
  if (!confirm('Удалить этот шаг чек-листа?')) return;
  try {
    await window.MockAPI.deleteStep(goalId, stepId);
    showToast('Шаг удален', 'info');
    await refreshAll();
  } catch (e) {
    showToast('Ошибка: ' + e.message, 'error');
  }
};

window.handleDeleteGoal = async (goalId) => {
  if (!confirm('Вы уверены, что хотите удалить эту карточку цели?')) return;
  try {
    await window.MockAPI.deleteGoal(goalId);
    showToast('Карточка цели удалена', 'info');
    await refreshAll();
  } catch (e) {
    showToast('Ошибка удаления: ' + e.message, 'error');
  }
};

/**
 * Открытие модального окна создания цели (UC-1)
 */
window.openCreateGoalModal = async () => {
  const modal = document.getElementById('goal-modal');
  const heading = document.getElementById('goal-modal-heading');
  const editId = document.getElementById('edit-goal-id');
  const sphereSelect = document.getElementById('goal-sphere-select');
  const stepsContainer = document.getElementById('modal-steps-container');

  if (!modal || !sphereSelect || !stepsContainer) return;

  if (heading) heading.textContent = "Новая цель на Карту желаний";
  if (editId) editId.value = '';

  const spheres = await window.MockAPI.getSpheres();
  sphereSelect.innerHTML = spheres.map(s => `
    <option value="${s.id}" ${appState.selectedSphereId === s.id ? 'selected' : ''}>
      ${s.title}
    </option>
  `).join('');

  document.getElementById('goal-form').reset();
  if (document.getElementById('goal-cost-amount')) document.getElementById('goal-cost-amount').value = '';
  if (document.getElementById('goal-currency')) document.getElementById('goal-currency').value = appState.activeCurrency;
  stepsContainer.innerHTML = '';

  addStepInputToModal("Первый ключевой шаг", 1);
  addStepInputToModal("Второй шаг декомпозиции", 1);

  modal.classList.remove('hidden');
  document.body.classList.add('overflow-hidden');
  safeLucideIcons();
};

function addStepInputToModal(defaultVal = "", defaultWeight = 1) {
  const stepsContainer = document.getElementById('modal-steps-container');
  if (!stepsContainer) return;

  const stepRow = document.createElement('div');
  stepRow.className = "flex items-center gap-2";
  stepRow.innerHTML = `
    <input type="text" 
           name="step_title[]" 
           value="${escapeHTML(defaultVal)}" 
           placeholder="Действие чек-листа..." 
           required
           class="flex-1 px-3 py-2 text-xs rounded-xl border border-[#DADCE0] dark:border-[#374151] bg-white dark:bg-[#1F2937] text-[#202124] dark:text-white focus:border-[#1A73E8] outline-none">
    <select name="step_weight[]" class="px-2 py-2 text-xs rounded-xl border border-[#DADCE0] dark:border-[#374151] bg-white dark:bg-[#1F2937] text-[#202124] dark:text-white focus:border-[#1A73E8] outline-none">
      <option value="1" ${defaultWeight == 1 ? 'selected' : ''}>Вес: 1</option>
      <option value="2" ${defaultWeight == 2 ? 'selected' : ''}>Вес: 2</option>
      <option value="3" ${defaultWeight == 3 ? 'selected' : ''}>Вес: 3</option>
    </select>
    <button type="button" class="p-1.5 text-[#5F6368] hover:text-[#D93025]" onclick="this.parentElement.remove()">
      <i data-lucide="minus-circle" class="w-4 h-4"></i>
    </button>
  `;
  stepsContainer.appendChild(stepRow);
  safeLucideIcons();
}

async function handleCreateGoalSubmit(e) {
  e.preventDefault();

  const editId = document.getElementById('edit-goal-id') ? document.getElementById('edit-goal-id').value : '';
  const title = document.getElementById('goal-title').value;
  const sphereId = document.getElementById('goal-sphere-select').value;
  const description = document.getElementById('goal-desc').value;
  const imageUrl = document.getElementById('goal-image-url').value;
  const deadline = document.getElementById('goal-deadline').value;
  const priority = document.getElementById('goal-priority').value;
  const statusSelect = document.getElementById('goal-status-select');
  const status = statusSelect ? statusSelect.value : 'in_progress';

  const costAmountEl = document.getElementById('goal-cost-amount');
  const currencyEl = document.getElementById('goal-currency');
  const costAmount = costAmountEl ? Math.max(0, parseFloat(costAmountEl.value) || 0) : 0;
  const currency = currencyEl ? currencyEl.value : 'BYN';

  const stepTitles = Array.from(document.querySelectorAll('input[name="step_title[]"]')).map(i => i.value.trim()).filter(Boolean);
  const stepWeights = Array.from(document.querySelectorAll('select[name="step_weight[]"]')).map(s => parseInt(s.value, 10));

  const steps = stepTitles.map((t, idx) => ({
    title: t,
    weight: stepWeights[idx] || 1
  }));

  try {
    if (editId) {
      await window.MockAPI.updateGoal(editId, {
        title,
        sphere_id: sphereId,
        description,
        image_url: imageUrl,
        deadline: deadline || null,
        priority,
        status,
        cost_amount: costAmount,
        currency
      });
      showToast('Цель успешно обновлена в CMS', 'success');
    } else {
      await window.MockAPI.createGoal({
        title,
        sphere_id: sphereId,
        description,
        image_url: imageUrl,
        deadline: deadline || null,
        priority,
        cost_amount: costAmount,
        currency,
        steps
      });
      showToast('✨ Цель создана и добавлена на доску!', 'success');
    }

    document.getElementById('goal-modal').classList.add('hidden');
    document.body.classList.remove('overflow-hidden');

    await refreshAll();
    renderCMSGoals();
  } catch (error) {
    showToast('Ошибка: ' + error.message, 'error');
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast-item px-4 py-2.5 rounded-xl shadow-md border text-xs font-semibold flex items-center gap-2.5 bg-white dark:bg-[#111827]`;

  let icon = 'info';
  let borderClass = 'border-[#DADCE0] dark:border-[#374151] text-[#202124] dark:text-white';

  if (type === 'success') {
    icon = 'check-circle-2';
    borderClass = 'border-[#1E8E3E] text-[#1E8E3E] dark:text-emerald-400';
  } else if (type === 'celebration') {
    icon = 'party-popper';
    borderClass = 'border-[#1A73E8] text-[#1A73E8] bg-[#E8F0FE] dark:bg-blue-950/40 dark:text-blue-300';
  } else if (type === 'error') {
    icon = 'alert-triangle';
    borderClass = 'border-[#D93025] text-[#D93025]';
  }

  toast.classList.add(...borderClass.split(' '));
  toast.innerHTML = `
    <i data-lucide="${icon}" class="w-4 h-4 shrink-0"></i>
    <span>${escapeHTML(message)}</span>
  `;

  container.appendChild(toast);
  safeLucideIcons();

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    setTimeout(() => toast.remove(), 250);
  }, 3000);
}

/**
 * Рендеринг таблицы сфер жизни в CMS
 */
async function renderCMSSpheres() {
  const tbody = document.getElementById('cms-spheres-table-body');
  if (!tbody) return;

  const spheres = await window.MockAPI.getSpheres();

  tbody.innerHTML = spheres.map(s => `
    <tr>
      <td>
        <div class="flex items-center gap-2">
          <span class="w-4 h-4 rounded-full border border-black/10 shrink-0" style="background-color: ${s.color};"></span>
          <span class="text-[11px] font-mono text-[#5F6368]">${s.color}</span>
        </div>
      </td>
      <td>
        <div class="font-semibold text-xs text-[#202124] dark:text-white flex items-center gap-1.5">
          <i data-lucide="${s.icon || 'star'}" class="w-3.5 h-3.5" style="color: ${s.color};"></i>
          <span>${escapeHTML(s.title)}</span>
        </div>
      </td>
      <td>
        <span class="text-xs text-[#5F6368] dark:text-[#94A3B8] line-clamp-1 max-w-xs">
          ${escapeHTML(s.description || '—')}
        </span>
      </td>
      <td>
        <span class="text-xs font-semibold text-[#1A73E8] font-mono">${s.target_score}</span>
      </td>
      <td>
        <span class="text-xs font-bold font-mono" style="color: ${s.color};">
          ${s.current_score.toFixed(1)}
        </span>
      </td>
      <td>
        <span class="text-xs text-[#5F6368] dark:text-[#94A3B8] font-medium">${s.total_active_goals}</span>
      </td>
      <td style="text-align: right;">
        <div class="flex items-center justify-end gap-1">
          <button onclick="window.openSphereModal('${s.id}')" 
                  title="Редактировать сферу"
                  class="p-1 rounded-lg text-[#1A73E8] hover:bg-[#E8F0FE] dark:hover:bg-blue-950/50 transition-colors">
            <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
          </button>
          <button onclick="window.deleteSphereFromCMS('${s.id}')" 
                  title="Удалить сферу"
                  class="p-1 rounded-lg text-[#D93025] hover:bg-rose-50 dark:hover:bg-rose-950/50 transition-colors">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      </td>
    </tr>
  `).join('');

  safeLucideIcons();
}

/**
 * Открытие модалки создания/редактирования сферы
 */
window.openSphereModal = async (sphereId = null) => {
  const modal = document.getElementById('sphere-modal');
  const modalTitle = document.getElementById('sphere-modal-title');
  const idInput = document.getElementById('sphere-id-input');
  const titleInput = document.getElementById('sphere-title-input');
  const descInput = document.getElementById('sphere-desc-input');
  const colorPicker = document.getElementById('sphere-color-picker');
  const colorText = document.getElementById('sphere-color-text');
  const iconSelect = document.getElementById('sphere-icon-select');
  const targetInput = document.getElementById('sphere-target-input');
  const currentInput = document.getElementById('sphere-current-input');

  if (!modal) return;

  if (sphereId) {
    const spheres = await window.MockAPI.getSpheres();
    const sphere = spheres.find(s => s.id === sphereId);
    if (!sphere) return;

    modalTitle.textContent = "Редактирование сферы жизни";
    idInput.value = sphere.id;
    titleInput.value = sphere.title;
    descInput.value = sphere.description || '';
    colorPicker.value = sphere.color;
    colorText.value = sphere.color;
    iconSelect.value = sphere.icon || 'star';
    targetInput.value = sphere.target_score;
    currentInput.value = sphere.current_score;
  } else {
    modalTitle.textContent = "Новая сфера жизни";
    idInput.value = '';
    titleInput.value = '';
    descInput.value = '';
    colorPicker.value = '#3B82F6';
    colorText.value = '#3B82F6';
    iconSelect.value = 'briefcase';
    targetInput.value = '10';
    currentInput.value = '0';
  }

  modal.classList.remove('hidden');
  document.body.classList.add('overflow-hidden');
  safeLucideIcons();
};

/**
 * Сабмит формы сферы в CMS
 */
async function handleSphereFormSubmit(e) {
  e.preventDefault();

  const id = document.getElementById('sphere-id-input').value;
  const title = document.getElementById('sphere-title-input').value.trim();
  const description = document.getElementById('sphere-desc-input').value.trim();
  const color = document.getElementById('sphere-color-text').value.trim();
  const icon = document.getElementById('sphere-icon-select').value;
  const target_score = parseFloat(document.getElementById('sphere-target-input').value) || 10;
  const current_score = parseFloat(document.getElementById('sphere-current-input').value) || 0;

  try {
    if (id) {
      await window.MockAPI.updateSphere(id, {
        title,
        description,
        color,
        icon,
        target_score,
        current_score
      });
      showToast('Сфера жизни обновлена', 'success');
    } else {
      await window.MockAPI.createSphere({
        title,
        description,
        color,
        icon,
        target_score
      });
      showToast('Сфера жизни успешно создана', 'success');
    }

    document.getElementById('sphere-modal').classList.add('hidden');
    document.body.classList.remove('overflow-hidden');

    await refreshAll();
    renderCMSSpheres();
  } catch (err) {
    showToast('Ошибка сохранения сферы: ' + err.message, 'error');
  }
}

/**
 * Удаление сферы из CMS
 */
window.deleteSphereFromCMS = async (sphereId) => {
  if (!confirm('Вы уверены, что хотите удалить эту сферу? Все связанные с ней цели также будут удалены!')) return;

  try {
    await window.MockAPI.deleteSphere(sphereId);
    showToast('Сфера жизни удалена', 'info');
    await refreshAll();
    renderCMSSpheres();
    renderCMSGoals();
  } catch (err) {
    showToast('Ошибка удаления сферы: ' + err.message, 'error');
  }
};

/**
 * Рендеринг реестра целей в CMS
 */
async function renderCMSGoals() {
  const tbody = document.getElementById('cms-goals-table-body');
  if (!tbody) return;

  const statusFilter = document.getElementById('cms-goals-status-filter');
  const selectedStatus = statusFilter ? statusFilter.value : 'all';

  let goals = await window.MockAPI.getGoals({ status: selectedStatus });

  tbody.innerHTML = goals.map(g => {
    const isAchieved = g.status === 'achieved';
    const statusColor = g.status === 'achieved' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' :
                        g.status === 'in_progress' ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300' :
                        g.status === 'draft' ? 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300' :
                        'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300';

    return `
      <tr>
        <td>
          <div class="w-10 h-7 rounded bg-[#F1F3F4] dark:bg-slate-800 overflow-hidden shrink-0">
            ${g.image_url ? `<img src="${g.image_url}" class="w-full h-full object-cover">` : `<div class="w-full h-full flex items-center justify-center text-[10px] text-slate-400">🖼️</div>`}
          </div>
        </td>
        <td>
          <span class="font-semibold text-xs text-[#202124] dark:text-white line-clamp-1">
            ${escapeHTML(g.title)}
          </span>
        </td>
        <td>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#F8F9FA] dark:bg-[#1F2937] border border-[#DADCE0] dark:border-[#374151]">
            <span class="w-1.5 h-1.5 rounded-full" style="background-color: ${g.sphere_color};"></span>
            ${escapeHTML(g.sphere_title)}
          </span>
        </td>
        <td>
          ${getPriorityBadge(g.priority)}
        </td>
        <td>
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${statusColor}">
            ${g.status}
          </span>
        </td>
        <td>
          <div class="flex items-center gap-2">
            <span class="text-xs font-mono font-bold text-[#1A73E8]">${g.progress_percent}%</span>
            <div class="w-12 h-1.5 bg-[#E8EAED] dark:bg-slate-800 rounded-full overflow-hidden">
              <div class="h-full rounded-full ${isAchieved ? 'bg-[#1E8E3E]' : 'bg-[#1A73E8]'}" style="width: ${g.progress_percent}%;"></div>
            </div>
          </div>
        </td>
        <td>
          <span class="text-[11px] text-[#5F6368] dark:text-[#94A3B8] font-mono">
            ${g.deadline || '—'}
          </span>
        </td>
        <td>
          <span class="font-mono text-xs font-bold text-[#0D9488] dark:text-[#2DD4BF]" title="Бюджет цели">
            ${formatGoalBudget(g.cost_amount, g.currency, appState.activeCurrency, appState.fxRate)}
          </span>
        </td>
        <td style="text-align: right;">
          <div class="flex items-center justify-end gap-1">
            <button onclick="window.openEditGoalModal('${g.id}')" 
                    title="Редактировать цель"
                    class="p-1 rounded-lg text-[#1A73E8] hover:bg-[#E8F0FE] dark:hover:bg-blue-950/50 transition-colors">
              <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
            </button>
            <button onclick="window.handleDeleteGoal('${g.id}')" 
                    title="Удалить цель"
                    class="p-1 rounded-lg text-[#D93025] hover:bg-rose-50 dark:hover:bg-rose-950/50 transition-colors">
              <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  safeLucideIcons();
}

/**
 * Открытие формы редактирования цели в CMS
 */
window.openEditGoalModal = async (goalId) => {
  const modal = document.getElementById('goal-modal');
  const heading = document.getElementById('goal-modal-heading');
  const editId = document.getElementById('edit-goal-id');
  const titleInput = document.getElementById('goal-title');
  const sphereSelect = document.getElementById('goal-sphere-select');
  const prioritySelect = document.getElementById('goal-priority');
  const deadlineInput = document.getElementById('goal-deadline');
  const statusSelect = document.getElementById('goal-status-select');
  const imageInput = document.getElementById('goal-image-url');
  const descInput = document.getElementById('goal-desc');
  const stepsContainer = document.getElementById('modal-steps-container');

  if (!modal) return;

  const goals = await window.MockAPI.getGoals();
  const goal = goals.find(g => g.id === goalId);
  if (!goal) return;

  const spheres = await window.MockAPI.getSpheres();
  sphereSelect.innerHTML = spheres.map(s => `
    <option value="${s.id}" ${s.id === goal.sphere_id ? 'selected' : ''}>
      ${s.title}
    </option>
  `).join('');

  heading.textContent = "Редактирование цели в CMS";
  editId.value = goal.id;
  titleInput.value = goal.title;
  prioritySelect.value = goal.priority;
  deadlineInput.value = goal.deadline || '';
  if (statusSelect) statusSelect.value = goal.status || 'in_progress';
  if (document.getElementById('goal-cost-amount')) {
    document.getElementById('goal-cost-amount').value = goal.cost_amount !== undefined ? goal.cost_amount : 0;
  }
  if (document.getElementById('goal-currency')) {
    document.getElementById('goal-currency').value = goal.currency || 'BYN';
  }
  imageInput.value = goal.image_url || '';
  descInput.value = goal.description || '';

  stepsContainer.innerHTML = '';
  if (goal.steps && goal.steps.length > 0) {
    goal.steps.forEach(st => {
      addStepInputToModal(st.title, st.weight);
    });
  } else {
    addStepInputToModal("Первый шаг декомпозиции", 1);
  }

  modal.classList.remove('hidden');
  document.body.classList.add('overflow-hidden');
  safeLucideIcons();
};

function escapeHTML(str) {
  if (!str) return '';
  return str.replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}

/**
 * Ролевой контроль доступа (RBAC: UC-4)
 */
function applyRBAC() {
  const currentUser = appState.currentUser || window.MockAPI.getCurrentUser();
  appState.currentUser = currentUser;

  const headerAvatar = document.getElementById('header-user-avatar');
  const headerName = document.getElementById('header-user-name');
  const headerBadge = document.getElementById('header-user-role-badge');
  const modeCmsBtn = document.getElementById('nav-mode-cms-btn');
  const mobileModeToggleBtn = document.getElementById('mobile-mode-toggle-btn');
  const navContainer = document.getElementById('header-nav-mode-container');

  // Обновление профиля в хедере
  if (headerAvatar && currentUser.avatar_url) {
    headerAvatar.src = currentUser.avatar_url;
  }
  if (headerName) {
    headerName.textContent = currentUser.name ? currentUser.name.split(' ')[0] : 'Профиль';
  }
  if (headerBadge) {
    if (currentUser.role === 'admin') {
      headerBadge.textContent = 'Admin';
      headerBadge.className = 'px-1.5 py-0.2 rounded text-[9px] font-extrabold uppercase tracking-wider bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300';
    } else if (currentUser.role === 'user') {
      headerBadge.textContent = 'User';
      headerBadge.className = 'px-1.5 py-0.2 rounded text-[9px] font-extrabold uppercase tracking-wider bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300';
    } else {
      headerBadge.textContent = 'Guest';
      headerBadge.className = 'px-1.5 py-0.2 rounded text-[9px] font-extrabold uppercase tracking-wider bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300';
    }
  }

  // Ролевое скрытие/отображение кнопки CMS
  if (currentUser.role === 'admin') {
    if (modeCmsBtn) modeCmsBtn.classList.remove('hidden');
    if (mobileModeToggleBtn) mobileModeToggleBtn.classList.remove('hidden');
    if (navContainer) navContainer.classList.remove('hidden');
  } else {
    if (modeCmsBtn) modeCmsBtn.classList.add('hidden');
    if (mobileModeToggleBtn) mobileModeToggleBtn.classList.add('hidden');
    // Если пользователь был в режиме CMS, принудительно возвращаем на дашборд
    if (appState.currentMode === 'cms' || (document.getElementById('cms-view') && !document.getElementById('cms-view').classList.contains('hidden'))) {
      if (typeof window.setAppMode === 'function') {
        window.setAppMode('dashboard');
      }
    }
  }

  safeLucideIcons();
}

/**
 * Управление окном авторизации и сменой профилей (RBAC)
 */
window.openAuthModal = function() {
  const modal = document.getElementById('auth-modal');
  if (!modal) return;

  const currentUser = appState.currentUser || window.MockAPI.getCurrentUser();
  const avatarEl = document.getElementById('auth-modal-user-avatar');
  const nameEl = document.getElementById('auth-modal-user-name');
  const emailEl = document.getElementById('auth-modal-user-email');
  const badgeEl = document.getElementById('auth-modal-user-badge');
  const hintEl = document.getElementById('auth-modal-permissions-hint');

  if (avatarEl) avatarEl.src = currentUser.avatar_url || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=200&q=80';
  if (nameEl) nameEl.textContent = currentUser.name;
  if (emailEl) emailEl.textContent = currentUser.email;

  if (badgeEl) {
    if (currentUser.role === 'admin') {
      badgeEl.textContent = 'Администратор (Admin)';
      badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300';
    } else if (currentUser.role === 'user') {
      badgeEl.textContent = 'Пользователь (User)';
      badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300';
    } else {
      badgeEl.textContent = 'Гость (Guest)';
      badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300';
    }
  }

  if (hintEl) {
    if (currentUser.role === 'admin') {
      hintEl.innerHTML = `<strong>🟢 Полный доступ (Admin):</strong> Доступен весь функционал — витрина целей, колесо баланса, справочник сфер, управление реестром и выгрузка SQL/JSON в панели CMS.`;
      hintEl.className = "text-[11px] leading-relaxed p-3 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200";
    } else {
      hintEl.innerHTML = `<strong>🔵 Пользовательский доступ (User):</strong> Доступна интерактивная карта желаний, отметка шагов чек-листа и радар баланса. Панель CMS защищена и скрыта.`;
      hintEl.className = "text-[11px] leading-relaxed p-3 rounded-xl bg-blue-50/70 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 text-blue-900 dark:text-blue-200";
    }
  }

  modal.classList.remove('hidden');
  document.body.classList.add('overflow-hidden');
  safeLucideIcons();
};

window.closeAuthModal = function() {
  const modal = document.getElementById('auth-modal');
  if (modal) {
    modal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  }
};

window.switchDemoUser = async function(email) {
  try {
    const authResult = await window.MockAPI.login(email);
    appState.currentUser = authResult.user;
    applyRBAC();
    window.closeAuthModal();
    showToast(`✨ Вы авторизованы как ${authResult.user.name} (${authResult.user.role.toUpperCase()})`, 'success');
  } catch (e) {
    showToast('Ошибка авторизации: ' + e.message, 'error');
  }
};

window.logoutUserSession = async function() {
  try {
    const guest = await window.MockAPI.logout();
    appState.currentUser = guest;
    applyRBAC();
    window.closeAuthModal();
    showToast('Вы вышли из системы (режим Гостя)', 'info');
  } catch (e) {
    showToast('Ошибка выхода: ' + e.message, 'error');
  }
};

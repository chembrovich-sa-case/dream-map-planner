/**
 * Слой эмуляции REST API сервиса «Горизонт»
 * Соответствует контракту OpenAPI 3.0.3 (docs/api/openapi.yaml)
 * Хранит данные в localStorage с защитой от сбоев и возможностью сброса к демо-данным.
 * Полностью совместим с открытием через протокол file:// (без ES-модулей, import и export).
 */

const STORAGE_KEY = 'horizont_planner_state_v1';

// Безопасный генератор UUID (работает и при file://, где crypto.randomUUID может быть недоступен)
function generateSafeUUID(prefix = '') {
  let uuid = null;
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    try {
      uuid = crypto.randomUUID();
    } catch (e) {
      uuid = null;
    }
  }
  if (!uuid) {
    uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
  return prefix ? prefix + uuid.slice(prefix.length) : uuid;
}

// Базовые демо-данные (синхронизированы со схемой database/schema.sql)
const DEFAULT_STATE = {
  spheres: [
    {
      id: "b0000000-0000-0000-0000-000000000001",
      user_id: "a0000000-0000-0000-0000-000000000001",
      title: "Карьера и бизнес",
      description: "Профессиональный рост, руководящие роли, масштабные рабочие проекты",
      color: "#3B82F6",
      icon: "briefcase",
      target_score: 10.0,
      current_score: 6.7,
      sort_order: 1
    },
    {
      id: "b0000000-0000-0000-0000-000000000002",
      user_id: "a0000000-0000-0000-0000-000000000001",
      title: "Финансы и капитал",
      description: "Личный бюджет, подушка безопасности и инвестиционный портфель",
      color: "#10B981",
      icon: "wallet",
      target_score: 10.0,
      current_score: 7.5,
      sort_order: 2
    },
    {
      id: "b0000000-0000-0000-0000-000000000003",
      user_id: "a0000000-0000-0000-0000-000000000001",
      title: "Здоровье и спорт",
      description: "Физическая форма, бег, сон, правильное питание и чекапы",
      color: "#EF4444",
      icon: "heart-pulse",
      target_score: 10.0,
      current_score: 5.0,
      sort_order: 3
    },
    {
      id: "b0000000-0000-0000-0000-000000000004",
      user_id: "a0000000-0000-0000-0000-000000000001",
      title: "Семья и отношения",
      description: "Качественное время с близкими, романтические свидания и традиции",
      color: "#EC4899",
      icon: "users",
      target_score: 10.0,
      current_score: 8.0,
      sort_order: 4
    },
    {
      id: "b0000000-0000-0000-0000-000000000005",
      user_id: "a0000000-0000-0000-0000-000000000001",
      title: "Личностный рост",
      description: "Чтение книг, изучение языков, системное мышление и привычки",
      color: "#8B5CF6",
      icon: "book-open",
      target_score: 10.0,
      current_score: 4.0,
      sort_order: 5
    },
    {
      id: "b0000000-0000-0000-0000-000000000006",
      user_id: "a0000000-0000-0000-0000-000000000001",
      title: "Яркость жизни",
      description: "Новые впечатления, поездки в горы, активный отдых и хобби",
      color: "#F59E0B",
      icon: "plane",
      target_score: 10.0,
      current_score: 3.3,
      sort_order: 6
    }
  ],
  goals: [
    {
      id: "c0000000-0000-0000-0000-000000000001",
      user_id: "a0000000-0000-0000-0000-000000000001",
      sphere_id: "b0000000-0000-0000-0000-000000000003", // Здоровье и спорт
      title: "Пробежать первый полумарафон (21.1 км)",
      description: "Подготовиться по плану тренера, пройти чекап и финишировать быстрее 1:55:00",
      image_url: "https://images.unsplash.com/photo-1452626038306-9aae5e071dd3?auto=format&fit=crop&w=800&q=80",
      deadline: "2027-05-20",
      priority: "high",
      status: "in_progress",
      progress_percent: 50,
      cost_amount: 850,
      currency: "BYN",
      created_at: "2026-10-01T09:00:00Z",
      completed_at: null,
      steps: [
        {
          id: "d0000000-0000-0000-0000-000000000001",
          title: "Пройти спортивный чекап сердца (ЭКГ под нагрузкой)",
          is_completed: true,
          sort_order: 1,
          weight: 1,
          completed_at: "2026-10-09T10:00:00Z"
        },
        {
          id: "d0000000-0000-0000-0000-000000000002",
          title: "Подобрать кроссовки с профессиональным гайт-анализом",
          is_completed: true,
          sort_order: 2,
          weight: 1,
          completed_at: "2026-10-14T15:00:00Z"
        },
        {
          id: "d0000000-0000-0000-0000-000000000003",
          title: "Пробежать тестовую длинную тренировку 16 км",
          is_completed: false,
          sort_order: 3,
          weight: 1,
          completed_at: null
        },
        {
          id: "d0000000-0000-0000-0000-000000000004",
          title: "Зарегистрироваться на полумарафон «Северная столица»",
          is_completed: false,
          sort_order: 4,
          weight: 1,
          completed_at: null
        }
      ]
    },
    {
      id: "c0000000-0000-0000-0000-000000000002",
      user_id: "a0000000-0000-0000-0000-000000000001",
      sphere_id: "b0000000-0000-0000-0000-000000000001", // Карьера и бизнес
      title: "Перейти на позицию Lead Architect",
      description: "Сформировать техническую стратегию платформы, защитить роадмап перед бизнесом",
      image_url: "https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=800&q=80",
      deadline: "2027-03-31",
      priority: "critical",
      status: "in_progress",
      progress_percent: 67,
      cost_amount: 600,
      currency: "USD",
      created_at: "2026-09-15T10:00:00Z",
      completed_at: null,
      steps: [
        {
          id: "d0000000-0000-0000-0000-000000000005",
          title: "Пройти сертификацию по облачной архитектуре и системному дизайну",
          is_completed: true,
          sort_order: 1,
          weight: 2,
          completed_at: "2026-10-04T12:00:00Z"
        },
        {
          id: "d0000000-0000-0000-0000-000000000006",
          title: "Разработать целевую архитектуру сервисов и ADR-документы",
          is_completed: true,
          sort_order: 2,
          weight: 2,
          completed_at: "2026-10-19T14:30:00Z"
        },
        {
          id: "d0000000-0000-0000-0000-000000000007",
          title: "Защитить стратегию перед CTO и топ-менеджментом",
          is_completed: false,
          sort_order: 3,
          weight: 2,
          completed_at: null
        }
      ]
    },
    {
      id: "c0000000-0000-0000-0000-000000000003",
      user_id: "a0000000-0000-0000-0000-000000000001",
      sphere_id: "b0000000-0000-0000-0000-000000000002", // Финансы
      title: "Сформировать финансовую подушку на 20 000 BYN",
      description: "Обеспечить неприкосновенный запас на 6 месяцев расходов на накопительном счете",
      image_url: "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?auto=format&fit=crop&w=800&q=80",
      deadline: "2026-12-31",
      priority: "high",
      status: "in_progress",
      progress_percent: 75,
      cost_amount: 20000,
      currency: "BYN",
      created_at: "2026-08-01T12:00:00Z",
      completed_at: null,
      steps: [
        {
          id: "d0000000-0000-0000-0000-000000000008",
          title: "Рассчитать точный семейный бюджет обязательных расходов",
          is_completed: true,
          sort_order: 1,
          weight: 1,
          completed_at: "2026-08-10T11:00:00Z"
        },
        {
          id: "d0000000-0000-0000-0000-000000000009",
          title: "Накопить первые 7 000 BYN",
          is_completed: true,
          sort_order: 2,
          weight: 1,
          completed_at: "2026-09-01T18:00:00Z"
        },
        {
          id: "d0000000-0000-0000-0000-000000000010",
          title: "Довести сумму на счете до 14 000 BYN",
          is_completed: true,
          sort_order: 3,
          weight: 1,
          completed_at: "2026-10-15T16:00:00Z"
        },
        {
          id: "d0000000-0000-0000-0000-000000000011",
          title: "Закрыть финальную планку — 20 000 BYN",
          is_completed: false,
          sort_order: 4,
          weight: 1,
          completed_at: null
        }
      ]
    },
    {
      id: "c0000000-0000-0000-0000-000000000004",
      user_id: "a0000000-0000-0000-0000-000000000001",
      sphere_id: "b0000000-0000-0000-0000-000000000006", // Яркость жизни
      title: "Экспедиция на Камчатку: вулканы и океан",
      description: "Увидеть Авачинскую бухту, совершить подъем на Мутновский вулкан и серфинг на Халактырском пляже",
      image_url: "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80",
      deadline: "2027-08-15",
      priority: "medium",
      status: "in_progress",
      progress_percent: 33,
      cost_amount: 2500,
      currency: "USD",
      created_at: "2026-09-20T10:00:00Z",
      completed_at: null,
      steps: [
        {
          id: "d0000000-0000-0000-0000-000000000012",
          title: "Выбрать сезон и забронировать даты в экспедиционной группе",
          is_completed: true,
          sort_order: 1,
          weight: 1,
          completed_at: "2026-10-10T12:00:00Z"
        },
        {
          id: "d0000000-0000-0000-0000-000000000013",
          title: "Купить авиабилеты Москва — Петропавловск-Камчатский",
          is_completed: false,
          sort_order: 2,
          weight: 1,
          completed_at: null
        },
        {
          id: "d0000000-0000-0000-0000-000000000014",
          title: "Подготовить мембранную трекинговую одежду и ботинки",
          is_completed: false,
          sort_order: 3,
          weight: 1,
          completed_at: null
        }
      ]
    },
    {
      id: "c0000000-0000-0000-0000-000000000005",
      user_id: "a0000000-0000-0000-0000-000000000001",
      sphere_id: "b0000000-0000-0000-0000-000000000004", // Семья и отношения
      title: "Семейное путешествие в Карелию на годовщину",
      description: "Арендовать деревянный дом у Ладожского озера, покататься на лодках и устроить праздничный ужин",
      image_url: "https://images.unsplash.com/photo-1510312305653-8ed496efae75?auto=format&fit=crop&w=800&q=80",
      deadline: "2026-11-20",
      priority: "high",
      status: "in_progress",
      progress_percent: 67,
      cost_amount: 1400,
      currency: "BYN",
      created_at: "2026-10-05T14:00:00Z",
      completed_at: null,
      steps: [
        {
          id: "d0000000-0000-0000-0000-000000000015",
          title: "Согласовать даты поездки со всеми членами семьи",
          is_completed: true,
          sort_order: 1,
          weight: 1,
          completed_at: "2026-10-08T12:00:00Z"
        },
        {
          id: "d0000000-0000-0000-0000-000000000016",
          title: "Забронировать панорамный коттедж в шхерах",
          is_completed: true,
          sort_order: 2,
          weight: 1,
          completed_at: "2026-10-12T16:00:00Z"
        },
        {
          id: "d0000000-0000-0000-0000-000000000017",
          title: "Купить билеты на ретро-поезд «Рускеальский экспресс»",
          is_completed: false,
          sort_order: 3,
          weight: 1,
          completed_at: null
        }
      ]
    },
    {
      id: "c0000000-0000-0000-0000-000000000006",
      user_id: "a0000000-0000-0000-0000-000000000001",
      sphere_id: "b0000000-0000-0000-0000-000000000005", // Личностный рост
      title: "Прочитать 12 книг по системному мышлению",
      description: "Внедрить конспектирование ключевых ментальных моделей и применение в работе",
      image_url: "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?auto=format&fit=crop&w=800&q=80",
      deadline: "2027-01-31",
      priority: "medium",
      status: "in_progress",
      progress_percent: 50,
      cost_amount: 320,
      currency: "BYN",
      created_at: "2026-09-01T10:00:00Z",
      completed_at: null,
      steps: [
        {
          id: "d0000000-0000-0000-0000-000000000018",
          title: "Составить список литературы (Донелла Медоуз, Питер Сенге, Нассим Талеб)",
          is_completed: true,
          sort_order: 1,
          weight: 1,
          completed_at: "2026-09-05T11:00:00Z"
        },
        {
          id: "d0000000-0000-0000-0000-000000000019",
          title: "Прочитать первые 4 книги и оформить цифровые конспекты",
          is_completed: true,
          sort_order: 2,
          weight: 2,
          completed_at: "2026-10-18T19:00:00Z"
        },
        {
          id: "d0000000-0000-0000-0000-000000000020",
          title: "Прочитать книги с 5 по 8",
          is_completed: false,
          sort_order: 3,
          weight: 2,
          completed_at: null
        },
        {
          id: "d0000000-0000-0000-0000-000000000021",
          title: "Прочитать финальные 4 книги и написать годовой обзор инсайтов",
          is_completed: false,
          sort_order: 4,
          weight: 2,
          completed_at: null
        }
      ]
    }
  ],
  balance_snapshots: [
    {
      id: "e0000000-0000-0000-0000-000000000001",
      user_id: "a0000000-0000-0000-0000-000000000001",
      overall_harmony_index: 0.65,
      notes: "Стартовая оценка баланса перед началом года",
      recorded_at: new Date(Date.now() - 30 * 86400000).toISOString(),
      created_at: new Date(Date.now() - 30 * 86400000).toISOString(),
      items: [
        { id: "f0000000-0000-0000-0000-000000000001", sphere_id: "b0000000-0000-0000-0000-000000000001", score: 4.0, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000002", sphere_id: "b0000000-0000-0000-0000-000000000002", score: 3.5, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000003", sphere_id: "b0000000-0000-0000-0000-000000000003", score: 3.0, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000004", sphere_id: "b0000000-0000-0000-0000-000000000004", score: 6.0, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000005", sphere_id: "b0000000-0000-0000-0000-000000000005", score: 4.0, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000006", sphere_id: "b0000000-0000-0000-0000-000000000006", score: 3.0, target_score: 10.0 }
      ]
    },
    {
      id: "e0000000-0000-0000-0000-000000000002",
      user_id: "a0000000-0000-0000-0000-000000000001",
      overall_harmony_index: 0.72,
      notes: "Прогресс в карьере и регулярные тренировки",
      recorded_at: new Date(Date.now() - 20 * 86400000).toISOString(),
      created_at: new Date(Date.now() - 20 * 86400000).toISOString(),
      items: [
        { id: "f0000000-0000-0000-0000-000000000007", sphere_id: "b0000000-0000-0000-0000-000000000001", score: 5.5, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000008", sphere_id: "b0000000-0000-0000-0000-000000000002", score: 4.0, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000009", sphere_id: "b0000000-0000-0000-0000-000000000003", score: 4.5, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000010", sphere_id: "b0000000-0000-0000-0000-000000000004", score: 6.5, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000011", sphere_id: "b0000000-0000-0000-0000-000000000005", score: 5.0, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000012", sphere_id: "b0000000-0000-0000-0000-000000000006", score: 3.5, target_score: 10.0 }
      ]
    },
    {
      id: "e0000000-0000-0000-0000-000000000003",
      user_id: "a0000000-0000-0000-0000-000000000001",
      overall_harmony_index: 0.79,
      notes: "Повышение дохода и закрытие чек-листов",
      recorded_at: new Date(Date.now() - 10 * 86400000).toISOString(),
      created_at: new Date(Date.now() - 10 * 86400000).toISOString(),
      items: [
        { id: "f0000000-0000-0000-0000-000000000013", sphere_id: "b0000000-0000-0000-0000-000000000001", score: 6.5, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000014", sphere_id: "b0000000-0000-0000-0000-000000000002", score: 6.0, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000015", sphere_id: "b0000000-0000-0000-0000-000000000003", score: 5.0, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000016", sphere_id: "b0000000-0000-0000-0000-000000000004", score: 7.5, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000017", sphere_id: "b0000000-0000-0000-0000-000000000005", score: 5.5, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000018", sphere_id: "b0000000-0000-0000-0000-000000000006", score: 4.0, target_score: 10.0 }
      ]
    },
    {
      id: "e0000000-0000-0000-0000-000000000004",
      user_id: "a0000000-0000-0000-0000-000000000001",
      overall_harmony_index: 0.85,
      notes: "Текущее гармоничное состояние колеса",
      recorded_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      items: [
        { id: "f0000000-0000-0000-0000-000000000019", sphere_id: "b0000000-0000-0000-0000-000000000001", score: 6.7, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000020", sphere_id: "b0000000-0000-0000-0000-000000000002", score: 7.5, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000021", sphere_id: "b0000000-0000-0000-0000-000000000003", score: 5.0, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000022", sphere_id: "b0000000-0000-0000-0000-000000000004", score: 8.0, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000023", sphere_id: "b0000000-0000-0000-0000-000000000005", score: 6.0, target_score: 10.0 },
        { id: "f0000000-0000-0000-0000-000000000024", sphere_id: "b0000000-0000-0000-0000-000000000006", score: 4.5, target_score: 10.0 }
      ]
    }
  ]
};

class MockDatabase {
  constructor() {
    this.init();
  }

  init() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      this.state = JSON.parse(JSON.stringify(DEFAULT_STATE));
      this.save();
    } else {
      try {
        this.state = JSON.parse(raw);
        if (!this.state.spheres || !this.state.goals) {
          throw new Error("Неполные данные");
        }
        // Авто-миграция существующих данных на мультивалютность (BYN / USD)
        this.state.goals.forEach(g => {
          if (g.cost_amount === undefined || g.cost_amount === null) {
            g.cost_amount = (g.currency === 'USD' ? 500 : 850);
          }
          if (!g.currency) {
            g.currency = 'BYN';
          }
          if (g.title && g.title.includes('₽')) {
            g.title = g.title.replace(/600\s*000\s*₽/g, '20 000 BYN');
          }
          if (g.steps) {
            g.steps.forEach(st => {
              if (st.title && st.title.includes('₽')) {
                st.title = st.title
                  .replace(/200\s*000\s*₽/g, '7 000 BYN')
                  .replace(/400\s*000\s*₽/g, '14 000 BYN')
                  .replace(/600\s*000\s*₽/g, '20 000 BYN');
              }
            });
          }
        });
        if (!this.state.balance_snapshots || !Array.isArray(this.state.balance_snapshots) || this.state.balance_snapshots.length === 0) {
          this.state.balance_snapshots = JSON.parse(JSON.stringify(DEFAULT_STATE.balance_snapshots));
        }
      } catch (e) {
        console.error("Ошибка парсинга localStorage, сброс к дефолту:", e);
        this.state = JSON.parse(JSON.stringify(DEFAULT_STATE));
        this.save();
      }
    }
    this.recalculateAll();
  }

  save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
    } catch (e) {
      console.warn("Не удалось сохранить в localStorage:", e);
    }
  }

  reset() {
    this.state = JSON.parse(JSON.stringify(DEFAULT_STATE));
    this.recalculateAll();
    this.save();
  }

  getPriorityWeight(priority) {
    switch (priority) {
      case 'critical': return 4;
      case 'high': return 3;
      case 'medium': return 2;
      case 'low': return 1;
      default: return 2;
    }
  }

  recalculateGoalProgress(goal) {
    if (!goal.steps || goal.steps.length === 0) {
      goal.progress_percent = goal.status === 'achieved' ? 100 : 0;
      return goal.progress_percent;
    }

    const totalWeight = goal.steps.reduce((acc, step) => acc + (step.weight || 1), 0);
    const completedWeight = goal.steps
      .filter(step => step.is_completed)
      .reduce((acc, step) => acc + (step.weight || 1), 0);

    if (totalWeight === 0) {
      goal.progress_percent = goal.status === 'achieved' ? 100 : 0;
    } else {
      goal.progress_percent = Math.round((completedWeight / totalWeight) * 100);
    }

    if (goal.progress_percent === 100) {
      goal.status = 'achieved';
      if (!goal.completed_at) {
        goal.completed_at = new Date().toISOString();
      }
    } else {
      if (goal.status === 'achieved') {
        goal.status = 'in_progress';
        goal.completed_at = null;
      }
    }

    return goal.progress_percent;
  }

  recalculateSphereScore(sphereId) {
    const sphere = this.state.spheres.find(s => s.id === sphereId);
    if (!sphere) return 0;

    const activeGoals = this.state.goals.filter(
      g => g.sphere_id === sphereId && g.status !== 'archived'
    );

    if (activeGoals.length === 0) {
      sphere.current_score = 0.0;
      return 0.0;
    }

    let sumPriorityWeights = 0;
    let sumWeightedProgress = 0;

    activeGoals.forEach(goal => {
      const weight = this.getPriorityWeight(goal.priority);
      sumPriorityWeights += weight;
      sumWeightedProgress += (goal.progress_percent / 100) * weight;
    });

    if (sumPriorityWeights === 0) {
      sphere.current_score = 0.0;
    } else {
      const calculated = (sumWeightedProgress / sumPriorityWeights) * 10;
      sphere.current_score = Math.min(10.0, Math.round(calculated * 10) / 10);
    }

    return sphere.current_score;
  }

  recalculateAll() {
    this.state.goals.forEach(goal => this.recalculateGoalProgress(goal));
    this.state.spheres.forEach(sphere => this.recalculateSphereScore(sphere.id));
    this.save();
  }

  calculateOverallHarmonyIndex() {
    const scores = this.state.spheres.map(s => s.current_score);
    if (scores.length === 0) return 1.0;

    const mean = scores.reduce((a, b) => a + b, 0) / scores.length;
    if (mean === 0) return 0.5;

    const variance = scores.reduce((sum, score) => sum + Math.pow(score - mean, 2), 0) / scores.length;
    const stdDev = Math.sqrt(variance);

    const rawHarmony = 1.0 - (stdDev / 5.0);
    const harmony = Math.max(0.1, Math.min(1.0, rawHarmony));
    return Math.round(harmony * 100) / 100;
  }
}

// Демо-пользователи системы с ролями RBAC (UC-4)
const DEMO_USERS = [
  {
    id: "a0000000-0000-0000-0000-000000000000",
    email: "admin@horizon.app",
    name: "Алексей Администраторов",
    role: "admin",
    avatar_url: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=200&q=80"
  },
  {
    id: "a0000000-0000-0000-0000-000000000001",
    email: "user@horizon.app",
    name: "Иван Горизонтов",
    role: "user",
    avatar_url: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80"
  }
];

const db = new MockDatabase();

/**
 * Глобальный объект window.MockAPI — внешний интерфейс по контракту OpenAPI
 */
window.MockAPI = {
  // ============================================================================
  // АУТЕНТИФИКАЦИЯ И РОЛЕВАЯ МОДЕЛЬ (RBAC: UC-4)
  // ============================================================================
  getCurrentUser() {
    try {
      const raw = localStorage.getItem('horizont_current_user');
      if (raw) return JSON.parse(raw);
    } catch (e) {
      console.warn("Ошибка чтения текущего пользователя:", e);
    }
    const defaultUser = DEMO_USERS[0];
    localStorage.setItem('horizont_current_user', JSON.stringify(defaultUser));
    return defaultUser;
  },

  async login(email) {
    const target = DEMO_USERS.find(u => u.email.toLowerCase() === email.toLowerCase());
    if (!target) {
      throw new Error(`Пользователь ${email} не найден`);
    }
    localStorage.setItem('horizont_current_user', JSON.stringify(target));
    return {
      token: "mock-jwt-" + btoa(target.email),
      user: target,
      expires_at: new Date(Date.now() + 86400000).toISOString()
    };
  },

  async logout() {
    const guestUser = {
      id: "a0000000-0000-0000-0000-000000000002",
      email: "guest@horizon.app",
      name: "Гость",
      role: "guest",
      avatar_url: null
    };
    localStorage.setItem('horizont_current_user', JSON.stringify(guestUser));
    return guestUser;
  },

  getDemoUsers() {
    return DEMO_USERS;
  },
  checkAdmin() {
    const user = this.getCurrentUser();
    if (!user || user.role !== 'admin') {
      throw new Error("403 Forbidden: Операция доступна только администраторам системы");
    }
  },
  // GET /spheres
  async getSpheres() {
    return db.state.spheres.map(s => {
      const activeGoals = db.state.goals.filter(g => g.sphere_id === s.id && g.status !== 'archived');
      return {
        ...s,
        total_active_goals: activeGoals.length
      };
    });
  },

  // POST /spheres
  async createSphere(sphereData) {
    this.checkAdmin();
    const newSphere = {
      id: generateSafeUUID('b'),
      user_id: "a0000000-0000-0000-0000-000000000001",
      title: sphereData.title,
      description: sphereData.description || null,
      color: sphereData.color,
      icon: sphereData.icon || "star",
      target_score: sphereData.target_score || 10.0,
      current_score: 0.0,
      sort_order: sphereData.sort_order || (db.state.spheres.length + 1)
    };
    db.state.spheres.push(newSphere);
    db.save();
    return newSphere;
  },

  // PATCH /spheres/{id}
  async updateSphere(id, updateData) {
    this.checkAdmin();
    const sphere = db.state.spheres.find(s => s.id === id);
    if (!sphere) throw new Error("Сфера жизни не найдена");

    Object.assign(sphere, updateData);
    if (updateData.target_score !== undefined || updateData.current_score !== undefined) {
      if (updateData.current_score !== undefined) {
        sphere.current_score = parseFloat(updateData.current_score);
      }
      if (updateData.target_score !== undefined) {
        sphere.target_score = parseFloat(updateData.target_score);
      }
    }
    db.save();
    return sphere;
  },

  // DELETE /spheres/{id}
  async deleteSphere(id) {
    this.checkAdmin();
    const idx = db.state.spheres.findIndex(s => s.id === id);
    if (idx === -1) throw new Error("Сфера жизни не найдена");

    // Каскадно удаляем связанные цели
    db.state.goals = db.state.goals.filter(g => g.sphere_id !== id);
    db.state.spheres.splice(idx, 1);
    db.recalculateAll();
    db.save();
    return { success: true, message: "Сфера жизни и привязанные цели успешно удалены" };
  },

  // GET /goals
  async getGoals({ sphereId = null, status = null } = {}) {
    let result = [...db.state.goals];
    if (sphereId) {
      result = result.filter(g => g.sphere_id === sphereId);
    }
    if (status && status !== 'all') {
      result = result.filter(g => g.status === status);
    }

    return result.map(goal => {
      const sphere = db.state.spheres.find(s => s.id === goal.sphere_id);
      return {
        ...goal,
        sphere_title: sphere ? sphere.title : "Без сферы",
        sphere_color: sphere ? sphere.color : "#94a3b8",
        sphere_icon: sphere ? sphere.icon : "circle",
        steps_count: goal.steps.length,
        completed_steps_count: goal.steps.filter(s => s.is_completed).length
      };
    });
  },

  // GET /goals/{id} (UC-5: Детальный просмотр карточки цели)
  async getGoalById(id) {
    const goal = db.state.goals.find(g => g.id === id);
    if (!goal) return null;
    const sphere = db.state.spheres.find(s => s.id === goal.sphere_id);
    return {
      ...goal,
      sphere_title: sphere ? sphere.title : "Без сферы",
      sphere_color: sphere ? sphere.color : "#94a3b8",
      sphere_icon: sphere ? sphere.icon : "circle",
      steps_count: goal.steps.length,
      completed_steps_count: goal.steps.filter(s => s.is_completed).length
    };
  },

  // POST /goals (UC-1: Создание карточки цели)
  async createGoal(goalData) {
    if (!goalData.title || !goalData.sphere_id) {
      throw new Error("Заголовок цели и сфера обязательны для заполнения");
    }

    const steps = (goalData.steps || []).map((step, idx) => ({
      id: generateSafeUUID('d'),
      title: step.title,
      is_completed: false,
      sort_order: idx + 1,
      weight: parseInt(step.weight, 10) || 1,
      completed_at: null
    }));

    const newGoal = {
      id: generateSafeUUID('c'),
      user_id: "a0000000-0000-0000-0000-000000000001",
      sphere_id: goalData.sphere_id,
      title: goalData.title.trim(),
      description: goalData.description ? goalData.description.trim() : "",
      image_url: goalData.image_url || null,
      deadline: goalData.deadline || null,
      priority: goalData.priority || "medium",
      status: "in_progress",
      progress_percent: 0,
      cost_amount: Math.max(0, parseFloat(goalData.cost_amount) || 0),
      currency: (goalData.currency === 'USD' ? 'USD' : 'BYN'),
      created_at: new Date().toISOString(),
      completed_at: null,
      steps: steps
    };

    db.state.goals.unshift(newGoal);
    db.recalculateGoalProgress(newGoal);
    db.recalculateSphereScore(newGoal.sphere_id);
    db.save();

    return newGoal;
  },

  // PATCH /goals/{id}
  async updateGoal(id, updateData) {
    const goal = db.state.goals.find(g => g.id === id);
    if (!goal) throw new Error("Цель не найдена");

    Object.assign(goal, updateData);
    db.recalculateGoalProgress(goal);
    db.recalculateSphereScore(goal.sphere_id);
    db.save();
    return goal;
  },

  // DELETE /goals/{id}
  async deleteGoal(id) {
    const goalIndex = db.state.goals.findIndex(g => g.id === id);
    if (goalIndex === -1) throw new Error("Цель не найдена");

    const sphereId = db.state.goals[goalIndex].sphere_id;
    db.state.goals.splice(goalIndex, 1);
    db.recalculateSphereScore(sphereId);
    db.save();
    return { success: true, message: "Карточка цели удалена" };
  },

  // PATCH /goals/{goalId}/steps/{stepId}/toggle (UC-2: Переключение чекбокса шага)
  async toggleStep(goalId, stepId, explicitStatus = undefined) {
    const goal = db.state.goals.find(g => g.id === goalId);
    if (!goal) throw new Error("Цель не найдена");

    const step = goal.steps.find(s => s.id === stepId);
    if (!step) throw new Error("Шаг чек-листа не найден");

    const sphere = db.state.spheres.find(s => s.id === goal.sphere_id);
    const previousSphereScore = sphere ? sphere.current_score : 0;

    if (explicitStatus !== undefined) {
      step.is_completed = Boolean(explicitStatus);
    } else {
      step.is_completed = !step.is_completed;
    }
    step.completed_at = step.is_completed ? new Date().toISOString() : null;

    const newProgress = db.recalculateGoalProgress(goal);
    const newSphereScore = db.recalculateSphereScore(goal.sphere_id);
    db.save();

    const scoreDelta = Math.round((newSphereScore - previousSphereScore) * 10) / 10;
    const isGoalCompleted = newProgress === 100;

    return {
      step: { ...step },
      goal_progress_percent: newProgress,
      goal_status: goal.status,
      sphere_metrics: {
        sphere_id: goal.sphere_id,
        sphere_title: sphere ? sphere.title : "",
        previous_score: previousSphereScore,
        new_score: newSphereScore,
        score_delta: scoreDelta
      },
      celebration: isGoalCompleted
    };
  },

  // Добавление шага в цель
  async addStep(goalId, title, weight = 1) {
    const goal = db.state.goals.find(g => g.id === goalId);
    if (!goal) throw new Error("Цель не найдена");

    const newStep = {
      id: generateSafeUUID('d'),
      title: title.trim(),
      is_completed: false,
      sort_order: goal.steps.length + 1,
      weight: parseInt(weight, 10) || 1,
      completed_at: null
    };

    goal.steps.push(newStep);
    db.recalculateGoalProgress(goal);
    db.recalculateSphereScore(goal.sphere_id);
    db.save();
    return newStep;
  },

  // Удаление шага из цели
  async deleteStep(goalId, stepId) {
    const goal = db.state.goals.find(g => g.id === goalId);
    if (!goal) throw new Error("Цель не найдена");

    const idx = goal.steps.findIndex(s => s.id === stepId);
    if (idx !== -1) {
      goal.steps.splice(idx, 1);
      db.recalculateGoalProgress(goal);
      db.recalculateSphereScore(goal.sphere_id);
      db.save();
    }
    return { success: true };
  },

  // GET /analytics/radar-chart
  async getRadarChartData() {
    const harmony = db.calculateOverallHarmonyIndex();
    const sectors = db.state.spheres.map(s => {
      const activeGoals = db.state.goals.filter(g => g.sphere_id === s.id && g.status !== 'archived');
      return {
        sphere_id: s.id,
        title: s.title,
        color: s.color,
        icon: s.icon,
        target_score: s.target_score,
        current_score: s.current_score,
        active_goals_count: activeGoals.length
      };
    });

    return {
      overall_harmony_index: harmony,
      evaluated_at: new Date().toISOString(),
      sectors: sectors
    };
  },

  // ============================================================================
  // ИСТОРИЧЕСКИЕ СРЕЗЫ БАЛАНСА И АНАЛИТИКА (BALANCE SNAPSHOTS & TRENDS)
  // ============================================================================

  async getSnapshots({ days = null, limit = 50 } = {}) {
    let list = db.state.balance_snapshots || [];
    if (days) {
      const since = Date.now() - days * 86400000;
      list = list.filter(sn => new Date(sn.recorded_at).getTime() >= since);
    }
    const sphereMap = {};
    db.state.spheres.forEach(s => { sphereMap[s.id] = s; });

    const enriched = list.map(sn => ({
      ...sn,
      items: (sn.items || []).map(it => {
        const s = sphereMap[it.sphere_id];
        return {
          ...it,
          sphere_title: s ? s.title : "Сфера",
          sphere_color: s ? s.color : "#3B82F6",
          sphere_icon: s ? s.icon : "compass"
        };
      })
    }));

    enriched.sort((a, b) => new Date(a.recorded_at) - new Date(b.recorded_at));
    return enriched.slice(0, limit);
  },

  async getAnalyticsTrend({ days = null } = {}) {
    const snapshots = await this.getSnapshots({ days, limit: 100 });
    const spheres = db.state.spheres;
    const labels = [];
    const dates = [];
    const harmony_series = [];
    const spheres_dict = {};

    spheres.forEach(s => {
      spheres_dict[s.id] = {
        sphere_id: s.id,
        title: s.title,
        color: s.color,
        icon: s.icon,
        scores: []
      };
    });

    snapshots.forEach(sn => {
      const d = new Date(sn.recorded_at);
      const day = String(d.getDate()).padStart(2, '0');
      const month = String(d.getMonth() + 1).padStart(2, '0');
      labels.push(`${day}.${month}`);
      dates.push(sn.recorded_at);
      harmony_series.push(Math.round((Number(sn.overall_harmony_index) || 0.5) * 100 * 10) / 10);

      const itemsMap = {};
      (sn.items || []).forEach(it => { itemsMap[it.sphere_id] = Number(it.score); });
      spheres.forEach(s => {
        const val = itemsMap[s.id] !== undefined ? itemsMap[s.id] : s.current_score;
        spheres_dict[s.id].scores.push(Math.round(val * 10) / 10);
      });
    });

    const cur_h = harmony_series.length ? harmony_series[harmony_series.length - 1] : 50;
    const earliest_h = harmony_series.length ? harmony_series[0] : 50;
    const delta = Math.round((cur_h - earliest_h) * 10) / 10;
    const percent_growth = earliest_h > 0 ? Math.round(((cur_h - earliest_h) / earliest_h * 100) * 10) / 10 : 0;

    return {
      labels,
      dates,
      harmony_series,
      spheres_series: Object.values(spheres_dict),
      snapshots_count: snapshots.length,
      current_harmony_index: Math.round((cur_h / 100) * 100) / 100,
      earliest_harmony_index: Math.round((earliest_h / 100) * 100) / 100,
      improvement_delta: delta,
      improvement_percent: percent_growth
    };
  },

  async createSnapshot({ notes = null, items = null } = {}) {
    db.recalculateAll();
    const spheres = db.state.spheres;
    const user = this.getCurrentUser();
    const harmony = db.calculateOverallHarmonyIndex();
    const now = new Date().toISOString();

    let snapshotItems = [];
    if (items && Array.isArray(items) && items.length > 0) {
      snapshotItems = items.map((it, idx) => ({
        id: "f" + String(Date.now() + idx).padStart(31, '0'),
        sphere_id: it.sphere_id,
        score: Number(it.score) || 0,
        target_score: Number(it.target_score) || 10
      }));
    } else {
      snapshotItems = spheres.map((s, idx) => ({
        id: "f" + String(Date.now() + idx).padStart(31, '0'),
        sphere_id: s.id,
        score: s.current_score,
        target_score: s.target_score
      }));
    }

    const newSnapshot = {
      id: "e" + String(Date.now()).padStart(31, '0'),
      user_id: user.id,
      overall_harmony_index: harmony,
      notes: notes || `Срез баланса от ${new Date().toLocaleDateString('ru-RU')} ${new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`,
      recorded_at: now,
      created_at: now,
      items: snapshotItems
    };

    if (!db.state.balance_snapshots) db.state.balance_snapshots = [];
    db.state.balance_snapshots.push(newSnapshot);
    db.save();

    return newSnapshot;
  },

  async deleteSnapshot(id) {
    if (!db.state.balance_snapshots) return { success: true };
    const idx = db.state.balance_snapshots.findIndex(s => s.id === id);
    if (idx !== -1) {
      db.state.balance_snapshots.splice(idx, 1);
      db.save();
    }
    return { success: true };
  },

  // Экспорт всей базы в JSON (CMS Backup)
  exportJSON() {
    const backup = {
      app: "Horizont Dream Map Planner",
      version: "1.0.0",
      exported_at: new Date().toISOString(),
      spheres: db.state.spheres,
      goals: db.state.goals
    };
    return JSON.stringify(backup, null, 2);
  },

  // Импорт базы из JSON (CMS Restore)
  importJSON(jsonString) {
    const parsed = typeof jsonString === 'string' ? JSON.parse(jsonString) : jsonString;
    if (!parsed || !Array.isArray(parsed.spheres) || !Array.isArray(parsed.goals)) {
      throw new Error("Неверная структура резервной копии. Требуются массивы 'spheres' и 'goals'.");
    }
    db.state.spheres = parsed.spheres;
    db.state.goals = parsed.goals;
    db.recalculateAll();
    db.save();
    return {
      success: true,
      spheres_count: db.state.spheres.length,
      goals_count: db.state.goals.length
    };
  },

  // Генерация исполняемого блока SQL INSERT для PostgreSQL
  generateSQLInserts() {
    let sql = `-- ============================================================================\n`;
    sql += `-- Экспорт данных проекта «Горизонт» в SQL INSERT (PostgreSQL)\n`;
    sql += `-- Дата генерации: ${new Date().toISOString()}\n`;
    sql += `-- ============================================================================\n\n`;

    // 1. Сферы жизни
    sql += `-- 1. Сферы жизни (life_spheres)\n`;
    sql += `INSERT INTO life_spheres (id, user_id, title, description, color, icon, target_score, current_score, sort_order)\nVALUES\n`;
    const sphereValues = db.state.spheres.map(s => {
      const desc = s.description ? `'${s.description.replace(/'/g, "''")}'` : 'NULL';
      return `  ('${s.id}', '${s.user_id || 'a0000000-0000-0000-0000-000000000001'}', '${s.title.replace(/'/g, "''")}', ${desc}, '${s.color}', '${s.icon || 'star'}', ${s.target_score}, ${s.current_score}, ${s.sort_order || 0})`;
    }).join(',\n');
    sql += sphereValues + `\nON CONFLICT (id) DO UPDATE SET current_score = EXCLUDED.current_score;\n\n`;

    // 2. Карточки целей
    if (db.state.goals.length > 0) {
      sql += `-- 2. Карточки целей (goal_cards)\n`;
      sql += `INSERT INTO goal_cards (id, user_id, sphere_id, title, description, image_url, deadline, priority, status, progress_percent, cost_amount, currency)\nVALUES\n`;
      const goalValues = db.state.goals.map(g => {
        const desc = g.description ? `'${g.description.replace(/'/g, "''")}'` : 'NULL';
        const img = g.image_url ? `'${g.image_url.replace(/'/g, "''")}'` : 'NULL';
        const ddl = g.deadline ? `'${g.deadline}'` : 'NULL';
        const cost = typeof g.cost_amount === 'number' ? g.cost_amount.toFixed(2) : '0.00';
        const cur = g.currency === 'USD' ? 'USD' : 'BYN';
        return `  ('${g.id}', '${g.user_id || 'a0000000-0000-0000-0000-000000000001'}', '${g.sphere_id}', '${g.title.replace(/'/g, "''")}', ${desc}, ${img}, ${ddl}, '${g.priority || 'medium'}', '${g.status || 'in_progress'}', ${g.progress_percent || 0}, ${cost}, '${cur}')`;
      }).join(',\n');
      sql += goalValues + `\nON CONFLICT (id) DO NOTHING;\n\n`;

      // 3. Шаги чек-листов
      const allSteps = [];
      db.state.goals.forEach(g => {
        if (g.steps && g.steps.length > 0) {
          g.steps.forEach(st => {
            allSteps.push({ ...st, goal_id: g.id });
          });
        }
      });

      if (allSteps.length > 0) {
        sql += `-- 3. Шаги чек-листа (goal_steps)\n`;
        sql += `INSERT INTO goal_steps (id, goal_id, title, is_completed, sort_order, weight)\nVALUES\n`;
        const stepValues = allSteps.map(st => {
          return `  ('${st.id}', '${st.goal_id}', '${st.title.replace(/'/g, "''")}', ${st.is_completed ? 'TRUE' : 'FALSE'}, ${st.sort_order || 1}, ${st.weight || 1})`;
        }).join(',\n');
        sql += stepValues + `\nON CONFLICT (id) DO NOTHING;\n\n`;
      }
    }

    // 4. Кэш курсов валют НБРБ
    const cachedFx = this.getCachedNbrbRate();
    const rateVal = cachedFx && cachedFx.rate ? cachedFx.rate : 2.97;
    sql += `-- 4. Кэш официального курса валюты Нацбанка РБ (exchange_rates_cache)\n`;
    sql += `INSERT INTO exchange_rates_cache (currency_code, scale, rate, rate_date)\nVALUES ('USD', 1, ${rateVal}, CURRENT_DATE)\nON CONFLICT (currency_code) DO NOTHING;\n\n`;

    return sql;
  },

  // Получение кэшированного курса НБРБ из localStorage
  getCachedNbrbRate() {
    try {
      const raw = localStorage.getItem('horizont_fx_rate');
      if (raw) return JSON.parse(raw);
    } catch (e) {
      console.warn("Ошибка чтения кэша курса НБРБ:", e);
    }
    return null;
  },

  // GET /integrations/nbrb/rate (Официальный курс валюты Нацбанка РБ с суточным кэшированием)
  async getNbrbRate(forceRefresh = false) {
    const today = new Date().toISOString().slice(0, 10);
    const cached = this.getCachedNbrbRate();

    // 1. Если есть валидный кэш за сегодня и не запрошен принудительный рефреш
    if (!forceRefresh && cached && cached.date === today && cached.rate) {
      return {
        currency_code: "USD",
        scale: cached.scale || 1,
        rate: cached.rate,
        rate_date: cached.date,
        source: cached.source || "localStorage (кэш за сегодня)",
        cached: true,
        fetched_at: cached.fetchedAt || new Date().toISOString()
      };
    }

    // 2. Обращение к официальному открытому JSON API Нацбанка Беларуси
    try {
      const response = await fetch('https://api.nbrb.by/exrates/rates/USD?parammode=2', {
        headers: { 'Accept': 'application/json' }
      });

      if (!response.ok) {
        throw new Error(`Ответ сервера НБРБ: HTTP ${response.status}`);
      }

      const data = await response.json();
      const officialRate = parseFloat(data.Cur_OfficialRate);
      if (!officialRate || isNaN(officialRate)) {
        throw new Error("Некорректный формат курса в ответе НБРБ");
      }

      const rateResult = {
        currency_code: "USD",
        scale: data.Cur_Scale || 1,
        rate: officialRate,
        rate_date: data.Date ? data.Date.slice(0, 10) : today,
        source: "api.nbrb.by (Нацбанк РБ)",
        cached: false,
        fetched_at: new Date().toISOString()
      };

      // Сохраняем в localStorage на 1 сутки
      try {
        localStorage.setItem('horizont_fx_rate', JSON.stringify({
          rate: rateResult.rate,
          scale: rateResult.scale,
          date: rateResult.rate_date,
          source: rateResult.source,
          fetchedAt: rateResult.fetched_at
        }));
      } catch (storageErr) {
        console.warn("Не удалось записать курс в localStorage:", storageErr);
      }

      return rateResult;
    } catch (networkError) {
      console.warn("Не удалось получить курс из api.nbrb.by, переключение на резервный источник:", networkError);

      // Если в кэше есть данные за предыдущие дни
      if (cached && cached.rate) {
        return {
          currency_code: "USD",
          scale: cached.scale || 1,
          rate: cached.rate,
          rate_date: cached.date || today,
          source: `localStorage (архивный кэш от ${cached.date || 'ранее'})`,
          cached: true,
          fetched_at: cached.fetchedAt || new Date().toISOString()
        };
      }

      // Резервный дефолтный курс по ТЗ (1 USD = 2.97 BYN)
      return {
        currency_code: "USD",
        scale: 1,
        rate: 2.9700,
        rate_date: today,
        source: "Резервный дефолтный курс (офлайн)",
        cached: false,
        fetched_at: new Date().toISOString()
      };
    }
  },

  // Сброс к исходным демо-данным
  resetToDefaults() {
    db.reset();
  }
};

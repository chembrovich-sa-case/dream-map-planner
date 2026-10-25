-- ============================================================================
-- Проект: «Горизонт» (dream-map-planner)
-- Назначение: Схема базы данных PostgreSQL (3NF, DDL, Constraints, Indexes, Views)
-- Диалект: PostgreSQL 14+
-- ============================================================================

-- Включение расширения для генерации UUID v4 (если не включено по умолчанию)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. ТАБЛИЦЫ СХЕМЫ (DDL)
-- ============================================================================

-- 1.1. Пользователи системы
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT chk_users_role CHECK (role IN ('admin', 'user', 'guest'))
);

COMMENT ON TABLE users IS 'Учетные записи пользователей сервиса с ролевой моделью (RBAC)';
COMMENT ON COLUMN users.email IS 'Уникальный адрес электронной почты (логин)';
COMMENT ON COLUMN users.password_hash IS 'Хэш пароля (Argon2 / bcrypt)';
COMMENT ON COLUMN users.role IS 'Роль в системе RBAC: admin (полный доступ к CMS и управлению), user (витрина и цели), guest (просмотр)';

-- 1.2. Сферы жизни (Колесо жизненного баланса)
CREATE TABLE IF NOT EXISTS life_spheres (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    color VARCHAR(7) NOT NULL,
    icon VARCHAR(50) NOT NULL,
    target_score NUMERIC(3,1) NOT NULL DEFAULT 10.0,
    current_score NUMERIC(3,1) NOT NULL DEFAULT 0.0,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_life_spheres_color_hex CHECK (color ~* '^#[0-9A-Fa-f]{6}$'),
    CONSTRAINT chk_life_spheres_target_score CHECK (target_score >= 0.0 AND target_score <= 10.0),
    CONSTRAINT chk_life_spheres_current_score CHECK (current_score >= 0.0 AND current_score <= 10.0)
);

COMMENT ON TABLE life_spheres IS 'Сферы жизни пользователя для радарной диаграммы';
COMMENT ON COLUMN life_spheres.target_score IS 'Целевой показатель сферы (от 0.0 до 10.0)';
COMMENT ON COLUMN life_spheres.current_score IS 'Текущий рассчитанный балл наполненности сферы (от 0.0 до 10.0)';

-- 1.3. Карточки целей / желаний (Доска визуализации и трекер)
CREATE TABLE IF NOT EXISTS goal_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sphere_id UUID NOT NULL REFERENCES life_spheres(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    image_url TEXT,
    deadline DATE,
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    progress_percent INT NOT NULL DEFAULT 0,
    cost_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(3) NOT NULL DEFAULT 'BYN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    CONSTRAINT chk_goal_cards_priority CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT chk_goal_cards_status CHECK (status IN ('draft', 'in_progress', 'achieved', 'archived')),
    CONSTRAINT chk_goal_cards_progress CHECK (progress_percent >= 0 AND progress_percent <= 100),
    CONSTRAINT chk_goal_cards_currency CHECK (currency IN ('BYN', 'USD')),
    CONSTRAINT chk_goal_cards_cost CHECK (cost_amount >= 0.00)
);

COMMENT ON TABLE goal_cards IS 'Карточки целей и желаний с привязкой к сферам';
COMMENT ON COLUMN goal_cards.priority IS 'Приоритет цели: low (вес 1), medium (2), high (3), critical (4)';
COMMENT ON COLUMN goal_cards.status IS 'Жизненный цикл цели: draft, in_progress, achieved, archived';
COMMENT ON COLUMN goal_cards.progress_percent IS 'Процент прогресса карточки (0-100), рассчитанный по шагам';
COMMENT ON COLUMN goal_cards.cost_amount IS 'Целевой бюджет/стоимость реализации цели (в валюте цели)';
COMMENT ON COLUMN goal_cards.currency IS 'Валюта бюджета цели (BYN или USD)';

-- 1.4. Шаги чек-листа цели (Декомпозиция)
CREATE TABLE IF NOT EXISTS goal_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES goal_cards(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INT NOT NULL DEFAULT 0,
    weight INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    CONSTRAINT chk_goal_steps_weight CHECK (weight > 0)
);

COMMENT ON TABLE goal_steps IS 'Атомарные шаги декомпозиции цели в чек-листе';
COMMENT ON COLUMN goal_steps.weight IS 'Вес шага цели (относительная сложность/значимость, по умолчанию 1)';

-- 1.5. История замеров баланса (Срезы радарного колеса)
CREATE TABLE IF NOT EXISTS balance_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    overall_harmony_index NUMERIC(3,2),
    notes TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_balance_snapshots_harmony CHECK (overall_harmony_index >= 0.00 AND overall_harmony_index <= 1.00)
);

COMMENT ON TABLE balance_snapshots IS 'Исторические точки фиксации баланса жизни';
COMMENT ON COLUMN balance_snapshots.overall_harmony_index IS 'Индекс гармоничности (от 0.00 до 1.00, обратный дисперсии)';

-- 1.6. Показатели отдельных сфер в срезе баланса
CREATE TABLE IF NOT EXISTS balance_snapshot_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_id UUID NOT NULL REFERENCES balance_snapshots(id) ON DELETE CASCADE,
    sphere_id UUID NOT NULL REFERENCES life_spheres(id) ON DELETE CASCADE,
    score NUMERIC(3,1) NOT NULL,
    target_score NUMERIC(3,1) NOT NULL DEFAULT 10.0,
    CONSTRAINT uq_snapshot_sphere UNIQUE (snapshot_id, sphere_id),
    CONSTRAINT chk_snapshot_items_score CHECK (score >= 0.0 AND score <= 10.0),
    CONSTRAINT chk_snapshot_items_target CHECK (target_score >= 0.0 AND target_score <= 10.0)
);

COMMENT ON TABLE balance_snapshot_items IS 'Показатели каждой сферы в рамках конкретного исторического замера';

-- 1.7. Кэш курсов валют API Нацбанка РБ (НБРБ)
CREATE TABLE IF NOT EXISTS exchange_rates_cache (
    currency_code VARCHAR(3) PRIMARY KEY,
    scale INT NOT NULL DEFAULT 1,
    rate NUMERIC(10, 4) NOT NULL,
    rate_date DATE NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_fx_currency CHECK (currency_code IN ('USD', 'EUR', 'RUB', 'CNY', 'BYN'))
);

COMMENT ON TABLE exchange_rates_cache IS 'Суточный кэш официальных курсов валют Нацбанка РБ (НБРБ)';
COMMENT ON COLUMN exchange_rates_cache.rate IS 'Официальный курс НБРБ за scale единиц валюты в белорусских рублях (BYN)';
COMMENT ON COLUMN exchange_rates_cache.rate_date IS 'Дата фиксации курса в календаре НБРБ';

-- ============================================================================
-- 2. ИНДЕКСЫ ДЛЯ ОПТИМИЗАЦИИ ВЫБОРОК
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_life_spheres_user_id ON life_spheres (user_id);
CREATE INDEX IF NOT EXISTS idx_life_spheres_sort ON life_spheres (user_id, sort_order);

CREATE INDEX IF NOT EXISTS idx_goal_cards_user_id ON goal_cards (user_id);
CREATE INDEX IF NOT EXISTS idx_goal_cards_sphere_id ON goal_cards (sphere_id);
CREATE INDEX IF NOT EXISTS idx_goal_cards_status ON goal_cards (user_id, status);
CREATE INDEX IF NOT EXISTS idx_goal_cards_deadline ON goal_cards (user_id, deadline) WHERE deadline IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_goal_steps_goal_id ON goal_steps (goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_steps_sort ON goal_steps (goal_id, sort_order);

CREATE INDEX IF NOT EXISTS idx_balance_snapshots_user_recorded ON balance_snapshots (user_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_balance_snapshot_items_snapshot ON balance_snapshot_items (snapshot_id);
CREATE INDEX IF NOT EXISTS idx_balance_snapshot_items_sphere ON balance_snapshot_items (sphere_id);

-- ============================================================================
-- 3. ПРЕДСТАВЛЕНИЯ (VIEWS) И ФУНКЦИИ ДЛЯ РАСЧЕТА МЕТРИК
-- ============================================================================

-- 3.1. Представление: Расчет прогресса целей на основе шагов чек-листа
CREATE OR REPLACE VIEW v_goal_progress AS
WITH step_metrics AS (
    SELECT
        goal_id,
        COUNT(*) AS total_steps,
        COUNT(*) FILTER (WHERE is_completed = TRUE) AS completed_steps,
        COALESCE(SUM(weight), 0) AS total_weight,
        COALESCE(SUM(weight) FILTER (WHERE is_completed = TRUE), 0) AS completed_weight
    FROM goal_steps
    GROUP BY goal_id
)
SELECT
    g.id AS goal_id,
    g.user_id,
    g.sphere_id,
    g.title,
    g.status,
    g.priority,
    g.cost_amount,
    g.currency,
    CASE g.priority
        WHEN 'low' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'high' THEN 3
        WHEN 'critical' THEN 4
        ELSE 2
    END AS priority_weight,
    COALESCE(sm.total_steps, 0) AS total_steps,
    COALESCE(sm.completed_steps, 0) AS completed_steps,
    CASE
        -- Защита от деления на ноль при отсутствии шагов
        WHEN COALESCE(sm.total_weight, 0) = 0 THEN
            CASE WHEN g.status = 'achieved' THEN 100.0 ELSE 0.0 END
        ELSE
            ROUND((sm.completed_weight::NUMERIC / sm.total_weight::NUMERIC) * 100.0, 1)
    END AS calculated_progress_percent
FROM goal_cards g
LEFT JOIN step_metrics sm ON sm.goal_id = g.id;

COMMENT ON VIEW v_goal_progress IS 'Динамический расчет процента выполнения целей по весам шагов';

-- 3.2. Представление: Метрики сфер для радарной диаграммы
CREATE OR REPLACE VIEW v_sphere_radar_metrics AS
WITH active_goals AS (
    SELECT
        goal_id,
        sphere_id,
        user_id,
        calculated_progress_percent,
        priority_weight,
        (calculated_progress_percent / 100.0) * priority_weight AS weighted_progress
    FROM v_goal_progress
    WHERE status != 'archived'
),
sphere_aggregates AS (
    SELECT
        s.id AS sphere_id,
        s.user_id,
        s.title AS sphere_title,
        s.color,
        s.icon,
        s.target_score,
        COUNT(ag.goal_id) AS total_active_goals,
        COALESCE(SUM(ag.priority_weight), 0) AS sum_priority_weights,
        COALESCE(SUM(ag.weighted_progress), 0) AS sum_weighted_progress
    FROM life_spheres s
    LEFT JOIN active_goals ag ON ag.sphere_id = s.id
    GROUP BY s.id, s.user_id, s.title, s.color, s.icon, s.target_score
)
SELECT
    sa.sphere_id,
    sa.user_id,
    sa.sphere_title,
    sa.color,
    sa.icon,
    sa.target_score,
    sa.total_active_goals,
    CASE
        -- Защита от деления на ноль (когда нет активных целей в сфере)
        WHEN sa.sum_priority_weights = 0 THEN 0.0
        ELSE
            LEAST(10.0, ROUND((sa.sum_weighted_progress / sa.sum_priority_weights) * 10.0, 1))
    END AS calculated_sphere_score
FROM sphere_aggregates sa;

COMMENT ON VIEW v_sphere_radar_metrics IS 'Сводные данные для радарной диаграммы баланса жизни';

-- 3.3. Функция обновления кэшированного балла сферы в таблице life_spheres
CREATE OR REPLACE FUNCTION fn_recalculate_sphere_score(p_sphere_id UUID)
RETURNS NUMERIC AS $$
DECLARE
    v_new_score NUMERIC(3,1);
BEGIN
    SELECT calculated_sphere_score
    INTO v_new_score
    FROM v_sphere_radar_metrics
    WHERE sphere_id = p_sphere_id;

    IF v_new_score IS NOT NULL THEN
        UPDATE life_spheres
        SET current_score = v_new_score,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = p_sphere_id;
    END IF;

    RETURN COALESCE(v_new_score, 0.0);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION fn_recalculate_sphere_score(UUID) IS 'Пересчет и фиксация балла сферы по ее идентификатору';

-- ============================================================================
-- 4. ТЕСТОВЫЕ ДАННЫЕ (SEED DATA)
-- ============================================================================

-- 4.1. Демо-пользователи с ролями RBAC (admin / user)
INSERT INTO users (id, email, password_hash, name, role, avatar_url)
VALUES 
(
    'a0000000-0000-0000-0000-000000000000',
    'admin@horizon.app',
    '$2a$12$e8Y5t1R1CgG6n3G9C9a1qOYQ7qf/v6YkP7fWbL2q7dFpP5Z8vK9G6',
    'Алексей Администраторов',
    'admin',
    'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=300&q=80'
),
(
    'a0000000-0000-0000-0000-000000000001',
    'user@horizon.app',
    '$2a$12$e8Y5t1R1CgG6n3G9C9a1qOYQ7qf/v6YkP7fWbL2q7dFpP5Z8vK9G6',
    'Иван Горизонтов',
    'user',
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80'
) ON CONFLICT (email) DO UPDATE SET role = EXCLUDED.role;

-- 4.2. 6 сфер жизни для демо-пользователя
INSERT INTO life_spheres (id, user_id, title, description, color, icon, target_score, current_score, sort_order)
VALUES
(
    'b0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    'Карьера и бизнес',
    'Профессиональный рост, руководящие роли, масштабные рабочие проекты',
    '#3B82F6',
    'briefcase',
    10.0,
    6.7,
    1
),
(
    'b0000000-0000-0000-0000-000000000002',
    'a0000000-0000-0000-0000-000000000001',
    'Финансы и капитал',
    'Личный бюджет, финансовая подушка безопасности и инвестиционный портфель',
    '#10B981',
    'wallet',
    10.0,
    7.5,
    2
),
(
    'b0000000-0000-0000-0000-000000000003',
    'a0000000-0000-0000-0000-000000000001',
    'Здоровье и спорт',
    'Физическая форма, бег, сон, правильное питание и регулярные чекапы',
    '#EF4444',
    'heart-pulse',
    10.0,
    5.0,
    3
),
(
    'b0000000-0000-0000-0000-000000000004',
    'a0000000-0000-0000-0000-000000000001',
    'Семья и отношения',
    'Качественное время с близкими, романтические свидания и семейные традиции',
    '#EC4899',
    'users',
    10.0,
    8.0,
    4
),
(
    'b0000000-0000-0000-0000-000000000005',
    'a0000000-0000-0000-0000-000000000001',
    'Личностный рост',
    'Чтение книг, изучение языков, системное мышление и ментальные привычки',
    '#8B5CF6',
    'book-open',
    10.0,
    4.0,
    5
),
(
    'b0000000-0000-0000-0000-000000000006',
    'a0000000-0000-0000-0000-000000000001',
    'Яркость жизни и путешествия',
    'Новые впечатления, поездки в горы, активный отдых и хобби',
    '#F59E0B',
    'plane',
    10.0,
    3.3,
    6
) ON CONFLICT (id) DO NOTHING;

-- 4.3. Карточки целей
INSERT INTO goal_cards (id, user_id, sphere_id, title, description, image_url, deadline, priority, status, progress_percent, cost_amount, currency)
VALUES
(
    'c0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000003', -- Здоровье и спорт
    'Пробежать первый полумарафон (21.1 км)',
    'Подготовиться по плану тренера, пройти чекап и финишировать быстрее 1:55:00',
    'https://images.unsplash.com/photo-1452626038306-9aae5e071dd3?auto=format&fit=crop&w=800&q=80',
    '2027-05-20',
    'high',
    'in_progress',
    50,
    850.00,
    'BYN'
),
(
    'c0000000-0000-0000-0000-000000000002',
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001', -- Карьера и бизнес
    'Перейти на позицию Lead Architect',
    'Сформировать стратегическое видение платформы, пройти сертификацию и защитить роадмап',
    'https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=800&q=80',
    '2027-03-31',
    'critical',
    'in_progress',
    67,
    600.00,
    'USD'
),
(
    'c0000000-0000-0000-0000-000000000003',
    'a0000000-0000-0000-0000-000000000002', -- Финансы
    'Сформировать финансовую подушку на 20 000 BYN',
    'Обеспечить неприкосновенный запас на 6 месяцев семейных расходов на накопительном счете',
    'https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?auto=format&fit=crop&w=800&q=80',
    '2026-12-31',
    'high',
    'in_progress',
    75,
    20000.00,
    'BYN'
),
(
    'c0000000-0000-0000-0000-000000000004',
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000006', -- Яркость жизни
    'Экспедиция на Камчатку: вулканы и Тихий океан',
    'Увидеть Авачинскую бухту, совершить подъем на кратер Мутновского вулкана и серфинг',
    'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80',
    '2027-08-15',
    'medium',
    'in_progress',
    33,
    2500.00,
    'USD'
) ON CONFLICT (id) DO NOTHING;

-- 4.4. Пункты чек-листа (декомпозиция целей)
INSERT INTO goal_steps (id, goal_id, title, is_completed, sort_order, weight, completed_at)
VALUES
-- Шаги к полумарафону (c0000000-0000-0000-0000-000000000001)
(
    'd0000000-0000-0000-0000-000000000001',
    'c0000000-0000-0000-0000-000000000001',
    'Пройти спортивный чекап сердца (ЭКГ под нагрузкой)',
    TRUE,
    1,
    1,
    CURRENT_TIMESTAMP - INTERVAL '15 days'
),
(
    'd0000000-0000-0000-0000-000000000002',
    'c0000000-0000-0000-0000-000000000001',
    'Подобрать профессиональные амортизирующие кроссовки с гайт-анализом',
    TRUE,
    2,
    1,
    CURRENT_TIMESTAMP - INTERVAL '10 days'
),
(
    'd0000000-0000-0000-0000-000000000003',
    'c0000000-0000-0000-0000-000000000001',
    'Пробежать тестовую длинную тренировку 16 км в темпе 5:30 мин/км',
    FALSE,
    3,
    1,
    NULL
),
(
    'd0000000-0000-0000-0000-000000000004',
    'c0000000-0000-0000-0000-000000000001',
    'Зарегистрироваться на полумарафон «Северная столица» и получить слот',
    FALSE,
    4,
    1,
    NULL
),

-- Шаги к позиции Lead Architect (c0000000-0000-0000-0000-000000000002)
(
    'd0000000-0000-0000-0000-000000000005',
    'c0000000-0000-0000-0000-000000000002',
    'Пройти сертификацию по облачной архитектуре и системному дизайну',
    TRUE,
    1,
    2,
    CURRENT_TIMESTAMP - INTERVAL '20 days'
),
(
    'd0000000-0000-0000-0000-000000000006',
    'c0000000-0000-0000-0000-000000000002',
    'Разработать целевую архитектуру микросервисов и ADR-документы',
    TRUE,
    2,
    2,
    CURRENT_TIMESTAMP - INTERVAL '5 days'
),
(
    'd0000000-0000-0000-0000-000000000007',
    'c0000000-0000-0000-0000-000000000002',
    'Защитить техническую стратегию перед CTO и бизнесом',
    FALSE,
    3,
    2,
    NULL
),

-- Шаги к финансовой подушке (c0000000-0000-0000-0000-000000000003)
(
    'd0000000-0000-0000-0000-000000000008',
    'c0000000-0000-0000-0000-000000000003',
    'Рассчитать точный бюджет обязательных расходов на 6 месяцев',
    TRUE,
    1,
    1,
    CURRENT_TIMESTAMP - INTERVAL '30 days'
),
(
    'd0000000-0000-0000-0000-000000000009',
    'c0000000-0000-0000-0000-000000000003',
    'Накопить первые 7 000 BYN',
    TRUE,
    2,
    1,
    CURRENT_TIMESTAMP - INTERVAL '20 days'
),
(
    'd0000000-0000-0000-0000-000000000010',
    'c0000000-0000-0000-0000-000000000003',
    'Довести сумму накопительного счета до 14 000 BYN',
    TRUE,
    3,
    1,
    CURRENT_TIMESTAMP - INTERVAL '5 days'
),
(
    'd0000000-0000-0000-0000-000000000011',
    'c0000000-0000-0000-0000-000000000003',
    'Закрыть финальную цель — 20 000 BYN неприкосновенного запаса',
    FALSE,
    4,
    1,
    NULL
),

-- Шаги к экспедиции на Камчатку (c0000000-0000-0000-0000-000000000004)
(
    'd0000000-0000-0000-0000-000000000012',
    'c0000000-0000-0000-0000-000000000004',
    'Выбрать даты отпуска и забронировать даты в экспедиционной группе',
    TRUE,
    1,
    1,
    CURRENT_TIMESTAMP - INTERVAL '7 days'
),
(
    'd0000000-0000-0000-0000-000000000013',
    'c0000000-0000-0000-0000-000000000004',
    'Купить авиабилеты Москва — Петропавловск-Камчатский',
    FALSE,
    2,
    1,
    NULL
),
(
    'd0000000-0000-0000-0000-000000000014',
    'c0000000-0000-0000-0000-000000000004',
    'Подготовить мембранную трекинговую одежду и ботинки',
    FALSE,
    3,
    1,
    NULL
) ON CONFLICT (id) DO NOTHING;

-- 4.5. Базовый замер баланса (исторический снапшот месяц назад)
INSERT INTO balance_snapshots (id, user_id, overall_harmony_index, notes, recorded_at)
VALUES (
    'e0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    0.72,
    'Стартовый замер при начале планирования года. Заметен провал в сфере спорта и отдыха.',
    CURRENT_TIMESTAMP - INTERVAL '30 days'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO balance_snapshot_items (id, snapshot_id, sphere_id, score, target_score)
VALUES
('f0000000-0000-0000-0000-000000000001', 'e0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 5.0, 10.0),
('f0000000-0000-0000-0000-000000000002', 'e0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000002', 4.5, 10.0),
('f0000000-0000-0000-0000-000000000003', 'e0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000003', 2.0, 10.0),
('f0000000-0000-0000-0000-000000000004', 'e0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000004', 7.0, 10.0),
('f0000000-0000-0000-0000-000000000005', 'e0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000005', 3.5, 10.0),
('f0000000-0000-0000-0000-000000000006', 'e0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000006', 2.0, 10.0)
ON CONFLICT (id) DO NOTHING;

-- 4.6. Начальный кэш курса USD по данным НБРБ
INSERT INTO exchange_rates_cache (currency_code, scale, rate, rate_date)
VALUES ('USD', 1, 2.9543, CURRENT_DATE)
ON CONFLICT (currency_code) DO NOTHING;

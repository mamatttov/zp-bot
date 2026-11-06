PRAGMA foreign_keys = ON;

-- Сотрудники
CREATE TABLE IF NOT EXISTS employees (
    id          INTEGER PRIMARY KEY,
    tab_no      TEXT    NOT NULL UNIQUE,
    full_name   TEXT    NOT NULL,
    position    TEXT    NOT NULL,
    link_code   TEXT    UNIQUE,
    tg_user_id  INTEGER UNIQUE,
    linked_at   TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1
);

-- Выплаты: одна строка = одна выплата
CREATE TABLE IF NOT EXISTS payments (
    id           INTEGER PRIMARY KEY,
    employee_id  INTEGER NOT NULL REFERENCES employees(id),
    period       TEXT    NOT NULL CHECK (period GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]'),
    kind         TEXT    NOT NULL CHECK (kind IN ('аванс', 'зарплата', 'премия', 'отпускные')),
    gross        REAL    NOT NULL CHECK (gross >= 0),
    social_fund  REAL    NOT NULL DEFAULT 0,
    income_tax   REAL    NOT NULL DEFAULT 0,
    net          REAL    NOT NULL,
    paid_at      TEXT    NOT NULL,
    notified_at  TEXT
);

CREATE INDEX IF NOT EXISTS ix_payments_emp_period ON payments(employee_id, period);
CREATE INDEX IF NOT EXISTS ix_payments_pending    ON payments(notified_at) WHERE notified_at IS NULL;

-- Сводка по месяцам
CREATE VIEW IF NOT EXISTS v_monthly AS
SELECT employee_id,
       period,
       ROUND(SUM(gross), 2)                    AS gross,
       ROUND(SUM(social_fund + income_tax), 2) AS withheld,
       ROUND(SUM(net), 2)                      AS net,
       COUNT(*)                                AS payments_cnt
FROM payments
GROUP BY employee_id, period;
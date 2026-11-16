CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============ USERS ============
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(40) NOT NULL UNIQUE,
    full_name       VARCHAR(120) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'user'
                    CHECK (role IN ('user', 'admin')),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users (lower(email));

-- ============ API KEYS ============
CREATE TABLE IF NOT EXISTS api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(80) NOT NULL,
    description     TEXT DEFAULT '',
    key_prefix      VARCHAR(20) NOT NULL,          -- ayaka_live_ + 6 char untuk display
    key_hash        TEXT NOT NULL UNIQUE,           -- SHA-256(pepper + secret)
    permissions     TEXT[] NOT NULL DEFAULT ARRAY[
                        'profile:read','premium:send','premium:status',
                        'premium:renew','premium:revoke'
                    ],
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','revoked','expired')),
    expires_at      TIMESTAMPTZ,
    last_used_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_api_keys_owner ON api_keys (owner_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys (key_hash);

-- ============ MAGIC LINK TOKENS ============
CREATE TABLE IF NOT EXISTS magic_link_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id      UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    owner_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    token_hash      TEXT NOT NULL UNIQUE,
    plan            VARCHAR(40) NOT NULL DEFAULT 'premium',
    expires_at      TIMESTAMPTZ NOT NULL,
    used_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_magic_tokens_hash ON magic_link_tokens (token_hash);
CREATE INDEX IF NOT EXISTS idx_magic_tokens_email ON magic_link_tokens (email, created_at DESC);

-- ============ PREMIUM SUBSCRIPTIONS ============
CREATE TABLE IF NOT EXISTS premium_subscriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','revoked','expired')),
    activated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner_id, email)
);
CREATE INDEX IF NOT EXISTS idx_premium_email ON premium_subscriptions (email);

-- ============ PREMIUM RENEWAL LOGS ============
CREATE TABLE IF NOT EXISTS premium_renewal_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES premium_subscriptions(id) ON DELETE CASCADE,
    api_key_id      UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    old_expires_at  TIMESTAMPTZ NOT NULL,
    new_expires_at  TIMESTAMPTZ NOT NULL,
    duration_days   INTEGER NOT NULL CHECK (duration_days > 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============ SESSIONS ============
CREATE TABLE IF NOT EXISTS user_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_hash    TEXT NOT NULL UNIQUE,
    csrf_token      TEXT NOT NULL,
    user_agent      TEXT,
    ip_hash         TEXT,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sessions_hash ON user_sessions (session_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON user_sessions (expires_at);

-- ============ API REQUEST LOGS ============
CREATE TABLE IF NOT EXISTS api_request_logs (
    id              BIGSERIAL PRIMARY KEY,
    request_id      UUID NOT NULL DEFAULT gen_random_uuid(),
    owner_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    api_key_id      UUID REFERENCES api_keys(id) ON DELETE SET NULL,
    method          VARCHAR(10) NOT NULL,
    endpoint        VARCHAR(255) NOT NULL,
    status_code     SMALLINT NOT NULL,
    response_ms     INTEGER NOT NULL DEFAULT 0,
    ip_hash         TEXT,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_logs_owner_time ON api_request_logs (owner_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_endpoint ON api_request_logs (endpoint, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_status ON api_request_logs (status_code);

-- ============ VISITOR ANALYTICS ============
CREATE TABLE IF NOT EXISTS visitor_analytics (
    id              BIGSERIAL PRIMARY KEY,
    visitor_hash    TEXT NOT NULL,
    path            VARCHAR(255) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_visitors_time ON visitor_analytics (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_visitors_hash ON visitor_analytics (visitor_hash, created_at DESC);

-- ============ AUDIT LOGS ============
CREATE TABLE IF NOT EXISTS audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    actor_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    action          VARCHAR(80) NOT NULL,
    target_type     VARCHAR(40),
    target_id       TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============ SYSTEM SETTINGS ============
CREATE TABLE IF NOT EXISTS system_settings (
    key             VARCHAR(80) PRIMARY KEY,
    value           JSONB NOT NULL DEFAULT '{}',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO system_settings (key, value) VALUES
    ('maintenance', '{"enabled": false, "message": "AYAKA API sedang dalam pemeliharaan."}'),
    ('announcement', '{"message": "", "active": false}')
ON CONFLICT (key) DO NOTHING;

-- ============ WEBHOOK CONFIGS ============
CREATE TABLE IF NOT EXISTS webhook_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url             TEXT NOT NULL,
    events          TEXT[] NOT NULL DEFAULT ARRAY['premium.activated'],
    secret          TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============ ADMIN BOOTSTRAP (jalankan manual setelah register) ============
-- UPDATE users SET role = 'admin' WHERE email = 'olpieditz336@gmail.com';
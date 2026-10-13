-- CLAIM LAGOS - Initial PostGIS + Core Schema
-- Optimized for Hostinger KVM 2 (8 GB RAM)
-- PLACEHOLDER: Public geo data seeded; replace with official Lagos/INEC boundaries when available.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- GEO HIERARCHY (first-class dimension)
-- Levels: state | division | senatorial | lga | lcda | ward | community | polling_area
-- ============================================================
CREATE TABLE geo_hierarchy (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level           VARCHAR(32) NOT NULL CHECK (level IN (
                        'state', 'division', 'senatorial', 'lga', 'lcda',
                        'ward', 'community', 'polling_area'
                    )),
    name            VARCHAR(255) NOT NULL,
    code            VARCHAR(64),
    parent_id       UUID REFERENCES geo_hierarchy(id) ON DELETE SET NULL,
    geometry        GEOMETRY(MultiPolygon, 4326),
    centroid        GEOMETRY(Point, 4326),
    source          VARCHAR(128) DEFAULT 'public',  -- 'public' | 'official' | 'derived'
    is_placeholder  BOOLEAN DEFAULT TRUE,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_geo_level ON geo_hierarchy(level);
CREATE INDEX idx_geo_parent ON geo_hierarchy(parent_id);
CREATE INDEX idx_geo_name_trgm ON geo_hierarchy USING gin (name gin_trgm_ops);
CREATE INDEX idx_geo_geometry ON geo_hierarchy USING GIST (geometry);
CREATE INDEX idx_geo_centroid ON geo_hierarchy USING GIST (centroid);

-- ============================================================
-- USERS & RBAC
-- ============================================================
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(64) UNIQUE NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE permissions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code        VARCHAR(128) UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE role_permissions (
    role_id         UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id   UUID REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    phone           VARCHAR(32),
    full_name       VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255),
    is_active       BOOLEAN DEFAULT TRUE,
    is_verified     BOOLEAN DEFAULT FALSE,
    mfa_enabled     BOOLEAN DEFAULT FALSE,
    mfa_secret      VARCHAR(64),
    last_login      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- Seed core roles
INSERT INTO roles (name, description) VALUES
('super_admin', 'Full system control'),
('campaign_director', 'Executive overview + Situation Room'),
('director_new_media', 'Owns New Media operations'),
('situation_room_manager', 'Daily Situation Room control'),
('intelligence_officer', 'Deep intelligence analysis'),
('digital_ads_manager', 'Advertising lifecycle'),
('social_media_manager', 'Social listening & content'),
('content_manager', 'CREATE module + approvals'),
('gis_analyst', 'Geo layers & mapping'),
('ai_analyst', 'AI models & recommendations'),
('data_analyst', 'Reporting & exports'),
('volunteer_coordinator', 'Ambassador oversight'),
('digital_ambassador', 'Field / digital ambassador'),
('read_only_executive', 'View-only executive access');

-- ============================================================
-- DIGITAL AMBASSADORS
-- ============================================================
CREATE TABLE digital_ambassadors (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    ward_id             UUID REFERENCES geo_hierarchy(id),
    status              VARCHAR(32) DEFAULT 'pending' CHECK (status IN (
                            'pending', 'verified', 'active', 'suspended', 'inactive'
                        )),
    verification_notes  TEXT,
    verified_at         TIMESTAMPTZ,
    verified_by         UUID REFERENCES users(id),
    phone               VARCHAR(32),
    whatsapp            VARCHAR(32),
    performance_score   NUMERIC(5,2) DEFAULT 0,
    total_tasks         INT DEFAULT 0,
    completed_tasks     INT DEFAULT 0,
    badges              JSONB DEFAULT '[]',
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_amb_ward ON digital_ambassadors(ward_id);
CREATE INDEX idx_amb_status ON digital_ambassadors(status);

-- ============================================================
-- TASKS & REPORTING
-- ============================================================
CREATE TABLE tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    task_type       VARCHAR(64),
    priority        VARCHAR(16) DEFAULT 'medium',
    status          VARCHAR(32) DEFAULT 'open',
    geo_id          UUID REFERENCES geo_hierarchy(id),
    created_by      UUID REFERENCES users(id),
    due_at          TIMESTAMPTZ,
    content_asset_id UUID,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE task_assignments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id         UUID REFERENCES tasks(id) ON DELETE CASCADE,
    ambassador_id   UUID REFERENCES digital_ambassadors(id) ON DELETE CASCADE,
    status          VARCHAR(32) DEFAULT 'assigned',
    assigned_at     TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    report_text     TEXT,
    report_media    JSONB DEFAULT '[]',
    UNIQUE(task_id, ambassador_id)
);

-- ============================================================
-- CONTENT & APPROVALS (human-in-the-loop)
-- ============================================================
CREATE TABLE content_assets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           VARCHAR(255) NOT NULL,
    body            TEXT,
    asset_type      VARCHAR(64),  -- post, image, video, thread, counter_narrative
    status          VARCHAR(32) DEFAULT 'draft' CHECK (status IN (
                        'draft', 'pending_review', 'approved', 'rejected', 'archived'
                    )),
    created_by      UUID REFERENCES users(id),
    approved_by     UUID REFERENCES users(id),
    approved_at     TIMESTAMPTZ,
    ai_generated    BOOLEAN DEFAULT FALSE,
    ai_prompt       TEXT,
    media_urls      JSONB DEFAULT '[]',
    target_geo_ids  UUID[],
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE content_approvals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id      UUID REFERENCES content_assets(id) ON DELETE CASCADE,
    reviewer_id     UUID REFERENCES users(id),
    action          VARCHAR(32),  -- approve | reject | request_changes
    comments        TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ALERTS & RECOMMENDATIONS
-- ============================================================
CREATE TABLE alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           VARCHAR(255) NOT NULL,
    severity        VARCHAR(16) DEFAULT 'medium',  -- low | medium | high | critical
    source          VARCHAR(64),
    geo_id          UUID REFERENCES geo_hierarchy(id),
    payload         JSONB DEFAULT '{}',
    status          VARCHAR(32) DEFAULT 'open',
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE recommendations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id        UUID REFERENCES alerts(id),
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    action_type     VARCHAR(64),  -- deploy_ambassadors | boost_ad | counter_narrative | escalate | etc.
    confidence      NUMERIC(3,2),
    status          VARCHAR(32) DEFAULT 'pending' CHECK (status IN (
                        'pending', 'accepted', 'rejected', 'executed'
                    )),
    ai_generated    BOOLEAN DEFAULT TRUE,
    reviewed_by     UUID REFERENCES users(id),
    reviewed_at     TIMESTAMPTZ,
    geo_id          UUID REFERENCES geo_hierarchy(id),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SOCIAL & ADS PLACEHOLDERS (high volume tables - partition later)
-- ============================================================
CREATE TABLE social_posts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform        VARCHAR(32) NOT NULL,  -- x | facebook | instagram | youtube | tiktok
    external_id     VARCHAR(255),
    author_handle   VARCHAR(255),
    content         TEXT,
    sentiment       VARCHAR(16),
    topics          TEXT[],
    geo_id          UUID REFERENCES geo_hierarchy(id),
    engagement      JSONB DEFAULT '{}',
    raw_payload     JSONB,
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ
);

CREATE INDEX idx_social_platform ON social_posts(platform);
CREATE INDEX idx_social_geo ON social_posts(geo_id);
CREATE INDEX idx_social_ingested ON social_posts(ingested_at DESC);

CREATE TABLE ad_campaigns (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform        VARCHAR(32) NOT NULL,
    external_id     VARCHAR(255),
    name            VARCHAR(255),
    status          VARCHAR(32),
    budget          NUMERIC(12,2),
    spend           NUMERIC(12,2) DEFAULT 0,
    metrics         JSONB DEFAULT '{}',
    geo_targets     UUID[],
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AUDIT & SYSTEM
-- ============================================================
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id),
    action          VARCHAR(128) NOT NULL,
    resource_type   VARCHAR(64),
    resource_id     UUID,
    details         JSONB DEFAULT '{}',
    ip_address      INET,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);

-- Grant
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO claim;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO claim;

-- Phase 4 addition
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS source_recommendation_id UUID;

-- Phase 5 Listen
CREATE TABLE IF NOT EXISTS keyword_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(128) NOT NULL,
    keywords TEXT[],
    platforms TEXT[],
    severity VARCHAR(16) DEFAULT 'medium',
    is_active BOOLEAN DEFAULT TRUE,
    geo_id UUID REFERENCES geo_hierarchy(id),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS sentiment_score FLOAT;
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS language VARCHAR(16);
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS is_bot_suspect BOOLEAN DEFAULT FALSE;
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS matched_keywords TEXT[];

-- Phase 6
CREATE TABLE IF NOT EXISTS ad_creatives (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES ad_campaigns(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    body TEXT,
    media_urls JSONB DEFAULT '[]',
    status VARCHAR(32) DEFAULT 'pending_review',
    metrics JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS influencers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    handle VARCHAR(255) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    display_name VARCHAR(255),
    category VARCHAR(32) DEFAULT 'neutral',
    reach INT DEFAULT 0,
    engagement_rate FLOAT DEFAULT 0,
    influence_score FLOAT DEFAULT 0,
    credibility FLOAT DEFAULT 0.5,
    geo_id UUID REFERENCES geo_hierarchy(id),
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rapid_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    trigger_alert_id UUID,
    narrative_type VARCHAR(64) DEFAULT 'counter_narrative',
    draft_body TEXT,
    status VARCHAR(32) DEFAULT 'queued',
    priority VARCHAR(16) DEFAULT 'high',
    assigned_to UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    ai_generated BOOLEAN DEFAULT TRUE,
    geo_id UUID REFERENCES geo_hierarchy(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_date DATE NOT NULL,
    event_type VARCHAR(64) DEFAULT 'other',
    geo_id UUID REFERENCES geo_hierarchy(id),
    created_by UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE ad_campaigns ADD COLUMN IF NOT EXISTS objective VARCHAR(64);
ALTER TABLE ad_campaigns ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id);

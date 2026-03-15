-- SOA-CLI PostgreSQL + pgvector schema
-- Apply with: psql "$SOA_DB_DSN" -f db/schema.sql

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL DEFAULT 'running',
    topic TEXT,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS papers (
    paper_pk BIGSERIAL PRIMARY KEY,
    source_paper_id TEXT NOT NULL UNIQUE,
    canonical_paper_id TEXT UNIQUE,
    title TEXT,
    year INTEGER,
    venue TEXT,
    authors JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS paper_aliases (
    alias_id BIGSERIAL PRIMARY KEY,
    paper_pk BIGINT NOT NULL REFERENCES papers(paper_pk) ON DELETE CASCADE,
    alias TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL DEFAULT 'auto',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS paper_embeddings (
    embedding_id BIGSERIAL PRIMARY KEY,
    paper_pk BIGINT NOT NULL REFERENCES papers(paper_pk) ON DELETE CASCADE,
    model_name TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (paper_pk, model_name)
);

CREATE INDEX IF NOT EXISTS idx_paper_embeddings_model ON paper_embeddings(model_name);
CREATE INDEX IF NOT EXISTS idx_paper_embeddings_ann ON paper_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS citations (
    citation_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    section_name TEXT,
    sentence_index INTEGER,
    canonical_paper_id TEXT NOT NULL,
    raw_citation_text TEXT,
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (canonical_paper_id) REFERENCES papers(canonical_paper_id)
);

CREATE TABLE IF NOT EXISTS sections (
    section_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    heading TEXT NOT NULL,
    level INTEGER NOT NULL,
    content_md TEXT NOT NULL,
    section_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    section_id BIGINT REFERENCES sections(section_id) ON DELETE SET NULL,
    claim_text TEXT NOT NULL,
    has_citation BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claim_evidence (
    claim_evidence_id BIGSERIAL PRIMARY KEY,
    claim_id BIGINT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE,
    canonical_paper_id TEXT NOT NULL REFERENCES papers(canonical_paper_id),
    confidence DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (claim_id, canonical_paper_id)
);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    logical_name TEXT NOT NULL,
    local_path TEXT,
    blob_uri TEXT,
    checksum_sha256 TEXT,
    content TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, logical_name)
);

CREATE TABLE IF NOT EXISTS metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    metric_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, metric_name)
);

CREATE TABLE IF NOT EXISTS benchmark_thresholds (
    threshold_id BIGSERIAL PRIMARY KEY,
    profile TEXT NOT NULL DEFAULT 'default',
    metric_name TEXT NOT NULL,
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (profile, metric_name)
);

INSERT INTO benchmark_thresholds (profile, metric_name, min_value, max_value)
VALUES
('default', 'citation_f1', 0.60, NULL),
('default', 'hsr', 0.50, NULL),
('default', 'tri_judge_score', 75.0, NULL)
ON CONFLICT (profile, metric_name) DO NOTHING;

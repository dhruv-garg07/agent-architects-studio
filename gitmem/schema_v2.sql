-- ============================================================
-- GitMem v2.0 — Complete Supabase Schema
-- Run this in Supabase SQL Editor
-- ============================================================

-- ============================================================
-- LAYER 3 — Workspaces & Access
-- ============================================================

-- Workspaces (Organizations)
CREATE TABLE IF NOT EXISTS gitmem_workspaces (
    workspace_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    owner_id TEXT NOT NULL,                -- user_id of creator
    plan TEXT NOT NULL DEFAULT 'free',     -- free, pro, enterprise
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workspaces_owner ON gitmem_workspaces(owner_id);
CREATE INDEX idx_workspaces_slug ON gitmem_workspaces(slug);

-- Workspace Members
CREATE TABLE IF NOT EXISTS gitmem_workspace_members (
    workspace_id TEXT NOT NULL REFERENCES gitmem_workspaces(workspace_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',   -- owner, admin, member, viewer
    invited_by TEXT,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, user_id)
);

CREATE INDEX idx_wm_user ON gitmem_workspace_members(user_id);

-- Repositories (Agent Memory Repos)
CREATE TABLE IF NOT EXISTS gitmem_repos (
    repo_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES gitmem_workspaces(workspace_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    description TEXT DEFAULT '',
    visibility TEXT NOT NULL DEFAULT 'private',  -- private, workspace, public
    owner_id TEXT NOT NULL,                      -- user_id who created it
    default_branch TEXT NOT NULL DEFAULT 'main',
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, slug)
);

CREATE INDEX idx_repos_workspace ON gitmem_repos(workspace_id);
CREATE INDEX idx_repos_owner ON gitmem_repos(owner_id);
CREATE INDEX idx_repos_visibility ON gitmem_repos(visibility);

-- Repo-Level Collaborators
CREATE TABLE IF NOT EXISTS gitmem_collaborators (
    repo_id TEXT NOT NULL REFERENCES gitmem_repos(repo_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'reader',   -- admin, writer, reader
    invited_by TEXT NOT NULL,
    accepted BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (repo_id, user_id)
);

CREATE INDEX idx_collab_user ON gitmem_collaborators(user_id);

-- ============================================================
-- LAYER 4 — Version Control
-- ============================================================

-- Memories
CREATE TABLE IF NOT EXISTS gitmem_memories (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL REFERENCES gitmem_repos(repo_id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL REFERENCES gitmem_workspaces(workspace_id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,                      -- backward compat
    type TEXT NOT NULL DEFAULT 'episodic',        -- episodic, semantic, procedural, state
    content TEXT NOT NULL,
    importance FLOAT NOT NULL DEFAULT 0.0,
    tags TEXT[] DEFAULT '{}',
    visibility TEXT NOT NULL DEFAULT 'private',   -- private, workspace, public
    provenance TEXT,                              -- author signature or source hash
    commit_hash TEXT,                            -- linked commit
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_memories_repo ON gitmem_memories(repo_id, created_at DESC);
CREATE INDEX idx_memories_workspace ON gitmem_memories(workspace_id);
CREATE INDEX idx_memories_agent ON gitmem_memories(agent_id, type);
CREATE INDEX idx_memories_type ON gitmem_memories(type);
CREATE INDEX idx_memories_importance ON gitmem_memories(repo_id, importance DESC);

-- Commits
CREATE TABLE IF NOT EXISTS gitmem_commits (
    hash TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL REFERENCES gitmem_repos(repo_id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL REFERENCES gitmem_workspaces(workspace_id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    message TEXT NOT NULL,
    parents TEXT[] DEFAULT '{}',
    tree_hash TEXT,                               -- Merkle root of memory state
    memory_snapshot TEXT[] DEFAULT '{}',           -- list of memory IDs
    stats JSONB NOT NULL DEFAULT '{}',            -- added, deleted, modified counts
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_commits_repo ON gitmem_commits(repo_id, timestamp DESC);
CREATE INDEX idx_commits_workspace ON gitmem_commits(workspace_id);
CREATE INDEX idx_commits_agent ON gitmem_commits(agent_id, timestamp DESC);

-- Branch & Tag Refs
CREATE TABLE IF NOT EXISTS gitmem_refs (
    repo_id TEXT NOT NULL REFERENCES gitmem_repos(repo_id) ON DELETE CASCADE,
    ref_name TEXT NOT NULL,                      -- e.g. 'main', 'feature/x', 'v1.0'
    ref_type TEXT NOT NULL DEFAULT 'branch',      -- branch, tag, agent
    target_hash TEXT NOT NULL,                    -- commit SHA
    is_protected BOOLEAN NOT NULL DEFAULT false,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (repo_id, ref_name)
);

CREATE INDEX idx_refs_repo ON gitmem_refs(repo_id);

-- RefLog (Audit Trail)
CREATE TABLE IF NOT EXISTS gitmem_reflog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id TEXT NOT NULL REFERENCES gitmem_repos(repo_id) ON DELETE CASCADE,
    ref_name TEXT NOT NULL,
    old_hash TEXT,
    new_hash TEXT NOT NULL,
    action TEXT NOT NULL,                         -- commit, checkout, merge, rollback, cherry-pick, reset
    actor_id TEXT NOT NULL,
    message TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reflog_repo ON gitmem_reflog(repo_id, created_at DESC);

-- ============================================================
-- LAYER 2 — Event Sourcing
-- ============================================================

CREATE TABLE IF NOT EXISTS gitmem_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL REFERENCES gitmem_workspaces(workspace_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,                    -- MEMORY_CREATED, COMMIT_CREATED, etc.
    actor_id TEXT NOT NULL,                      -- user_id or agent_id
    entity_type TEXT NOT NULL,                   -- memory, commit, branch, repo, workspace
    entity_id TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_workspace ON gitmem_events(workspace_id, created_at DESC);
CREATE INDEX idx_events_type ON gitmem_events(event_type, created_at DESC);
CREATE INDEX idx_events_actor ON gitmem_events(actor_id, created_at DESC);
CREATE INDEX idx_events_entity ON gitmem_events(entity_type, entity_id);

-- ============================================================
-- INFRA — Background Job Queue
-- ============================================================

CREATE TABLE IF NOT EXISTS gitmem_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL REFERENCES gitmem_workspaces(workspace_id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,                      -- embed, summarize, compact, gc, reindex
    payload JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',       -- pending, running, completed, failed, dead
    priority INT NOT NULL DEFAULT 0,              -- higher = more urgent
    attempts INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error TEXT,
    result JSONB
);

CREATE INDEX idx_jobs_pending ON gitmem_jobs(status, priority DESC, created_at)
    WHERE status = 'pending';
CREATE INDEX idx_jobs_workspace ON gitmem_jobs(workspace_id, status);

-- ============================================================
-- LEGACY — Repo Metadata (kept for backward compat)
-- ============================================================

CREATE TABLE IF NOT EXISTS gitmem_repo_meta (
    id INT PRIMARY KEY DEFAULT 1,
    name TEXT DEFAULT 'memory-store',
    description TEXT DEFAULT 'Central memory repository for AI agents',
    owner TEXT DEFAULT 'system',
    visibility TEXT DEFAULT 'public',
    default_branch TEXT DEFAULT 'main',
    branches JSONB DEFAULT '{"main": "HEAD"}',
    star_count INT DEFAULT 0,
    fork_count INT DEFAULT 0,
    watcher_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- STORAGE BUCKET (run via Supabase Dashboard or API)
-- ============================================================
-- Create bucket: gitmem-objects
-- This stores SHA-addressed zstd-compressed JSON blobs
-- for the Merkle DAG (blobs, trees, commits)
--
-- Bucket settings:
--   Name: gitmem-objects
--   Public: false
--   File size limit: 50MB
--   Allowed MIME types: application/octet-stream, application/json

-- ============================================================
-- HELPER: Auto-update updated_at timestamps
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_workspaces_updated_at
    BEFORE UPDATE ON gitmem_workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_repos_updated_at
    BEFORE UPDATE ON gitmem_repos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON gitmem_memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- GitMem Supabase Schema
-- Run this in your Supabase SQL Editor to initialize the database

-- 1. Memories Table
CREATE TABLE IF NOT EXISTS public.gitmem_memories (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT,
    embedding vector(1536), -- Optional, dependent on pgvector
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    importance FLOAT DEFAULT 0.0,
    scope TEXT DEFAULT 'private',
    tags TEXT[],
    provenance TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    commit_hash TEXT
);

-- Index for querying memories
CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON public.gitmem_memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_type ON public.gitmem_memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON public.gitmem_memories(created_at);


-- 2. Commits Table
CREATE TABLE IF NOT EXISTS public.gitmem_commits (
    hash TEXT PRIMARY KEY,
    message TEXT,
    agent_id TEXT NOT NULL,
    author_id TEXT,
    parents TEXT[],
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tree_hash TEXT,
    memory_snapshot TEXT[], -- List of Memory IDs
    stats JSONB DEFAULT '{}'::jsonb
);

-- Index for commits
CREATE INDEX IF NOT EXISTS idx_commits_agent_id ON public.gitmem_commits(agent_id);
CREATE INDEX IF NOT EXISTS idx_commits_timestamp ON public.gitmem_commits(timestamp);


-- 3. Repository Metadata Table (Singleton or per repo)
CREATE TABLE IF NOT EXISTS public.gitmem_repo_meta (
    id SERIAL PRIMARY KEY,
    name TEXT DEFAULT 'memory-store',
    description TEXT,
    owner TEXT DEFAULT 'system',
    visibility TEXT DEFAULT 'public',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    star_count INTEGER DEFAULT 0,
    fork_count INTEGER DEFAULT 0,
    watcher_count INTEGER DEFAULT 0,
    default_branch TEXT DEFAULT 'main',
    branches JSONB DEFAULT '{"main": "HEAD"}'::jsonb
);

-- Insert default metadata if not exists
INSERT INTO public.gitmem_repo_meta (id, name, branches)
VALUES (1, 'memory-store', '{"main": "HEAD"}'::jsonb)
ON CONFLICT (id) DO NOTHING;

-- Enable Row Level Security (Optional, for now allowing all)
ALTER TABLE public.gitmem_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gitmem_commits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gitmem_repo_meta ENABLE ROW LEVEL SECURITY;

-- Policies (Open for MVP)
CREATE POLICY "Enable all access for all users" ON public.gitmem_memories FOR ALL USING (true);
CREATE POLICY "Enable all access for all users" ON public.gitmem_commits FOR ALL USING (true);
CREATE POLICY "Enable all access for all users" ON public.gitmem_repo_meta FOR ALL USING (true);


-- ============================================================================
-- EXTENDED FOLDER STRUCTURE TABLES (Added for multi-source data)
-- ============================================================================

-- 4. Document Uploads Table (documents/ folder)
CREATE TABLE IF NOT EXISTS public.gitmem_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    folder TEXT NOT NULL CHECK (folder IN ('uploads', 'attachments', 'references')),
    filename TEXT NOT NULL,
    content_type TEXT,
    size_bytes BIGINT,
    storage_path TEXT,  -- Supabase Storage path or URL
    content TEXT,       -- For text files, store content directly
    description TEXT,
    tags TEXT[],
    uploaded_by TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_agent_id ON public.gitmem_documents(agent_id);
CREATE INDEX IF NOT EXISTS idx_documents_folder ON public.gitmem_documents(folder);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON public.gitmem_documents(created_at);


-- 5. Agent Checkpoints Table (checkpoints/ folder)
CREATE TABLE IF NOT EXISTS public.gitmem_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    checkpoint_type TEXT NOT NULL CHECK (checkpoint_type IN ('snapshot', 'session', 'recovery', 'auto')),
    name TEXT,
    description TEXT,
    commit_hash TEXT,
    parent_checkpoint_id UUID REFERENCES public.gitmem_checkpoints(id),
    memory_counts JSONB DEFAULT '{}'::jsonb,  -- {"episodic": 10, "semantic": 5, ...}
    session_id TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_agent_id ON public.gitmem_checkpoints(agent_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_type ON public.gitmem_checkpoints(checkpoint_type);
CREATE INDEX IF NOT EXISTS idx_checkpoints_created_at ON public.gitmem_checkpoints(created_at);


-- 6. API Call Logs Table (sources/api/ folder)
CREATE TABLE IF NOT EXISTS public.gitmem_api_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    method TEXT,
    request_headers JSONB DEFAULT '{}'::jsonb,
    request_body JSONB,
    response_status INT,
    response_data JSONB,
    duration_ms INT,
    cached BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_logs_agent_id ON public.gitmem_api_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint ON public.gitmem_api_logs(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_logs_created_at ON public.gitmem_api_logs(created_at);


-- 7. MCP Server Inputs Table (sources/mcp/ folder)
CREATE TABLE IF NOT EXISTS public.gitmem_mcp_inputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_description TEXT,
    input_data JSONB,
    output_data JSONB,
    session_id TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    duration_ms INT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mcp_inputs_agent_id ON public.gitmem_mcp_inputs(agent_id);
CREATE INDEX IF NOT EXISTS idx_mcp_inputs_tool_name ON public.gitmem_mcp_inputs(tool_name);
CREATE INDEX IF NOT EXISTS idx_mcp_inputs_created_at ON public.gitmem_mcp_inputs(created_at);


-- 8. Webhooks Table (sources/webhooks/ folder)
CREATE TABLE IF NOT EXISTS public.gitmem_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    source TEXT NOT NULL,           -- e.g., 'github', 'slack', 'custom'
    event_type TEXT,                -- e.g., 'push', 'message', 'issue'
    payload JSONB NOT NULL,
    headers JSONB DEFAULT '{}'::jsonb,
    signature TEXT,                 -- Webhook signature for verification
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhooks_agent_id ON public.gitmem_webhooks(agent_id);
CREATE INDEX IF NOT EXISTS idx_webhooks_source ON public.gitmem_webhooks(source);
CREATE INDEX IF NOT EXISTS idx_webhooks_processed ON public.gitmem_webhooks(processed);
CREATE INDEX IF NOT EXISTS idx_webhooks_created_at ON public.gitmem_webhooks(created_at);


-- 9. Integrations Config Table (sources/integrations/ folder)
CREATE TABLE IF NOT EXISTS public.gitmem_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    integration_type TEXT NOT NULL,  -- 'slack', 'github', 'notion', 'google_drive', etc.
    name TEXT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}'::jsonb,  -- Connection settings (encrypted in production)
    credentials JSONB DEFAULT '{}'::jsonb,  -- OAuth tokens, API keys (encrypted)
    sync_status TEXT DEFAULT 'idle',  -- 'idle', 'syncing', 'error'
    last_sync_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_integrations_agent_id ON public.gitmem_integrations(agent_id);
CREATE INDEX IF NOT EXISTS idx_integrations_type ON public.gitmem_integrations(integration_type);


-- 10. Activity Logs Table (logs/ folder)
CREATE TABLE IF NOT EXISTS public.gitmem_activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    log_type TEXT NOT NULL CHECK (log_type IN ('access', 'mutation', 'error', 'system')),
    action TEXT NOT NULL,           -- 'read', 'write', 'delete', 'create', etc.
    resource_type TEXT,             -- 'memory', 'document', 'checkpoint', etc.
    resource_id TEXT,
    actor_type TEXT,                -- 'user', 'agent', 'system'
    actor_id TEXT,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_logs_agent_id ON public.gitmem_activity_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_type ON public.gitmem_activity_logs(log_type);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON public.gitmem_activity_logs(created_at);


-- Enable RLS on new tables
ALTER TABLE public.gitmem_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gitmem_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gitmem_api_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gitmem_mcp_inputs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gitmem_webhooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gitmem_integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gitmem_activity_logs ENABLE ROW LEVEL SECURITY;

-- Open policies for MVP
CREATE POLICY "Enable all access" ON public.gitmem_documents FOR ALL USING (true);
CREATE POLICY "Enable all access" ON public.gitmem_checkpoints FOR ALL USING (true);
CREATE POLICY "Enable all access" ON public.gitmem_api_logs FOR ALL USING (true);
CREATE POLICY "Enable all access" ON public.gitmem_mcp_inputs FOR ALL USING (true);
CREATE POLICY "Enable all access" ON public.gitmem_webhooks FOR ALL USING (true);
CREATE POLICY "Enable all access" ON public.gitmem_integrations FOR ALL USING (true);
CREATE POLICY "Enable all access" ON public.gitmem_activity_logs FOR ALL USING (true);

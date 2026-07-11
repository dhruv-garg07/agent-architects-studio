create table if not exists public.agent_connections (
    id uuid primary key,
    source_agent_id text not null,
    target_agent_id text not null,
    permissions jsonb not null default '[]'::jsonb,
    scope text not null default 'all',
    status text not null default 'pending',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_agent_connections_source on public.agent_connections(source_agent_id);
create index if not exists idx_agent_connections_target on public.agent_connections(target_agent_id);
create index if not exists idx_agent_connections_status on public.agent_connections(status);

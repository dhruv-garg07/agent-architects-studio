-- GitMem Tables Setup

-- Enable pgvector
create extension if not exists vector;

-- 1. Memories Table (Full Schema Alignment)
create table if not exists gitmem_memories (
  id text primary key,
  agent_id text not null,
  type text not null, -- episodic, semantic, knowledge (docs)
  content text not null,
  created_at timestamptz default now(),
  importance float8 default 0.0,
  scope text default 'private',
  tags text[], -- Matches _text in Supabase
  provenance text,
  metadata jsonb default '{}'::jsonb,
  commit_hash text
);

alter table gitmem_memories enable row level security;
do $$ 
begin
  drop policy if exists "Allow public access" on gitmem_memories;
  create policy "Allow public access" on gitmem_memories for all using (true) with check (true);
end $$;

-- 2. Commits Table
create table if not exists gitmem_commits (
  hash text primary key,
  agent_id text not null,
  author_id text not null,
  message text not null,
  timestamp timestamptz default now(),
  parents jsonb default '[]'::jsonb,
  memory_snapshot jsonb default '[]'::jsonb,
  stats jsonb default '{}'::jsonb
);

alter table gitmem_commits enable row level security;
do $$ 
begin
  drop policy if exists "Allow public access" on gitmem_commits;
  create policy "Allow public access" on gitmem_commits for all using (true) with check (true);
end $$;

-- 3. Repo Metadata Table
create table if not exists gitmem_repo_meta (
  id serial primary key,
  star_count int default 0,
  fork_count int default 0,
  watcher_count int default 0,
  branches jsonb default '{"main": null}'::jsonb
);

alter table gitmem_repo_meta enable row level security;
do $$ 
begin
  drop policy if exists "Allow public access" on gitmem_repo_meta;
  create policy "Allow public access" on gitmem_repo_meta for all using (true) with check (true);
end $$;

insert into gitmem_repo_meta (id, star_count, fork_count, branches)
select 1, 0, 0, '{"main": null}'::jsonb
where not exists (select 1 from gitmem_repo_meta where id = 1);

-- 4. Checkpoints Table
create table if not exists gitmem_checkpoints (
  id uuid default gen_random_uuid() primary key,
  agent_id text not null,
  checkpoint_type text default 'stable',
  name text,
  description text,
  commit_hash text,
  state_dump jsonb,
  created_at timestamptz default now(),
  metadata jsonb default '{}'::jsonb
);

alter table gitmem_checkpoints enable row level security;
do $$ 
begin
  drop policy if exists "Allow public access" on gitmem_checkpoints;
  create policy "Allow public access" on gitmem_checkpoints for all using (true) with check (true);
end $$;

-- 5. Logs Table
create table if not exists gitmem_logs (
  id uuid default gen_random_uuid() primary key,
  agent_id text not null,
  type text default 'system',
  event text not null,
  details jsonb,
  created_at timestamptz default now()
);

alter table gitmem_logs enable row level security;
do $$ 
begin
  drop policy if exists "Allow public access" on gitmem_logs;
  create policy "Allow public access" on gitmem_logs for all using (true) with check (true);
end $$;

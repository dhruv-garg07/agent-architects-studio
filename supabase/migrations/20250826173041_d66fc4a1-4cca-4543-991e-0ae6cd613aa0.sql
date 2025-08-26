
-- Extensions for fast search
create extension if not exists pg_trgm;

-- 1) Roles to support admin-only verification
create type public.app_role as enum ('admin','moderator','user');

create table if not exists public.user_roles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  role public.app_role not null,
  unique (user_id, role),
  created_at timestamptz not null default now()
);

alter table public.user_roles enable row level security;

create or replace function public.has_role(_user_id uuid, _role public.app_role)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.user_roles
    where user_id = _user_id
      and role = _role
  );
$$;

-- RLS for user_roles
create policy if not exists "Users can view their own roles"
  on public.user_roles
  for select
  to authenticated
  using (auth.uid() = user_id);

create policy if not exists "Admins can view all roles"
  on public.user_roles
  for select
  to authenticated
  using (public.has_role(auth.uid(), 'admin'));

create policy if not exists "Admins can insert roles"
  on public.user_roles
  for insert
  to authenticated
  with check (public.has_role(auth.uid(), 'admin'));

create policy if not exists "Admins can update roles"
  on public.user_roles
  for update
  to authenticated
  using (public.has_role(auth.uid(), 'admin'));

create policy if not exists "Admins can delete roles"
  on public.user_roles
  for delete
  to authenticated
  using (public.has_role(auth.uid(), 'admin'));

-- 2) Verification workflow
create table if not exists public.agent_verifications (
  id uuid primary key default gen_random_uuid(),
  agent_id uuid not null references public.agent_profiles(id) on delete cascade,
  reviewer_id uuid not null,
  status text not null check (status in ('approved','rejected','suspended')),
  notes text,
  created_at timestamptz not null default now()
);

alter table public.agent_verifications enable row level security;

-- Public can read verification history; only admins can write
create policy if not exists "Agent verifications are viewable by everyone"
  on public.agent_verifications
  for select using (true);

create policy if not exists "Admins can insert agent verifications"
  on public.agent_verifications
  for insert
  to authenticated
  with check (public.has_role(auth.uid(), 'admin') and reviewer_id = auth.uid());

create policy if not exists "Admins can update agent verifications"
  on public.agent_verifications
  for update
  to authenticated
  using (public.has_role(auth.uid(), 'admin'));

create policy if not exists "Admins can delete agent verifications"
  on public.agent_verifications
  for delete
  to authenticated
  using (public.has_role(auth.uid(), 'admin'));

-- After a verification is recorded, sync status to agent_profiles
create or replace function public.apply_agent_verification()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.agent_profiles
  set status = NEW.status, updated_at = now()
  where id = NEW.agent_id;
  return NEW;
end;
$$;

drop trigger if exists trg_apply_agent_verification on public.agent_verifications;
create trigger trg_apply_agent_verification
after insert on public.agent_verifications
for each row execute function public.apply_agent_verification();

-- Ensure only admins can set "approved/rejected/suspended"; creators can set "draft/pending_review"
create or replace function public.enforce_agent_status_permissions()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  is_admin boolean;
begin
  is_admin := public.has_role(auth.uid(), 'admin');

  if not is_admin then
    if NEW.status not in ('draft','pending_review') then
      raise exception 'Only admins can set status to %, allowed for creators: draft, pending_review', NEW.status;
    end if;
    if TG_OP = 'UPDATE' and NEW.creator_id <> auth.uid() then
      raise exception 'You can only update your own agent';
    end if;
  end if;

  return NEW;
end;
$$;

drop trigger if exists trg_enforce_agent_status_permissions on public.agent_profiles;
create trigger trg_enforce_agent_status_permissions
before insert or update of status, creator_id on public.agent_profiles
for each row execute function public.enforce_agent_status_permissions();

-- Allow admins to update any agent (in addition to existing creator update policy)
create policy if not exists "Admins can update any agent profiles"
  on public.agent_profiles
  for update
  to authenticated
  using (public.has_role(auth.uid(), 'admin'));

-- 3) Keep avg_rating on agent_profiles in sync with reviews
create or replace function public.refresh_agent_rating()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  target_agent uuid;
  new_avg numeric;
begin
  target_agent := coalesce(NEW.agent_id, OLD.agent_id);

  select coalesce(avg(rating), 0) into new_avg
  from public.agent_reviews
  where agent_id = target_agent;

  update public.agent_profiles
  set avg_rating = new_avg, updated_at = now()
  where id = target_agent;

  return coalesce(NEW, OLD);
end;
$$;

drop trigger if exists trg_refresh_agent_rating_ins on public.agent_reviews;
drop trigger if exists trg_refresh_agent_rating_upd on public.agent_reviews;
drop trigger if exists trg_refresh_agent_rating_del on public.agent_reviews;

create trigger trg_refresh_agent_rating_ins
after insert on public.agent_reviews
for each row execute function public.refresh_agent_rating();

create trigger trg_refresh_agent_rating_upd
after update on public.agent_reviews
for each row execute function public.refresh_agent_rating();

create trigger trg_refresh_agent_rating_del
after delete on public.agent_reviews
for each row execute function public.refresh_agent_rating();

-- 4) Indexes for fast search & filters
create index if not exists agent_profiles_name_trgm on public.agent_profiles using gin (name gin_trgm_ops);
create index if not exists agent_profiles_description_trgm on public.agent_profiles using gin (description gin_trgm_ops);
create index if not exists agent_profiles_tags_gin on public.agent_profiles using gin (tags);
create index if not exists agent_profiles_modalities_gin on public.agent_profiles using gin (modalities);
create index if not exists agent_profiles_capabilities_gin on public.agent_profiles using gin (capabilities);
create index if not exists agent_profiles_category_idx on public.agent_profiles (category);
create index if not exists agent_profiles_model_idx on public.agent_profiles (model);
create index if not exists agent_profiles_status_idx on public.agent_profiles (status);

-- 5) Realtime for creators and agents
alter table public.user_profiles replica identity full;
alter table public.agent_profiles replica identity full;

alter publication supabase_realtime add table public.user_profiles;
alter publication supabase_realtime add table public.agent_profiles;

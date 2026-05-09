-- VaudTaxAI Phase B session persistence.
-- Anonymous sessions are keyed by session_uuid. Application code must set
-- app.session_uuid before scoped reads/writes when using RLS.

create table if not exists sessions (
  session_uuid uuid primary key,
  snapshot jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  expires_at timestamptz
);

create table if not exists documents (
  id bigserial primary key,
  session_uuid uuid not null references sessions(session_uuid) on delete cascade,
  doc_id text not null,
  filename text not null,
  document_type text not null,
  storage_path text,
  created_at timestamptz not null default now()
);

create table if not exists tax_facts (
  id bigserial primary key,
  session_uuid uuid not null references sessions(session_uuid) on delete cascade,
  canonical_field text not null,
  value jsonb not null,
  source_doc text not null,
  source_page integer not null,
  confidence numeric,
  confirmed_by_user boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists findings (
  id bigserial primary key,
  session_uuid uuid not null references sessions(session_uuid) on delete cascade,
  rule_id text not null,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists interview_answers (
  id bigserial primary key,
  session_uuid uuid not null references sessions(session_uuid) on delete cascade,
  question_id text not null,
  answer text not null,
  created_at timestamptz not null default now()
);

create table if not exists audit_log (
  id bigserial primary key,
  session_uuid uuid not null references sessions(session_uuid) on delete cascade,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table sessions enable row level security;
alter table documents enable row level security;
alter table tax_facts enable row level security;
alter table findings enable row level security;
alter table interview_answers enable row level security;
alter table audit_log enable row level security;

create policy "session scoped sessions" on sessions
  using (session_uuid::text = current_setting('app.session_uuid', true));
create policy "session scoped documents" on documents
  using (session_uuid::text = current_setting('app.session_uuid', true));
create policy "session scoped tax_facts" on tax_facts
  using (session_uuid::text = current_setting('app.session_uuid', true));
create policy "session scoped findings" on findings
  using (session_uuid::text = current_setting('app.session_uuid', true));
create policy "session scoped interview_answers" on interview_answers
  using (session_uuid::text = current_setting('app.session_uuid', true));
create policy "session scoped audit_log" on audit_log
  using (session_uuid::text = current_setting('app.session_uuid', true));

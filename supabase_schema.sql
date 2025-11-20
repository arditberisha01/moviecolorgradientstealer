-- Create a table for caching analysis results
create table if not exists analysis_cache (
  id uuid default uuid_generate_v4() primary key,
  cache_key text not null unique, -- Hash of URL or Movie Query
  lut_path text not null,
  frame_path text not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security (RLS)
alter table analysis_cache enable row level security;

-- Create a policy that allows public read access (since our app is public)
create policy "Allow public read access" on analysis_cache for select using (true);

-- Create a policy that allows insert/update for authenticated users (or anon if we want)
-- For simplicity in this MVP, we'll allow anon to insert if they have the key
create policy "Allow anon insert" on analysis_cache for insert with check (true);


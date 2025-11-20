# Database Migration Required

To enable caching features, you need to create the `analysis_cache` table in your Supabase database.

1.  Go to your Supabase Dashboard: [https://app.supabase.com](https://app.supabase.com)
2.  Select your project (`hhxtlrdtopezduyqwvld`).
3.  Go to the **SQL Editor**.
4.  Click **New Query**.
5.  Paste the contents of `supabase_schema.sql`:

```sql
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

-- Create a policy that allows public read access
create policy "Allow public read access" on analysis_cache for select using (true);

-- Create a policy that allows insert for anon users
create policy "Allow anon insert" on analysis_cache for insert with check (true);
```

6.  Click **Run**.

Once this is done, caching will automatically work!


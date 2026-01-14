-- Create GitMem Waitlist Table
-- Run this SQL script in your Supabase SQL Editor

CREATE TABLE IF NOT EXISTS public.gitmem_waitlist (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  name VARCHAR(255),
  tools TEXT,
  stack TEXT,
  goals TEXT,
  setup TEXT,
  open_to_feedback BOOLEAN DEFAULT false,
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on email for faster lookups
CREATE INDEX idx_gitmem_waitlist_email ON public.gitmem_waitlist(email);

-- Create index on created_at for sorting by signup date
CREATE INDEX idx_gitmem_waitlist_created_at ON public.gitmem_waitlist(created_at DESC);

-- Create index on open_to_feedback for filtering interested users
CREATE INDEX idx_gitmem_waitlist_feedback ON public.gitmem_waitlist(open_to_feedback);

-- Enable Row Level Security (Optional but recommended)
ALTER TABLE public.gitmem_waitlist ENABLE ROW LEVEL SECURITY;

-- Allow anyone to insert (for anonymous signups)
CREATE POLICY "Allow insert for all" ON public.gitmem_waitlist
  FOR INSERT
  TO authenticated, anon
  WITH CHECK (true);

-- Allow authenticated users to read their own data
CREATE POLICY "Allow read own data" ON public.gitmem_waitlist
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id OR user_id IS NULL);

-- Allow anon read (optional - remove if you want this private)
CREATE POLICY "Allow read for anon" ON public.gitmem_waitlist
  FOR SELECT
  TO anon
  USING (true);

-- Grant permissions
GRANT ALL ON public.gitmem_waitlist TO authenticated;
GRANT INSERT, SELECT ON public.gitmem_waitlist TO anon;

-- Optional: Create a view for admin dashboard (without sensitive data)
CREATE OR REPLACE VIEW public.gitmem_waitlist_summary AS
SELECT 
  id,
  email,
  name,
  tools,
  stack,
  goals,
  open_to_feedback,
  created_at
FROM public.gitmem_waitlist
ORDER BY created_at DESC;

-- Grant view permissions
GRANT SELECT ON public.gitmem_waitlist_summary TO authenticated;

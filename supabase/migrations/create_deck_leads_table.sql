-- Create Deck Leads Table
-- Run this SQL script in your Supabase SQL Editor

CREATE TABLE IF NOT EXISTS public.deck_leads (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name VARCHAR(255),
  email VARCHAR(255),
  phone VARCHAR(255),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on created_at for sorting by signup date
CREATE INDEX idx_deck_leads_created_at ON public.deck_leads(created_at DESC);

-- Enable Row Level Security
ALTER TABLE public.deck_leads ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users (service role) to insert/read
CREATE POLICY "Allow service role full access" ON public.deck_leads
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

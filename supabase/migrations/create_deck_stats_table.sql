-- Create a simple table to store global statistics for the deck
CREATE TABLE deck_stats (
    id SERIAL PRIMARY KEY,
    views INTEGER DEFAULT 218
);

-- Initialize the single row to exactly 218 as requested
INSERT INTO deck_stats (id, views) VALUES (1, 218) ON CONFLICT DO NOTHING;

-- Create a secure RPC function to atomically increment the view count.
-- Atomic increments are critical for view counters so that if 100 people 
-- load the deck at the exact same millisecond, no views are lost.
CREATE OR REPLACE FUNCTION increment_deck_views()
RETURNS integer AS $$
DECLARE
  new_views integer;
BEGIN
  -- We increment the row with id=1 and return the new value immediately
  UPDATE deck_stats 
  SET views = views + 1 
  WHERE id = 1 
  RETURNING views INTO new_views;
  
  RETURN new_views;
END;
$$ LANGUAGE plpgsql;

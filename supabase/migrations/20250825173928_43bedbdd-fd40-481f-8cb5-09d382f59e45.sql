-- Create agent_profiles table for detailed agent metadata
CREATE TABLE public.agent_profiles (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  creator_id UUID NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  version TEXT DEFAULT '1.0.0',
  category TEXT,
  tags TEXT[],
  github_url TEXT,
  model TEXT,
  license TEXT DEFAULT 'MIT',
  modalities TEXT[],
  capabilities TEXT[],
  io_schema JSONB,
  protocols TEXT[],
  runtime_dependencies TEXT[],
  dockerfile_url TEXT,
  upvotes INTEGER DEFAULT 0,
  total_runs INTEGER DEFAULT 0,
  avg_rating DECIMAL(2,1) DEFAULT 0,
  success_rate DECIMAL(5,2) DEFAULT 0,
  avg_latency INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'review'))
);

-- Create user_profiles table for creator information
CREATE TABLE public.user_profiles (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL UNIQUE,
  display_name TEXT,
  bio TEXT,
  avatar_url TEXT,
  github_username TEXT,
  twitter_username TEXT,
  website_url TEXT,
  reputation_score INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create agent_reviews table for ratings and feedback
CREATE TABLE public.agent_reviews (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id UUID NOT NULL REFERENCES public.agent_profiles(id) ON DELETE CASCADE,
  reviewer_id UUID NOT NULL,
  rating INTEGER CHECK (rating >= 1 AND rating <= 5),
  review_text TEXT,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create agent_comments table for discussions
CREATE TABLE public.agent_comments (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id UUID NOT NULL REFERENCES public.agent_profiles(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  parent_id UUID REFERENCES public.agent_comments(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  comment_type TEXT DEFAULT 'discussion' CHECK (comment_type IN ('discussion', 'question', 'feedback')),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create collaboration_requests table
CREATE TABLE public.collaboration_requests (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id UUID NOT NULL REFERENCES public.agent_profiles(id) ON DELETE CASCADE,
  requester_id UUID NOT NULL,
  creator_id UUID NOT NULL,
  message TEXT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined')),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create agent_changelog table for version history
CREATE TABLE public.agent_changelog (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id UUID NOT NULL REFERENCES public.agent_profiles(id) ON DELETE CASCADE,
  version TEXT NOT NULL,
  changes TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE public.agent_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.collaboration_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_changelog ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for agent_profiles
CREATE POLICY "Agent profiles are viewable by everyone" 
ON public.agent_profiles 
FOR SELECT 
USING (true);

CREATE POLICY "Users can create their own agent profiles" 
ON public.agent_profiles 
FOR INSERT 
WITH CHECK (auth.uid() = creator_id);

CREATE POLICY "Users can update their own agent profiles" 
ON public.agent_profiles 
FOR UPDATE 
USING (auth.uid() = creator_id);

-- Create RLS policies for user_profiles
CREATE POLICY "User profiles are viewable by everyone" 
ON public.user_profiles 
FOR SELECT 
USING (true);

CREATE POLICY "Users can update their own profile" 
ON public.user_profiles 
FOR UPDATE 
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own profile" 
ON public.user_profiles 
FOR INSERT 
WITH CHECK (auth.uid() = user_id);

-- Create RLS policies for agent_reviews
CREATE POLICY "Agent reviews are viewable by everyone" 
ON public.agent_reviews 
FOR SELECT 
USING (true);

CREATE POLICY "Authenticated users can create reviews" 
ON public.agent_reviews 
FOR INSERT 
WITH CHECK (auth.uid() = reviewer_id);

-- Create RLS policies for agent_comments
CREATE POLICY "Agent comments are viewable by everyone" 
ON public.agent_comments 
FOR SELECT 
USING (true);

CREATE POLICY "Authenticated users can create comments" 
ON public.agent_comments 
FOR INSERT 
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own comments" 
ON public.agent_comments 
FOR UPDATE 
USING (auth.uid() = user_id);

-- Create RLS policies for collaboration_requests
CREATE POLICY "Users can view collaboration requests they're involved in" 
ON public.collaboration_requests 
FOR SELECT 
USING (auth.uid() = requester_id OR auth.uid() = creator_id);

CREATE POLICY "Authenticated users can create collaboration requests" 
ON public.collaboration_requests 
FOR INSERT 
WITH CHECK (auth.uid() = requester_id);

CREATE POLICY "Creators can update collaboration requests" 
ON public.collaboration_requests 
FOR UPDATE 
USING (auth.uid() = creator_id);

-- Create RLS policies for agent_changelog
CREATE POLICY "Agent changelog is viewable by everyone" 
ON public.agent_changelog 
FOR SELECT 
USING (true);

-- Create function to update timestamps
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
NEW.updated_at = now();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_agent_profiles_updated_at
BEFORE UPDATE ON public.agent_profiles
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at
BEFORE UPDATE ON public.user_profiles
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_agent_comments_updated_at
BEFORE UPDATE ON public.agent_comments
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_collaboration_requests_updated_at
BEFORE UPDATE ON public.collaboration_requests
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

-- Create indexes for better performance
CREATE INDEX idx_agent_profiles_creator_id ON public.agent_profiles(creator_id);
CREATE INDEX idx_agent_profiles_category ON public.agent_profiles(category);
CREATE INDEX idx_agent_profiles_status ON public.agent_profiles(status);
CREATE INDEX idx_agent_reviews_agent_id ON public.agent_reviews(agent_id);
CREATE INDEX idx_agent_comments_agent_id ON public.agent_comments(agent_id);
CREATE INDEX idx_agent_comments_parent_id ON public.agent_comments(parent_id);
CREATE INDEX idx_collaboration_requests_agent_id ON public.collaboration_requests(agent_id);
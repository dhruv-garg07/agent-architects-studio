import { supabase } from "@/integrations/supabase/client";
import type { TablesInsert, TablesUpdate } from "@/integrations/supabase/types";

// Fetch all agents for a given creator
export async function getUserAgents(creatorId: string) {
  const { data, error } = await supabase
    .from('agent_profiles')
    .select('*')
    .eq('creator_id', creatorId)
    .order('created_at', { ascending: false });
  if (error) throw error;
  return data ?? [];
}

// Create a new agent profile
export async function createAgent(payload: TablesInsert<'agent_profiles'>) {
  const { data, error } = await supabase
    .from('agent_profiles')
    .insert([payload])
    .select()
    .single();
  if (error) throw error;
  return data;
}

// Update an existing agent profile
export async function updateAgent(id: string, payload: TablesUpdate<'agent_profiles'>) {
  const { data, error } = await supabase
    .from('agent_profiles')
    .update(payload)
    .eq('id', id)
    .select()
    .single();
  if (error) throw error;
  return data;
}

// Delete an agent profile
export async function deleteAgent(id: string) {
  const { error } = await supabase
    .from('agent_profiles')
    .delete()
    .eq('id', id);
  if (error) throw error;
}

// Fetch top agents for leaderboard
export async function getTopAgents(limit = 10) {
  const { data, error } = await supabase
    .from('agent_profiles')
    .select(`*, user_profiles(display_name, avatar_url)`)
    .eq('status', 'published')
    .order('avg_rating', { ascending: false })
    .limit(limit);
  if (error) throw error;
  return data ?? [];
}

// Fetch top creators for leaderboard
export async function getTopCreators(limit = 10) {
  const { data, error } = await supabase
    .from('user_profiles')
    .select('*')
    .limit(limit);
  if (error) throw error;
  return data ?? [];
}

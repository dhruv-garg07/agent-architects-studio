
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/components/ui/use-toast";
import { Star, Play, Eye, Users, Code, TrendingUp, Clock } from "lucide-react";
import SearchAndFilters from "@/components/SearchAndFilters";
import { NavLink } from "react-router-dom";

interface Creator {
  display_name: string;
  avatar_url: string;
}

interface Agent {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  model: string;
  modalities: string[];
  capabilities: string[];
  status: string;
  avg_rating: number;
  total_runs: number;
  created_at: string;
  creator_id: string;
}

interface AgentWithCreator extends Agent {
  creator: Creator;
}

interface SearchFilters {
  search: string;
  category: string;
  model: string;
  modalities: string[];
  capabilities: string[];
  status: string;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
}

const Explore = () => {
  const [agents, setAgents] = useState<AgentWithCreator[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filters, setFilters] = useState<SearchFilters>({
    search: '',
    category: '',
    model: '',
    modalities: [],
    capabilities: [],
    status: 'published', // Default to published agents
    sortBy: 'created_at',
    sortOrder: 'desc'
  });
  const { toast } = useToast();

  useEffect(() => {
    fetchAgents();
  }, [filters]);

  const fetchAgents = async () => {
    setIsLoading(true);
    try {
      let query = supabase
        .from('agent_profiles')
        .select('*');

      // Apply filters
      if (filters.search) {
        query = query.or(`name.ilike.%${filters.search}%,description.ilike.%${filters.search}%`);
      }
      
      if (filters.category) {
        query = query.eq('category', filters.category);
      }
      
      if (filters.model) {
        query = query.eq('model', filters.model);
      }
      
      if (filters.status) {
        query = query.eq('status', filters.status);
      }
      
      if (filters.modalities.length > 0) {
        query = query.overlaps('modalities', filters.modalities);
      }
      
      if (filters.capabilities.length > 0) {
        query = query.overlaps('capabilities', filters.capabilities);
      }

      // Apply sorting
      query = query.order(filters.sortBy, { ascending: filters.sortOrder === 'asc' });

      const { data: agentData, error } = await query;

      if (error) throw error;

      if (agentData && agentData.length > 0) {
        // Fetch creator profiles separately
        const creatorIds = agentData.map(agent => agent.creator_id);
        const { data: creatorData, error: creatorError } = await supabase
          .from('user_profiles')
          .select('user_id, display_name, avatar_url')
          .in('user_id', creatorIds);

        if (creatorError) throw creatorError;

        // Combine agent data with creator data
        const agentsWithCreators = agentData.map(agent => {
          const creator = creatorData?.find(c => c.user_id === agent.creator_id) || {
            display_name: 'Unknown Creator',
            avatar_url: ''
          };
          return {
            ...agent,
            creator: {
              display_name: creator.display_name || 'Unknown Creator',
              avatar_url: creator.avatar_url || ''
            }
          };
        });

        setAgents(agentsWithCreators);
      } else {
        setAgents([]);
      }
    } catch (error) {
      console.error('Error fetching agents:', error);
      toast({
        title: "Error",
        description: "Failed to fetch agents",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "published": return "sage";
      case "draft": return "secondary";
      case "pending_review": return "soft-ochre";
      case "approved": return "sage";
      case "rejected": return "destructive";
      case "suspended": return "destructive";
      default: return "secondary";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "published": return "Published";
      case "draft": return "Draft";
      case "pending_review": return "Pending Review";
      case "approved": return "Approved";
      case "rejected": return "Rejected";
      case "suspended": return "Suspended";
      default: return status;
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
    return num.toString();
  };

  const getCreatorInitials = (name: string) => {
    return name?.split(' ').map(n => n[0]).join('').toUpperCase() || '?';
  };

  if (isLoading && agents.length === 0) {
    return (
      <div className="container mx-auto px-4 lg:px-8 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="w-8 h-8 animate-spin mx-auto mb-2 border-2 border-primary border-t-transparent rounded-full" />
            <p className="text-muted-foreground">Loading agents...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl lg:text-4xl font-bold font-inter mb-2">
          Explore Agents
        </h1>
        <p className="text-muted-foreground">
          Discover and deploy AI agents from the community
        </p>
      </div>

      <div className="grid lg:grid-cols-4 gap-8">
        {/* Filters Sidebar */}
        <div className="lg:col-span-1">
          <SearchAndFilters
            filters={filters}
            onFiltersChange={setFilters}
            isLoading={isLoading}
            resultCount={agents.length}
          />
        </div>

        {/* Results */}
        <div className="lg:col-span-3">
          {agents.length === 0 && !isLoading ? (
            <Card className="card-elevated">
              <CardContent className="py-12 text-center">
                <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
                  <Code className="w-8 h-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold mb-2">No agents found</h3>
                <p className="text-muted-foreground mb-4">
                  Try adjusting your search criteria or filters
                </p>
                <Button onClick={() => setFilters({
                  search: '',
                  category: '',
                  model: '',
                  modalities: [],
                  capabilities: [],
                  status: 'published',
                  sortBy: 'created_at',
                  sortOrder: 'desc'
                })}>
                  Clear Filters
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-6">
              {agents.map((agent) => (
                <Card key={agent.id} className="card-elevated hover:shadow-lg transition-all duration-200">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-start space-x-4 flex-1">
                        <div className="w-12 h-12 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-semibold shrink-0">
                          {agent.name.charAt(0)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-2">
                            <h3 className="font-semibold text-lg truncate">{agent.name}</h3>
                            <Badge className={`btn-${getStatusColor(agent.status)} shrink-0`}>
                              {getStatusText(agent.status)}
                            </Badge>
                          </div>
                          <p className="text-muted-foreground text-sm line-clamp-2 mb-3">
                            {agent.description}
                          </p>
                          
                          {/* Tags */}
                          {agent.tags && agent.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mb-3">
                              {agent.tags.slice(0, 3).map((tag) => (
                                <Badge key={tag} variant="outline" className="text-xs">
                                  {tag}
                                </Badge>
                              ))}
                              {agent.tags.length > 3 && (
                                <Badge variant="outline" className="text-xs">
                                  +{agent.tags.length - 3} more
                                </Badge>
                              )}
                            </div>
                          )}

                          {/* Creator Info */}
                          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                            <div className="w-5 h-5 bg-primary rounded-full flex items-center justify-center text-primary-foreground text-xs font-medium">
                              {agent.creator?.avatar_url ? (
                                <img 
                                  src={agent.creator.avatar_url} 
                                  alt={agent.creator.display_name} 
                                  className="w-5 h-5 rounded-full object-cover"
                                />
                              ) : (
                                getCreatorInitials(agent.creator?.display_name || "")
                              )}
                            </div>
                            <span>by {agent.creator?.display_name || "Unknown"}</span>
                            <span>•</span>
                            <span>{agent.category}</span>
                            <span>•</span>
                            <span>{agent.model}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Stats and Actions */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-6 text-sm text-muted-foreground">
                        <div className="flex items-center space-x-1">
                          <Star className="w-4 h-4 text-soft-ochre fill-soft-ochre" />
                          <span>{agent.avg_rating.toFixed(1)}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Play className="w-4 h-4" />
                          <span>{formatNumber(agent.total_runs)} runs</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Clock className="w-4 h-4" />
                          <span>{new Date(agent.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        <Button asChild variant="outline" size="sm">
                          <NavLink to={`/agent/${agent.id}`}>
                            <Eye className="w-4 h-4 mr-1" />
                            View
                          </NavLink>
                        </Button>
                        {agent.status === 'published' && (
                          <Button size="sm" className="btn-primary">
                            <Play className="w-4 h-4 mr-1" />
                            Deploy
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}

              {isLoading && (
                <div className="text-center py-8">
                  <div className="w-6 h-6 animate-spin mx-auto mb-2 border-2 border-primary border-t-transparent rounded-full" />
                  <p className="text-sm text-muted-foreground">Loading more agents...</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Explore;

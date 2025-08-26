
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/components/ui/use-toast";
import { Search, Users, Star, Code, TrendingUp, Award, Github, Globe } from "lucide-react";

interface CreatorProfile {
  id: string;
  display_name: string;
  bio: string;
  avatar_url: string;
  github_username: string;
  website_url: string;
  reputation_score: number;
  created_at: string;
  user_id: string;
}

interface CreatorStats {
  agent_count: number;
  total_runs: number;
  avg_rating: number;
}

interface CreatorWithStats extends CreatorProfile {
  agent_count: number;
  total_runs: number;
  avg_rating: number;
}

const Creators = () => {
  const [creators, setCreators] = useState<CreatorWithStats[]>([]);
  const [filteredCreators, setFilteredCreators] = useState<CreatorWithStats[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState("reputation");
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    fetchCreators();
    
    // Set up real-time subscription
    const subscription = supabase
      .channel('creators-changes')
      .on('postgres_changes', 
        { event: '*', schema: 'public', table: 'user_profiles' },
        () => fetchCreators()
      )
      .subscribe();

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    filterAndSortCreators();
  }, [creators, searchTerm, sortBy]);

  const fetchCreators = async () => {
    try {
      // Fetch user profiles first
      const { data: profiles, error: profilesError } = await supabase
        .from('user_profiles')
        .select('*');

      if (profilesError) throw profilesError;

      if (!profiles || profiles.length === 0) {
        setCreators([]);
        return;
      }

      // Fetch agent statistics for each creator
      const creatorIds = profiles.map(p => p.user_id);
      
      const { data: agentStats, error: statsError } = await supabase
        .from('agent_profiles')
        .select('creator_id, total_runs, avg_rating')
        .in('creator_id', creatorIds);

      if (statsError) throw statsError;

      // Process data to get stats per creator
      const creatorsWithStats = profiles.map(creator => {
        const creatorAgents = agentStats?.filter(a => a.creator_id === creator.user_id) || [];
        const agent_count = creatorAgents.length;
        const total_runs = creatorAgents.reduce((sum, agent) => sum + (agent.total_runs || 0), 0);
        const avg_rating = creatorAgents.length > 0 
          ? creatorAgents.reduce((sum, agent) => sum + (agent.avg_rating || 0), 0) / creatorAgents.length 
          : 0;

        return {
          ...creator,
          agent_count,
          total_runs,
          avg_rating
        };
      });
      
      setCreators(creatorsWithStats);
    } catch (error) {
      console.error('Error fetching creators:', error);
      toast({
        title: "Error",
        description: "Failed to fetch creators",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const filterAndSortCreators = () => {
    let filtered = creators.filter(creator =>
      creator.display_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      creator.bio?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    filtered.sort((a, b) => {
      switch (sortBy) {
        case "reputation":
          return b.reputation_score - a.reputation_score;
        case "agents":
          return b.agent_count - a.agent_count;
        case "rating":
          return b.avg_rating - a.avg_rating;
        case "runs":
          return b.total_runs - a.total_runs;
        default:
          return 0;
      }
    });

    setFilteredCreators(filtered);
  };

  const getCreatorInitials = (name: string) => {
    return name?.split(' ').map(n => n[0]).join('').toUpperCase() || '?';
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 lg:px-8 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="w-8 h-8 animate-spin mx-auto mb-2 border-2 border-primary border-t-transparent rounded-full" />
            <p className="text-muted-foreground">Loading creators...</p>
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
          Creator Community
        </h1>
        <p className="text-muted-foreground">
          Discover and connect with AI agent creators
        </p>
      </div>

      <Tabs defaultValue="directory" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2 max-w-md">
          <TabsTrigger value="directory">Directory</TabsTrigger>
          <TabsTrigger value="leaderboard">Leaderboard</TabsTrigger>
        </TabsList>

        <TabsContent value="directory">
          {/* Search and Filter */}
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
              <Input
                placeholder="Search creators..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="reputation">Reputation</SelectItem>
                <SelectItem value="agents">Agent Count</SelectItem>
                <SelectItem value="rating">Average Rating</SelectItem>
                <SelectItem value="runs">Total Runs</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Creators Grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCreators.map((creator) => (
              <Card key={creator.id} className="card-elevated hover:shadow-lg transition-shadow">
                <CardHeader className="pb-4">
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-semibold">
                      {creator.avatar_url ? (
                        <img 
                          src={creator.avatar_url} 
                          alt={creator.display_name} 
                          className="w-12 h-12 rounded-full object-cover"
                        />
                      ) : (
                        getCreatorInitials(creator.display_name || "")
                      )}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-lg">{creator.display_name}</h3>
                      <div className="flex items-center space-x-2">
                        <Badge variant="secondary" className="text-xs">
                          <Star className="w-3 h-3 mr-1" />
                          {creator.reputation_score}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                    {creator.bio || "No bio available"}
                  </p>
                  
                  <div className="grid grid-cols-3 gap-4 mb-4 text-center">
                    <div>
                      <div className="font-semibold text-lg">{creator.agent_count}</div>
                      <div className="text-xs text-muted-foreground">Agents</div>
                    </div>
                    <div>
                      <div className="font-semibold text-lg">{creator.total_runs.toLocaleString()}</div>
                      <div className="text-xs text-muted-foreground">Runs</div>
                    </div>
                    <div>
                      <div className="font-semibold text-lg">{creator.avg_rating.toFixed(1)}</div>
                      <div className="text-xs text-muted-foreground">Rating</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex space-x-2">
                      {creator.github_username && (
                        <Button size="sm" variant="outline">
                          <Github className="w-4 h-4" />
                        </Button>
                      )}
                      {creator.website_url && (
                        <Button size="sm" variant="outline">
                          <Globe className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                    <Button size="sm" className="btn-primary">
                      View Profile
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="leaderboard">
          <div className="space-y-6">
            {/* Top 3 */}
            <div className="grid md:grid-cols-3 gap-6">
              {filteredCreators.slice(0, 3).map((creator, index) => (
                <Card key={creator.id} className={`card-elevated ${index === 0 ? 'ring-2 ring-primary' : ''}`}>
                  <CardHeader className="text-center pb-4">
                    <div className="flex justify-center mb-2">
                      {index === 0 && <Award className="w-8 h-8 text-soft-ochre" />}
                      {index === 1 && <Award className="w-8 h-8 text-muted-foreground" />}
                      {index === 2 && <Award className="w-8 h-8 text-warm-coral" />}
                    </div>
                    <div className="w-16 h-16 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-bold text-xl mx-auto mb-2">
                      {creator.avatar_url ? (
                        <img 
                          src={creator.avatar_url} 
                          alt={creator.display_name} 
                          className="w-16 h-16 rounded-full object-cover"
                        />
                      ) : (
                        getCreatorInitials(creator.display_name || "")
                      )}
                    </div>
                    <CardTitle className="text-lg">{creator.display_name}</CardTitle>
                    <div className="text-2xl font-bold text-primary">{creator.reputation_score}</div>
                    <div className="text-sm text-muted-foreground">Reputation Score</div>
                  </CardHeader>
                </Card>
              ))}
            </div>

            {/* Full Leaderboard */}
            <Card className="card-elevated">
              <CardHeader>
                <CardTitle>Full Leaderboard</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {filteredCreators.map((creator, index) => (
                    <div key={creator.id} className="flex items-center space-x-4 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                      <div className="w-8 h-8 flex items-center justify-center font-bold text-lg">
                        #{index + 1}
                      </div>
                      <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-semibold">
                        {creator.avatar_url ? (
                          <img 
                            src={creator.avatar_url} 
                            alt={creator.display_name} 
                            className="w-10 h-10 rounded-full object-cover"
                          />
                        ) : (
                          getCreatorInitials(creator.display_name || "")
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="font-semibold">{creator.display_name}</div>
                        <div className="text-sm text-muted-foreground">
                          {creator.agent_count} agents • {creator.total_runs.toLocaleString()} runs
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-lg">{creator.reputation_score}</div>
                        <div className="text-xs text-muted-foreground">points</div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Creators;

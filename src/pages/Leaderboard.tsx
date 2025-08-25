import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { getTopAgents, getTopCreators } from "@/lib/api/agents";
import {
  Trophy,
  Star,
  TrendingUp,
  Play,
  Clock,
  Award,
  Target,
  Zap
} from "lucide-react";

const Leaderboard = () => {
  const [topAgents, setTopAgents] = useState([]);
  const [topCreators, setTopCreators] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const { toast } = useToast();

  useEffect(() => {
    fetchLeaderboardData();
  }, []);

  const fetchLeaderboardData = async () => {
    try {
      const agents = await getTopAgents();
      setTopAgents(agents);
      const creators = await getTopCreators();
      setTopCreators(creators);
    } catch (error) {
      console.error('Error fetching leaderboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <Trophy className="w-5 h-5 text-yellow-500" />;
      case 2:
        return <Award className="w-5 h-5 text-gray-400" />;
      case 3:
        return <Award className="w-5 h-5 text-orange-600" />;
      default:
        return <span className="w-5 h-5 flex items-center justify-center text-sm font-bold text-muted-foreground">{rank}</span>;
    }
  };

  return (
    <div className="container mx-auto px-4 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center space-x-3 mb-4">
          <Trophy className="w-8 h-8 text-primary" />
          <h1 className="text-3xl lg:text-4xl font-bold font-inter">
            Community Leaderboard
          </h1>
        </div>
        <p className="text-muted-foreground">
          Discover the top-performing agents and most accomplished creators in our community
        </p>
      </div>

      {/* Challenge Banner */}
      <Card className="card-elevated mb-8 bg-gradient-to-r from-primary/5 to-dusty-blue/5 border-primary/20">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold mb-2 flex items-center">
                <Target className="w-5 h-5 mr-2 text-primary" />
                Monthly Challenge: Best Code Assistant
              </h3>
              <p className="text-muted-foreground">
                Submit your best coding agent to compete for the top spot and win community recognition
              </p>
            </div>
            <Button className="bg-primary hover:bg-primary-hover" onClick={() => navigate('/studio')}>
              Join Challenge
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="agents" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="agents">Top Agents</TabsTrigger>
          <TabsTrigger value="creators">Top Creators</TabsTrigger>
          <TabsTrigger value="trending">Trending</TabsTrigger>
        </TabsList>

        <TabsContent value="agents">
          <div className="space-y-4">
            {topAgents.map((agent, index) => (
              <Card key={agent.id} className="card-elevated">
                <CardContent className="p-6">
                  <div className="flex items-center space-x-4">
                    <div className="flex items-center justify-center w-12 h-12 bg-muted rounded-lg">
                      {getRankIcon(index + 1)}
                    </div>
                    
                    <div className="w-12 h-12 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-semibold">
                      {agent.name.charAt(0)}
                    </div>
                    
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h3 className="font-semibold text-lg">{agent.name}</h3>
                        <Badge className="btn-sage">{agent.category}</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        by {agent.user_profiles?.display_name || "Anonymous"}
                      </p>
                    </div>
                    
                    <div className="text-right space-y-1">
                      <div className="flex items-center space-x-1">
                        <Star className="w-4 h-4 fill-soft-ochre text-soft-ochre" />
                        <span className="font-semibold">{agent.avg_rating || "0.0"}</span>
                      </div>
                      <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                        <span className="flex items-center space-x-1">
                          <Play className="w-3 h-3" />
                          <span>{(agent.total_runs || 0).toLocaleString()}</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <Zap className="w-3 h-3" />
                          <span>{agent.success_rate || 0}%</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="creators">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {topCreators.map((creator, index) => (
              <Card key={creator.id} className="card-elevated">
                <CardContent className="p-6">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="flex items-center justify-center w-8 h-8">
                      {getRankIcon(index + 1)}
                    </div>
                    <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-semibold">
                      {creator.display_name?.charAt(0) || "A"}
                    </div>
                    <div>
                      <h3 className="font-semibold">{creator.display_name || "Anonymous"}</h3>
                      <p className="text-sm text-muted-foreground">
                        Reputation: {creator.reputation_score || 0}
                      </p>
                    </div>
                  </div>
                  
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <div className="flex justify-between">
                      <span>Agents Published:</span>
                      <span className="font-semibold">0</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Total Runs:</span>
                      <span className="font-semibold">0</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg Rating:</span>
                      <span className="font-semibold">0.0</span>
                    </div>
                  </div>
                  
                  <Button
                    variant="outline"
                    className="w-full mt-4"
                    onClick={() => toast({ title: 'Coming soon', description: 'Creator profiles are under development' })}
                  >
                    View Profile
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="trending">
          <div className="grid lg:grid-cols-2 gap-6">
            <Card className="card-elevated">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <TrendingUp className="w-5 h-5 mr-2 text-dusty-blue" />
                  Rising Stars
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center space-x-3 p-3 bg-sage/5 rounded-lg">
                    <div className="w-8 h-8 bg-sage rounded-lg flex items-center justify-center text-sage-foreground font-semibold text-sm">
                      N
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-sm">Neural Writer</p>
                      <p className="text-xs text-muted-foreground">+247% runs this week</p>
                    </div>
                    <TrendingUp className="w-4 h-4 text-sage" />
                  </div>
                  
                  <div className="flex items-center space-x-3 p-3 bg-dusty-blue/5 rounded-lg">
                    <div className="w-8 h-8 bg-dusty-blue rounded-lg flex items-center justify-center text-dusty-blue-foreground font-semibold text-sm">
                      Q
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-sm">Query Master</p>
                      <p className="text-xs text-muted-foreground">+189% runs this week</p>
                    </div>
                    <TrendingUp className="w-4 h-4 text-dusty-blue" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="card-elevated">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Clock className="w-5 h-5 mr-2 text-soft-ochre" />
                  Recently Added
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center space-x-3 p-3 bg-soft-ochre/5 rounded-lg">
                    <div className="w-8 h-8 bg-soft-ochre rounded-lg flex items-center justify-center text-soft-ochre-foreground font-semibold text-sm">
                      A
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-sm">API Generator</p>
                      <p className="text-xs text-muted-foreground">Added 2 hours ago</p>
                    </div>
                    <Badge variant="outline">New</Badge>
                  </div>
                  
                  <div className="flex items-center space-x-3 p-3 bg-warm-coral/5 rounded-lg">
                    <div className="w-8 h-8 bg-warm-coral rounded-lg flex items-center justify-center text-warm-coral-foreground font-semibold text-sm">
                      D
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-sm">Debug Helper</p>
                      <p className="text-xs text-muted-foreground">Added 1 day ago</p>
                    </div>
                    <Badge variant="outline">New</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Leaderboard;
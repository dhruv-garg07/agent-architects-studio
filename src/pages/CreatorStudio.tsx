
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/components/ui/use-toast";
import { Plus, FileText, Settings, BarChart3, Users, AlertTriangle, Clock, CheckCircle, Eye, Pencil } from "lucide-react";
import AgentVerification from "@/components/AgentVerification";

interface Agent {
  id: string;
  name: string;
  description: string;
  category: string;
  status: string;
  created_at: string;
  total_runs: number;
  avg_rating: number;
  upvotes: number;
}

const CreatorStudio = () => {
  const [user, setUser] = useState<any>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("agents");
  const { toast } = useToast();

  // Form states for new agent
  const [isCreating, setIsCreating] = useState(false);
  const [newAgent, setNewAgent] = useState({
    name: "",
    description: "",
    category: "",
    model: "gpt-4",
    tags: [] as string[],
    capabilities: [] as string[],
    modalities: [] as string[]
  });

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        toast({
          title: "Authentication required",
          description: "Please sign in to access Creator Studio",
          variant: "destructive"
        });
        return;
      }

      setUser(user);
      
      // Check if user is admin (simple check for now)
      const { data: profile } = await supabase
        .from('user_profiles')
        .select('*')
        .eq('user_id', user.id)
        .single();

      // For now, consider any user an admin for testing
      // You can implement proper role checking later
      setIsAdmin(true);

      await fetchUserAgents(user.id);
    } catch (error) {
      console.error('Auth check error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchUserAgents = async (userId: string) => {
    try {
      const { data, error } = await supabase
        .from('agent_profiles')
        .select('*')
        .eq('creator_id', userId)
        .order('created_at', { ascending: false });

      if (error) throw error;
      setAgents(data || []);
    } catch (error) {
      console.error('Error fetching user agents:', error);
      toast({
        title: "Error",
        description: "Failed to fetch your agents",
        variant: "destructive"
      });
    }
  };

  const handleCreateAgent = async () => {
    if (!user) return;
    
    setIsCreating(true);
    try {
      const { error } = await supabase
        .from('agent_profiles')
        .insert({
          creator_id: user.id,
          name: newAgent.name,
          description: newAgent.description,
          category: newAgent.category,
          model: newAgent.model,
          tags: newAgent.tags,
          capabilities: newAgent.capabilities,
          modalities: newAgent.modalities,
          status: 'draft'
        });

      if (error) throw error;

      toast({
        title: "Success",
        description: "Agent created successfully",
      });

      // Reset form and refresh agents
      setNewAgent({
        name: "",
        description: "",
        category: "",
        model: "gpt-4",
        tags: [],
        capabilities: [],
        modalities: []
      });
      
      await fetchUserAgents(user.id);
    } catch (error) {
      console.error('Error creating agent:', error);
      toast({
        title: "Error",
        description: "Failed to create agent",
        variant: "destructive"
      });
    } finally {
      setIsCreating(false);
    }
  };

  const handleSubmitForReview = async (agentId: string) => {
    try {
      const { error } = await supabase
        .from('agent_profiles')
        .update({ status: 'pending_review' })
        .eq('id', agentId);

      if (error) throw error;

      toast({
        title: "Success",
        description: "Agent submitted for review",
      });

      if (user) {
        await fetchUserAgents(user.id);
      }
    } catch (error) {
      console.error('Error submitting for review:', error);
      toast({
        title: "Error",
        description: "Failed to submit for review",
        variant: "destructive"
      });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "published": return "sage";
      case "draft": return "secondary";
      case "pending_review": return "soft-ochre";
      case "approved": return "sage";
      case "rejected": return "destructive";
      default: return "secondary";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "published": return <CheckCircle className="w-4 h-4" />;
      case "pending_review": return <Clock className="w-4 h-4" />;
      case "draft": return <FileText className="w-4 h-4" />;
      case "rejected": return <AlertTriangle className="w-4 h-4" />;
      default: return <FileText className="w-4 h-4" />;
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 lg:px-8 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="w-8 h-8 animate-spin mx-auto mb-2 border-2 border-primary border-t-transparent rounded-full" />
            <p className="text-muted-foreground">Loading Creator Studio...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container mx-auto px-4 lg:px-8 py-8">
        <Card className="card-elevated">
          <CardContent className="py-8 text-center">
            <AlertTriangle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Authentication Required</h3>
            <p className="text-muted-foreground mb-4">
              Please sign in to access Creator Studio
            </p>
            <Button onClick={() => window.location.href = '/auth'}>
              Sign In
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl lg:text-4xl font-bold font-inter mb-2">
          Creator Studio
        </h1>
        <p className="text-muted-foreground">
          Build, manage, and publish your AI agents
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-4 max-w-2xl">
          <TabsTrigger value="agents">My Agents</TabsTrigger>
          <TabsTrigger value="create">Create New</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          {isAdmin && <TabsTrigger value="verification">Verification</TabsTrigger>}
        </TabsList>

        <TabsContent value="agents">
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold">Your Agents</h2>
              <Button onClick={() => setActiveTab("create")} className="btn-primary">
                <Plus className="w-4 h-4 mr-2" />
                Create Agent
              </Button>
            </div>

            {agents.length === 0 ? (
              <Card className="card-elevated">
                <CardContent className="py-12 text-center">
                  <FileText className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No agents yet</h3>
                  <p className="text-muted-foreground mb-4">
                    Create your first AI agent to get started
                  </p>
                  <Button onClick={() => setActiveTab("create")} className="btn-primary">
                    <Plus className="w-4 h-4 mr-2" />
                    Create Your First Agent
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {agents.map((agent) => (
                  <Card key={agent.id} className="card-elevated hover:shadow-lg transition-shadow">
                    <CardHeader className="pb-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-semibold">
                            {agent.name.charAt(0)}
                          </div>
                          <div>
                            <CardTitle className="text-lg">{agent.name}</CardTitle>
                            <Badge className={`btn-${getStatusColor(agent.status)} mt-1`}>
                              {getStatusIcon(agent.status)}
                              <span className="ml-1 capitalize">{agent.status.replace('_', ' ')}</span>
                            </Badge>
                          </div>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                        {agent.description}
                      </p>
                      
                      <div className="grid grid-cols-3 gap-4 mb-4 text-center">
                        <div>
                          <div className="font-semibold text-lg">{agent.total_runs}</div>
                          <div className="text-xs text-muted-foreground">Runs</div>
                        </div>
                        <div>
                          <div className="font-semibold text-lg">{agent.avg_rating.toFixed(1)}</div>
                          <div className="text-xs text-muted-foreground">Rating</div>
                        </div>
                        <div>
                          <div className="font-semibold text-lg">{agent.upvotes}</div>
                          <div className="text-xs text-muted-foreground">Upvotes</div>
                        </div>
                      </div>

                      <div className="flex space-x-2">
                        <Button size="sm" variant="outline" className="flex-1">
                          <Eye className="w-4 h-4 mr-1" />
                          View
                        </Button>
                        <Button size="sm" variant="outline" className="flex-1">
                          <Pencil className="w-4 h-4 mr-1" />
                          Edit
                        </Button>
                        {agent.status === 'draft' && (
                          <Button 
                            size="sm" 
                            className="btn-primary flex-1"
                            onClick={() => handleSubmitForReview(agent.id)}
                          >
                            Submit
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="create">
          <div className="max-w-2xl mx-auto space-y-6">
            <h2 className="text-2xl font-bold">Create New Agent</h2>
            
            <Card className="card-elevated">
              <CardHeader>
                <CardTitle>Agent Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="agent-name">Agent Name</Label>
                  <Input
                    id="agent-name"
                    placeholder="Enter agent name"
                    value={newAgent.name}
                    onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
                  />
                </div>

                <div>
                  <Label htmlFor="agent-description">Description</Label>
                  <Textarea
                    id="agent-description"
                    placeholder="Describe what your agent does..."
                    value={newAgent.description}
                    onChange={(e) => setNewAgent({ ...newAgent, description: e.target.value })}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="agent-category">Category</Label>
                    <Select value={newAgent.category} onValueChange={(value) => setNewAgent({ ...newAgent, category: value })}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select category" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="productivity">Productivity</SelectItem>
                        <SelectItem value="creative">Creative</SelectItem>
                        <SelectItem value="data-analysis">Data Analysis</SelectItem>
                        <SelectItem value="customer-service">Customer Service</SelectItem>
                        <SelectItem value="automation">Automation</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="agent-model">Model</Label>
                    <Select value={newAgent.model} onValueChange={(value) => setNewAgent({ ...newAgent, model: value })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="gpt-4">GPT-4</SelectItem>
                        <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                        <SelectItem value="claude-3">Claude 3</SelectItem>
                        <SelectItem value="gemini-pro">Gemini Pro</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex space-x-4 pt-4">
                  <Button 
                    onClick={handleCreateAgent}
                    disabled={isCreating || !newAgent.name || !newAgent.description}
                    className="btn-primary flex-1"
                  >
                    {isCreating ? "Creating..." : "Create Agent"}
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={() => setActiveTab("agents")}
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="analytics">
          <div className="space-y-6">
            <h2 className="text-2xl font-bold">Analytics</h2>
            <Card className="card-elevated">
              <CardContent className="py-12 text-center">
                <BarChart3 className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Analytics Dashboard</h3>
                <p className="text-muted-foreground">
                  Detailed analytics for your agents coming soon
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {isAdmin && (
          <TabsContent value="verification">
            <AgentVerification isAdmin={isAdmin} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
};

export default CreatorStudio;

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/components/ui/use-toast";
import { 
  Plus, 
  Github, 
  Upload, 
  Save, 
  Eye, 
  Trash2, 
  Edit, 
  Star, 
  Users, 
  TrendingUp,
  Settings,
  FileText,
  Code,
  Play,
  Database,
  Globe,
  CheckCircle,
  AlertCircle,
  Clock
} from "lucide-react";
import AgentVerification from "@/components/AgentVerification";

const CreatorStudio = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [user, setUser] = useState(null);
  const [myAgents, setMyAgents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const { toast } = useToast();
  
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    category: "",
    tags: [],
    githubUrl: "",
    model: "",
    license: "MIT",
    modalities: [],
    capabilities: [],
    ioSchema: "",
    protocols: [],
    runtimeDependencies: [],
    dockerfileUrl: ""
  });

  useEffect(() => {
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        setUser(session.user);
        await checkAdminRole(session.user.id);
        fetchUserAgents(session.user.id);
      } else {
        setIsLoading(false);
      }
    };

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (session?.user) {
        setUser(session.user);
        fetchUserAgents(session.user.id);
      } else {
        setUser(null);
        setMyAgents([]);
        setIsLoading(false);
      }
    });

    checkUser();
    return () => subscription.unsubscribe();
  }, []);

  const checkAdminRole = async (userId) => {
    try {
      const { data, error } = await supabase
        .from('user_roles')
        .select('role')
        .eq('user_id', userId)
        .eq('role', 'admin')
        .maybeSingle();

      if (error && error.code !== 'PGRST116') throw error;
      setIsAdmin(!!data);
    } catch (error) {
      console.error('Error checking admin role:', error);
    }
  };

  const fetchUserAgents = async (userId) => {
    try {
      const { data, error } = await supabase
        .from('agent_profiles')
        .select('*')
        .eq('creator_id', userId)
        .order('created_at', { ascending: false });

      if (error) throw error;
      setMyAgents(data || []);
    } catch (error) {
      console.error('Error fetching agents:', error);
      toast({
        title: "Error",
        description: "Failed to fetch your agents",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const categories = [
    "Code Generation", "Data Analysis", "Content Creation", 
    "Automation", "Research", "Customer Service", "Design", "Marketing"
  ];

  const models = ["GPT-4", "Claude 3.5", "LangChain", "Custom", "Gemini"];
  
  const modalities = ["Text", "Vision", "Audio", "Multimodal"];
  const capabilities = [
    "Code Generation", "Data Analysis", "Web Search", "File Processing",
    "API Integration", "Database Queries", "Image Generation", "Text Processing"
  ];
  const protocols = ["REST API", "GraphQL", "WebSocket", "gRPC", "Custom"];

  const handleSubmit = async () => {
    if (!user) {
      toast({
        title: "Authentication required",
        description: "Please log in to submit an agent",
        variant: "destructive"
      });
      return;
    }

    try {
      const agentData = {
        creator_id: user.id,
        name: formData.name,
        description: formData.description,
        category: formData.category,
        tags: formData.tags,
        github_url: formData.githubUrl,
        model: formData.model,
        license: formData.license,
        modalities: formData.modalities,
        capabilities: formData.capabilities,
        io_schema: formData.ioSchema ? JSON.parse(formData.ioSchema) : null,
        protocols: formData.protocols,
        runtime_dependencies: formData.runtimeDependencies,
        dockerfile_url: formData.dockerfileUrl,
        status: 'pending_review'
      };

      const { error } = await supabase
        .from('agent_profiles')
        .insert([agentData]);

      if (error) throw error;

      toast({
        title: "Success!",
        description: "Your agent has been submitted for review"
      });

      // Reset form
      setFormData({
        name: "",
        description: "",
        category: "",
        tags: [],
        githubUrl: "",
        model: "",
        license: "MIT",
        modalities: [],
        capabilities: [],
        ioSchema: "",
        protocols: [],
        runtimeDependencies: [],
        dockerfileUrl: ""
      });
      setCurrentStep(1);
      fetchUserAgents(user.id);
    } catch (error) {
      console.error('Error submitting agent:', error);
      toast({
        title: "Error",
        description: "Failed to submit agent",
        variant: "destructive"
      });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "published": return "sage";
      case "approved": return "sage";
      case "draft": return "secondary";
      case "pending_review": return "soft-ochre";
      case "rejected": return "destructive";
      case "suspended": return "destructive";
      default: return "secondary";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "published": return "Published";
      case "approved": return "Approved";
      case "draft": return "Draft";
      case "pending_review": return "Pending Review";
      case "rejected": return "Rejected";
      case "suspended": return "Suspended";
      default: return status;
    }
  };

  if (!user) {
    return (
      <div className="container mx-auto px-4 lg:px-8 py-8">
        <Card className="card-elevated max-w-md mx-auto">
          <CardContent className="p-8 text-center">
            <AlertCircle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Authentication Required</h2>
            <p className="text-muted-foreground mb-4">
              Please log in to access the Creator Studio
            </p>
            <Button onClick={() => window.location.href = '/auth'}>
              Sign In
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 lg:px-8 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Clock className="w-8 h-8 animate-spin mx-auto mb-2 text-muted-foreground" />
            <p className="text-muted-foreground">Loading...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h1 className="text-3xl lg:text-4xl font-bold font-inter mb-2">
              Creator Studio
            </h1>
            <p className="text-muted-foreground">
              Professional agent foundry for the Manhattan Project community
            </p>
          </div>
          <Button className="bg-primary hover:bg-primary-hover">
            <Plus className="w-4 h-4 mr-2" />
            New Agent
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className={`grid w-full ${isAdmin ? 'grid-cols-5' : 'grid-cols-4'}`}>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="agents">My Agents ({myAgents.length})</TabsTrigger>
          <TabsTrigger value="foundry">Agent Foundry</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          {isAdmin && <TabsTrigger value="verification">Verification</TabsTrigger>}
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <Card className="card-elevated">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Total Agents</p>
                    <p className="text-2xl font-bold">{myAgents.length}</p>
                  </div>
                  <div className="w-12 h-12 bg-sage/20 rounded-lg flex items-center justify-center">
                    <Code className="w-6 h-6 text-sage-foreground" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="card-elevated">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Total Runs</p>
                    <p className="text-2xl font-bold">
                      {myAgents.reduce((total, agent) => total + (agent.total_runs || 0), 0).toLocaleString()}
                    </p>
                  </div>
                  <div className="w-12 h-12 bg-dusty-blue/20 rounded-lg flex items-center justify-center">
                    <Play className="w-6 h-6 text-dusty-blue-foreground" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="card-elevated">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Avg Rating</p>
                    <p className="text-2xl font-bold">
                      {myAgents.length > 0 
                        ? (myAgents.reduce((total, agent) => total + (agent.avg_rating || 0), 0) / myAgents.length).toFixed(1)
                        : "0.0"
                      }
                    </p>
                  </div>
                  <div className="w-12 h-12 bg-soft-ochre/20 rounded-lg flex items-center justify-center">
                    <Star className="w-6 h-6 text-soft-ochre-foreground" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="card-elevated">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Published</p>
                    <p className="text-2xl font-bold">
                      {myAgents.filter(agent => agent.status === 'published').length}
                    </p>
                  </div>
                  <div className="w-12 h-12 bg-warm-coral/20 rounded-lg flex items-center justify-center">
                    <Users className="w-6 h-6 text-warm-coral-foreground" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Recent Activity */}
          <Card className="card-elevated">
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center space-x-3 p-3 bg-sage/5 rounded-lg">
                  <div className="w-8 h-8 bg-sage/20 rounded-full flex items-center justify-center">
                    <TrendingUp className="w-4 h-4 text-sage-foreground" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">CodeCraft AI reached 12k runs</p>
                    <p className="text-xs text-muted-foreground">2 hours ago</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3 p-3 bg-dusty-blue/5 rounded-lg">
                  <div className="w-8 h-8 bg-dusty-blue/20 rounded-full flex items-center justify-center">
                    <Star className="w-4 h-4 text-dusty-blue-foreground" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">New 5-star review on CodeCraft AI</p>
                    <p className="text-xs text-muted-foreground">1 day ago</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3 p-3 bg-soft-ochre/5 rounded-lg">
                  <div className="w-8 h-8 bg-soft-ochre/20 rounded-full flex items-center justify-center">
                    <FileText className="w-4 h-4 text-soft-ochre-foreground" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">Task Assistant submitted for review</p>
                    <p className="text-xs text-muted-foreground">3 days ago</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* My Agents Tab */}
        <TabsContent value="agents">
          <div className="space-y-6">
            {myAgents.map((agent) => (
              <Card key={agent.id} className="card-elevated">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-semibold">
                        {agent.name.charAt(0)}
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <h3 className="font-semibold text-lg">{agent.name}</h3>
                          <Badge className={`btn-${getStatusColor(agent.status)}`}>
                            {getStatusText(agent.status)}
                          </Badge>
                        </div>
                        <p className="text-muted-foreground text-sm">{agent.description}</p>
                        <div className="flex items-center space-x-4 mt-2 text-sm text-muted-foreground">
                          <span>Updated {agent.lastUpdated}</span>
                          {agent.status === "published" && (
                            <>
                              <span>•</span>
                              <span>{agent.rating} rating</span>
                              <span>•</span>
                              <span>{agent.runs} runs</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <Button variant="outline" size="sm">
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button variant="outline" size="sm">
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button variant="outline" size="sm">
                        <Settings className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Agent Foundry Tab */}
        <TabsContent value="foundry">
          <Card className="card-elevated">
            <CardHeader>
              <CardTitle>Agent Foundry - Professional Registration</CardTitle>
              <p className="text-sm text-muted-foreground">
                Complete metadata and configuration for your AI agent
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Step Indicator */}
              <div className="flex items-center space-x-4 mb-8">
                {[
                  { num: 1, title: "Registration", icon: FileText },
                  { num: 2, title: "Interface", icon: Database },
                  { num: 3, title: "Capabilities", icon: Settings },
                  { num: 4, title: "Environment", icon: Globe }
                ].map((step, index) => (
                  <div key={step.num} className="flex items-center">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium ${
                      step.num <= currentStep 
                        ? "bg-primary text-primary-foreground" 
                        : "bg-muted text-muted-foreground"
                    }`}>
                      <step.icon className="w-4 h-4" />
                    </div>
                    <div className="ml-2 hidden md:block">
                      <p className="text-xs font-medium">{step.title}</p>
                    </div>
                    {index < 3 && (
                      <div className={`w-12 h-1 mx-2 ${
                        step.num < currentStep ? "bg-primary" : "bg-muted"
                      }`} />
                    )}
                  </div>
                ))}
              </div>

              {/* Step 1: Registration */}
              {currentStep === 1 && (
                <div className="space-y-6">
                  <div className="border-l-4 border-primary pl-4">
                    <h3 className="text-lg font-semibold">Agent Registration</h3>
                    <p className="text-sm text-muted-foreground">Core metadata and identification</p>
                  </div>
                  
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="name">Agent Name *</Label>
                      <Input 
                        id="name"
                        placeholder="e.g., CodeCraft AI"
                        value={formData.name}
                        onChange={(e) => setFormData({...formData, name: e.target.value})}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="category">Category *</Label>
                      <Select value={formData.category} onValueChange={(value) => setFormData({...formData, category: value})}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select primary category" />
                        </SelectTrigger>
                        <SelectContent>
                          {categories.map((category) => (
                            <SelectItem key={category} value={category}>
                              {category}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="description">Description *</Label>
                    <Textarea 
                      id="description"
                      placeholder="Comprehensive description of your agent's capabilities and use cases..."
                      value={formData.description}
                      onChange={(e) => setFormData({...formData, description: e.target.value})}
                      className="min-h-[120px]"
                    />
                  </div>

                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="model">Foundation Model *</Label>
                      <Select value={formData.model} onValueChange={(value) => setFormData({...formData, model: value})}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select foundation model" />
                        </SelectTrigger>
                        <SelectContent>
                          {models.map((model) => (
                            <SelectItem key={model} value={model}>
                              {model}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="license">License</Label>
                      <Select value={formData.license} onValueChange={(value) => setFormData({...formData, license: value})}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="MIT">MIT</SelectItem>
                          <SelectItem value="Apache-2.0">Apache 2.0</SelectItem>
                          <SelectItem value="GPL-3.0">GPL 3.0</SelectItem>
                          <SelectItem value="Custom">Custom</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="githubUrl">GitHub Repository *</Label>
                    <Input 
                      id="githubUrl"
                      placeholder="https://github.com/username/repo"
                      value={formData.githubUrl}
                      onChange={(e) => setFormData({...formData, githubUrl: e.target.value})}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Modalities *</Label>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      {modalities.map((modality) => (
                        <div key={modality} className="flex items-center space-x-2">
                          <Checkbox 
                            id={modality}
                            checked={formData.modalities.includes(modality)}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                setFormData({...formData, modalities: [...formData.modalities, modality]});
                              } else {
                                setFormData({...formData, modalities: formData.modalities.filter(m => m !== modality)});
                              }
                            }}
                          />
                          <Label htmlFor={modality} className="text-sm">{modality}</Label>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Step 2: Interface Declaration */}
              {currentStep === 2 && (
                <div className="space-y-6">
                  <div className="border-l-4 border-dusty-blue pl-4">
                    <h3 className="text-lg font-semibold">Interface Declaration</h3>
                    <p className="text-sm text-muted-foreground">Define API schema and communication protocols</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="ioSchema">I/O Schema (JSON)</Label>
                    <Textarea 
                      id="ioSchema"
                      placeholder='{"input": {"type": "string", "description": "User prompt"}, "output": {"type": "string", "description": "Generated response"}}'
                      value={formData.ioSchema}
                      onChange={(e) => setFormData({...formData, ioSchema: e.target.value})}
                      className="min-h-[150px] font-mono text-sm"
                    />
                    <p className="text-xs text-muted-foreground">Define the input/output structure in JSON schema format</p>
                  </div>

                  <div className="space-y-2">
                    <Label>Supported Protocols *</Label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {protocols.map((protocol) => (
                        <div key={protocol} className="flex items-center space-x-2">
                          <Checkbox 
                            id={protocol}
                            checked={formData.protocols.includes(protocol)}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                setFormData({...formData, protocols: [...formData.protocols, protocol]});
                              } else {
                                setFormData({...formData, protocols: formData.protocols.filter(p => p !== protocol)});
                              }
                            }}
                          />
                          <Label htmlFor={protocol} className="text-sm">{protocol}</Label>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Step 3: Capability Manifest */}
              {currentStep === 3 && (
                <div className="space-y-6">
                  <div className="border-l-4 border-soft-ochre pl-4">
                    <h3 className="text-lg font-semibold">Capability Manifest</h3>
                    <p className="text-sm text-muted-foreground">Declare supported intents and external tools</p>
                  </div>

                  <div className="space-y-2">
                    <Label>Core Capabilities *</Label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {capabilities.map((capability) => (
                        <div key={capability} className="flex items-center space-x-2">
                          <Checkbox 
                            id={capability}
                            checked={formData.capabilities.includes(capability)}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                setFormData({...formData, capabilities: [...formData.capabilities, capability]});
                              } else {
                                setFormData({...formData, capabilities: formData.capabilities.filter(c => c !== capability)});
                              }
                            }}
                          />
                          <Label htmlFor={capability} className="text-sm">{capability}</Label>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="runtimeDeps">Runtime Dependencies</Label>
                    <Textarea 
                      id="runtimeDeps"
                      placeholder="List required packages, APIs, or external services..."
                      value={formData.runtimeDependencies.join('\n')}
                      onChange={(e) => setFormData({...formData, runtimeDependencies: e.target.value.split('\n').filter(dep => dep.trim())})}
                      className="min-h-[100px]"
                    />
                    <p className="text-xs text-muted-foreground">One dependency per line</p>
                  </div>
                </div>
              )}

              {/* Step 4: Execution Environment */}
              {currentStep === 4 && (
                <div className="space-y-6">
                  <div className="border-l-4 border-warm-coral pl-4">
                    <h3 className="text-lg font-semibold">Execution Environment</h3>
                    <p className="text-sm text-muted-foreground">Configure runtime environment for live demos</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="dockerfileUrl">Dockerfile URL</Label>
                    <Input 
                      id="dockerfileUrl"
                      placeholder="https://raw.githubusercontent.com/username/repo/main/Dockerfile"
                      value={formData.dockerfileUrl}
                      onChange={(e) => setFormData({...formData, dockerfileUrl: e.target.value})}
                    />
                    <p className="text-xs text-muted-foreground">
                      URL to your Dockerfile for containerized execution in live demos
                    </p>
                  </div>

                  <Card className="p-4 bg-muted/30">
                    <h4 className="font-medium mb-2">Environment Summary</h4>
                    <div className="space-y-1 text-sm text-muted-foreground">
                      <p>• <strong>Name:</strong> {formData.name || "Not specified"}</p>
                      <p>• <strong>Category:</strong> {formData.category || "Not specified"}</p>
                      <p>• <strong>Model:</strong> {formData.model || "Not specified"}</p>
                      <p>• <strong>Modalities:</strong> {formData.modalities.join(", ") || "None selected"}</p>
                      <p>• <strong>Capabilities:</strong> {formData.capabilities.length} selected</p>
                      <p>• <strong>Protocols:</strong> {formData.protocols.join(", ") || "None selected"}</p>
                    </div>
                  </Card>
                </div>
              )}

              {/* Navigation */}
              <div className="flex justify-between pt-6 border-t">
                <Button 
                  variant="outline" 
                  onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
                  disabled={currentStep === 1}
                >
                  Previous
                </Button>
                <Button 
                  className="bg-primary hover:bg-primary-hover"
                  onClick={currentStep === 4 ? handleSubmit : () => setCurrentStep(Math.min(4, currentStep + 1))}
                  disabled={currentStep === 4 && (!formData.name || !formData.description || !formData.category)}
                >
                  {currentStep === 4 ? "Submit to Review" : "Next"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Verification Tab (Admin Only) */}
        {isAdmin && (
          <TabsContent value="verification">
            <AgentVerification isAdmin={isAdmin} />
          </TabsContent>
        )}

        {/* Analytics Tab */}
        <TabsContent value="analytics">
          <div className="grid md:grid-cols-2 gap-6">
            <Card className="card-elevated">
              <CardHeader>
                <CardTitle>Performance Overview</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Total Runs</span>
                    <span className="font-semibold">12,347</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Avg Session Duration</span>
                    <span className="font-semibold">4m 32s</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Success Rate</span>
                    <span className="font-semibold">94.2%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">User Retention</span>
                    <span className="font-semibold">67.8%</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="card-elevated">
              <CardHeader>
                <CardTitle>Recent Reviews</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-primary-foreground text-sm font-medium">
                      D
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-medium">dev_master</span>
                        <div className="flex">
                          {Array.from({ length: 5 }).map((_, i) => (
                            <Star key={i} className="w-3 h-3 fill-soft-ochre text-soft-ochre" />
                          ))}
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        "Incredible tool! Saved me hours..."
                      </p>
                    </div>
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

export default CreatorStudio;

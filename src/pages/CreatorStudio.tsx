import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
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
  Play
} from "lucide-react";

const CreatorStudio = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    category: "",
    tags: [],
    githubUrl: "",
    model: "",
    license: "MIT"
  });

  const myAgents = [
    {
      id: 1,
      name: "CodeCraft AI",
      description: "Advanced code generation and refactoring assistant",
      status: "published",
      rating: 4.9,
      runs: "12.3k",
      lastUpdated: "2 days ago"
    },
    {
      id: 2,
      name: "DataViz Pro",
      description: "Intelligent data visualization tool",
      status: "draft",
      rating: 0,
      runs: "0",
      lastUpdated: "1 week ago"
    },
    {
      id: 3,
      name: "Task Assistant",
      description: "Productivity and task management agent",
      status: "review",
      rating: 0,
      runs: "0",
      lastUpdated: "3 days ago"
    }
  ];

  const categories = [
    "Code Generation", "Data Analysis", "Content Creation", 
    "Automation", "Research", "Customer Service", "Design", "Marketing"
  ];

  const models = ["GPT-4", "Claude 3.5", "LangChain", "Custom", "Gemini"];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "published": return "sage";
      case "draft": return "secondary";
      case "review": return "soft-ochre";
      default: return "secondary";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "published": return "Published";
      case "draft": return "Draft";
      case "review": return "Under Review";
      default: return status;
    }
  };

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
              Manage and submit your AI agents to the community
            </p>
          </div>
          <Button className="bg-primary hover:bg-primary-hover">
            <Plus className="w-4 h-4 mr-2" />
            New Agent
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="agents">My Agents</TabsTrigger>
          <TabsTrigger value="submit">Submit Agent</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <Card className="card-elevated">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Total Agents</p>
                    <p className="text-2xl font-bold">3</p>
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
                    <p className="text-2xl font-bold">12.3k</p>
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
                    <p className="text-2xl font-bold">4.9</p>
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
                    <p className="text-sm font-medium text-muted-foreground">Followers</p>
                    <p className="text-2xl font-bold">2.3k</p>
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

        {/* Submit Agent Tab */}
        <TabsContent value="submit">
          <Card className="card-elevated">
            <CardHeader>
              <CardTitle>Submit New Agent</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Step Indicator */}
              <div className="flex items-center space-x-4">
                {[1, 2, 3, 4].map((step) => (
                  <div key={step} className="flex items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                      step <= currentStep 
                        ? "bg-primary text-primary-foreground" 
                        : "bg-muted text-muted-foreground"
                    }`}>
                      {step}
                    </div>
                    {step < 4 && (
                      <div className={`w-12 h-1 mx-2 ${
                        step < currentStep ? "bg-primary" : "bg-muted"
                      }`} />
                    )}
                  </div>
                ))}
              </div>

              {/* Step 1: Basic Information */}
              {currentStep === 1 && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Basic Information</h3>
                  
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
                          <SelectValue placeholder="Select category" />
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
                      placeholder="Describe what your agent does and how it helps users..."
                      value={formData.description}
                      onChange={(e) => setFormData({...formData, description: e.target.value})}
                      className="min-h-[100px]"
                    />
                  </div>

                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="model">Foundation Model</Label>
                      <Select value={formData.model} onValueChange={(value) => setFormData({...formData, model: value})}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select model" />
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
                  onClick={() => setCurrentStep(Math.min(4, currentStep + 1))}
                  disabled={currentStep === 4}
                >
                  {currentStep === 4 ? "Submit" : "Next"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

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
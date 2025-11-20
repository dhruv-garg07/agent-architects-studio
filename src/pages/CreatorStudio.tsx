import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getUserAgents, createAgent, updateAgent, deleteAgent } from "@/lib/api/agents";
import type { Tables, TablesInsert, TablesUpdate } from "@/integrations/supabase/types";
import {
  AlertCircle,
  BarChart3,
  CheckCircle2,
  Edit3,
  Eye,
  Loader2,
  Plus,
  Rocket,
  Trash2,
  TrendingUp,
} from "lucide-react";

type Agent = Tables<"agent_profiles">;

type FormState = {
  name: string;
  description: string;
  category: string;
  model: string;
  tags: string;
  modalities: string;
  capabilities: string;
  githubUrl: string;
  license: string;
  status: string;
};

const emptyForm: FormState = {
  name: "",
  description: "",
  category: "",
  model: "",
  tags: "",
  modalities: "",
  capabilities: "",
  githubUrl: "",
  license: "MIT",
  status: "draft",
};

const categories = [
  "Code Generation",
  "Data Analysis",
  "Automation",
  "Content Creation",
  "Customer Service",
  "Research",
  "Design",
  "Marketing",
];

const models = ["GPT-4", "Claude 3.5", "LangChain", "Gemini", "Custom"];
const statuses = ["draft", "pending_review", "published", "suspended"];

const toList = (value: string) =>
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

const CreatorStudio = () => {
  const [userId, setUserId] = useState<string | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [activeTab, setActiveTab] = useState("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormState>(emptyForm);
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    let mounted = true;

    const hydrate = async () => {
      const { data } = await supabase.auth.getSession();
      if (!mounted) return;
      const sessionUser = data.session?.user ?? null;
      setUserId(sessionUser?.id ?? null);
      if (sessionUser?.id) {
        await loadAgents(sessionUser.id);
      }
      setIsLoading(false);
    };

    hydrate();
    const { data: authListener } = supabase.auth.onAuthStateChange((_event, session) => {
      const nextUserId = session?.user?.id ?? null;
      setUserId(nextUserId);
      if (nextUserId) loadAgents(nextUserId);
    });

    return () => {
      mounted = false;
      authListener?.subscription.unsubscribe();
    };
  }, []);

  const loadAgents = async (creatorId: string) => {
    try {
      const records = await getUserAgents(creatorId);
      setAgents(records);
    } catch (error) {
      console.error("Error fetching user agents:", error);
      toast({
        title: "Could not load agents",
        description: "We ran into an issue pulling your agents. Please try again.",
        variant: "destructive",
      });
    }
  };

  const stats = useMemo(() => {
    const published = agents.filter((agent) => agent.status === "published").length;
    const totalRuns = agents.reduce((sum, agent) => sum + (agent.total_runs ?? 0), 0);
    const avgRating =
      agents.length === 0
        ? 0
        : agents.reduce((sum, agent) => sum + (agent.avg_rating ?? 0), 0) / agents.length;

    return {
      published,
      totalRuns,
      avgRating: Number.isFinite(avgRating) ? avgRating : 0,
    };
  }, [agents]);

  const startCreate = () => {
    setEditingId(null);
    setFormData(emptyForm);
    setActiveTab("foundry");
  };

  const startEditing = (agent: Agent) => {
    setEditingId(agent.id);
    setFormData({
      name: agent.name ?? "",
      description: agent.description ?? "",
      category: agent.category ?? "",
      model: agent.model ?? "",
      tags: (agent.tags ?? []).join(", "),
      modalities: (agent.modalities ?? []).join(", "),
      capabilities: (agent.capabilities ?? []).join(", "),
      githubUrl: agent.github_url ?? "",
      license: agent.license ?? "MIT",
      status: agent.status ?? "draft",
    });
    setActiveTab("foundry");
  };

  const resetForm = () => {
    setEditingId(null);
    setFormData(emptyForm);
  };

  const handleSubmit = async () => {
    if (!userId) {
      toast({
        title: "Sign in required",
        description: "You need an account to create or edit an agent.",
        variant: "destructive",
      });
      return;
    }

    if (!formData.name.trim() || !formData.description.trim()) {
      toast({
        title: "Missing details",
        description: "Please add a name and description before saving.",
        variant: "destructive",
      });
      return;
    }

    setIsSaving(true);

    const basePayload: TablesInsert<"agent_profiles"> & TablesUpdate<"agent_profiles"> = {
      creator_id: userId,
      name: formData.name.trim(),
      description: formData.description.trim(),
      category: formData.category || null,
      model: formData.model || null,
      tags: toList(formData.tags),
      modalities: toList(formData.modalities),
      capabilities: toList(formData.capabilities),
      github_url: formData.githubUrl || null,
      license: formData.license || "MIT",
      status: formData.status || "draft",
    };

    try {
      if (editingId) {
        const updated = await updateAgent(editingId, basePayload);
        setAgents((previous) =>
          previous.map((agent) => (agent.id === editingId ? updated : agent)),
        );
        toast({ title: "Agent updated", description: `${formData.name} has been saved.` });
      } else {
        const created = await createAgent(basePayload);
        setAgents((previous) => [created, ...previous]);
        toast({
          title: "Agent submitted",
          description: "We saved your agent. If it requires review, we will notify you.",
        });
      }
      resetForm();
      setActiveTab("agents");
    } catch (error) {
      console.error("Error saving agent:", error);
      toast({
        title: "Save failed",
        description: "We could not save your agent. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteAgent(id);
      setAgents((previous) => previous.filter((agent) => agent.id !== id));
      toast({ title: "Agent removed", description: "The agent has been deleted." });
    } catch (error) {
      console.error("Error deleting agent:", error);
      toast({
        title: "Delete failed",
        description: "We could not delete this agent. Please try again.",
        variant: "destructive",
      });
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 lg:px-8 py-12">
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-10 h-10 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <p className="text-muted-foreground text-sm">Loading Creator Studio...</p>
        </div>
      </div>
    );
  }

  if (!userId) {
    return (
      <div className="container mx-auto px-4 lg:px-8 py-12">
        <Card className="card-elevated">
          <CardContent className="py-10 text-center space-y-3">
            <AlertCircle className="w-10 h-10 text-muted-foreground mx-auto" />
            <h3 className="text-xl font-semibold">Sign in to continue</h3>
            <p className="text-muted-foreground">
              The Creator Studio lets you publish, edit, and track your agents.
            </p>
            <Button onClick={() => navigate("/auth")} className="mt-2">
              Go to sign in
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 lg:px-8 py-10 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-wide text-muted-foreground">Creator Studio</p>
          <h1 className="text-3xl lg:text-4xl font-bold font-inter mt-1">Build with clarity</h1>
          <p className="text-muted-foreground mt-2">
            Minimal workflow to draft, publish, and monitor your agents.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" onClick={() => setActiveTab("agents")}>
            <Eye className="w-4 h-4 mr-2" />
            View agents
          </Button>
          <Button onClick={startCreate}>
            <Plus className="w-4 h-4 mr-2" />
            New agent
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid grid-cols-4 w-full">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="agents">Agents</TabsTrigger>
          <TabsTrigger value="foundry">Foundry</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid md:grid-cols-3 gap-4">
            <Card className="card-elevated">
              <CardContent className="p-6 flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Published agents</p>
                  <p className="text-3xl font-semibold mt-1">{stats.published}</p>
                </div>
                <CheckCircle2 className="w-8 h-8 text-primary" />
              </CardContent>
            </Card>
            <Card className="card-elevated">
              <CardContent className="p-6 flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total runs</p>
                  <p className="text-3xl font-semibold mt-1">{stats.totalRuns.toLocaleString()}</p>
                </div>
                <Rocket className="w-8 h-8 text-primary" />
              </CardContent>
            </Card>
            <Card className="card-elevated">
              <CardContent className="p-6 flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Average rating</p>
                  <p className="text-3xl font-semibold mt-1">
                    {stats.avgRating ? stats.avgRating.toFixed(1) : "—"}
                  </p>
                </div>
                <TrendingUp className="w-8 h-8 text-primary" />
              </CardContent>
            </Card>
          </div>
          <Card className="card-elevated">
            <CardContent className="p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold">Ship faster</h3>
                <p className="text-muted-foreground">
                  Keep drafts lean, then mark them published when they feel solid.
                </p>
              </div>
              <Button variant="outline" onClick={startCreate}>
                <Plus className="w-4 h-4 mr-2" />
                Start a draft
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="agents" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Your agents</h2>
            <Button variant="outline" onClick={startCreate}>
              <Plus className="w-4 h-4 mr-2" />
              New agent
            </Button>
          </div>

          {agents.length === 0 ? (
            <Card className="card-elevated">
              <CardContent className="py-10 text-center space-y-3">
                <h3 className="text-lg font-semibold">Nothing here yet</h3>
                <p className="text-muted-foreground">
                  Draft your first agent to see it appear here.
                </p>
                <Button onClick={startCreate}>Create agent</Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 gap-4">
              {agents.map((agent) => (
                <Card key={agent.id} className="card-elevated">
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <CardTitle className="text-lg">{agent.name}</CardTitle>
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {agent.description}
                        </p>
                      </div>
                      <Badge variant="secondary" className="capitalize">
                        {agent.status ?? "draft"}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Rocket className="w-4 h-4" />
                        <span>{agent.total_runs ?? 0} runs</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <TrendingUp className="w-4 h-4" />
                        <span>{agent.avg_rating?.toFixed(1) ?? "—"} rating</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" onClick={() => navigate(`/agent/${agent.id}`)}>
                        <Eye className="w-4 h-4 mr-1" />
                        View
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => startEditing(agent)}>
                        <Edit3 className="w-4 h-4 mr-1" />
                        Edit
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => handleDelete(agent.id)}>
                        <Trash2 className="w-4 h-4 mr-1" />
                        Delete
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="foundry" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">
              {editingId ? "Edit agent" : "Create agent"}
            </h2>
            {editingId && (
              <Button variant="outline" size="sm" onClick={resetForm}>
                Reset
              </Button>
            )}
          </div>

          <Card className="card-elevated">
            <CardContent className="space-y-4 p-6">
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    placeholder="Give your agent a concise name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="category">Category</Label>
                  <Select
                    value={formData.category || "none"}
                    onValueChange={(value) =>
                      setFormData({ ...formData, category: value === "none" ? "" : value })
                    }
                  >
                    <SelectTrigger id="category">
                      <SelectValue placeholder="Pick a category" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Unspecified</SelectItem>
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
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Describe what your agent does and how it behaves."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="min-h-[120px]"
                />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="model">Model</Label>
                  <Select
                    value={formData.model || "none"}
                    onValueChange={(value) =>
                      setFormData({ ...formData, model: value === "none" ? "" : value })
                    }
                  >
                    <SelectTrigger id="model">
                      <SelectValue placeholder="Select a model" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Not specified</SelectItem>
                      {models.map((model) => (
                        <SelectItem key={model} value={model}>
                          {model}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="status">Status</Label>
                  <Select
                    value={formData.status}
                    onValueChange={(value) => setFormData({ ...formData, status: value })}
                  >
                    <SelectTrigger id="status">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {statuses.map((status) => (
                        <SelectItem key={status} value={status}>
                          {status.replace("_", " ")}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="tags">Tags</Label>
                  <Input
                    id="tags"
                    placeholder="comma separated — eg: TypeScript, tooling"
                    value={formData.tags}
                    onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="modalities">Modalities</Label>
                  <Input
                    id="modalities"
                    placeholder="comma separated — eg: text, vision"
                    value={formData.modalities}
                    onChange={(e) => setFormData({ ...formData, modalities: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="capabilities">Capabilities</Label>
                <Input
                  id="capabilities"
                  placeholder="comma separated — eg: code generation, retrieval"
                  value={formData.capabilities}
                  onChange={(e) => setFormData({ ...formData, capabilities: e.target.value })}
                />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="github">GitHub URL</Label>
                  <Input
                    id="github"
                    placeholder="https://github.com/your-agent"
                    value={formData.githubUrl}
                    onChange={(e) => setFormData({ ...formData, githubUrl: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="license">License</Label>
                  <Input
                    id="license"
                    placeholder="MIT, Apache-2.0..."
                    value={formData.license}
                    onChange={(e) => setFormData({ ...formData, license: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <Button onClick={handleSubmit} disabled={isSaving}>
                  {isSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                  {isSaving ? "Saving..." : editingId ? "Save changes" : "Create agent"}
                </Button>
                <Button variant="outline" onClick={resetForm} disabled={isSaving}>
                  Clear
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics">
          <Card className="card-elevated">
            <CardContent className="py-12 text-center space-y-3">
              <BarChart3 className="w-12 h-12 text-muted-foreground mx-auto" />
              <h3 className="text-lg font-semibold">Analytics coming soon</h3>
              <p className="text-muted-foreground">
                We are building a clean dashboard for runs, conversions, and reliability.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default CreatorStudio;

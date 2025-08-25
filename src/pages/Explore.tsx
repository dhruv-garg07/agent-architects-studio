import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, Filter, Star, Play, Github, TrendingUp, Clock, Users } from "lucide-react";

const Explore = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedModel, setSelectedModel] = useState("all");
  const [sortBy, setSortBy] = useState("trending");

  const categories = [
    "All Categories", "Code Generation", "Data Analysis", "Content Creation", 
    "Automation", "Research", "Customer Service", "Design", "Marketing"
  ];

  const models = ["All Models", "GPT-4", "Claude 3.5", "LangChain", "Custom", "Gemini"];

  const agents = [
    {
      id: 1,
      name: "CodeCraft AI",
      description: "Advanced code generation and refactoring assistant that helps developers write cleaner, more efficient code",
      creator: "alexdevs",
      avatar: "A",
      rating: 4.9,
      runs: "12.3k",
      updated: "2 days ago",
      tags: ["Code Generation", "GPT-4", "TypeScript"],
      category: "Code Generation",
      featured: true
    },
    {
      id: 2,
      name: "DataViz Pro",
      description: "Intelligent data visualization and analysis tool for creating beautiful charts and insights",
      creator: "datascience_team",
      avatar: "D",
      rating: 4.8,
      runs: "8.7k",
      updated: "1 week ago",
      tags: ["Data Analysis", "Claude 3.5", "Python"],
      category: "Data Analysis",
      featured: true
    },
    {
      id: 3,
      name: "TaskFlow Manager",
      description: "Autonomous workflow orchestration agent for complex business process automation",
      creator: "productivity_hub",
      avatar: "T",
      rating: 4.7,
      runs: "15.2k",
      updated: "3 days ago",
      tags: ["Automation", "LangChain", "API"],
      category: "Automation",
      featured: false
    },
    {
      id: 4,
      name: "Content Genius",
      description: "AI-powered content creation assistant for blogs, social media, and marketing copy",
      creator: "content_creators",
      avatar: "C",
      rating: 4.6,
      runs: "9.1k",
      updated: "5 days ago",
      tags: ["Content Creation", "GPT-4", "Marketing"],
      category: "Content Creation",
      featured: false
    },
    {
      id: 5,
      name: "Research Assistant",
      description: "Academic research and paper analysis tool with citation management",
      creator: "academic_tools",
      avatar: "R",
      rating: 4.8,
      runs: "6.4k",
      updated: "1 day ago",
      tags: ["Research", "Claude 3.5", "Academic"],
      category: "Research",
      featured: true
    },
    {
      id: 6,
      name: "Customer Support AI",
      description: "Intelligent customer service agent with multi-language support and sentiment analysis",
      creator: "support_solutions",
      avatar: "S",
      rating: 4.5,
      runs: "18.7k",
      updated: "4 days ago",
      tags: ["Customer Service", "Custom", "NLP"],
      category: "Customer Service",
      featured: false
    }
  ];

  const getTagColor = (tag: string) => {
    if (tag.includes("GPT")) return "sage";
    if (tag.includes("Claude")) return "dusty-blue";
    if (tag.includes("LangChain")) return "soft-ochre";
    return "secondary";
  };

  return (
    <div className="container mx-auto px-4 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-3xl lg:text-4xl font-bold font-inter mb-2">
              Explore AI Agents
            </h1>
            <p className="text-muted-foreground">
              Discover and test {agents.length} powerful AI agents built by the community
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <Button variant="outline" className="btn-sage">
              <TrendingUp className="w-4 h-4 mr-2" />
              Trending
            </Button>
            <Button variant="outline">
              <Clock className="w-4 h-4 mr-2" />
              Recent
            </Button>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <Input
              placeholder="Search agents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          
          <div className="flex gap-4">
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                {categories.map((category) => (
                  <SelectItem key={category} value={category.toLowerCase().replace(" ", "-")}>
                    {category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selectedModel} onValueChange={setSelectedModel}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder="Model" />
              </SelectTrigger>
              <SelectContent>
                {models.map((model) => (
                  <SelectItem key={model} value={model.toLowerCase().replace(" ", "-")}>
                    {model}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button variant="outline" size="icon">
              <Filter className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Featured Section */}
      <div className="mb-12">
        <h2 className="text-xl font-semibold mb-6 flex items-center">
          <Star className="w-5 h-5 mr-2 text-soft-ochre fill-soft-ochre" />
          Featured Agents
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.filter(agent => agent.featured).map((agent) => (
            <Card key={agent.id} className="card-elevated group cursor-pointer">
              <CardContent className="p-6">
                <div className="space-y-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-semibold">
                        {agent.avatar}
                      </div>
                      <div>
                        <h3 className="font-semibold group-hover:text-primary transition-colors">
                          {agent.name}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          by {agent.creator}
                        </p>
                      </div>
                    </div>
                    <Button size="sm" variant="ghost" className="opacity-0 group-hover:opacity-100 transition-opacity">
                      <Play className="w-4 h-4" />
                    </Button>
                  </div>

                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {agent.description}
                  </p>

                  <div className="flex flex-wrap gap-2">
                    {agent.tags.slice(0, 3).map((tag, index) => (
                      <Badge 
                        key={index} 
                        variant="secondary" 
                        className={`btn-${getTagColor(tag)} text-xs`}
                      >
                        {tag}
                      </Badge>
                    ))}
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-card-border">
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-1">
                        <Star className="w-4 h-4 fill-soft-ochre text-soft-ochre" />
                        <span className="text-sm font-medium">{agent.rating}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Users className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">{agent.runs}</span>
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {agent.updated}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* All Agents Grid */}
      <div>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">All Agents</h2>
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="trending">Trending</SelectItem>
              <SelectItem value="recent">Recent</SelectItem>
              <SelectItem value="rating">Highest Rated</SelectItem>
              <SelectItem value="runs">Most Used</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <Card key={agent.id} className="card-elevated group cursor-pointer">
              <CardContent className="p-6">
                <div className="space-y-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-semibold">
                        {agent.avatar}
                      </div>
                      <div>
                        <h3 className="font-semibold group-hover:text-primary transition-colors">
                          {agent.name}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          by {agent.creator}
                        </p>
                      </div>
                    </div>
                    <div className="flex space-x-1">
                      <Button size="sm" variant="ghost" className="opacity-0 group-hover:opacity-100 transition-opacity">
                        <Play className="w-4 h-4" />
                      </Button>
                      <Button size="sm" variant="ghost" className="opacity-0 group-hover:opacity-100 transition-opacity">
                        <Github className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>

                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {agent.description}
                  </p>

                  <div className="flex flex-wrap gap-2">
                    {agent.tags.slice(0, 3).map((tag, index) => (
                      <Badge 
                        key={index} 
                        variant="secondary" 
                        className={`btn-${getTagColor(tag)} text-xs`}
                      >
                        {tag}
                      </Badge>
                    ))}
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-card-border">
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-1">
                        <Star className="w-4 h-4 fill-soft-ochre text-soft-ochre" />
                        <span className="text-sm font-medium">{agent.rating}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Users className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">{agent.runs}</span>
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {agent.updated}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Load More */}
        <div className="text-center mt-12">
          <Button variant="outline" size="lg">
            Load More Agents
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Explore;
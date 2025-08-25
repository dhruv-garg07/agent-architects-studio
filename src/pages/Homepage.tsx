import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowRight, Star, Users, Zap, Github, Play, TrendingUp, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import heroImage from "@/assets/hero-image.jpg";

const Homepage = () => {
  const featuredAgents = [
    {
      name: "CodeCraft AI",
      description: "Advanced code generation and refactoring assistant",
      creator: "alexdevs",
      rating: 4.9,
      runs: "12.3k",
      tags: ["Code Generation", "GPT-4"],
      color: "sage"
    },
    {
      name: "DataViz Pro",
      description: "Intelligent data visualization and analysis",
      creator: "datascience_team",
      rating: 4.8,
      runs: "8.7k",
      tags: ["Data Analysis", "Claude 3.5"],
      color: "dusty-blue"
    },
    {
      name: "TaskFlow Manager",
      description: "Autonomous workflow orchestration agent",
      creator: "productivity_hub",
      rating: 4.7,
      runs: "15.2k",
      tags: ["Automation", "LangChain"],
      color: "soft-ochre"
    }
  ];

  return (
    <div>
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-background via-background to-sage/10">
        <div className="container mx-auto px-4 lg:px-8 py-16 lg:py-24">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="space-y-4">
                <Badge variant="secondary" className="bg-sage/20 text-sage-foreground border-sage/30">
                  🚀 Platform V1 Now Live
                </Badge>
                <h1 className="text-4xl lg:text-6xl font-bold font-inter leading-tight">
                  Discover & Deploy
                  <span className="block text-sage-foreground">AI Agents</span>
                </h1>
                <p className="text-xl text-muted-foreground max-w-lg leading-relaxed">
                  The definitive hub for autonomous AI agents. Explore, test, and deploy 
                  powerful AI solutions crafted by the community.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-4">
                <Button asChild size="lg" className="bg-primary hover:bg-primary-hover">
                  <Link to="/explore">
                    Explore Agents
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button asChild variant="outline" size="lg" className="btn-sage">
                  <Link to="/submit">
                    Submit Your Agent
                    <Plus className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
              </div>

              <div className="flex items-center space-x-8 text-sm text-muted-foreground">
                <div className="flex items-center space-x-2">
                  <Users className="w-4 h-4" />
                  <span>2,847 creators</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Zap className="w-4 h-4" />
                  <span>156 agents</span>
                </div>
                <div className="flex items-center space-x-2">
                  <TrendingUp className="w-4 h-4" />
                  <span>45k+ runs</span>
                </div>
              </div>
            </div>

            <div className="relative">
              <div className="relative rounded-2xl overflow-hidden card-elevated bg-card">
                <img 
                  src={heroImage} 
                  alt="AI Agents Platform" 
                  className="w-full h-auto"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Agents */}
      <section className="py-16 lg:py-24">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl lg:text-4xl font-bold font-inter mb-4">
              Featured Agents
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Discover top-rated AI agents built by our community of expert developers
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {featuredAgents.map((agent, index) => (
              <Card key={index} className="card-elevated group cursor-pointer">
                <CardContent className="p-6">
                  <div className="space-y-4">
                    <div className="flex items-start justify-between">
                      <div className="space-y-2">
                        <h3 className="font-semibold text-lg group-hover:text-primary transition-colors">
                          {agent.name}
                        </h3>
                        <p className="text-muted-foreground text-sm">
                          by {agent.creator}
                        </p>
                      </div>
                      <Button size="sm" variant="ghost" className="opacity-0 group-hover:opacity-100 transition-opacity">
                        <Play className="w-4 h-4" />
                      </Button>
                    </div>

                    <p className="text-sm text-muted-foreground">
                      {agent.description}
                    </p>

                    <div className="flex flex-wrap gap-2">
                      {agent.tags.map((tag, tagIndex) => (
                        <Badge 
                          key={tagIndex} 
                          variant="secondary" 
                          className={`btn-${agent.color} text-xs`}
                        >
                          {tag}
                        </Badge>
                      ))}
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-card-border">
                      <div className="flex items-center space-x-1">
                        <Star className="w-4 h-4 fill-soft-ochre text-soft-ochre" />
                        <span className="text-sm font-medium">{agent.rating}</span>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {agent.runs} runs
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="text-center mt-12">
            <Button asChild variant="outline" size="lg">
              <Link to="/explore">
                View All Agents
                <ArrowRight className="w-5 h-5 ml-2" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 lg:py-24 bg-sage/5">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl lg:text-4xl font-bold font-inter mb-4">
              Why The Manhattan Project?
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Professional-grade platform for AI agent discovery and deployment
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-sage/20 rounded-2xl flex items-center justify-center mx-auto">
                <Play className="w-8 h-8 text-sage-foreground" />
              </div>
              <h3 className="text-xl font-semibold">Interactive Demos</h3>
              <p className="text-muted-foreground">
                Test agents directly in your browser with our sandboxed environment
              </p>
            </div>

            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-dusty-blue/20 rounded-2xl flex items-center justify-center mx-auto">
                <Github className="w-8 h-8 text-dusty-blue-foreground" />
              </div>
              <h3 className="text-xl font-semibold">Open Source</h3>
              <p className="text-muted-foreground">
                Every agent links to its source code for transparency and collaboration
              </p>
            </div>

            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-soft-ochre/20 rounded-2xl flex items-center justify-center mx-auto">
                <Users className="w-8 h-8 text-soft-ochre-foreground" />
              </div>
              <h3 className="text-xl font-semibold">Community Driven</h3>
              <p className="text-muted-foreground">
                Ratings, reviews, and reputation system ensure quality and trust
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 lg:py-24">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="bg-gradient-to-r from-sage/10 via-dusty-blue/10 to-soft-ochre/10 rounded-3xl p-8 lg:p-16 text-center">
            <h2 className="text-3xl lg:text-4xl font-bold font-inter mb-4">
              Ready to Share Your AI Agent?
            </h2>
            <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
              Join our community of creators and showcase your AI agents to thousands of developers and businesses
            </p>
            <Button asChild size="lg" className="bg-primary hover:bg-primary-hover">
              <Link to="/submit">
                Get Started Today
                <ArrowRight className="w-5 h-5 ml-2" />
              </Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Homepage;
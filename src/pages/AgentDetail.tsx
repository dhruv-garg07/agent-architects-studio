import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Textarea } from "@/components/ui/textarea";
import { 
  Star, 
  Play, 
  Github, 
  Download, 
  Share2, 
  Heart, 
  MessageSquare, 
  TrendingUp,
  Calendar,
  Tag,
  ExternalLink,
  Copy,
  Send
} from "lucide-react";

const AgentDetail = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [outputValue, setOutputValue] = useState("");

  const agent = {
    name: "CodeCraft AI",
    description: "Advanced code generation and refactoring assistant that helps developers write cleaner, more efficient code with intelligent suggestions and automated improvements.",
    creator: {
      name: "alexdevs",
      avatar: "A",
      reputation: 4.9,
      followers: "2.3k",
      verified: true
    },
    stats: {
      rating: 4.9,
      totalRuns: "12.3k",
      thisMonth: "2.1k",
      reviews: 147,
      stars: 89,
      forks: 23
    },
    tags: ["Code Generation", "GPT-4", "TypeScript", "React", "Node.js"],
    category: "Development Tools",
    version: "2.1.0",
    lastUpdated: "2 days ago",
    license: "MIT",
    documentation: `# CodeCraft AI

An intelligent code generation and refactoring assistant powered by GPT-4.

## Features

- **Smart Code Generation**: Generate functions, classes, and components based on natural language descriptions
- **Intelligent Refactoring**: Automatically improve code structure and performance
- **Multi-language Support**: Works with JavaScript, TypeScript, Python, and more
- **Context-aware Suggestions**: Understands your codebase context for better recommendations

## Usage

\`\`\`typescript
import { CodeCraft } from 'codecraft-ai';

const agent = new CodeCraft({
  apiKey: 'your-api-key',
  model: 'gpt-4'
});

const result = await agent.generateFunction({
  description: 'Create a function that validates email addresses',
  language: 'typescript'
});
\`\`\`

## Configuration

The agent can be configured with various parameters:

- \`temperature\`: Controls creativity (0.0 - 1.0)
- \`maxTokens\`: Maximum response length
- \`language\`: Target programming language
- \`framework\`: Specific framework context`,
    reviews: [
      {
        id: 1,
        user: "dev_master",
        avatar: "D",
        rating: 5,
        comment: "Incredible tool! Saved me hours of development time. The code quality is consistently high.",
        date: "3 days ago",
        helpful: 12
      },
      {
        id: 2,
        user: "code_reviewer",
        avatar: "C",
        rating: 5,
        comment: "Best AI coding assistant I've used. The refactoring suggestions are spot-on.",
        date: "1 week ago",
        helpful: 8
      },
      {
        id: 3,
        user: "full_stack_dev",
        avatar: "F",
        rating: 4,
        comment: "Great for rapid prototyping. Sometimes needs refinement but overall excellent.",
        date: "2 weeks ago",
        helpful: 5
      }
    ]
  };

  const handleRun = async () => {
    setIsRunning(true);
    setOutputValue("Processing your request...");
    
    // Simulate API call
    setTimeout(() => {
      setOutputValue(`// Generated TypeScript function based on your input
function validateEmail(email: string): boolean {
  const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
  
  if (!email || typeof email !== 'string') {
    return false;
  }
  
  // Check basic format
  if (!emailRegex.test(email)) {
    return false;
  }
  
  // Additional validations
  const parts = email.split('@');
  const localPart = parts[0];
  const domain = parts[1];
  
  // Local part should not exceed 64 characters
  if (localPart.length > 64) {
    return false;
  }
  
  // Domain should not exceed 253 characters
  if (domain.length > 253) {
    return false;
  }
  
  return true;
}

// Usage example:
console.log(validateEmail("user@example.com")); // true
console.log(validateEmail("invalid.email"));    // false`);
      setIsRunning(false);
    }, 2000);
  };

  return (
    <div className="container mx-auto px-4 lg:px-8 py-8">
      <div className="grid lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-8">
          {/* Header */}
          <div className="space-y-6">
            <div className="flex items-start justify-between">
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <h1 className="text-3xl lg:text-4xl font-bold font-inter">
                    {agent.name}
                  </h1>
                  <Badge className="btn-sage">v{agent.version}</Badge>
                </div>
                
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <Avatar className="w-6 h-6">
                      <AvatarFallback className="text-xs bg-primary text-primary-foreground">
                        {agent.creator.avatar}
                      </AvatarFallback>
                    </Avatar>
                    <span className="text-sm text-muted-foreground">
                      by <span className="font-medium text-foreground">{agent.creator.name}</span>
                    </span>
                    {agent.creator.verified && (
                      <Badge variant="secondary" className="text-xs">Verified</Badge>
                    )}
                  </div>
                  
                  <div className="flex items-center space-x-1">
                    <Star className="w-4 h-4 fill-soft-ochre text-soft-ochre" />
                    <span className="text-sm font-medium">{agent.stats.rating}</span>
                    <span className="text-sm text-muted-foreground">
                      ({agent.stats.reviews} reviews)
                    </span>
                  </div>
                </div>

                <p className="text-lg text-muted-foreground max-w-2xl">
                  {agent.description}
                </p>

                <div className="flex flex-wrap gap-2">
                  {agent.tags.map((tag, index) => (
                    <Badge key={index} variant="secondary" className="btn-sage">
                      <Tag className="w-3 h-3 mr-1" />
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="flex space-x-2">
                <Button variant="outline" size="sm">
                  <Heart className="w-4 h-4" />
                </Button>
                <Button variant="outline" size="sm">
                  <Share2 className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-4">
              <Button className="bg-primary hover:bg-primary-hover">
                <Play className="w-4 h-4 mr-2" />
                Try Now
              </Button>
              <Button variant="outline" className="btn-dusty-blue">
                <Github className="w-4 h-4 mr-2" />
                View Source
              </Button>
              <Button variant="outline">
                <Download className="w-4 h-4 mr-2" />
                Download
              </Button>
              <Button variant="outline">
                <Copy className="w-4 h-4 mr-2" />
                Copy Install
              </Button>
            </div>
          </div>

          {/* Interactive Demo */}
          <Card className="card-elevated">
            <CardHeader>
              <CardTitle className="flex items-center">
                <Play className="w-5 h-5 mr-2" />
                Interactive Demo
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Describe what you want to generate:
                </label>
                <Textarea
                  placeholder="e.g., Create a function that validates email addresses with proper error handling"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  className="min-h-[80px]"
                />
              </div>
              
              <Button 
                onClick={handleRun} 
                disabled={isRunning || !inputValue.trim()}
                className="w-full bg-primary hover:bg-primary-hover"
              >
                {isRunning ? "Processing..." : "Generate Code"}
                <Send className="w-4 h-4 ml-2" />
              </Button>

              {outputValue && (
                <div>
                  <label className="text-sm font-medium mb-2 block">Output:</label>
                  <pre className="bg-muted p-4 rounded-lg text-sm overflow-x-auto border">
                    <code>{outputValue}</code>
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Tabs Content */}
          <Tabs defaultValue="documentation" className="space-y-6">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="documentation">Documentation</TabsTrigger>
              <TabsTrigger value="reviews">Reviews ({agent.stats.reviews})</TabsTrigger>
              <TabsTrigger value="changelog">Changelog</TabsTrigger>
            </TabsList>

            <TabsContent value="documentation">
              <Card>
                <CardContent className="p-6">
                  <div className="prose prose-sm max-w-none">
                    <pre className="whitespace-pre-wrap text-sm leading-relaxed">
                      {agent.documentation}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="reviews">
              <div className="space-y-6">
                {agent.reviews.map((review) => (
                  <Card key={review.id}>
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center space-x-3">
                          <Avatar>
                            <AvatarFallback className="bg-primary text-primary-foreground">
                              {review.avatar}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <div className="font-medium">{review.user}</div>
                            <div className="text-sm text-muted-foreground">{review.date}</div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-1">
                          {Array.from({ length: 5 }).map((_, i) => (
                            <Star
                              key={i}
                              className={`w-4 h-4 ${
                                i < review.rating
                                  ? "fill-soft-ochre text-soft-ochre"
                                  : "text-muted-foreground"
                              }`}
                            />
                          ))}
                        </div>
                      </div>
                      <p className="text-muted-foreground mb-4">{review.comment}</p>
                      <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                        <button className="flex items-center space-x-1 hover:text-foreground">
                          <MessageSquare className="w-4 h-4" />
                          <span>Reply</span>
                        </button>
                        <span>{review.helpful} found this helpful</span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="changelog">
              <Card>
                <CardContent className="p-6">
                  <div className="space-y-6">
                    <div className="border-l-2 border-sage pl-4">
                      <div className="flex items-center space-x-2 mb-2">
                        <Badge className="btn-sage">v2.1.0</Badge>
                        <span className="text-sm text-muted-foreground">2 days ago</span>
                      </div>
                      <h4 className="font-medium mb-2">Enhanced Code Quality</h4>
                      <ul className="text-sm text-muted-foreground space-y-1">
                        <li>• Improved TypeScript type inference</li>
                        <li>• Better error handling suggestions</li>
                        <li>• Added support for React 18 patterns</li>
                      </ul>
                    </div>
                    
                    <div className="border-l-2 border-muted pl-4">
                      <div className="flex items-center space-x-2 mb-2">
                        <Badge variant="secondary">v2.0.3</Badge>
                        <span className="text-sm text-muted-foreground">1 week ago</span>
                      </div>
                      <h4 className="font-medium mb-2">Bug Fixes</h4>
                      <ul className="text-sm text-muted-foreground space-y-1">
                        <li>• Fixed async/await pattern generation</li>
                        <li>• Improved variable naming consistency</li>
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Stats Card */}
          <Card className="card-elevated">
            <CardHeader>
              <CardTitle className="text-lg">Agent Statistics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-sage-foreground">
                    {agent.stats.rating}
                  </div>
                  <div className="text-sm text-muted-foreground">Rating</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-dusty-blue-foreground">
                    {agent.stats.totalRuns}
                  </div>
                  <div className="text-sm text-muted-foreground">Total Runs</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-soft-ochre-foreground">
                    {agent.stats.thisMonth}
                  </div>
                  <div className="text-sm text-muted-foreground">This Month</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-warm-coral-foreground">
                    {agent.stats.reviews}
                  </div>
                  <div className="text-sm text-muted-foreground">Reviews</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Creator Info */}
          <Card className="card-elevated">
            <CardHeader>
              <CardTitle className="text-lg">Creator</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center space-x-3">
                <Avatar className="w-12 h-12">
                  <AvatarFallback className="bg-primary text-primary-foreground text-lg">
                    {agent.creator.avatar}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <div className="font-medium">{agent.creator.name}</div>
                  <div className="text-sm text-muted-foreground">
                    {agent.creator.followers} followers
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                <Star className="w-4 h-4 fill-soft-ochre text-soft-ochre" />
                <span className="text-sm">{agent.creator.reputation} reputation</span>
              </div>

              <Button variant="outline" className="w-full btn-sage">
                View Profile
              </Button>
            </CardContent>
          </Card>

          {/* Meta Information */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Category</span>
                <span className="text-sm font-medium">{agent.category}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">License</span>
                <span className="text-sm font-medium">{agent.license}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Updated</span>
                <span className="text-sm font-medium">{agent.lastUpdated}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Stars</span>
                <span className="text-sm font-medium">{agent.stats.stars}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AgentDetail;
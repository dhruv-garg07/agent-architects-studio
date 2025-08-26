
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/components/ui/use-toast";
import { CheckCircle, XCircle, AlertTriangle, Clock, User } from "lucide-react";

interface Creator {
  display_name: string;
  avatar_url: string;
}

interface Agent {
  id: string;
  name: string;
  description: string;
  category: string;
  model: string;
  status: string;
  created_at: string;
  creator_id: string;
}

interface AgentWithCreator extends Agent {
  creator: Creator;
}

interface AgentVerificationProps {
  isAdmin: boolean;
}

const AgentVerification = ({ isAdmin }: AgentVerificationProps) => {
  const [pendingAgents, setPendingAgents] = useState<AgentWithCreator[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<AgentWithCreator | null>(null);
  const [verificationNotes, setVerificationNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    if (isAdmin) {
      fetchPendingAgents();
    }
  }, [isAdmin]);

  const fetchPendingAgents = async () => {
    try {
      const { data: agentData, error: agentError } = await supabase
        .from('agent_profiles')
        .select('*')
        .eq('status', 'pending_review')
        .order('created_at', { ascending: true });

      if (agentError) throw agentError;

      if (agentData && agentData.length > 0) {
        // Fetch creator profiles separately - fix the field selection
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

        setPendingAgents(agentsWithCreators);
      } else {
        setPendingAgents([]);
      }
    } catch (error) {
      console.error('Error fetching pending agents:', error);
      toast({
        title: "Error",
        description: "Failed to fetch pending agents",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerification = async (agentId: string, status: 'approved' | 'rejected') => {
    if (!selectedAgent || selectedAgent.id !== agentId) return;
    
    setIsSubmitting(true);
    try {
      // Since we don't have the agent_verifications table or RPC function yet,
      // let's just update the agent status directly
      const newStatus = status === 'approved' ? 'published' : 'rejected';
      
      const { error: updateError } = await supabase
        .from('agent_profiles')
        .update({ status: newStatus })
        .eq('id', agentId);
      
      if (updateError) throw updateError;

      toast({
        title: "Success",
        description: `Agent ${status === 'approved' ? 'approved' : 'rejected'} successfully`,
      });

      // Reset form and refresh list
      setSelectedAgent(null);
      setVerificationNotes("");
      fetchPendingAgents();
    } catch (error) {
      console.error('Error processing verification:', error);
      toast({
        title: "Error",
        description: "Failed to process verification",
        variant: "destructive"
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getCreatorInitials = (name: string) => {
    return name?.split(' ').map(n => n[0]).join('').toUpperCase() || '?';
  };

  if (!isAdmin) {
    return (
      <Card className="card-elevated">
        <CardContent className="py-8 text-center">
          <AlertTriangle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Admin Access Required</h3>
          <p className="text-muted-foreground">
            You need admin privileges to access agent verification.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card className="card-elevated">
        <CardContent className="py-8 text-center">
          <div className="w-8 h-8 animate-spin mx-auto mb-2 border-2 border-primary border-t-transparent rounded-full" />
          <p className="text-muted-foreground">Loading pending agents...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Agent Verification</h2>
        <Badge variant="secondary">
          {pendingAgents.length} pending review
        </Badge>
      </div>

      {pendingAgents.length === 0 ? (
        <Card className="card-elevated">
          <CardContent className="py-8 text-center">
            <CheckCircle className="w-12 h-12 text-sage mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">All caught up!</h3>
            <p className="text-muted-foreground">
              No agents pending verification at this time.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Pending Agents List */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Pending Agents</h3>
            {pendingAgents.map((agent) => (
              <Card 
                key={agent.id} 
                className={`cursor-pointer transition-all ${
                  selectedAgent?.id === agent.id 
                    ? 'ring-2 ring-primary card-elevated' 
                    : 'card-elevated hover:shadow-md'
                }`}
                onClick={() => setSelectedAgent(agent)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start space-x-3">
                    <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-semibold shrink-0">
                      {agent.name.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <h4 className="font-semibold truncate">{agent.name}</h4>
                        <Badge variant="outline" className="shrink-0">
                          <Clock className="w-3 h-3 mr-1" />
                          Pending
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
                        {agent.description}
                      </p>
                      <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                        <div className="flex items-center space-x-1">
                          <div className="w-4 h-4 bg-primary rounded-full flex items-center justify-center text-primary-foreground text-xs">
                            {agent.creator?.avatar_url ? (
                              <img 
                                src={agent.creator.avatar_url} 
                                alt={agent.creator.display_name} 
                                className="w-4 h-4 rounded-full object-cover"
                              />
                            ) : (
                              getCreatorInitials(agent.creator?.display_name || "")
                            )}
                          </div>
                          <span>{agent.creator?.display_name}</span>
                        </div>
                        <span>•</span>
                        <span>{agent.category}</span>
                        <span>•</span>
                        <span>{new Date(agent.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Verification Panel */}
          <div className="lg:sticky lg:top-4">
            {selectedAgent ? (
              <Card className="card-elevated">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-semibold">
                      {selectedAgent.name.charAt(0)}
                    </div>
                    <span>Review: {selectedAgent.name}</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className="text-sm font-medium">Description</Label>
                    <p className="text-sm text-muted-foreground mt-1">
                      {selectedAgent.description}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-sm font-medium">Category</Label>
                      <p className="text-sm text-muted-foreground mt-1">
                        {selectedAgent.category}
                      </p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium">Model</Label>
                      <p className="text-sm text-muted-foreground mt-1">
                        {selectedAgent.model}
                      </p>
                    </div>
                  </div>

                  <div>
                    <Label className="text-sm font-medium">Creator</Label>
                    <div className="flex items-center space-x-2 mt-1">
                      <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center text-primary-foreground text-xs">
                        {selectedAgent.creator?.avatar_url ? (
                          <img 
                            src={selectedAgent.creator.avatar_url} 
                            alt={selectedAgent.creator.display_name} 
                            className="w-6 h-6 rounded-full object-cover"
                          />
                        ) : (
                          getCreatorInitials(selectedAgent.creator?.display_name || "")
                        )}
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {selectedAgent.creator?.display_name}
                      </span>
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="verification-notes">Review Notes</Label>
                    <Textarea
                      id="verification-notes"
                      placeholder="Add any notes about your review decision..."
                      value={verificationNotes}
                      onChange={(e) => setVerificationNotes(e.target.value)}
                      className="mt-1"
                    />
                  </div>

                  <div className="flex space-x-3 pt-4">
                    <Button
                      onClick={() => handleVerification(selectedAgent.id, 'approved')}
                      disabled={isSubmitting}
                      className="btn-sage flex-1"
                    >
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Approve
                    </Button>
                    <Button
                      onClick={() => handleVerification(selectedAgent.id, 'rejected')}
                      disabled={isSubmitting}
                      variant="destructive"
                      className="flex-1"
                    >
                      <XCircle className="w-4 h-4 mr-2" />
                      Reject
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="card-elevated">
                <CardContent className="py-8 text-center">
                  <User className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Select an Agent</h3>
                  <p className="text-muted-foreground">
                    Choose an agent from the list to review and verify.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentVerification;

import { useState } from "react";
import { Plus, MessageSquare, Send, Download, Search, Sparkles, Brain } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Session {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

interface RagResult {
  id: string;
  content: string;
  source: string;
  relevance: number;
}

const MemoryPage = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [ragResults, setRagResults] = useState<RagResult[]>([]);
  const [currentSession, setCurrentSession] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [chatHistoryEnabled, setChatHistoryEnabled] = useState(true);
  const [fileRagEnabled, setFileRagEnabled] = useState(false);

  const handleNewSession = () => {
    const newSession: Session = {
      id: `session-${Date.now()}`,
      title: `New Chat`,
      lastMessage: "",
      timestamp: new Date().toLocaleTimeString(),
    };
    setSessions([newSession, ...sessions]);
    setCurrentSession(newSession.id);
    setMessages([]);
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: inputValue,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages([...messages, userMessage]);
    setInputValue("");

    // Simulate assistant response
    setTimeout(() => {
      const assistantMessage: Message = {
        id: `msg-${Date.now() + 1}`,
        role: "assistant",
        content: "I can help you explore your memory data! You can ask me questions about your recent sessions, search for specific information, or analyze patterns in your data.",
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    }, 1000);
  };

  return (
    <div className="flex h-screen bg-[#0f0f0f] fixed inset-0 z-40">
      {/* Left Sidebar - Sessions */}
      <div className="w-72 bg-[#1a1a1a] border-r border-[#2d2d2d] flex flex-col">
        {/* New Session Button */}
        <div className="p-4">
          <Button
            onClick={handleNewSession}
            className="w-full bg-[#4285f4] hover:bg-[#5a9cf5] text-white font-medium gap-2 transition-all duration-200 hover:-translate-y-0.5 active:scale-[0.98]"
          >
            <Plus className="h-4 w-4" />
            New Session
          </Button>
        </div>

        {/* Settings */}
        <div className="px-4 py-3 border-t border-[#2d2d2d]">
          <h3 className="text-xs font-medium text-[#9aa0a6] uppercase tracking-wider mb-3">
            Settings
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-[#e8eaed]">Chat History</span>
              <Switch
                checked={chatHistoryEnabled}
                onCheckedChange={setChatHistoryEnabled}
                className="data-[state=checked]:bg-[#4285f4]"
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[#e8eaed]">File RAG</span>
              <Switch
                checked={fileRagEnabled}
                onCheckedChange={setFileRagEnabled}
                className="data-[state=checked]:bg-[#4285f4]"
              />
            </div>
          </div>
        </div>

        {/* Sessions List */}
        <ScrollArea className="flex-1 border-t border-[#2d2d2d]">
          <div className="p-3 space-y-1">
            {sessions.length === 0 ? (
              <div className="text-center py-10">
                <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-[#2d2d2d] flex items-center justify-center">
                  <MessageSquare className="h-6 w-6 text-[#9aa0a6]" />
                </div>
                <p className="text-[#9aa0a6] text-sm">No chat sessions yet</p>
                <p className="text-xs text-[#6b6b6b] mt-1">Start a conversation</p>
              </div>
            ) : (
              sessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => setCurrentSession(session.id)}
                  className={`w-full text-left p-3 rounded-lg transition-all duration-200 ${currentSession === session.id
                    ? "bg-[#2d2d2d] border border-[#4285f4]/30"
                    : "hover:bg-[#252525] border border-transparent"
                    }`}
                >
                  <p className="text-sm font-medium text-[#e8eaed] truncate">
                    {session.title}
                  </p>
                  <p className="text-xs text-[#6b6b6b] mt-1">{session.timestamp}</p>
                </button>
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Center - Chat Panel */}
      <div className="flex-1 flex flex-col bg-[#0f0f0f] border-r border-[#2d2d2d]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#2d2d2d]">
          <h2 className="text-lg font-medium text-white">AI Assistant</h2>
          <p className="text-sm text-[#9aa0a6] mt-0.5">
            Ask questions about your memory data
          </p>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1 p-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-20">
              {/* Creation of Adam Image */}
              <div className="relative mb-8">
                <div className="w-80 h-48 rounded-2xl overflow-hidden shadow-2xl shadow-[#4285f4]/10 border border-[#2d2d2d]">
                  <img
                    src="/creation-hands.png"
                    alt="Creation of Adam - Human and AI connection"
                    className="w-full h-full object-cover"
                  />
                </div>
              </div>
              <h2 className="text-2xl font-medium text-white mb-2">Where Memory Meets Intelligence</h2>
              <p className="text-[#9aa0a6] text-center max-w-md">
                Bridge the gap between your knowledge and AI. Ask anything about your stored memories.
              </p>
              <div className="flex gap-3 mt-8">
                <button className="px-4 py-2 rounded-full bg-[#2d2d2d] text-[#e8eaed] text-sm hover:bg-[#3d3d3d] transition-all">
                  What's in my memory?
                </button>
                <button className="px-4 py-2 rounded-full bg-[#2d2d2d] text-[#e8eaed] text-sm hover:bg-[#3d3d3d] transition-all">
                  Search for...
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"
                    }`}
                >
                  <div
                    className={`max-w-[80%] px-4 py-3 rounded-2xl ${message.role === "user"
                      ? "bg-[#4285f4] text-white rounded-br-md"
                      : "bg-[#2d2d2d] text-[#e8eaed] rounded-bl-md"
                      }`}
                  >
                    <p className="text-sm">{message.content}</p>
                    <p className="text-xs mt-2 opacity-60">{message.timestamp}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Chat Input */}
        <div className="p-4 border-t border-[#2d2d2d] bg-[#1a1a1a]">
          <form onSubmit={handleSendMessage} className="flex items-center gap-3">
            <div className="flex-1 relative">
              <button
                type="button"
                className="absolute left-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-[#2d2d2d] hover:bg-[#3d3d3d] flex items-center justify-center text-[#9aa0a6] hover:text-white transition-all"
              >
                <Plus className="h-4 w-4" />
              </button>
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask about your memory..."
                className="w-full bg-[#2d2d2d] border border-[#3d3d3d] rounded-full py-3 pl-14 pr-4 text-[#e8eaed] placeholder-[#6b6b6b] focus:outline-none focus:border-[#4285f4] focus:ring-1 focus:ring-[#4285f4] transition-all"
              />
            </div>
            <Button
              type="submit"
              size="icon"
              className="w-11 h-11 rounded-full bg-[#4285f4] hover:bg-[#5a9cf5] transition-all hover:-translate-y-0.5 active:scale-95"
            >
              <Send className="h-5 w-5" />
            </Button>
          </form>
        </div>
      </div>

      {/* Right Panel - RAG Results */}
      <div className="w-80 bg-[#1a1a1a] flex flex-col">
        <div className="px-5 py-4 border-b border-[#2d2d2d] flex justify-between items-center">
          <h2 className="text-base font-medium text-white">RAG Results</h2>
          <Button
            variant="ghost"
            size="icon"
            className="w-8 h-8 rounded-lg bg-[#2d2d2d] hover:bg-[#3d3d3d] text-[#9aa0a6] hover:text-white"
          >
            <Download className="h-4 w-4" />
          </Button>
        </div>

        <ScrollArea className="flex-1 p-4">
          {ragResults.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-[#2d2d2d] flex items-center justify-center">
                <Search className="h-7 w-7 text-[#6b6b6b]" />
              </div>
              <p className="text-[#9aa0a6] text-sm">No results yet</p>
              <p className="text-xs text-[#6b6b6b] mt-1">Ask a question to see matches</p>
            </div>
          ) : (
            <div className="space-y-3">
              {ragResults.map((result) => (
                <div
                  key={result.id}
                  className="p-4 rounded-xl bg-[#252525] border border-[#2d2d2d] hover:border-[#4285f4]/30 transition-all"
                >
                  <p className="text-sm text-[#e8eaed] line-clamp-3">{result.content}</p>
                  <div className="flex items-center justify-between mt-3">
                    <span className="text-xs text-[#6b6b6b]">{result.source}</span>
                    <span className="text-xs text-[#4285f4]">
                      {Math.round(result.relevance * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </div>
    </div>
  );
};

export default MemoryPage;

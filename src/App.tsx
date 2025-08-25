import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Homepage from "./pages/Homepage";
import Explore from "./pages/Explore";
import AgentDetail from "./pages/AgentDetail";
import Leaderboard from "./pages/Leaderboard";
import CreatorStudio from "./pages/CreatorStudio";
import Auth from "./pages/Auth";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Homepage />} />
            <Route path="explore" element={<Explore />} />
            <Route path="agent/:id" element={<AgentDetail />} />
            <Route path="leaderboard" element={<Leaderboard />} />
            <Route path="studio" element={<CreatorStudio />} />
            <Route path="auth" element={<Auth />} />
            <Route path="trending" element={<Explore />} />
            <Route path="categories" element={<Explore />} />
            <Route path="creators" element={<Explore />} />
            <Route path="submit" element={<Explore />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;

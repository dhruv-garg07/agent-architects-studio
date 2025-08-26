import {
  BrowserRouter,
  Routes,
  Route,
} from "react-router-dom";
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import Layout from "./components/Layout";
import Homepage from "./pages/Homepage";
import Explore from "./pages/Explore";
import AgentDetail from "./pages/AgentDetail";
import Auth from "./pages/Auth";
import CreatorStudio from "./pages/CreatorStudio";
import Creators from "./pages/Creators";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Homepage />} />
            <Route path="explore" element={<Explore />} />
            <Route path="agent/:id" element={<AgentDetail />} />
            <Route path="trending" element={<Explore />} />
            <Route path="categories" element={<Explore />} />
            <Route path="creators" element={<Creators />} />
            <Route path="submit" element={<CreatorStudio />} />
          </Route>
          <Route path="/auth" element={<Auth />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;

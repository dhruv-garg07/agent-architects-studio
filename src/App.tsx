import {
  BrowserRouter,
  Routes,
  Route,
} from "react-router-dom";
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";

// New template pages
import HomePage from "./templates/base/HomePage";
import MemoryPage from "./templates/memory/MemoryPage";
import AuthPage from "./templates/auth/AuthPage";
import WaitlistPage from "./templates/waitlist/WaitlistPage";
import HarshitPage from "./templates/harshit/HarshitPage";
import NotFoundPage from "./templates/errors/NotFoundPage";

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Main Routes - Divine experience */}
          <Route path="/" element={<HomePage />} />
          <Route path="/memory" element={<MemoryPage />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/signin" element={<AuthPage />} />
          <Route path="/signup" element={<AuthPage />} />
          <Route path="/waitlist" element={<WaitlistPage />} />
          <Route path="/join" element={<WaitlistPage />} />
          <Route path="/founder" element={<HarshitPage />} />

          {/* 404 */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;

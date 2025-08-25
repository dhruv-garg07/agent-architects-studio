import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Search, User, Plus, Menu, X } from "lucide-react";
import { useState } from "react";

const Layout = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();

  const navigation = [
    { name: "Explore", href: "/explore" },
    { name: "Trending", href: "/trending" },
    { name: "Categories", href: "/categories" },
    { name: "Creators", href: "/creators" },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation Header */}
      <header className="border-b border-card-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <NavLink to="/" className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <div className="w-4 h-4 bg-primary-foreground rounded-sm transform rotate-45"></div>
              </div>
              <span className="text-xl font-semibold font-inter">The Manhattan Project</span>
            </NavLink>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-8">
              {navigation.map((item) => (
                <NavLink
                  key={item.name}
                  to={item.href}
                  className={({ isActive }) =>
                    `text-sm font-medium transition-colors hover:text-primary ${
                      isActive ? "text-primary" : "text-muted-foreground"
                    }`
                  }
                >
                  {item.name}
                </NavLink>
              ))}
            </nav>

            {/* Actions */}
            <div className="flex items-center space-x-4">
              <Button variant="ghost" size="sm" className="hidden sm:flex" onClick={() => navigate('/explore')}>
                <Search className="w-4 h-4 mr-2" />
                Search
              </Button>

              <Button variant="outline" size="sm" className="btn-sage" onClick={() => navigate('/studio')}>
                <Plus className="w-4 h-4 mr-2" />
                Submit Agent
              </Button>

              <Button variant="ghost" size="sm" onClick={() => navigate('/auth')}>
                <User className="w-4 h-4" />
              </Button>

              {/* Mobile menu button */}
              <Button
                variant="ghost"
                size="sm"
                className="md:hidden"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
              </Button>
            </div>
          </div>

          {/* Mobile Navigation */}
          {mobileMenuOpen && (
            <div className="md:hidden py-4 border-t border-card-border">
              <nav className="flex flex-col space-y-4">
                {navigation.map((item) => (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    className={({ isActive }) =>
                      `text-sm font-medium transition-colors hover:text-primary ${
                        isActive ? "text-primary" : "text-muted-foreground"
                      }`
                    }
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    {item.name}
                  </NavLink>
                ))}
                <Button variant="ghost" size="sm" className="justify-start">
                  <Search className="w-4 h-4 mr-2" />
                  Search
                </Button>
              </nav>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main>
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-card-border bg-card/30 mt-20">
        <div className="container mx-auto px-4 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="col-span-1 md:col-span-2">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-6 h-6 bg-primary rounded-md flex items-center justify-center">
                  <div className="w-3 h-3 bg-primary-foreground rounded-sm transform rotate-45"></div>
                </div>
                <span className="text-lg font-semibold font-inter">The Manhattan Project</span>
              </div>
              <p className="text-muted-foreground text-sm max-w-md">
                The definitive hub for discovering, sharing, and demonstrating autonomous AI agents. 
                Combining community collaboration with professional-grade tools.
              </p>
            </div>
            
            <div>
              <h3 className="font-medium mb-4">Platform</h3>
              <div className="space-y-3 text-sm text-muted-foreground">
                <a href="/explore" className="block hover:text-primary transition-colors">Explore Agents</a>
                <a href="/submit" className="block hover:text-primary transition-colors">Submit Agent</a>
                <a href="/docs" className="block hover:text-primary transition-colors">Documentation</a>
                <a href="/api" className="block hover:text-primary transition-colors">API</a>
              </div>
            </div>
            
            <div>
              <h3 className="font-medium mb-4">Community</h3>
              <div className="space-y-3 text-sm text-muted-foreground">
                <a href="/creators" className="block hover:text-primary transition-colors">Top Creators</a>
                <a href="/leaderboard" className="block hover:text-primary transition-colors">Leaderboard</a>
                <a href="/discord" className="block hover:text-primary transition-colors">Discord</a>
                <a href="/github" className="block hover:text-primary transition-colors">GitHub</a>
              </div>
            </div>
          </div>
          
          <div className="sketch-divider my-8"></div>
          
          <div className="flex flex-col md:flex-row justify-between items-center text-sm text-muted-foreground">
            <p>&copy; 2024 The Manhattan Project. Built for the AI community.</p>
            <div className="flex space-x-6 mt-4 md:mt-0">
              <a href="/privacy" className="hover:text-primary transition-colors">Privacy</a>
              <a href="/terms" className="hover:text-primary transition-colors">Terms</a>
              <a href="/contact" className="hover:text-primary transition-colors">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
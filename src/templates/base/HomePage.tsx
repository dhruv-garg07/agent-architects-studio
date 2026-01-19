import { Button } from "@/components/ui/button";
import { ArrowRight, Brain, Sparkles, Database, Search, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import AmbientMusic from "@/components/AmbientMusic";

const HomePage = () => {
    return (
        <div className="min-h-screen bg-[#0f0f0f] text-[#e8eaed]">
            {/* Minimal Nav */}
            <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0f0f0f]/80 backdrop-blur-sm border-b border-[#2d2d2d]">
                <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
                    <Link to="/" className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#4285f4] to-[#9b87f5] flex items-center justify-center">
                            <Brain className="h-4 w-4 text-white" />
                        </div>
                        <span className="font-semibold text-lg">GitMem</span>
                    </Link>
                    <div className="flex items-center gap-4">
                        <Link to="/memory" className="text-sm text-[#9aa0a6] hover:text-white transition-colors">
                            Memory
                        </Link>
                        <Link to="/auth" className="text-sm text-[#9aa0a6] hover:text-white transition-colors">
                            Sign In
                        </Link>
                        <Button asChild size="sm" className="bg-[#4285f4] hover:bg-[#5a9cf5]">
                            <Link to="/memory">Get Started</Link>
                        </Button>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="pt-32 pb-20 px-6">
                <div className="max-w-4xl mx-auto text-center">
                    {/* Creation of Adam Image */}
                    <div className="relative mb-12 inline-block">
                        <div className="w-96 h-56 rounded-3xl overflow-hidden shadow-2xl shadow-[#4285f4]/20 border border-[#2d2d2d] mx-auto">
                            <img
                                src="/creation-hands.png"
                                alt="Human and AI Connection"
                                className="w-full h-full object-cover"
                            />
                        </div>
                        <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 px-4 py-1.5 rounded-full bg-[#1a1a1a] border border-[#2d2d2d] text-xs text-[#9aa0a6]">
                            <Sparkles className="h-3 w-3 inline-block mr-1.5 text-[#4285f4]" />
                            Where Memory Meets Intelligence
                        </div>
                    </div>

                    <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
                        Real context for your
                        <span className="block bg-gradient-to-r from-[#4285f4] via-[#9b87f5] to-[#4285f4] bg-clip-text text-transparent">
                            coding agents.
                        </span>
                    </h1>

                    <p className="text-xl text-[#9aa0a6] max-w-2xl mx-auto mb-10 leading-relaxed">
                        Index your repos and docs so agents stop hallucinating and you stop wasting tokens.
                        Ground-truth information for AI that actually works.
                    </p>

                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <Button asChild size="lg" className="bg-[#4285f4] hover:bg-[#5a9cf5] text-white px-8 py-6 text-lg rounded-xl transition-all hover:-translate-y-0.5">
                            <Link to="/memory">
                                Try GitMem Now
                                <ArrowRight className="w-5 h-5 ml-2" />
                            </Link>
                        </Button>
                        <Button asChild variant="outline" size="lg" className="border-[#3d3d3d] bg-[#1a1a1a] hover:bg-[#2d2d2d] text-white px-8 py-6 text-lg rounded-xl">
                            <Link to="/explore">
                                View Documentation
                            </Link>
                        </Button>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="py-20 px-6 border-t border-[#2d2d2d]">
                <div className="max-w-5xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-bold mb-4">Built for AI-first workflows</h2>
                        <p className="text-[#9aa0a6] max-w-xl mx-auto">
                            Everything your coding agents need to deliver accurate, context-aware responses.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-6">
                        {/* Feature 1 */}
                        <div className="p-6 rounded-2xl bg-[#1a1a1a] border border-[#2d2d2d] hover:border-[#4285f4]/30 transition-all group">
                            <div className="w-12 h-12 rounded-xl bg-[#4285f4]/10 flex items-center justify-center mb-4 group-hover:bg-[#4285f4]/20 transition-colors">
                                <Database className="h-6 w-6 text-[#4285f4]" />
                            </div>
                            <h3 className="text-lg font-semibold mb-2">Index Everything</h3>
                            <p className="text-sm text-[#9aa0a6] leading-relaxed">
                                Repos, docs, packages — index any source and make it instantly searchable by your agents.
                            </p>
                        </div>

                        {/* Feature 2 */}
                        <div className="p-6 rounded-2xl bg-[#1a1a1a] border border-[#2d2d2d] hover:border-[#4285f4]/30 transition-all group">
                            <div className="w-12 h-12 rounded-xl bg-[#9b87f5]/10 flex items-center justify-center mb-4 group-hover:bg-[#9b87f5]/20 transition-colors">
                                <Search className="h-6 w-6 text-[#9b87f5]" />
                            </div>
                            <h3 className="text-lg font-semibold mb-2">Semantic Search</h3>
                            <p className="text-sm text-[#9aa0a6] leading-relaxed">
                                Sub-5 second responses across all indexed content using state-of-the-art RAG.
                            </p>
                        </div>

                        {/* Feature 3 */}
                        <div className="p-6 rounded-2xl bg-[#1a1a1a] border border-[#2d2d2d] hover:border-[#4285f4]/30 transition-all group">
                            <div className="w-12 h-12 rounded-xl bg-[#34a853]/10 flex items-center justify-center mb-4 group-hover:bg-[#34a853]/20 transition-colors">
                                <Zap className="h-6 w-6 text-[#34a853]" />
                            </div>
                            <h3 className="text-lg font-semibold mb-2">Reduce Hallucinations</h3>
                            <p className="text-sm text-[#9aa0a6] leading-relaxed">
                                Ground your AI in real data. No more made-up APIs or outdated information.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-20 px-6 border-t border-[#2d2d2d]">
                <div className="max-w-3xl mx-auto text-center">
                    <div className="p-12 rounded-3xl bg-gradient-to-br from-[#1a1a1a] to-[#0f0f0f] border border-[#2d2d2d]">
                        <h2 className="text-3xl font-bold mb-4">Ready to supercharge your agents?</h2>
                        <p className="text-[#9aa0a6] mb-8 max-w-md mx-auto">
                            Join developers who are building AI that actually knows what it's talking about.
                        </p>
                        <Button asChild size="lg" className="bg-[#4285f4] hover:bg-[#5a9cf5] px-8 py-6 text-lg rounded-xl">
                            <Link to="/memory">
                                Start for Free
                                <ArrowRight className="w-5 h-5 ml-2" />
                            </Link>
                        </Button>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-8 px-6 border-t border-[#2d2d2d]">
                <div className="max-w-5xl mx-auto flex flex-col md:flex-row justify-between items-center text-sm text-[#6b6b6b]">
                    <div className="flex items-center gap-2 mb-4 md:mb-0">
                        <Brain className="h-4 w-4" />
                        <span>© 2026 The Manhattan Project</span>
                    </div>
                    <div className="flex gap-6">
                        <Link to="/waitlist" className="hover:text-white transition-colors">Join Waitlist</Link>
                        <Link to="/founder" className="hover:text-white transition-colors">Founder</Link>
                        <Link to="/auth" className="hover:text-white transition-colors">Sign In</Link>
                    </div>
                </div>
            </footer>

            {/* Divine Ambient Music */}
            <AmbientMusic />
        </div>
    );
};

export default HomePage;

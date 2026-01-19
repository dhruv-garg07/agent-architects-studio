import { Link } from "react-router-dom";
import { Mail, ExternalLink, Sparkles } from "lucide-react";

const HarshitPage = () => {
    return (
        <div className="min-h-screen bg-[#0f0f0f] text-[#e8eaed] relative overflow-hidden">
            {/* Celestial Background */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-gradient-radial from-[#4285f4]/8 via-[#9b87f5]/3 to-transparent rounded-full blur-3xl" />
                <div className="absolute bottom-0 right-0 w-[600px] h-[400px] bg-[#4285f4]/5 rounded-full blur-3xl" />
                {/* Stars */}
                {[...Array(20)].map((_, i) => (
                    <div
                        key={i}
                        className="absolute w-1 h-1 bg-white/30 rounded-full"
                        style={{
                            top: `${Math.random() * 100}%`,
                            left: `${Math.random() * 100}%`,
                            animationDelay: `${Math.random() * 3}s`,
                        }}
                    />
                ))}
            </div>

            <main className="relative z-10 max-w-3xl mx-auto px-6 py-20">
                {/* Divine Header */}
                <header className="text-center mb-16">
                    {/* Avatar with divine glow */}
                    <div className="relative inline-block mb-8">
                        <div className="w-40 h-40 rounded-full overflow-hidden border-2 border-[#4285f4]/40 shadow-2xl shadow-[#4285f4]/20">
                            <img
                                src="/static/harshit.png"
                                alt="Harshit"
                                className="w-full h-full object-cover"
                            />
                        </div>
                        <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-[#1a1a1a] border border-[#2d2d2d] text-xs text-[#34a853]">
                            <Sparkles className="w-3 h-3 inline-block mr-1" />
                            Shipping Daily
                        </div>
                    </div>

                    <p className="text-[#9aa0a6] text-lg mb-2 italic">
                        "In the beginning was the problem, and the problem was with the engineer..."
                    </p>
                    <h1 className="text-4xl md:text-5xl font-serif font-bold mb-4 leading-tight">
                        <span className="bg-gradient-to-r from-white via-[#e8eaed] to-[#9aa0a6] bg-clip-text text-transparent">
                            Harshit
                        </span>
                    </h1>
                    <p className="text-[#9aa0a6]">
                        Founder @ <span className="text-white">The Manhattan Project</span>
                    </p>
                </header>

                {/* The Gospel */}
                <section className="mb-16">
                    <blockquote className="text-center text-xl md:text-2xl font-serif italic text-[#9aa0a6] leading-relaxed mb-8">
                        "From the halls of <span className="text-white">IIT Ropar</span>, a vision emerged—<br />
                        to build systems that remain steadfast when the tempest of scarcity rages,<br />
                        to forge memory where forgetfulness once reigned."
                    </blockquote>
                </section>

                {/* The Mission Cards */}
                <section className="grid md:grid-cols-2 gap-6 mb-16">
                    <div className="p-6 rounded-2xl bg-[#1a1a1a]/80 border border-[#2d2d2d] hover:border-[#4285f4]/30 transition-all">
                        <h3 className="text-xs font-bold text-[#4285f4] uppercase tracking-widest mb-3">
                            The Calling
                        </h3>
                        <p className="text-[#9aa0a6] text-sm leading-relaxed font-serif italic">
                            An Electrical Engineer and AI Researcher, called to ensure that technical
                            models remain robust when resources are scarce and expertise is thin.
                        </p>
                    </div>

                    <div className="p-6 rounded-2xl bg-[#1a1a1a]/80 border border-[#2d2d2d] hover:border-[#9b87f5]/30 transition-all">
                        <h3 className="text-xs font-bold text-[#9b87f5] uppercase tracking-widest mb-3">
                            The Doctrine
                        </h3>
                        <p className="text-[#9aa0a6] text-sm leading-relaxed font-serif italic">
                            Frugal engineering—solving systemic inefficiencies without the luxury of
                            infinite resources. Robustness over idealism. Impact over vanity.
                        </p>
                    </div>

                    <div className="p-6 rounded-2xl bg-[#1a1a1a]/80 border border-[#2d2d2d] hover:border-[#34a853]/30 transition-all md:col-span-2">
                        <h3 className="text-xs font-bold text-[#34a853] uppercase tracking-widest mb-3">
                            The Creations
                        </h3>
                        <p className="text-[#9aa0a6] text-sm leading-relaxed font-serif italic mb-4">
                            Architect of <span className="text-white">MAHA</span> and <span className="text-white">RadBot</span>—
                            vessels of memory-first orchestration, designed for global, practical
                            scalability in the realm of agentic workflows.
                        </p>
                        <div className="flex flex-wrap gap-2">
                            {["Resource Optimization", "Memory Architectures", "Robust Systems", "Agentic Orchestration"].map((skill) => (
                                <span
                                    key={skill}
                                    className="px-3 py-1.5 text-xs rounded-lg bg-[#2d2d2d] border border-[#3d3d3d] text-[#e8eaed]"
                                >
                                    {skill}
                                </span>
                            ))}
                        </div>
                    </div>
                </section>

                {/* The Invitation */}
                <section className="text-center mb-16">
                    <p className="text-[#9aa0a6] font-serif italic mb-8">
                        "Seek audience, and the doors shall open."
                    </p>
                    <div className="flex flex-wrap gap-4 justify-center">
                        <a
                            href="https://themanhattanproject.ai"
                            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[#4285f4] hover:bg-[#5a9cf5] text-white font-medium transition-all hover:-translate-y-0.5"
                        >
                            Enter the Studio
                            <ExternalLink className="w-4 h-4" />
                        </a>
                        <a
                            href="mailto:2021eeb1175@iitrpr.ac.in"
                            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[#1a1a1a] border border-[#2d2d2d] hover:border-[#4285f4]/30 text-white font-medium transition-all hover:-translate-y-0.5"
                        >
                            <Mail className="w-4 h-4" />
                            Seek Audience
                        </a>
                    </div>
                </section>

                {/* Footer */}
                <footer className="text-center border-t border-[#2d2d2d] pt-8">
                    <p className="text-[#6b6b6b] text-sm">
                        © 2026 The Manhattan Project
                    </p>
                    <p className="text-[#4d4d4d] text-xs mt-2 font-serif italic">
                        Excellence · Innovation · Resilience · Impact
                    </p>
                </footer>

                {/* Back link */}
                <div className="text-center mt-8">
                    <Link to="/" className="text-[#6b6b6b] hover:text-white text-sm transition-colors">
                        ← Return to the Gates
                    </Link>
                </div>
            </main>
        </div>
    );
};

export default HarshitPage;

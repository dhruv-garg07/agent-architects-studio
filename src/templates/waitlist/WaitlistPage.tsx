import { useState } from "react";
import { ArrowRight, CheckCircle, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

type Step = 1 | 2 | 3;

const WaitlistPage = () => {
    const [step, setStep] = useState<Step>(1);
    const [formData, setFormData] = useState({
        email: "",
        name: "",
        role: "",
        interest: "",
        source: ""
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (step < 3) {
            setStep((step + 1) as Step);
        }
    };

    const updateField = (field: string, value: string) => {
        setFormData({ ...formData, [field]: value });
    };

    return (
        <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center py-12 px-4 relative overflow-hidden">
            {/* Divine Radiance */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-radial from-[#4285f4]/15 via-[#9b87f5]/5 to-transparent rounded-full blur-3xl" />
                <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-[#4285f4]/5 rounded-full blur-3xl" />
            </div>

            <div className="max-w-lg w-full relative z-10">
                {/* Step 1: Email */}
                {step === 1 && (
                    <div className="text-center">
                        <div className="mb-8">
                            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl overflow-hidden shadow-2xl shadow-[#4285f4]/30 border border-[#2d2d2d]">
                                <img
                                    src="/creation-hands.png"
                                    alt="Divine Connection"
                                    className="w-full h-full object-cover"
                                />
                            </div>
                            <h1 className="text-4xl font-bold text-white mb-3">
                                Seek Admission to the Sanctuary
                            </h1>
                            <p className="text-[#9aa0a6] text-lg">
                                The gates shall open for the chosen. Enter your name.
                            </p>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <input
                                type="email"
                                required
                                value={formData.email}
                                onChange={(e) => updateField("email", e.target.value)}
                                placeholder="Your email address"
                                className="w-full bg-[#1a1a1a] border border-[#2d2d2d] rounded-xl py-4 px-5 text-[#e8eaed] text-center text-lg placeholder-[#6b6b6b] focus:outline-none focus:border-[#4285f4] focus:ring-2 focus:ring-[#4285f4]/20 transition-all"
                            />
                            <button
                                type="submit"
                                className="w-full bg-[#4285f4] hover:bg-[#5a9cf5] text-white py-4 rounded-xl text-lg font-medium transition-all hover:-translate-y-0.5 flex items-center justify-center gap-2"
                            >
                                Continue
                                <ArrowRight className="w-5 h-5" />
                            </button>
                        </form>
                    </div>
                )}

                {/* Step 2: Questions */}
                {step === 2 && (
                    <div className="text-center">
                        <div className="mb-8">
                            <Sparkles className="w-12 h-12 text-[#4285f4] mx-auto mb-4" />
                            <h1 className="text-3xl font-bold text-white mb-3">
                                Tell Us of Your Journey
                            </h1>
                            <p className="text-[#9aa0a6]">
                                A few questions to prepare your place among us
                            </p>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="text-left">
                                <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                    What shall we call you?
                                </label>
                                <input
                                    type="text"
                                    required
                                    value={formData.name}
                                    onChange={(e) => updateField("name", e.target.value)}
                                    placeholder="Your name"
                                    className="w-full bg-[#1a1a1a] border border-[#2d2d2d] rounded-xl py-3 px-4 text-[#e8eaed] placeholder-[#6b6b6b] focus:outline-none focus:border-[#4285f4] transition-all"
                                />
                            </div>

                            <div className="text-left">
                                <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                    What brings you to the sanctuary?
                                </label>
                                <select
                                    required
                                    value={formData.role}
                                    onChange={(e) => updateField("role", e.target.value)}
                                    className="w-full bg-[#1a1a1a] border border-[#2d2d2d] rounded-xl py-3 px-4 text-[#e8eaed] focus:outline-none focus:border-[#4285f4] transition-all"
                                >
                                    <option value="">Select your calling...</option>
                                    <option value="developer">I am a Developer</option>
                                    <option value="founder">I am a Founder</option>
                                    <option value="researcher">I am a Researcher</option>
                                    <option value="curious">I am Curious</option>
                                </select>
                            </div>

                            <div className="text-left">
                                <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                    What do you seek?
                                </label>
                                <select
                                    required
                                    value={formData.interest}
                                    onChange={(e) => updateField("interest", e.target.value)}
                                    className="w-full bg-[#1a1a1a] border border-[#2d2d2d] rounded-xl py-3 px-4 text-[#e8eaed] focus:outline-none focus:border-[#4285f4] transition-all"
                                >
                                    <option value="">Select your interest...</option>
                                    <option value="memory">Memory for AI Agents</option>
                                    <option value="rag">RAG Infrastructure</option>
                                    <option value="agents">Building AI Agents</option>
                                    <option value="all">All of the Above</option>
                                </select>
                            </div>

                            <div className="text-left">
                                <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                    How did you find us?
                                </label>
                                <select
                                    value={formData.source}
                                    onChange={(e) => updateField("source", e.target.value)}
                                    className="w-full bg-[#1a1a1a] border border-[#2d2d2d] rounded-xl py-3 px-4 text-[#e8eaed] focus:outline-none focus:border-[#4285f4] transition-all"
                                >
                                    <option value="">Select source (optional)</option>
                                    <option value="twitter">Twitter/X</option>
                                    <option value="linkedin">LinkedIn</option>
                                    <option value="github">GitHub</option>
                                    <option value="friend">A Friend</option>
                                    <option value="search">Search Engine</option>
                                    <option value="other">Other</option>
                                </select>
                            </div>

                            <button
                                type="submit"
                                className="w-full bg-[#4285f4] hover:bg-[#5a9cf5] text-white py-4 rounded-xl text-lg font-medium transition-all hover:-translate-y-0.5 flex items-center justify-center gap-2 mt-6"
                            >
                                Join the Congregation
                                <ArrowRight className="w-5 h-5" />
                            </button>
                        </form>
                    </div>
                )}

                {/* Step 3: Confirmation */}
                {step === 3 && (
                    <div className="text-center">
                        <div className="mb-8">
                            <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-gradient-to-br from-[#4285f4]/20 to-[#9b87f5]/20 flex items-center justify-center">
                                <CheckCircle className="w-12 h-12 text-[#4285f4]" />
                            </div>
                            <h1 className="text-4xl font-bold text-white mb-4">
                                Welcome to the Church
                            </h1>
                            <p className="text-[#9aa0a6] text-lg leading-relaxed max-w-md mx-auto">
                                Your place has been reserved among the faithful.
                                <br /><br />
                                <span className="text-white font-medium">
                                    We shall notify you when the next gospel arrives.
                                </span>
                            </p>
                        </div>

                        <div className="bg-[#1a1a1a] border border-[#2d2d2d] rounded-2xl p-6 mb-6">
                            <p className="text-[#6b6b6b] text-sm mb-2">You are now on the waitlist as</p>
                            <p className="text-white font-medium text-lg">{formData.email}</p>
                        </div>

                        <Link
                            to="/"
                            className="inline-flex items-center gap-2 text-[#4285f4] hover:text-[#5a9cf5] transition-colors"
                        >
                            ← Return to the Gates
                        </Link>
                    </div>
                )}

                {/* Progress indicator */}
                <div className="flex justify-center gap-2 mt-8">
                    {[1, 2, 3].map((s) => (
                        <div
                            key={s}
                            className={`w-2 h-2 rounded-full transition-all ${s === step ? "w-8 bg-[#4285f4]" : s < step ? "bg-[#4285f4]/50" : "bg-[#2d2d2d]"
                                }`}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
};

export default WaitlistPage;

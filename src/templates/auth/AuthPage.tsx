import { useState } from "react";
import { Brain, Github, Mail } from "lucide-react";
import { Link } from "react-router-dom";

const AuthPage = () => {
    const [activeTab, setActiveTab] = useState<"signin" | "signup">("signin");
    const [userRole, setUserRole] = useState("");

    return (
        <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center py-12 px-4 relative overflow-hidden">
            {/* Decorative Elements - Gospel-like radiance */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-gradient-radial from-[#4285f4]/10 via-transparent to-transparent rounded-full blur-3xl" />
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-[#9b87f5]/5 rounded-full blur-3xl" />
            </div>

            <div className="max-w-md w-full relative z-10">
                {/* Logo Header */}
                <div className="text-center mb-8">
                    <Link to="/" className="inline-flex items-center gap-3 mb-6">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#4285f4] to-[#9b87f5] flex items-center justify-center shadow-lg shadow-[#4285f4]/20">
                            <Brain className="h-6 w-6 text-white" />
                        </div>
                    </Link>
                    <h1 className="text-3xl font-bold text-white tracking-tight mb-2">
                        {activeTab === "signin" ? "Enter the Sanctuary" : "Join the Congregation"}
                    </h1>
                    <p className="text-[#9aa0a6]">
                        {activeTab === "signin"
                            ? "Sign in to continue your journey"
                            : "Create an account to begin your path"}
                    </p>
                </div>

                {/* Auth Card */}
                <div className="bg-[#1a1a1a] border border-[#2d2d2d] rounded-2xl p-8 shadow-2xl">
                    {/* Tabs */}
                    <div className="flex border-b border-[#2d2d2d] mb-6">
                        <button
                            onClick={() => setActiveTab("signin")}
                            className={`flex-1 py-3 text-center font-medium transition-all ${activeTab === "signin"
                                    ? "border-b-2 border-[#4285f4] text-[#4285f4]"
                                    : "text-[#9aa0a6] hover:text-white"
                                }`}
                        >
                            Sign In
                        </button>
                        <button
                            onClick={() => setActiveTab("signup")}
                            className={`flex-1 py-3 text-center font-medium transition-all ${activeTab === "signup"
                                    ? "border-b-2 border-[#4285f4] text-[#4285f4]"
                                    : "text-[#9aa0a6] hover:text-white"
                                }`}
                        >
                            Sign Up
                        </button>
                    </div>

                    {/* Sign In Form - Submits to Flask /login */}
                    {activeTab === "signin" && (
                        <form action="/login" method="POST" className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                    Email Address
                                </label>
                                <input
                                    type="email"
                                    name="email"
                                    required
                                    placeholder="Enter your email"
                                    className="w-full bg-[#2d2d2d] border border-[#3d3d3d] rounded-xl py-3 px-4 text-[#e8eaed] placeholder-[#6b6b6b] focus:outline-none focus:border-[#4285f4] focus:ring-1 focus:ring-[#4285f4] transition-all"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                    Password
                                </label>
                                <input
                                    type="password"
                                    name="password"
                                    required
                                    placeholder="Enter your password"
                                    className="w-full bg-[#2d2d2d] border border-[#3d3d3d] rounded-xl py-3 px-4 text-[#e8eaed] placeholder-[#6b6b6b] focus:outline-none focus:border-[#4285f4] focus:ring-1 focus:ring-[#4285f4] transition-all"
                                />
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <label className="flex items-center text-[#9aa0a6]">
                                    <input type="checkbox" name="remember" className="mr-2 rounded" />
                                    Remember me
                                </label>
                                <a href="#" className="text-[#4285f4] hover:underline">
                                    Forgot password?
                                </a>
                            </div>
                            <button
                                type="submit"
                                className="w-full bg-[#4285f4] hover:bg-[#5a9cf5] text-white py-4 rounded-xl transition-all hover:-translate-y-0.5 font-medium"
                            >
                                Sign In
                            </button>
                        </form>
                    )}

                    {/* Sign Up Form - Submits to Flask /register */}
                    {activeTab === "signup" && (
                        <form action="/register" method="POST" className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                        Full Name
                                    </label>
                                    <input
                                        type="text"
                                        name="full_name"
                                        required
                                        placeholder="Your name"
                                        className="w-full bg-[#2d2d2d] border border-[#3d3d3d] rounded-xl py-3 px-4 text-[#e8eaed] placeholder-[#6b6b6b] focus:outline-none focus:border-[#4285f4] transition-all"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                        Username
                                    </label>
                                    <input
                                        type="text"
                                        name="username"
                                        required
                                        placeholder="username"
                                        className="w-full bg-[#2d2d2d] border border-[#3d3d3d] rounded-xl py-3 px-4 text-[#e8eaed] placeholder-[#6b6b6b] focus:outline-none focus:border-[#4285f4] transition-all"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                    Email Address
                                </label>
                                <input
                                    type="email"
                                    name="email"
                                    required
                                    placeholder="Enter your email"
                                    className="w-full bg-[#2d2d2d] border border-[#3d3d3d] rounded-xl py-3 px-4 text-[#e8eaed] placeholder-[#6b6b6b] focus:outline-none focus:border-[#4285f4] transition-all"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                    Password
                                </label>
                                <input
                                    type="password"
                                    name="password"
                                    required
                                    placeholder="Create a password"
                                    className="w-full bg-[#2d2d2d] border border-[#3d3d3d] rounded-xl py-3 px-4 text-[#e8eaed] placeholder-[#6b6b6b] focus:outline-none focus:border-[#4285f4] transition-all"
                                />
                                <p className="text-xs text-[#6b6b6b] mt-1">Must be at least 8 characters</p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                    Confirm Password
                                </label>
                                <input
                                    type="password"
                                    name="confirm_password"
                                    required
                                    placeholder="Confirm your password"
                                    className="w-full bg-[#2d2d2d] border border-[#3d3d3d] rounded-xl py-3 px-4 text-[#e8eaed] placeholder-[#6b6b6b] focus:outline-none focus:border-[#4285f4] transition-all"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                    How will you use the platform?
                                </label>
                                <select
                                    name="user_role"
                                    required
                                    value={userRole}
                                    onChange={(e) => setUserRole(e.target.value)}
                                    className="w-full bg-[#2d2d2d] border border-[#3d3d3d] rounded-xl py-3 px-4 text-[#e8eaed] focus:outline-none focus:border-[#4285f4] transition-all"
                                >
                                    <option value="">Select your path...</option>
                                    <option value="creator">Creator (Submit AI agents)</option>
                                    <option value="user">Seeker (Use AI agents)</option>
                                </select>
                            </div>

                            {/* Creator fields */}
                            {userRole === "creator" && (
                                <div className="space-y-4 pt-2">
                                    <div>
                                        <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                            Portfolio or GitHub URL
                                        </label>
                                        <input
                                            type="url"
                                            name="portfolio_url"
                                            placeholder="https://github.com/your-username"
                                            className="w-full bg-[#2d2d2d] border border-[#3d3d3d] rounded-xl py-3 px-4 text-[#e8eaed] placeholder-[#6b6b6b] focus:outline-none focus:border-[#4285f4] transition-all"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                            Areas of Expertise
                                        </label>
                                        <input
                                            type="text"
                                            name="expertise"
                                            placeholder="NLP, Computer Vision, Generative AI"
                                            className="w-full bg-[#2d2d2d] border border-[#3d3d3d] rounded-xl py-3 px-4 text-[#e8eaed] placeholder-[#6b6b6b] focus:outline-none focus:border-[#4285f4] transition-all"
                                        />
                                    </div>
                                </div>
                            )}

                            {/* User fields */}
                            {userRole === "user" && (
                                <div className="pt-2">
                                    <label className="block text-sm font-medium text-[#e8eaed] mb-2">
                                        Primary Interest
                                    </label>
                                    <select
                                        name="primary_interest"
                                        className="w-full bg-[#2d2d2d] border border-[#3d3d3d] rounded-xl py-3 px-4 text-[#e8eaed] focus:outline-none focus:border-[#4285f4] transition-all"
                                    >
                                        <option value="">Select your interest...</option>
                                        <option value="business">For my business or work</option>
                                        <option value="personal">For personal projects</option>
                                        <option value="research">For academic research</option>
                                        <option value="browsing">Just exploring</option>
                                    </select>
                                </div>
                            )}

                            <div className="flex items-start text-sm pt-2">
                                <input type="checkbox" name="terms" required className="mr-2 mt-1 rounded" />
                                <span className="text-[#9aa0a6]">
                                    I accept the{" "}
                                    <a href="#" className="text-[#4285f4] hover:underline">Terms</a>
                                    {" "}and{" "}
                                    <a href="#" className="text-[#4285f4] hover:underline">Privacy Policy</a>
                                </span>
                            </div>
                            <button
                                type="submit"
                                className="w-full bg-[#4285f4] hover:bg-[#5a9cf5] text-white py-4 rounded-xl transition-all hover:-translate-y-0.5 font-medium"
                            >
                                Create Account
                            </button>
                        </form>
                    )}

                    {/* Divider */}
                    <div className="relative my-6">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-[#2d2d2d]" />
                        </div>
                        <div className="relative flex justify-center text-sm">
                            <span className="px-3 bg-[#1a1a1a] text-[#6b6b6b]">Or continue with</span>
                        </div>
                    </div>

                    {/* Social Login - Links to Flask OAuth */}
                    <div className="space-y-3">
                        <a
                            href="/login/github"
                            className="w-full flex items-center justify-center gap-2 bg-[#2d2d2d] hover:bg-[#3d3d3d] border border-[#3d3d3d] hover:border-[#4285f4]/30 rounded-xl py-3 px-4 text-[#e8eaed] transition-all"
                        >
                            <Github className="w-5 h-5" />
                            Continue with GitHub
                        </a>
                        <a
                            href="/login/google"
                            className="w-full flex items-center justify-center gap-2 bg-[#2d2d2d] hover:bg-[#3d3d3d] border border-[#3d3d3d] hover:border-[#4285f4]/30 rounded-xl py-3 px-4 text-[#e8eaed] transition-all"
                        >
                            <Mail className="w-5 h-5" />
                            Continue with Google
                        </a>
                    </div>
                </div>

                {/* Footer */}
                <p className="text-center text-[#6b6b6b] text-sm mt-6">
                    <Link to="/" className="hover:text-white transition-colors">
                        ← Return to the Gates
                    </Link>
                </p>
            </div>
        </div>
    );
};

export default AuthPage;

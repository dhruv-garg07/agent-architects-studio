import { Link } from "react-router-dom";
import { RefreshCw } from "lucide-react";

const ServerErrorPage = () => {
    return (
        <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center px-6 relative overflow-hidden">
            {/* Divine glow - warning */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-gradient-radial from-[#ea4335]/10 via-transparent to-transparent rounded-full blur-3xl" />
            </div>

            <div className="text-center relative z-10">
                {/* 500 Number */}
                <div className="mb-8">
                    <span className="text-[150px] font-bold leading-none bg-gradient-to-b from-[#ea4335]/20 to-transparent bg-clip-text text-transparent">
                        500
                    </span>
                </div>

                <h1 className="text-3xl md:text-4xl font-serif font-bold text-white mb-4">
                    The Sanctuary Requires Rest
                </h1>

                <p className="text-[#9aa0a6] text-lg max-w-md mx-auto mb-8 font-serif italic">
                    Even the divine must pause for reflection.
                    Our systems are gathering strength. Return shortly.
                </p>

                <div className="flex gap-4 justify-center">
                    <button
                        onClick={() => window.location.reload()}
                        className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[#1a1a1a] border border-[#2d2d2d] hover:border-[#4285f4]/30 text-white font-medium transition-all hover:-translate-y-0.5"
                    >
                        <RefreshCw className="w-4 h-4" />
                        Try Again
                    </button>
                    <Link
                        to="/"
                        className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[#4285f4] hover:bg-[#5a9cf5] text-white font-medium transition-all hover:-translate-y-0.5"
                    >
                        Return Home
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default ServerErrorPage;

import { Link } from "react-router-dom";
import { Home } from "lucide-react";

const NotFoundPage = () => {
    return (
        <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center px-6 relative overflow-hidden">
            {/* Divine glow */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-gradient-radial from-[#9b87f5]/10 via-transparent to-transparent rounded-full blur-3xl" />
            </div>

            <div className="text-center relative z-10">
                {/* 404 Number */}
                <div className="mb-8">
                    <span className="text-[150px] font-bold leading-none bg-gradient-to-b from-[#4285f4]/20 to-transparent bg-clip-text text-transparent">
                        404
                    </span>
                </div>

                <h1 className="text-3xl md:text-4xl font-serif font-bold text-white mb-4">
                    This Path Leads Not to Salvation
                </h1>

                <p className="text-[#9aa0a6] text-lg max-w-md mx-auto mb-8 font-serif italic">
                    The page you seek has wandered into the void,
                    lost like a soul without guidance.
                </p>

                <Link
                    to="/"
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[#4285f4] hover:bg-[#5a9cf5] text-white font-medium transition-all hover:-translate-y-0.5"
                >
                    <Home className="w-4 h-4" />
                    Return to the Gates
                </Link>
            </div>
        </div>
    );
};

export default NotFoundPage;

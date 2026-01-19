import { useState, useRef, useEffect } from "react";
import { Volume2, VolumeX } from "lucide-react";

interface AmbientMusicProps {
    src?: string;
    autoPlay?: boolean;
}

const AmbientMusic = ({
    src = "/music/gregorian-chant.mp3",
    autoPlay = false
}: AmbientMusicProps) => {
    const [isMuted, setIsMuted] = useState(true);
    const [isLoaded, setIsLoaded] = useState(false);
    const audioRef = useRef<HTMLAudioElement>(null);

    useEffect(() => {
        if (audioRef.current) {
            audioRef.current.volume = 0.15; // Low volume for ambient feel
        }
    }, []);

    const toggleMute = () => {
        if (audioRef.current) {
            if (isMuted) {
                audioRef.current.play().catch(() => {
                    // Handle autoplay restrictions
                    console.log("Autoplay blocked - user must interact first");
                });
            }
            audioRef.current.muted = !isMuted;
            setIsMuted(!isMuted);
        }
    };

    return (
        <>
            <audio
                ref={audioRef}
                src={src}
                loop
                preload="auto"
                onCanPlay={() => setIsLoaded(true)}
            />

            {isLoaded && (
                <button
                    onClick={toggleMute}
                    className="fixed bottom-6 right-6 z-50 p-3 rounded-full bg-[#1a1a1a]/80 backdrop-blur-sm border border-[#2d2d2d] hover:border-[#4285f4]/30 text-[#9aa0a6] hover:text-white transition-all group"
                    title={isMuted ? "Play divine music" : "Mute music"}
                >
                    {isMuted ? (
                        <VolumeX className="w-5 h-5" />
                    ) : (
                        <Volume2 className="w-5 h-5 text-[#4285f4]" />
                    )}

                    {/* Tooltip */}
                    <span className="absolute bottom-full right-0 mb-2 px-3 py-1.5 rounded-lg bg-[#1a1a1a] border border-[#2d2d2d] text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
                        {isMuted ? "Enable divine ambience" : "Mute music"}
                    </span>
                </button>
            )}
        </>
    );
};

export default AmbientMusic;

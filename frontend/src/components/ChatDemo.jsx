import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, Calculator, HeartPulse, Users, Target, Activity, Bot } from 'lucide-react';

const SCENARIOS = [
  {
    id: 1, title: "Maths", icon: <Calculator size={16} />, color: "bg-blue-600", borderColor: "border-blue-500/50", textColor: "text-blue-400",
    question: "X² + 5X + 6 = 0 wisadanne kohomada?",
    answer: "අපි මෙය සාධක කඩා විසඳමු 🧮:\n(X + 3)(X + 2) = 0\n\nඑවිට,\nX + 3 = 0 හෝ X + 2 = 0 වේ.\nපිළිතුර: X = -3 හෝ X = -2"
  },
  {
    id: 2, title: "Science", icon: <Zap size={16} />, color: "bg-yellow-600", borderColor: "border-yellow-500/50", textColor: "text-yellow-400",
    question: "Science wala 'Jeewa Gola' gana kiyala dennako?",
    answer: "ජීව ගෝලය (Biosphere) 🌍\nපෘථිවිය මත ජීවීන් වාසය කරන කලාපයයි. මෙය ප්‍රධාන කොටස් 3කි:\n\n• වායු ගෝලය (Atmosphere)\n• ජල ගෝලය (Hydrosphere)\n• ශිලා ගෝලය (Lithosphere)"
  },
  {
    id: 3, title: "Health", icon: <HeartPulse size={16} />, color: "bg-red-600", borderColor: "border-red-500/50", textColor: "text-red-400",
    question: "Sathunge anathuru walakwa ganne komada?",
    answer: "සතුන්ගෙන් වන අනතුරු වළක්වා ගැනීම 🏥:\n\n1. ආරක්ෂිත පාවහන් (Boots) පැළඳීම.\n2. රාත්‍රියේ විදුලි පන්දම් භාවිතය.\n3. ගෙවත්ත පිරිසිදුව තබා ගැනීම."
  }
];

const OnlineStats = () => {
    // Start with realistic number
    const [online, setOnline] = useState(421);

    // Slower, realistic update logic (Every 8 seconds)
    useEffect(() => {
        const interval = setInterval(() => {
            setOnline(prev => {
                const change = Math.floor(Math.random() * 11) - 5; // -5 to +5
                return prev + change > 200 ? prev + change : 205;
            });
        }, 8000); 
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="flex flex-row justify-between items-center w-full pt-6 border-t border-white/10 px-2 md:px-0">
            {/* Active Students */}
            <div className="flex flex-col items-center md:items-start">
                <div className="flex items-center gap-1 text-gray-500 text-xs md:text-sm uppercase tracking-wider mb-1">
                    <Users size={14} className="text-blue-500" /> <span className="md:inline">Active</span>
                </div>
                <div className="text-xl md:text-3xl font-bold text-white">10k+</div>
            </div>
            
            {/* Divider */}
            <div className="h-8 w-[1px] bg-white/10 mx-2"></div>

            {/* Accuracy */}
            <div className="flex flex-col items-center md:items-start">
                <div className="flex items-center gap-1 text-gray-500 text-xs md:text-sm uppercase tracking-wider mb-1">
                    <Target size={14} className="text-amber-500" /> Accuracy
                </div>
                <div className="text-xl md:text-3xl font-bold text-white">98%</div>
            </div>

            {/* Divider */}
            <div className="h-8 w-[1px] bg-white/10 mx-2"></div>

            {/* Online Now */}
            <div className="flex flex-col items-center md:items-start">
                <div className="flex items-center gap-1 text-gray-500 text-xs md:text-sm uppercase tracking-wider mb-1">
                    <Activity size={14} className="text-green-500" /> <span className="md:inline">Online</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="text-xl md:text-3xl font-bold text-green-400 tabular-nums min-w-[3ch] text-right md:text-left">
                        {online}
                    </div>
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
                    </span>
                </div>
            </div>
        </div>
    );
};

export default function ChatDemo() {
  const [activeIndex, setActiveIndex] = useState(0);
  const activeScenario = SCENARIOS[activeIndex];

  // Auto-switch Logic (10 seconds)
  useEffect(() => {
    const timer = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % SCENARIOS.length);
    }, 10000); 
    return () => clearInterval(timer);
  }, []);

  return (
    <section className="py-16 md:py-32 bg-[#050505] relative overflow-hidden" id="demo">
      <div className="max-w-7xl mx-auto px-4 md:px-6 grid lg:grid-cols-2 gap-10 lg:gap-20 items-center">
        
        {/* TOP SECTION (MOBILE): HEADLINE & STATS */}
        <div className="space-y-8 z-10 order-1 lg:order-1">
            <div className="text-center lg:text-left">
                <h2 className="text-4xl md:text-6xl font-black text-white mb-4 leading-tight">
                    Master Any Subject <br className="hidden md:block" />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-300 to-yellow-600">
                        In Seconds.
                    </span>
                </h2>
                <p className="text-gray-400 text-base md:text-xl leading-relaxed max-w-md mx-auto lg:mx-0">
                    Your Personal AI Tutor that simplifies O/L theories in Sinhala.
                </p>
            </div>
            {/* STATS ROW (Larger Fonts) */}
            <OnlineStats />
        </div>

        {/* RIGHT SIDE: CHAT UI */}
        <div className="relative flex items-center justify-center order-2 lg:order-2 w-full">
            
            <div className="bg-[#0A0A0A] border border-white/10 rounded-3xl shadow-2xl h-[450px] md:h-[500px] w-full flex flex-col relative z-20 overflow-hidden">
                
                {/* Chat Header */}
                <div className="flex items-center gap-3 border-b border-white/5 p-4 bg-[#0A0A0A]/50 backdrop-blur-md z-10">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-gray-800 to-black border border-white/10 flex items-center justify-center text-amber-500 shadow-lg">
                        <Bot size={18} />
                    </div>
                    <div>
                        <h3 className="text-white font-bold text-base md:text-lg leading-none">My Guru AI</h3>
                        <p className="text-green-500 text-xs flex items-center gap-1 font-medium mt-1">
                            <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span> Online
                        </p>
                    </div>
                </div>

                {/* Chat Content - FIXED CUT OFF ISSUE */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar flex flex-col justify-center">
                    <AnimatePresence mode='wait'>
                        <motion.div
                            key={activeScenario.id}
                            className="space-y-4 w-full"
                        >
                            {/* User Question */}
                            <motion.div 
                                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                transition={{ duration: 0.3 }}
                                className="flex justify-end"
                            >
                                {/* Added break-words and max-w-fit */}
                                <div className="bg-blue-600 text-white px-4 py-3 rounded-2xl rounded-tr-sm shadow-lg text-sm md:text-base break-words max-w-fit">
                                    {activeScenario.question}
                                </div>
                            </motion.div>

                            {/* Bot Answer */}
                            <motion.div 
                                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                transition={{ duration: 0.3, delay: 0.5 }}
                                className="flex justify-start"
                            >
                                {/* Added break-words and corrected widths */}
                                <div className="bg-[#151515] border border-white/10 text-gray-200 px-4 py-3 md:px-6 md:py-5 rounded-2xl rounded-tl-sm shadow-lg w-full md:max-w-[90%]">
                                    <div className={`text-[10px] font-bold mb-2 uppercase tracking-wider ${activeScenario.textColor}`}>
                                        {activeScenario.title} Answer
                                    </div>
                                    {/* whitespace-pre-wrap ensures new lines work, break-words prevents cut off */}
                                    <p className="whitespace-pre-wrap leading-relaxed text-sm md:text-[15px] break-words">
                                        {activeScenario.answer}
                                    </p>
                                </div>
                            </motion.div>
                        </motion.div>
                    </AnimatePresence>
                </div>

                {/* Fake Input */}
                <div className="p-4 bg-[#0A0A0A]/50 backdrop-blur-md z-10">
                    <div className="bg-[#151515] h-12 md:h-14 rounded-full w-full flex items-center px-4 md:px-6 gap-3 opacity-50 border border-white/5">
                        <div className="w-1/2 h-2 bg-white/10 rounded-full"></div>
                    </div>
                </div>
            </div>

            {/* Side Buttons (Desktop Only) */}
            <div className="absolute -right-12 top-1/2 -translate-y-1/2 flex-col gap-4 z-30 hidden lg:flex">
                {SCENARIOS.map((item, index) => (
                    <button
                        key={item.id}
                        onClick={() => setActiveIndex(index)}
                        className={`w-12 h-12 rounded-full flex items-center justify-center border-2 transition-all duration-300 shadow-xl ${
                            activeIndex === index 
                            ? `${item.color} border-white text-white scale-110` 
                            : "bg-[#151515] border-white/10 text-gray-500 hover:border-amber-500 hover:text-white"
                        }`}
                    >
                        {item.icon}
                    </button>
                ))}
            </div>

        </div>
      </div>
    </section>
  );
}
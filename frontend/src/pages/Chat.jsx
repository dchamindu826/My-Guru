import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { 
  Send, Menu, X, Image as ImageIcon, Bot, User, 
  Sparkles, Moon, Sun, ChevronDown, LogOut 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { supabase } from '../lib/supabase'; 

export default function Chat() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [userPlan, setUserPlan] = useState('free');
  
  // --- STATE ---
  const [theme, setTheme] = useState('dark');
  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [showSubjectMenu, setShowSubjectMenu] = useState(false);
  
  // User Preferences
  const [selectedSubject, setSelectedSubject] = useState("Science");
  const [selectedMedium, setSelectedMedium] = useState("Sinhala");
  const [selectedGrade, setSelectedGrade] = useState("O/L");

  // Chat Data
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    {
        id: 1, 
        role: 'ai', 
        content: `ආයුබෝවන් ${user?.displayName || 'පුතේ'}! 👋 \nමම My Guru.\n\nඅද අපි ${selectedSubject} පාඩම පටන් ගමුද? ඔයාගේ ප්‍රශ්නය අහන්න.`, 
        timestamp: new Date()
    }
  ]);
  
  // Credits (Fetch from DB)
  const [credits, setCredits] = useState(3);

  const messagesEndRef = useRef(null);

  // DATA LISTS
  const subjects = ["Science", "Mathematics", "History", "Buddhism", "ICT", "Health", "Sinhala", "English"];

  // SCROLL TO BOTTOM
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // INITIAL LOAD
  useEffect(() => {
    if (user) {
        fetchUserData();
    }
  }, [user]);

  const fetchUserData = async () => {
      const { data } = await supabase.from('profiles').select('plan_type, credits_left').eq('id', user.id).single();
      if(data) {
          setUserPlan(data.plan_type);
          setCredits(data.credits_left);
      }
  };

  // --- SEND MESSAGE LOGIC ---
  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    // 1. Show User Message
    const userMsg = { id: Date.now(), role: 'user', content: input, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
        // 2. Call Python Backend
        const res = await fetch("https://myguru.lumi-automation.com/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id: user.id,
                message: userMsg.content,
                subject: selectedSubject,
                grade: selectedGrade,
                medium: selectedMedium
            })
        });
        const data = await res.json();

        // 3. Handle Response
        if (data.status === "no_credits") {
            setMessages(prev => [...prev, { 
                id: Date.now(), 
                role: 'ai', 
                content: data.answer,
                isSystem: true // Special styling
            }]);
        } else {
            const aiMsg = {
                id: Date.now() + 1,
                role: 'ai',
                content: data.answer,
                image: data.image_url,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, aiMsg]);
            
            // Update Credits
            if (data.credits_left !== undefined) setCredits(data.credits_left);

            // Warning
            if (data.warning) {
                setTimeout(() => {
                    setMessages(prev => [...prev, {
                        id: Date.now() + 99,
                        role: 'ai',
                        content: "🛑 පුතේ මතක් කිරීමක්!\n\nතව ප්‍රශ්න 10යි ඉතුරු. Unlimited Plan එක අරගන්න.",
                        isSystem: true
                    }]);
                }, 1000);
            }
        }
    } catch (e) {
        setMessages(prev => [...prev, { id: Date.now(), role: 'ai', content: "Network Error. Please try again." }]);
    } finally {
        setIsTyping(false);
    }
  };

  return (
    <div className={`flex h-screen font-sans overflow-hidden ${theme === 'dark' ? 'bg-[#050505] text-white' : 'bg-[#FDFDFD] text-gray-900'}`}>
      
      {/* SIDEBAR */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-72 border-r flex flex-col transition-transform duration-300
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        ${theme === 'dark' ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200 shadow-xl'}
      `}>
        <div className="p-6 border-b border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
                <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-amber-400 to-orange-600 flex items-center justify-center font-bold text-black">G</div>
                <span className="font-bold text-xl tracking-tight">My Guru</span>
            </div>
            <button onClick={() => setSidebarOpen(false)} className="md:hidden"><X size={24} /></button>
        </div>

        {/* History */}
        <div className="p-4 space-y-2">
            <p className="text-xs text-gray-500 font-bold uppercase tracking-wider mb-2 px-2">History</p>
            <button className="w-full text-left p-3 rounded-xl hover:bg-white/5 text-sm truncate text-gray-400">
                Science - Newton's Laws...
            </button>
        </div>

        <div className="flex-1"></div>

        {/* User Footer */}
        <div className="p-4 border-t border-white/10 bg-[#080808]">
            <div className="flex items-center gap-3 mb-4">
                <img src={user?.photoURL} alt="User" className="w-10 h-10 rounded-full" />
                <div>
                    <p className="font-bold text-sm truncate">{user?.displayName}</p>
                    <p className="text-xs text-amber-500 font-medium capitalize">{userPlan} Plan</p>
                </div>
            </div>
            {userPlan !== 'genius' && (
                <div className="mb-4 bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
                    <div className="flex justify-between text-xs mb-1 text-amber-500">
                        <span>Daily Credits</span>
                        <span>{credits} left</span>
                    </div>
                    <div className="w-full bg-gray-800 h-1 rounded-full overflow-hidden">
                        <div className="bg-amber-500 h-full" style={{ width: `${(credits/20)*100}%` }}></div>
                    </div>
                </div>
            )}
            <button onClick={() => { logout(); navigate('/'); }} className="w-full py-2 rounded-lg text-xs font-bold flex items-center justify-center gap-2 text-gray-400 hover:bg-white/5 transition">
                <LogOut size={14} /> Log Out
            </button>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 flex flex-col md:ml-72 relative">
        
        {/* HEADER */}
        <div className={`flex items-center justify-between px-4 md:px-6 py-3 border-b backdrop-blur-md z-10 ${
            theme === 'dark' ? 'bg-[#050505]/80 border-white/10' : 'bg-white/80 border-gray-200'
        }`}>
            <div className="flex items-center gap-3">
                <button onClick={() => setSidebarOpen(true)} className="md:hidden"><Menu size={24}/></button>
                
                <div className="relative">
                    <button 
                        onClick={() => setShowSubjectMenu(!showSubjectMenu)}
                        className="flex items-center gap-2 px-4 py-2 rounded-full bg-[#151515] border border-white/10 hover:border-amber-500/50 transition"
                    >
                        <span className="text-amber-500"><Sparkles size={16} fill="currentColor" /></span>
                        <span className="font-bold text-sm">{selectedSubject}</span>
                        <span className="text-xs text-gray-500 border-l border-gray-700 pl-2 ml-1">{selectedGrade}</span>
                        <ChevronDown size={14} className="text-gray-500" />
                    </button>

                    <AnimatePresence>
                        {showSubjectMenu && (
                            <>
                                <div className="fixed inset-0 z-10" onClick={() => setShowSubjectMenu(false)}></div>
                                <motion.div 
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: 10 }}
                                    className="absolute top-full left-0 mt-2 w-56 bg-[#111] border border-white/10 rounded-xl shadow-2xl z-20 overflow-hidden"
                                >
                                    <div className="p-2 grid gap-1 max-h-64 overflow-y-auto custom-scrollbar">
                                        <p className="text-xs text-gray-500 font-bold px-2 py-1">Select Subject</p>
                                        {subjects.map(sub => (
                                            <button 
                                                key={sub}
                                                onClick={() => { setSelectedSubject(sub); setShowSubjectMenu(false); }}
                                                className={`text-left px-3 py-2 rounded-lg text-sm transition ${
                                                    selectedSubject === sub ? 'bg-amber-500 text-black font-bold' : 'text-gray-300 hover:bg-white/5'
                                                }`}
                                            >
                                                {sub}
                                            </button>
                                        ))}
                                    </div>
                                    <div className="border-t border-white/10 p-2 bg-black/20 flex gap-2">
                                        {['Sinhala', 'English'].map(m => (
                                            <button 
                                                key={m}
                                                onClick={() => setSelectedMedium(m)}
                                                className={`flex-1 text-xs py-1.5 rounded-md border ${
                                                    selectedMedium === m ? 'bg-white/10 border-amber-500 text-amber-500' : 'border-transparent text-gray-500 hover:bg-white/5'
                                                }`}
                                            >
                                                {m}
                                            </button>
                                        ))}
                                    </div>
                                </motion.div>
                            </>
                        )}
                    </AnimatePresence>
                </div>
            </div>

            <button 
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                className="p-2 rounded-full hover:bg-white/10 text-gray-400 transition"
            >
                {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
            </button>
        </div>

        {/* CHAT AREA */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
            {messages.map((msg) => (
                <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm ${
                        msg.role === 'ai' 
                        ? 'bg-[#151515] border border-white/10 text-amber-500' 
                        : 'bg-blue-600 text-white'
                    }`}>
                        {msg.role === 'ai' ? <Bot size={16} /> : <User size={16} />}
                    </div>

                    <div className={`max-w-[85%] md:max-w-[70%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                        {msg.isSystem ? (
                            <div className="bg-amber-500/10 border border-amber-500/30 p-4 rounded-xl text-amber-200 text-sm mb-2 shadow-lg">
                                <p className="whitespace-pre-wrap font-medium">{msg.content}</p>
                                <button onClick={() => navigate('/checkout')} className="mt-3 bg-amber-500 text-black text-xs font-bold px-4 py-2 rounded-lg hover:scale-105 transition">
                                    Upgrade to Unlimited 🚀
                                </button>
                            </div>
                        ) : (
                            <div className={`px-5 py-3.5 rounded-2xl text-sm md:text-[15px] leading-relaxed shadow-sm whitespace-pre-wrap ${
                                msg.role === 'user'
                                ? 'bg-blue-600 text-white rounded-tr-sm'
                                : (theme === 'dark' ? 'bg-[#151515] border border-white/10 text-gray-200 rounded-tl-sm' : 'bg-white border border-gray-100 text-gray-800 rounded-tl-sm')
                            }`}>
                                {msg.content}
                                {msg.image && <img src={msg.image} className="mt-3 rounded-lg border border-white/10" />}
                            </div>
                        )}
                    </div>
                </div>
            ))}
            {isTyping && <div className="text-xs text-gray-500 animate-pulse ml-12">My Guru is writing...</div>}
            <div ref={messagesEndRef} />
        </div>

        {/* INPUT AREA */}
        <div className={`p-4 md:p-6 z-20 ${theme === 'dark' ? 'bg-[#050505]' : 'bg-[#FDFDFD]'}`}>
            <div className={`max-w-4xl mx-auto flex items-end gap-2 p-2 rounded-3xl shadow-xl border transition-all ${
                theme === 'dark' ? 'bg-[#111] border-white/10 focus-within:border-amber-500/50' : 'bg-white border-gray-200 focus-within:border-amber-500'
            }`}>
                <button className="p-3 rounded-full hover:bg-white/10 text-gray-400 transition">
                    <ImageIcon size={20} />
                </button>
                <textarea 
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={`Ask anything about ${selectedSubject}...`}
                    className="w-full bg-transparent resize-none focus:outline-none py-3 px-2 text-sm md:text-base text-white placeholder-gray-600"
                    rows="1"
                    style={{ minHeight: '44px' }}
                />
                <button 
                    onClick={handleSend}
                    className="p-3 bg-amber-500 text-black rounded-full hover:scale-105 transition shadow-lg shadow-amber-500/20 mb-1"
                >
                    <Send size={20} />
                </button>
            </div>
            <p className="text-center text-[10px] text-gray-600 mt-2">
                Questions Remaining: {userPlan === 'genius' ? 'Unlimited' : credits}
            </p>
        </div>

      </main>
    </div>
  );
}
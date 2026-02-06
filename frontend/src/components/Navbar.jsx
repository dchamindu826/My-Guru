import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { Menu, X, LogIn, User } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
// IMPORT YOUR LOGO HERE if you have it in assets folder
// import logoImg from '../assets/logo.png'; 

export default function Navbar() {
  const { user, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  // Handle scroll effect for navbar background
  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { name: "Home", path: "/", id: "hero" },
    { name: "Plans", path: "/", id: "pricing" },
    { name: "About Us", path: "/", id: "demo" }, // Changed to demo section for 'About'
  ];

  const handleNavClick = (path, id) => {
    setIsOpen(false);
    if (location.pathname === path && id) {
        // If already on home page, just scroll
        const element = document.getElementById(id);
        if (element) element.scrollIntoView({ behavior: 'smooth' });
    } else {
        // Navigate first (you might need extra logic to scroll after nav)
        navigate(path);
    }
  };

  return (
    <nav className={`fixed top-0 w-full z-50 transition-all duration-300 ${
        scrolled ? 'bg-[#050505]/90 backdrop-blur-xl border-b border-white/10 py-3' : 'bg-transparent py-5'
    }`}>
      <div className="max-w-7xl mx-auto px-6 flex justify-between items-center">
        
        {/* LOGO & ANIMATED NAME */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
          {/* REPLACE src below with your actual logo import eg: src={logoImg} */}
          <img src="https://via.placeholder.com/40?text=MG" alt="My Guru Logo" className="w-10 h-10 rounded-xl" />
          
          <motion.div 
             animate={{ 
                 scale: [1, 1.02, 1],
                 textShadow: ["0 0 0px #fbbf24", "0 0 10px #fbbf24", "0 0 0px #fbbf24"]
             }}
             transition={{ duration: 2, repeat: Infinity }}
             className="flex flex-col"
          >
            <span className="text-2xl font-black text-white tracking-tight leading-none">
                My Guru
            </span>
            <span className="text-[10px] text-amber-500 font-bold tracking-[0.2em] uppercase"></span>
          </motion.div>
        </div>

        {/* DESKTOP MENU */}
        <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
                <button 
                    key={link.name} 
                    onClick={() => handleNavClick(link.path, link.id)} 
                    className="text-sm font-bold text-gray-300 hover:text-amber-500 transition uppercase tracking-wider"
                >
                    {link.name}
                </button>
            ))}
            
            {user ? (
                <button onClick={() => navigate('/profile')} className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-4 py-2 rounded-full transition border border-white/10">
                    <img src={user.photoURL} alt="User" className="w-7 h-7 rounded-full" />
                    <span className="text-sm font-bold text-white">Profile</span>
                </button>
            ) : (
                <button 
                    onClick={loginWithGoogle}
                    className="bg-gradient-to-r from-amber-500 to-yellow-600 text-black px-6 py-2.5 rounded-full font-bold text-sm hover:scale-105 transition flex items-center gap-2 shadow-lg shadow-amber-500/20"
                >
                    <LogIn size={16} /> Login
                </button>
            )}
        </div>

        {/* MOBILE MENU BUTTON */}
        <button onClick={() => setIsOpen(!isOpen)} className="md:hidden text-white p-2 rounded-lg hover:bg-white/10 transition">
            {isOpen ? <X size={28} className="text-amber-500" /> : <Menu size={28} />}
        </button>
      </div>

      {/* NEW CLEAN MOBILE MENU OVERLAY */}
      <AnimatePresence>
        {isOpen && (
            <motion.div 
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.2 }}
                className="md:hidden absolute top-full left-0 w-full bg-[#0A0A0A] border-b border-white/10 shadow-2xl"
            >
                <div className="px-6 py-8 space-y-6 flex flex-col items-center text-center">
                    {navLinks.map((link) => (
                        <button 
                            key={link.name} 
                            onClick={() => handleNavClick(link.path, link.id)} 
                            className="text-2xl font-bold text-white hover:text-amber-500 transition"
                        >
                            {link.name}
                        </button>
                    ))}
                    
                    <div className="w-24 h-[1px] bg-white/10 my-4"></div>

                    {user ? (
                        <button onClick={() => { handleNavClick('/profile'); }} className="flex flex-col items-center gap-3">
                            <img src={user.photoURL} alt="User" className="w-16 h-16 rounded-full border-2 border-amber-500" />
                            <div>
                                <p className="font-bold text-xl text-white">{user.displayName}</p>
                                <p className="text-sm text-amber-500">View Dashboard</p>
                            </div>
                        </button>
                    ) : (
                        <button onClick={() => { loginWithGoogle(); setIsOpen(false); }} className="w-full max-w-xs bg-amber-500 text-black py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2">
                            <LogIn size={20} /> Login with Google
                        </button>
                    )}
                </div>
            </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
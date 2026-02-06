import React from 'react';
import { Globe, Lock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Footer() {
  const navigate = useNavigate();

  return (
    <footer className="bg-black py-12 border-t border-white/5 relative z-10">
      <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-6">
        
        {/* Brand */}
        <div className="text-center md:text-left">
            <div className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-amber-200 to-yellow-600">
                My Guru AI
            </div>
            <p className="text-gray-500 text-xs mt-1">
                The Digital Architect for Education 🇱🇰
            </p>
        </div>

        {/* Copyright */}
        <div className="text-gray-500 text-sm">
            © 2026 Lumi Automation. All rights reserved.
        </div>

        {/* Links */}
        <div className="flex gap-6 items-center">
            <button 
                onClick={() => navigate('/terms')}
                className="text-gray-600 hover:text-white transition flex items-center gap-2 text-sm"
            >
                <Globe size={16} /> Terms
            </button>
            <button 
                onClick={() => navigate('/privacy')}
                className="text-gray-600 hover:text-white transition flex items-center gap-2 text-sm"
            >
                <Lock size={16} /> Privacy
            </button>
        </div>

      </div>
    </footer>
  );
}
import React from 'react';
import Spline from '@splinetool/react-spline';
import { motion } from 'framer-motion';
import { MessageCircle, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Hero() {
  const navigate = useNavigate();

  return (
    // min-h-[85vh] දැම්මාම Full Screen එකට වඩා ටිකක් අඩුවෙන් උස හැදෙනවා. 
    // එතකොට යට කොටස (ChatDemo) ඉක්මනට පේනවා.
    <div className="relative w-full min-h-[85vh] bg-[#050505] overflow-hidden flex items-center justify-center pb-12 md:pb-0">
      
      {/* Background Ambience (Glows) */}
      <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] bg-blue-600/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] bg-amber-500/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 w-full grid lg:grid-cols-2 gap-8 items-center relative z-10 pt-24 lg:pt-0">
        
        {/* LEFT SIDE: 3D ROBOT */}
        <motion.div 
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 1 }}
          className="order-2 lg:order-1 h-[350px] lg:h-[550px] w-full relative flex items-center justify-center"
        >
          {/* Robot Container */}
          <div className="w-full h-full relative z-20 scale-110 lg:scale-125">
             <Spline scene="https://prod.spline.design/LULA0DXPVCfeGcv9/scene.splinecode" />
          </div>
          
          {/* Robot Glow Behind */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] bg-amber-500/20 blur-[80px] rounded-full -z-10" />
        </motion.div>

        {/* RIGHT SIDE: TEXT CONTENT */}
        <motion.div 
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 1, delay: 0.2 }}
          className="order-1 lg:order-2 text-center lg:text-left space-y-6"
        >
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-amber-500/30 bg-amber-500/10 text-amber-500 text-xs font-bold uppercase tracking-wider mx-auto lg:mx-0">
            <Sparkles size={14} />
            <span>AI Powered Education</span>
          </div>

          {/* Main Heading (Single Line) */}
          <h1 className="text-5xl md:text-6xl lg:text-8xl font-black text-white leading-tight tracking-tighter whitespace-nowrap">
            MY <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-orange-600">GURU</span>
          </h1>

          {/* Expanded Description */}
          <div className="text-gray-400 text-base md:text-lg max-w-xl mx-auto lg:mx-0 leading-relaxed space-y-2">
            <p>
              The Digital Architect for your Education. 
              Unlock your full potential with customized learning paths and instant support.
            </p>
            <p className="text-gray-300 font-medium">
              විද්‍යාව, ගණිතය, ඉතිහාසය ඇතුළු ඕනෑම විෂයක් සරල සිංහලෙන්, පියවරෙන් පියවර නිවැරදිව ඉගෙන ගන්න. 
              ඔබේ පෞද්ගලික ගුරුවරයා දැන් ඔබ ළඟම.
            </p>
          </div>

          {/* CTA Button */}
          <div className="pt-4">
            <button 
              onClick={() => navigate('/chat')}
              className="group relative inline-flex items-center justify-center gap-3 bg-white text-black px-8 py-4 rounded-2xl font-bold text-lg hover:scale-105 transition-all duration-300 shadow-[0_0_20px_rgba(255,255,255,0.3)] hover:shadow-[0_0_40px_rgba(255,191,0,0.5)]"
            >
              <span>Ask from Guru</span>
              <MessageCircle className="group-hover:rotate-12 transition-transform" size={24} />
              
              {/* Button Inner Glow */}
              <div className="absolute inset-0 rounded-2xl ring-2 ring-white/50 group-hover:ring-amber-500/50 transition-all" />
            </button>
            <p className="mt-4 text-xs text-gray-500">Free access • No credit card required</p>
          </div>
        </motion.div>

      </div>
      
      {/* Bottom Fade - Reduced Height */}
      <div className="absolute bottom-0 w-full h-20 bg-gradient-to-t from-[#050505] to-transparent z-10"></div>
    </div>
  );
}
import React from 'react';
import { motion } from 'framer-motion';
import { Check, Zap, Star, Crown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext'; // Auth Context එක Import කරගන්න

export default function Pricing() {
  const navigate = useNavigate();
  const { user, loginWithGoogle } = useAuth(); // User ඉන්නවද බලන්න

  // Plan Button Click Logic
  const handlePlanClick = (plan) => {
    if (user) {
        // User ලොග් වෙලා නම්
        if (plan.name === 'Starter') {
            navigate('/chat'); // Free නම් Chat එකට
        } else {
            // Paid නම් විස්තරත් එක්ක Checkout එකට
            navigate('/checkout', { 
                state: { 
                    planName: plan.name, 
                    price: plan.price 
                } 
            });
        }
    } else {
        // User ලොග් වෙලා නැත්නම් Login වෙන්න කියනවා
        loginWithGoogle();
    }
  };

  const plans = [
    { 
        name: "Starter", 
        price: "Free", 
        period: "Forever",
        icon: <Zap size={24} />,
        features: [
            { title: "3 Questions/Day", desc: "Good for quick doubts" },
            { title: "Limited Subjects", desc: "Only core subjects" },
            { title: "Basic Answers", desc: "Short text explanations" }
        ], 
        cta: "Start Free", 
        bg: "bg-[#0F0F0F]", 
        border: "border-white/10" 
    },
    { 
        name: "Scholar", 
        price: "Rs. 499", 
        period: "Per Month",
        icon: <Star size={24} />,
        features: [
            { title: "100 Questions/Day", desc: "Perfect for daily study" },
            { title: "All O/L Subjects", desc: "Science, Maths, History & more" },
            { title: "Past Paper Help", desc: "Analyze previous exams" },
            { title: "Priority Speed", desc: "Faster response time" }
        ], 
        cta: "Get Started", 
        bg: "bg-gradient-to-b from-[#1a1a1a] to-black", 
        border: "border-amber-500", 
        popular: true 
    },
    { 
        name: "Genius", 
        price: "Rs. 990", 
        period: "Per Term",
        icon: <Crown size={24} />,
        features: [
            { title: "Unlimited Access", desc: "No daily limits" },
            { title: "Teacher Support", desc: "Direct WhatsApp Help" },
            { title: "Study Plans", desc: "AI generated schedules" },
            { title: "Voice Mode", desc: "Coming soon feature" }
        ], 
        cta: "Go Unlimited", 
        bg: "bg-[#0F0F0F]", 
        border: "border-purple-500/30" 
    }
  ];

  return (
    <section className="py-32 bg-[#050505]" id="pricing">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-20">
            <h2 className="text-5xl font-black text-white mb-6">Simple Pricing</h2>
            <p className="text-gray-400 text-lg">Invest in your education. Cancel anytime.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
            {plans.map((plan, idx) => (
                <motion.div 
                    key={idx} 
                    whileHover={{ y: -10 }} 
                    className={`p-8 rounded-[2rem] border ${plan.border} ${plan.bg} relative flex flex-col min-h-[600px] transition-shadow duration-300 hover:shadow-2xl hover:shadow-amber-500/10`}
                >
                    {plan.popular && (
                        <div className="absolute -top-5 left-1/2 -translate-x-1/2 bg-amber-500 text-black px-6 py-2 rounded-full text-xs font-black uppercase tracking-widest shadow-lg shadow-amber-500/40">
                            Best Value
                        </div>
                    )}
                    
                    {/* Header */}
                    <div className="mb-8 pb-8 border-b border-white/5">
                        <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mb-6 text-white">
                            {plan.icon}
                        </div>
                        <h3 className="text-2xl font-bold text-white mb-2">{plan.name}</h3>
                        <div className="flex items-baseline gap-2">
                            <span className="text-5xl font-black text-white">{plan.price}</span>
                            <span className="text-gray-500 text-sm font-medium">{plan.period}</span>
                        </div>
                    </div>

                    {/* Features */}
                    <ul className="space-y-6 flex-1">
                        {plan.features.map((feat, i) => (
                            <li key={i} className="flex gap-4">
                                <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-1">
                                    <Check size={14} className="text-green-500" />
                                </div>
                                <div>
                                    <p className="text-gray-200 font-bold text-sm">{feat.title}</p>
                                    <p className="text-gray-500 text-xs mt-0.5">{feat.desc}</p>
                                </div>
                            </li>
                        ))}
                    </ul>

                    {/* Button */}
                    <button 
                        onClick={() => handlePlanClick(plan)}
                        className={`w-full py-5 rounded-2xl font-bold text-sm mt-8 transition-all duration-300 ${
                            plan.popular 
                            ? 'bg-gradient-to-r from-amber-500 to-yellow-600 text-black hover:scale-105 shadow-lg shadow-amber-500/20' 
                            : 'bg-white text-black hover:bg-gray-200'
                        }`}
                    >
                        {plan.cta}
                    </button>
                </motion.div>
            ))}
        </div>
      </div>
    </section>
  );
}
import React, { useState } from 'react';
import { Upload, CheckCircle, Copy, ShieldCheck, CreditCard, Lock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Checkout() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  const handleFileChange = (e) => {
    if (e.target.files[0]) setFile(e.target.files[0]);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => navigate('/profile'), 2000);
  };

  return (
    <div className="min-h-screen bg-[#050505] text-white pt-24 pb-12 px-6">
      <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-16">
        
        {/* LEFT COLUMN: ORDER SUMMARY */}
        <div className="space-y-8">
            <div>
                <h1 className="text-4xl md:text-5xl font-black text-white mb-4">Upgrade to <span className="text-amber-500">Pro</span></h1>
                <p className="text-gray-400 text-lg">Unlock unlimited access to the world's best AI Tutor.</p>
            </div>

            <div className="bg-[#111] border border-white/10 rounded-3xl p-8 space-y-6">
                <div className="flex justify-between items-center border-b border-white/10 pb-6">
                    <div>
                        <p className="text-white font-bold text-xl">Scholar Plan</p>
                        <p className="text-gray-500 text-sm">Monthly Subscription</p>
                    </div>
                    <p className="text-3xl font-bold text-white">Rs. 499</p>
                </div>
                <div className="space-y-3">
                    <div className="flex items-center gap-3 text-gray-300">
                        <CheckCircle size={18} className="text-green-500" /> 100 Questions per day
                    </div>
                    <div className="flex items-center gap-3 text-gray-300">
                        <CheckCircle size={18} className="text-green-500" /> All Subjects Access
                    </div>
                    <div className="flex items-center gap-3 text-gray-300">
                        <CheckCircle size={18} className="text-green-500" /> Priority Support
                    </div>
                </div>
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex items-center gap-3">
                    <ShieldCheck size={24} className="text-amber-500" />
                    <p className="text-xs text-amber-500/80 font-bold uppercase tracking-wide">100% Satisfaction Guarantee</p>
                </div>
            </div>
        </div>

        {/* RIGHT COLUMN: PAYMENT FORM */}
        <div className="bg-[#0F0F0F] border border-white/10 rounded-3xl p-8 lg:p-10 shadow-2xl">
            <div className="flex items-center gap-3 mb-8">
                <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center">
                    <Lock size={18} className="text-amber-500" />
                </div>
                <h2 className="text-xl font-bold">Secure Checkout</h2>
            </div>

            {/* Bank Details */}
            <div className="bg-black border border-white/10 rounded-2xl p-6 mb-8 relative">
                <div className="absolute -top-3 right-4 bg-white text-black text-[10px] font-bold px-2 py-1 rounded">
                    BANK TRANSFER
                </div>
                <div className="flex justify-between items-end mb-4">
                    <div>
                        <p className="text-gray-500 text-xs uppercase font-bold mb-1">Bank</p>
                        <p className="text-white font-bold">Commercial Bank</p>
                    </div>
                    <div className="text-right">
                        <p className="text-gray-500 text-xs uppercase font-bold mb-1">Account No</p>
                        <div className="flex items-center gap-2">
                            <p className="text-amber-500 font-mono font-bold text-xl">8001234567</p>
                            <button onClick={() => navigator.clipboard.writeText('8001234567')} className="hover:text-white text-gray-500">
                                <Copy size={16} />
                            </button>
                        </div>
                    </div>
                </div>
                <p className="text-gray-500 text-xs">Name: <span className="text-gray-300">Lumi Automation</span></p>
            </div>

            {/* Upload Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                    <label className="block text-sm font-bold text-gray-400 mb-2">WhatsApp Number</label>
                    <input 
                        type="tel" 
                        required
                        placeholder="077 123 4567" 
                        className="w-full bg-[#151515] border border-white/10 rounded-xl p-4 text-white focus:border-amber-500 outline-none transition placeholder:text-gray-600 font-mono"
                    />
                </div>

                <div className="border-2 border-dashed border-white/10 rounded-2xl p-8 text-center hover:border-amber-500/50 transition cursor-pointer relative bg-[#151515]">
                    <input 
                        type="file" 
                        accept="image/*"
                        onChange={handleFileChange}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />
                    <div className="flex flex-col items-center gap-2">
                        <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center mb-2">
                            {file ? <CheckCircle className="text-green-500" /> : <Upload className="text-gray-400" />}
                        </div>
                        <p className="font-bold text-white text-sm">{file ? file.name : "Upload Payment Slip"}</p>
                        <p className="text-xs text-gray-500">JPG, PNG or PDF</p>
                    </div>
                </div>

                <button 
                    type="submit" 
                    disabled={!file || submitted}
                    className={`w-full py-5 rounded-xl font-bold text-black transition transform hover:scale-[1.02] flex items-center justify-center gap-2 ${submitted ? 'bg-green-500' : 'bg-gradient-to-r from-amber-500 to-yellow-600'}`}
                >
                    {submitted ? "Processing..." : "Confirm Payment"}
                </button>
            </form>
        </div>

      </div>
    </div>
  );
}
import React, { useState } from 'react';
import { Upload, CheckCircle, Copy, ShieldCheck, Lock, AlertTriangle } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { useAuth } from '../context/AuthContext';

export default function Checkout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  
  // Default values handling
  const planName = location.state?.planName || "Scholar";
  const planPrice = location.state?.price || "Rs. 499";

  const [file, setFile] = useState(null);
  const [whatsapp, setWhatsapp] = useState('');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files[0]) setFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !user) return;

    setLoading(true);
    setMsg(null);

    try {
        console.log("Starting Upload Process...");

        // 1. Slip Image එක Upload කිරීම
        const fileExt = file.name.split('.').pop();
        // File Name එක Unique විදියට හදමු (Folder path එක අයින් කළා simple වෙන්න)
        const fileName = `${user.id}_${Date.now()}.${fileExt}`;

        console.log("Uploading file to bucket 'slips':", fileName);

        const { data: uploadData, error: uploadError } = await supabase.storage
            .from('slips')
            .upload(fileName, file, {
                cacheControl: '3600',
                upsert: false
            });

        if (uploadError) {
            console.error("Storage Error Details:", uploadError);
            throw new Error(`Storage Error: ${uploadError.message}`);
        }

        // 2. Public URL එක ගැනීම
        const { data: { publicUrl } } = supabase.storage
            .from('slips')
            .getPublicUrl(fileName);

        console.log("File Uploaded. URL:", publicUrl);

        // 3. Database එකට Data දැමීම
        const { error: insertError } = await supabase
            .from('payments')
            .insert({
                user_id: user.id,
                amount: parseFloat(planPrice.replace('Rs. ', '').replace(',', '')),
                slip_url: publicUrl,
                status: 'pending',
                package_name: planName,
                whatsapp_number: whatsapp,
                ai_confidence: 0
            });

        if (insertError) {
            console.error("Database Insert Error:", insertError);
            throw new Error(`Database Error: ${insertError.message}`);
        }

        setMsg({ type: 'success', text: 'Slip Uploaded Successfully! Redirecting...' });
        
        // 3 Seconds වලින් Redirect වෙනවා
        setTimeout(() => navigate('/profile'), 3000);

    } catch (error) {
        console.error("Full Error Object:", error);
        setMsg({ type: 'error', text: error.message || 'Upload failed. Please check console.' });
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] text-white pt-24 pb-12 px-6">
      <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-16">
        
        {/* LEFT: Order Summary */}
        <div className="space-y-8">
            <div>
                <h1 className="text-4xl font-black text-white mb-4">Upgrade to <span className="text-amber-500">{planName}</span></h1>
                <p className="text-gray-400">Complete payment to unlock premium features.</p>
            </div>

            <div className="bg-[#111] border border-white/10 rounded-3xl p-8 space-y-6">
                <div className="flex justify-between items-center border-b border-white/10 pb-6">
                    <div>
                        <p className="text-white font-bold text-xl">{planName} Plan</p>
                        <p className="text-gray-500 text-sm">Subscription</p>
                    </div>
                    <p className="text-3xl font-bold text-white">{planPrice}</p>
                </div>
                <div className="space-y-3">
                    <div className="flex items-center gap-3 text-gray-300"><CheckCircle size={18} className="text-green-500" /> Premium AI Access</div>
                    <div className="flex items-center gap-3 text-gray-300"><CheckCircle size={18} className="text-green-500" /> Priority Support</div>
                </div>
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex items-center gap-3">
                    <ShieldCheck size={24} className="text-amber-500" />
                    <p className="text-xs text-amber-500/80 font-bold uppercase tracking-wide">Secure Verification</p>
                </div>
            </div>
        </div>

        {/* RIGHT: Payment Form */}
        <div className="bg-[#0F0F0F] border border-white/10 rounded-3xl p-8 shadow-2xl">
            <div className="flex items-center gap-3 mb-8">
                <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center">
                    <Lock size={18} className="text-amber-500" />
                </div>
                <h2 className="text-xl font-bold">Secure Upload</h2>
            </div>

            {/* Bank Details */}
            <div className="bg-black border border-white/10 rounded-2xl p-6 mb-8 relative">
                <div className="absolute -top-3 right-4 bg-white text-black text-[10px] font-bold px-2 py-1 rounded">BANK TRANSFER</div>
                <div className="mb-4">
                    <p className="text-gray-500 text-xs uppercase font-bold mb-1">Bank</p>
                    <p className="text-white font-bold">Commercial Bank</p>
                </div>
                <div className="flex justify-between items-end">
                    <div>
                        <p className="text-gray-500 text-xs uppercase font-bold mb-1">Account No</p>
                         <p className="text-amber-500 font-mono font-bold text-xl">8001234567</p>
                    </div>
                    <button onClick={() => navigator.clipboard.writeText('8001234567')} className="text-gray-500 hover:text-white"><Copy size={18}/></button>
                </div>
            </div>

            {/* Messages */}
            {msg && (
                <div className={`p-4 rounded-xl mb-6 flex items-center gap-2 ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                    {msg.type === 'error' && <AlertTriangle size={18}/>}
                    {msg.text}
                </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                    <label className="block text-sm font-bold text-gray-400 mb-2">WhatsApp Number</label>
                    <input 
                        type="tel" required
                        value={whatsapp} onChange={(e) => setWhatsapp(e.target.value)}
                        placeholder="077 123 4567" 
                        className="w-full bg-[#151515] border border-white/10 rounded-xl p-4 text-white focus:border-amber-500 outline-none"
                    />
                </div>

                <div className="border-2 border-dashed border-white/10 rounded-2xl p-8 text-center relative bg-[#151515] hover:border-amber-500/50 transition">
                    <input 
                        type="file" accept="image/*" required
                        onChange={handleFileChange}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />
                    <div className="flex flex-col items-center gap-2">
                        <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center mb-2">
                            {file ? <CheckCircle className="text-green-500" /> : <Upload className="text-gray-400" />}
                        </div>
                        <p className="font-bold text-white text-sm">{file ? file.name : "Upload Payment Slip"}</p>
                        <p className="text-xs text-gray-500">Tap to browse</p>
                    </div>
                </div>

                <button 
                    type="submit" disabled={loading}
                    className="w-full py-5 rounded-xl font-bold text-black bg-gradient-to-r from-amber-500 to-yellow-600 hover:scale-[1.02] transition disabled:opacity-50"
                >
                    {loading ? "Uploading..." : "Confirm Payment"}
                </button>
            </form>
        </div>

      </div>
    </div>
  );
}
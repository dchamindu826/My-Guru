import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { Check, X, AlertTriangle, ScanLine, Smartphone, Zap, MessageSquare } from 'lucide-react';
import { supabase } from '../../lib/supabase';

const Orders = () => {
  const [slips, setSlips] = useState([]);
  const [selectedSlip, setSelectedSlip] = useState(null);
  const [smsText, setSmsText] = useState('');
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => { fetchSlips(); }, []);

  const fetchSlips = async () => {
    const { data } = await supabase
      .from('payments')
      .select('*, profiles(full_name)')
      .order('created_at', { ascending: false });
    if (data) setSlips(data);
  };

  const runAiCheck = async () => {
    if (!smsText) return alert("Please paste the Bank SMS first!");
    setAnalyzing(true);
    try {
        const res = await api.post('/verify-slip-ai', {
            payment_id: selectedSlip.id,
            sms_text: smsText
        });
        alert(`AI Analysis: ${res.data.data.is_match ? "MATCHED! ✅" : "MISMATCH! ❌"}`);
        fetchSlips(); // Refresh UI
        setSelectedSlip(null);
        setSmsText('');
    } catch (e) {
        alert("AI Error. Check console.");
        console.error(e);
    } finally {
        setAnalyzing(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-100px)] gap-6 p-4">
      
      {/* 1. Slip List */}
      <div className="w-1/4 bg-neutral-900/80 border border-neutral-800 rounded-2xl overflow-hidden flex flex-col">
        <div className="p-4 bg-neutral-900 border-b border-neutral-800">
            <h2 className="text-white font-bold flex items-center gap-2"><Smartphone size={18} className="text-yellow-500"/> Slips</h2>
        </div>
        <div className="overflow-y-auto flex-1 p-2 space-y-2">
          {slips.map((slip) => (
            <div key={slip.id} onClick={() => setSelectedSlip(slip)}
              className={`p-3 rounded-lg cursor-pointer border ${selectedSlip?.id === slip.id ? 'border-yellow-500 bg-yellow-500/10' : 'border-neutral-800 bg-neutral-900'}`}>
              <div className="flex justify-between"><span className="text-white font-bold">{slip.profiles?.full_name}</span><span className="text-cyan-400">Rs.{slip.amount}</span></div>
              <div className="text-xs text-gray-500 mt-1 uppercase">{slip.status}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 2. Main AI Cockpit */}
      <div className="flex-1 bg-black border border-neutral-800 rounded-2xl p-6 flex gap-6 relative overflow-hidden">
        {selectedSlip ? (
            <>
                {/* Left: Slip Image */}
                <div className="w-1/2 flex flex-col gap-4">
                    <div className="bg-neutral-900 h-full rounded-xl border border-neutral-700 overflow-hidden relative">
                        <img src={selectedSlip.slip_url} className="w-full h-full object-contain" alt="Slip" />
                        {selectedSlip.ai_confidence > 0 && (
                            <div className="absolute top-4 right-4 bg-black/80 text-green-400 px-3 py-1 rounded-full border border-green-500/50 text-sm font-bold shadow-[0_0_15px_rgba(34,197,94,0.4)]">
                                AI Confidence: {selectedSlip.ai_confidence}%
                            </div>
                        )}
                    </div>
                </div>

                {/* Right: SMS Input & AI Controls */}
                <div className="w-1/2 flex flex-col gap-4">
                    
                    {/* SMS Simulator Box */}
                    <div className="bg-neutral-900/50 p-4 rounded-xl border border-neutral-700">
                        <label className="text-gray-400 text-sm mb-2 flex items-center gap-2">
                            <MessageSquare size={16} className="text-cyan-400"/> Paste Bank SMS Here
                        </label>
                        <textarea 
                            className="w-full h-32 bg-black border border-neutral-600 rounded-lg p-3 text-green-400 font-mono text-sm focus:border-cyan-500 outline-none"
                            placeholder="Example: Bank: Sampath | Ref: 123456 | Amount: Rs. 1500.00 Credited..."
                            value={selectedSlip.bank_sms_text || smsText}
                            onChange={(e) => setSmsText(e.target.value)}
                            disabled={!!selectedSlip.bank_sms_text} // SMS already there
                        />
                    </div>

                    {/* AI Results Display */}
                    {selectedSlip.extracted_data && (
                        <div className="bg-green-900/10 border border-green-500/30 p-4 rounded-xl">
                            <h4 className="text-green-400 font-bold mb-2 flex items-center gap-2"><Check size={16}/> AI Match Results</h4>
                            <p className="text-gray-300 text-sm">Reason: {selectedSlip.extracted_data.reason}</p>
                        </div>
                    )}

                    {/* Action Buttons */}
                    <button 
                        onClick={runAiCheck}
                        disabled={analyzing || !!selectedSlip.extracted_data}
                        className={`w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-3 transition-all ${analyzing ? 'bg-gray-700 text-gray-400' : 'bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-[0_0_20px_rgba(6,182,212,0.4)]'}`}
                    >
                        {analyzing ? "AI SCANNING..." : <><Zap size={20} /> RUN AI VERIFICATION</>}
                    </button>

                </div>
            </>
        ) : (
            <div className="m-auto text-center opacity-40">
                <ScanLine size={80} className="mx-auto mb-4 text-cyan-500"/>
                <h2 className="text-2xl font-bold text-white">Select a Slip</h2>
            </div>
        )}
      </div>
    </div>
  );
};

export default Orders;
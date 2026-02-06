import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { supabase } from '../lib/supabase'; // Make sure this path is correct
import { useNavigate } from 'react-router-dom';
import { LogOut, History, MessageCircle, Clock, CheckCircle, XCircle, Loader, User } from 'lucide-react';

export default function Profile() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  const [profileData, setProfileData] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fetch Data from Supabase
  useEffect(() => {
    if (!user) return;

    const fetchData = async () => {
      try {
        // 1. Fetch Profile Details (Credits, Plan)
        const { data: profile, error: profileError } = await supabase
          .from('profiles')
          .select('*')
          .eq('email', user.email)
          .single();

        if (profileError && profileError.code !== 'PGRST116') console.error(profileError);
        setProfileData(profile);

        // 2. Fetch Payment History
        const { data: payments, error: paymentError } = await supabase
          .from('payments')
          .select('*')
          .eq('user_email', user.email)
          .order('submitted_at', { ascending: false });

        if (paymentError) console.error(paymentError);
        setOrders(payments || []);

      } catch (error) {
        console.error("Error loading data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user]);

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  if (loading) {
    return <div className="min-h-screen bg-[#050505] flex items-center justify-center text-amber-500"><Loader className="animate-spin" size={40}/></div>;
  }

  return (
    <div className="min-h-screen bg-[#050505] text-white p-4 md:p-6 pt-24">
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Header Card */}
        <div className="flex flex-col md:flex-row justify-between items-center bg-[#111] p-6 rounded-2xl border border-white/10 gap-4">
            <div className="flex items-center gap-4 w-full md:w-auto">
                <img src={user?.photoURL} alt="Profile" className="w-14 h-14 md:w-16 md:h-16 rounded-full border-2 border-amber-500 object-cover" />
                <div>
                    <h1 className="text-xl md:text-2xl font-bold">{user?.displayName}</h1>
                    <p className="text-gray-400 text-xs md:text-sm">{user?.email}</p>
                </div>
            </div>
            <button onClick={handleLogout} className="w-full md:w-auto flex items-center justify-center gap-2 bg-red-500/10 text-red-400 px-5 py-2 rounded-xl hover:bg-red-500/20 transition text-sm font-bold">
                <LogOut size={18} /> Logout
            </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Plan Card */}
            <div className="bg-[#111] p-6 rounded-2xl border border-white/5 relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition">
                    <User size={60} />
                </div>
                <p className="text-gray-400 text-xs uppercase font-bold tracking-wider mb-2">Current Plan</p>
                <h3 className="text-2xl md:text-3xl font-bold text-amber-500 capitalize">
                    {profileData?.plan_type || 'Free Starter'}
                </h3>
                <p className="text-xs text-gray-500 mt-2">
                    {profileData?.plan_type === 'free' ? 'Upgrade for more features' : 'Active Subscription'}
                </p>
            </div>

            {/* Credits Card */}
            <div className="bg-[#111] p-6 rounded-2xl border border-white/5">
                <p className="text-gray-400 text-xs uppercase font-bold tracking-wider mb-2">Daily Credits</p>
                <div className="flex items-end gap-2">
                    <h3 className="text-3xl font-bold text-white">
                        {profileData ? (profileData.daily_credits_limit - profileData.credits_used) : 3}
                    </h3>
                    <span className="text-gray-500 text-sm mb-1">/ {profileData?.daily_credits_limit || 3} left</span>
                </div>
                <div className="w-full bg-gray-800 h-1.5 rounded-full mt-4 overflow-hidden">
                    <div 
                        className="bg-blue-500 h-full transition-all duration-500" 
                        style={{ width: `${profileData ? ((profileData.daily_credits_limit - profileData.credits_used) / profileData.daily_credits_limit) * 100 : 100}%` }}
                    ></div>
                </div>
            </div>

            {/* Support Card */}
            <a href="https://wa.me/94701234567" target="_blank" rel="noreferrer" className="bg-[#111] p-6 rounded-2xl border border-white/5 hover:border-green-500/50 transition cursor-pointer flex flex-col justify-center items-center text-center">
                <div className="w-12 h-12 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center mb-3">
                    <MessageCircle size={24} />
                </div>
                <h3 className="font-bold text-white">WhatsApp Support</h3>
                <p className="text-xs text-gray-400 mt-1">Get help from a human tutor.</p>
            </a>
        </div>

        {/* Order History */}
        <div className="bg-[#111] rounded-2xl border border-white/10 overflow-hidden">
            <div className="p-6 border-b border-white/10 flex items-center gap-2">
                <History className="text-amber-500" size={20} />
                <h2 className="text-lg font-bold">Payment History</h2>
            </div>
            
            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-white/5 text-gray-400 text-[10px] uppercase tracking-wider">
                        <tr>
                            <th className="p-4 font-medium">Date</th>
                            <th className="p-4 font-medium">Plan</th>
                            <th className="p-4 font-medium">Status</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-sm">
                        {orders.length > 0 ? orders.map((order) => (
                            <tr key={order.id} className="hover:bg-white/5 transition">
                                <td className="p-4 text-gray-300">
                                    {new Date(order.submitted_at).toLocaleDateString()}
                                </td>
                                <td className="p-4 font-bold text-white capitalize">{order.plan_selected}</td>
                                <td className="p-4">
                                    <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide flex items-center gap-1 w-fit
                                        ${order.status === 'approved' ? 'bg-green-500/20 text-green-400' : 
                                          order.status === 'rejected' ? 'bg-red-500/20 text-red-400' : 
                                          'bg-yellow-500/20 text-yellow-400'}`}>
                                        {order.status === 'approved' && <CheckCircle size={12} />}
                                        {order.status === 'rejected' && <XCircle size={12} />}
                                        {order.status === 'pending' && <Clock size={12} />}
                                        {order.status}
                                    </span>
                                </td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="3" className="p-8 text-center text-gray-500 text-sm">
                                    No payment history found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>

      </div>
    </div>
  );
}
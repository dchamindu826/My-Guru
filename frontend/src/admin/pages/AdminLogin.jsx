import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../../lib/supabase';
import { Lock, ShieldCheck } from 'lucide-react';

const AdminLogin = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const { data: { user }, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (authError) throw authError;

      const { data: profile } = await supabase
        .from('profiles')
        .select('role')
        .eq('id', user.id)
        .single();

      if (profile?.role === 'admin') {
        navigate('/admin/dashboard');
      } else {
        await supabase.auth.signOut();
        setError("Admin Access Denied.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4 relative overflow-hidden">
      
      {/* Background Glow Effects */}
      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-yellow-600/20 rounded-full blur-[100px]" />
      <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-yellow-800/20 rounded-full blur-[100px]" />

      <div className="relative z-10 bg-neutral-900/60 backdrop-blur-xl p-8 rounded-2xl shadow-2xl w-full max-w-md border border-yellow-500/20">
        
        {/* Header Icon */}
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-gradient-to-br from-yellow-500/20 to-black rounded-full border border-yellow-500/50 shadow-[0_0_15px_rgba(234,179,8,0.3)]">
            <Lock size={32} className="text-yellow-400" />
          </div>
        </div>

        <h2 className="text-3xl font-bold text-center text-white mb-2 tracking-wide">
          ADMIN <span className="text-yellow-500">PORTAL</span>
        </h2>
        <p className="text-gray-400 text-center text-sm mb-8">Secure Access for MyGuru Management</p>
        
        {error && (
          <div className="bg-red-900/20 border border-red-500/50 text-red-400 p-3 rounded-lg mb-6 text-sm flex items-center justify-center">
            <ShieldCheck size={16} className="mr-2" />
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-6">
          <div className="group">
            <label className="block text-yellow-500/80 text-xs uppercase tracking-wider mb-2 font-semibold">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-black/50 border border-neutral-700 text-white rounded-lg p-3 focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500 focus:outline-none transition-all placeholder-gray-600"
              placeholder="admin@myguru.com"
              required
            />
          </div>
          
          <div className="group">
            <label className="block text-yellow-500/80 text-xs uppercase tracking-wider mb-2 font-semibold">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-black/50 border border-neutral-700 text-white rounded-lg p-3 focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500 focus:outline-none transition-all placeholder-gray-600"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-yellow-600 to-yellow-500 hover:from-yellow-500 hover:to-yellow-400 text-black font-bold py-3 px-4 rounded-lg transition-all transform hover:scale-[1.02] shadow-lg shadow-yellow-500/20 disabled:opacity-50 disabled:cursor-not-allowed mt-4"
          >
            {loading ? 'Authenticating...' : 'ACCESS DASHBOARD'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-neutral-600 text-xs">Protected by Lumi Automation Security</p>
        </div>
      </div>
    </div>
  );
};

export default AdminLogin;
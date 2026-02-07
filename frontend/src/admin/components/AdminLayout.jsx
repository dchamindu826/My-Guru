import React, { useState, useEffect } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, ShoppingCart, Package, Users, LogOut, Menu, X, ChevronRight } from 'lucide-react';
import { supabase } from '../../lib/supabase';

const AdminLayout = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const checkAdmin = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        navigate('/admin/login');
        return;
      }
      
      const { data: profile } = await supabase
        .from('profiles')
        .select('role')
        .eq('id', user.id)
        .single();

      if (profile?.role !== 'admin') {
        navigate('/');
      }
    };
    checkAdmin();
  }, [navigate]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    navigate('/admin/login');
  };

  const menuItems = [
    { path: '/admin/dashboard', name: 'Overview', icon: LayoutDashboard },
    { path: '/admin/orders', name: 'Pending Slips', icon: ShoppingCart },
    { path: '/admin/packages', name: 'Packages', icon: Package },
    { path: '/admin/users', name: 'Students', icon: Users },
  ];

  return (
    <div className="flex h-screen bg-black text-white font-sans selection:bg-yellow-500 selection:text-black">
      
      {/* Sidebar - Black & Gold Theme */}
      <div className={`${isSidebarOpen ? 'w-72' : 'w-20'} bg-neutral-900/50 backdrop-blur-md border-r border-neutral-800 transition-all duration-300 flex flex-col relative`}>
        
        {/* Logo Area */}
        <div className="p-6 flex items-center justify-between border-b border-neutral-800/50">
          <div className={`flex items-center gap-2 ${!isSidebarOpen && 'hidden'}`}>
             <div className="w-3 h-8 bg-yellow-500 rounded-sm"></div>
             <h1 className="font-bold text-xl tracking-wider">MY<span className="text-yellow-500">GURU</span></h1>
          </div>
          <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-2 hover:bg-neutral-800 rounded text-yellow-500">
            {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Menu Items */}
        <nav className="flex-1 p-4 space-y-2 mt-4">
          {menuItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center p-3 rounded-xl transition-all duration-200 group ${
                  isActive 
                  ? 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20' 
                  : 'text-gray-400 hover:bg-neutral-800 hover:text-white'
                }`}
              >
                <item.icon size={22} className={`${isActive ? 'text-yellow-500' : 'text-gray-500 group-hover:text-white'}`} />
                
                {isSidebarOpen && (
                  <div className="flex justify-between w-full items-center ml-3">
                    <span className="font-medium text-sm">{item.name}</span>
                    {isActive && <ChevronRight size={16} />}
                  </div>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Logout Section */}
        <div className="p-4 border-t border-neutral-800">
          <button onClick={handleLogout} className="flex items-center w-full p-3 rounded-xl text-neutral-400 hover:text-red-400 hover:bg-red-500/10 transition-colors">
            <LogOut size={20} />
            <span className={`ml-3 text-sm font-medium ${!isSidebarOpen && 'hidden'}`}>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-auto bg-black p-8 relative">
        {/* Background Gradient for Main Content */}
        <div className="absolute top-0 left-0 w-full h-64 bg-gradient-to-b from-neutral-900 to-black pointer-events-none" />
        
        <div className="relative z-10">
            <Outlet /> 
        </div>
      </div>
    </div>
  );
};

export default AdminLayout;
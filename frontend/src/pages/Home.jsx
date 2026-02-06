import React from 'react';
import Hero from '../components/Hero';
import ChatDemo from '../components/ChatDemo';
import Pricing from '../components/Pricing';
import SupportWidget from '../components/SupportWidget';

export default function Home() {
  return (
    <div className="bg-[#050505] min-h-screen text-white">
      <Hero />
      <ChatDemo />
      <Pricing />
      <SupportWidget />
    </div>
  );
}
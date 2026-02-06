import React from 'react';
export default function Privacy() {
  return (
    <div className="min-h-screen bg-[#050505] text-white p-12 max-w-4xl mx-auto">
      <h1 className="text-4xl font-bold mb-8 text-amber-500">Privacy Policy</h1>
      <p className="mb-4 text-gray-300">Last updated: February 2026</p>
      <div className="space-y-6 text-gray-400">
        <p>1. <strong>Data Collection:</strong> We collect your email and profile picture for login purposes via Google.</p>
        <p>2. <strong>Usage:</strong> Your chat data is processed to provide AI tutoring answers. We do not sell your data.</p>
        <p>3. <strong>Security:</strong> All payments are verified manually or via secure gateways.</p>
      </div>
    </div>
  );
}
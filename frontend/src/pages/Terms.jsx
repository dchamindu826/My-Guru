import React from 'react';
export default function Terms() {
  return (
    <div className="min-h-screen bg-[#050505] text-white p-12 max-w-4xl mx-auto">
      <h1 className="text-4xl font-bold mb-8 text-amber-500">Terms & Conditions</h1>
      <div className="space-y-6 text-gray-400">
        <p>1. <strong>Usage Limit:</strong> Free accounts are limited to 3 questions/day.</p>
        <p>2. <strong>Accuracy:</strong> While My Guru AI strives for accuracy, always verify with your textbooks.</p>
        <p>3. <strong>Refunds:</strong> Payments are non-refundable once the plan is activated.</p>
      </div>
    </div>
  );
}
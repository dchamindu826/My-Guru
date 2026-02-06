import React from 'react';
import { MessageCircle } from 'lucide-react';

export default function SupportWidget() {
  return (
    <a 
      href="https://wa.me/94701234567" // ඔයාගේ නම්බර් එක මෙතනට දාන්න
      target="_blank"
      rel="noopener noreferrer"
      className="fixed bottom-6 right-6 bg-green-500 text-white p-4 rounded-full shadow-lg hover:scale-110 transition z-50 flex items-center gap-2 font-bold"
    >
      <MessageCircle size={24} />
      <span className="hidden md:inline">Support</span>
    </a>
  );
}
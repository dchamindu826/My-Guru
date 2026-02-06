import { createClient } from '@supabase/supabase-js';

// Environment variables වලින් keys ගන්න
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_KEY;

export const supabase = createClient(supabaseUrl, supabaseKey);
'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Loader2,
  Mail,
  Terminal,
  AlertTriangle,
  ArrowLeft,
  Send,
  CheckCircle,
  KeyRound,
  type LucideIcon,
} from 'lucide-react';

// Matrix rain background (smaller scale for auth pages)
function MatrixRainMini() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const chars = 'アイウエオカキクケコサシスセソ01';
    const fontSize = 12;
    const columns = Math.floor(canvas.width / fontSize);
    const drops: number[] = Array(columns).fill(1);

    const draw = () => {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.font = `${fontSize}px monospace`;

      for (let i = 0; i < drops.length; i++) {
        if (Math.random() > 0.97) {
          const text = chars[Math.floor(Math.random() * chars.length)];
          const x = i * fontSize;
          const y = drops[i] * fontSize;

          ctx.fillStyle = `rgba(0, 255, 255, ${Math.random() * 0.3 + 0.05})`;
          ctx.fillText(text, x, y);

          if (y > canvas.height && Math.random() > 0.99) {
            drops[i] = 0;
          }
          drops[i]++;
        }
      }
    };

    const interval = setInterval(draw, 60);
    return () => {
      clearInterval(interval);
      window.removeEventListener('resize', resizeCanvas);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none opacity-20"
      style={{ zIndex: 0 }}
    />
  );
}

// Animated input component
function CyberInput({
  id,
  type,
  value,
  onChange,
  placeholder,
  icon: Icon,
  disabled,
}: {
  id: string;
  type: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder: string;
  icon: LucideIcon;
  disabled?: boolean;
}) {
  const [isFocused, setIsFocused] = useState(false);

  return (
    <div
      className={`
        relative group transition-all duration-300
        ${isFocused ? 'transform scale-[1.02]' : ''}
      `}
    >
      {/* Corner accents */}
      <div className={`absolute -top-px -left-px w-2 h-2 border-t border-l transition-colors duration-300 ${isFocused ? 'border-cyan-400' : 'border-cyan-500/30'}`} />
      <div className={`absolute -top-px -right-px w-2 h-2 border-t border-r transition-colors duration-300 ${isFocused ? 'border-cyan-400' : 'border-cyan-500/30'}`} />
      <div className={`absolute -bottom-px -left-px w-2 h-2 border-b border-l transition-colors duration-300 ${isFocused ? 'border-cyan-400' : 'border-cyan-500/30'}`} />
      <div className={`absolute -bottom-px -right-px w-2 h-2 border-b border-r transition-colors duration-300 ${isFocused ? 'border-cyan-400' : 'border-cyan-500/30'}`} />

      {/* Glow effect */}
      {isFocused && (
        <div className="absolute inset-0 bg-cyan-500/5 animate-pulse" />
      )}

      <div className="relative flex items-center">
        <Icon className={`absolute left-4 w-4 h-4 transition-colors duration-300 ${isFocused ? 'text-cyan-400' : 'text-white/30'}`} />
        <input
          id={id}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          className={`
            w-full pl-12 pr-4 py-4
            bg-black/50 border text-sm font-mono text-white
            placeholder:text-white/20
            focus:outline-none transition-all duration-300
            ${isFocused ? 'border-cyan-400/60 shadow-[0_0_15px_rgba(0,255,255,0.15)]' : 'border-white/10'}
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        />
      </div>
    </div>
  );
}

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [countdown, setCountdown] = useState(0);

  // Countdown timer for resend
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      // Simulate API call - in production, call your backend API
      await new Promise((resolve) => setTimeout(resolve, 1500));

      // For now, always succeed (replace with actual API call)
      setIsSuccess(true);
      setCountdown(60); // 60 second cooldown before resend
    } catch (err: any) {
      setError('SYSTEM ERROR: Unable to process request');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    if (countdown > 0) return;
    setIsLoading(true);

    try {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      setCountdown(60);
    } catch (err) {
      setError('SYSTEM ERROR: Unable to resend');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Background effects */}
      <MatrixRainMini />
      <div className="fixed inset-0 grid-pattern pointer-events-none opacity-30" />
      <div className="fixed inset-0 scan-lines pointer-events-none opacity-50" />

      {/* Header */}
      <header className="relative z-10 border-b border-cyan-500/20">
        <div className="container mx-auto px-4 py-4">
          <Link
            href="/"
            className="inline-flex items-center gap-3 group"
          >
            <ArrowLeft className="w-4 h-4 text-white/40 group-hover:text-cyan-400 transition-colors" />
            <div className="w-8 h-8 bg-black border border-cyan-500 flex items-center justify-center group-hover:border-cyan-400 transition-colors">
              <Terminal className="w-4 h-4 text-cyan-500 group-hover:text-cyan-400" />
            </div>
            <span className="font-mono font-bold text-white group-hover:text-cyan-400 transition-colors">
              AGENTVERSE
            </span>
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 flex items-center justify-center min-h-[calc(100vh-80px)] p-4">
        <div className="w-full max-w-md">
          {/* Card */}
          <div className="relative bg-black/80 border border-cyan-500/30 p-8 backdrop-blur-sm">
            {/* Corner decorations */}
            <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-cyan-500" />
            <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-cyan-500" />
            <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-cyan-500" />
            <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-cyan-500" />

            {!isSuccess ? (
              <>
                {/* Header */}
                <div className="text-center mb-8">
                  <div className="inline-flex items-center gap-2 px-3 py-1 bg-yellow-500/10 border border-yellow-500/30 mb-4">
                    <KeyRound className="w-3 h-3 text-yellow-400" />
                    <span className="text-xs font-mono text-yellow-400 uppercase tracking-wider">
                      Recovery Protocol
                    </span>
                  </div>
                  <h1 className="text-2xl font-mono font-bold text-white mb-2">
                    RESET <span className="text-cyan-400">PASSWORD</span>
                  </h1>
                  <p className="text-sm font-mono text-white/40">
                    Enter your email to receive reset instructions
                  </p>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="space-y-5">
                  {/* Error message */}
                  {error && (
                    <div className="flex items-center gap-3 px-4 py-3 bg-red-500/10 border border-red-500/30 animate-shake">
                      <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
                      <span className="text-sm font-mono text-red-400">{error}</span>
                    </div>
                  )}

                  {/* Email input */}
                  <div className="space-y-2">
                    <label htmlFor="email" className="block text-[10px] font-mono text-white/40 uppercase tracking-wider">
                      Registered Email Address
                    </label>
                    <CyberInput
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="agent@agentverse.io"
                      icon={Mail}
                      disabled={isLoading}
                    />
                  </div>

                  {/* Info message */}
                  <div className="flex items-start gap-3 px-4 py-3 bg-white/5 border border-white/10">
                    <div className="w-4 h-4 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <div className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-pulse" />
                    </div>
                    <p className="text-xs font-mono text-white/50 leading-relaxed">
                      A secure reset link will be transmitted to your registered email. Link expires in 15 minutes.
                    </p>
                  </div>

                  {/* Submit button */}
                  <Button
                    type="submit"
                    disabled={isLoading || !email}
                    className={`
                      w-full py-6 font-mono text-sm
                      bg-gradient-to-r from-cyan-500 to-blue-500 text-black
                      hover:from-cyan-400 hover:to-blue-400
                      disabled:from-white/10 disabled:to-white/10 disabled:text-white/30
                      transition-all duration-300
                      ${!isLoading && email ? 'hover:shadow-[0_0_30px_rgba(0,255,255,0.3)]' : ''}
                    `}
                  >
                    {isLoading ? (
                      <span className="flex items-center justify-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        TRANSMITTING...
                      </span>
                    ) : (
                      <span className="flex items-center justify-center gap-2">
                        <Send className="w-4 h-4" />
                        SEND RESET LINK
                      </span>
                    )}
                  </Button>
                </form>
              </>
            ) : (
              /* Success state */
              <div className="text-center py-4 animate-fade-in">
                <div className="w-20 h-20 border-2 border-green-500 flex items-center justify-center mx-auto mb-6">
                  <CheckCircle className="w-10 h-10 text-green-500" />
                </div>
                <h2 className="text-xl font-mono font-bold text-white mb-2">
                  TRANSMISSION <span className="text-green-400">COMPLETE</span>
                </h2>
                <p className="text-sm font-mono text-white/40 mb-6">
                  Check your inbox for the reset link
                </p>

                {/* Email display */}
                <div className="px-4 py-3 bg-white/5 border border-white/10 mb-6">
                  <div className="flex items-center justify-center gap-2">
                    <Mail className="w-4 h-4 text-cyan-400" />
                    <span className="text-sm font-mono text-cyan-400">{email}</span>
                  </div>
                </div>

                {/* Resend button */}
                <button
                  onClick={handleResend}
                  disabled={countdown > 0 || isLoading}
                  className={`
                    text-sm font-mono transition-colors
                    ${countdown > 0 ? 'text-white/30' : 'text-cyan-400 hover:text-cyan-300'}
                  `}
                >
                  {isLoading ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Resending...
                    </span>
                  ) : countdown > 0 ? (
                    `Resend available in ${countdown}s`
                  ) : (
                    'Resend reset link'
                  )}
                </button>

                {/* Progress bar for countdown */}
                {countdown > 0 && (
                  <div className="mt-4 h-1 bg-white/10 overflow-hidden">
                    <div
                      className="h-full bg-cyan-500 transition-all duration-1000"
                      style={{ width: `${(countdown / 60) * 100}%` }}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Divider */}
            <div className="flex items-center gap-4 my-6">
              <div className="flex-1 h-px bg-gradient-to-r from-transparent to-white/10" />
              <span className="text-[10px] font-mono text-white/20 uppercase">or</span>
              <div className="flex-1 h-px bg-gradient-to-l from-transparent to-white/10" />
            </div>

            {/* Back to login */}
            <div className="text-center">
              <p className="text-sm font-mono text-white/40">
                Remember your credentials?{' '}
                <Link
                  href="/auth/login"
                  className="text-cyan-400 hover:text-cyan-300 transition-colors underline underline-offset-4"
                >
                  Access system
                </Link>
              </p>
            </div>

            {/* Status bar */}
            <div className="mt-8 pt-4 border-t border-white/5">
              <div className="flex items-center justify-between text-[10px] font-mono text-white/20">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                  <span>SECURE CHANNEL</span>
                </div>
                <span>E2E ENCRYPTED</span>
              </div>
            </div>
          </div>

          {/* Bottom text */}
          <p className="text-center text-[10px] font-mono text-white/20 mt-6">
            Need help?{' '}
            <a href="#" className="text-cyan-500/60 hover:text-cyan-400">
              Contact Support
            </a>
          </p>
        </div>
      </main>

      {/* Custom animations */}
      <style jsx>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-5px); }
          75% { transform: translateX(5px); }
        }

        .animate-shake {
          animation: shake 0.3s ease-in-out;
        }

        @keyframes fade-in {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }

        .animate-fade-in {
          animation: fade-in 0.4s ease-out;
        }
      `}</style>
    </div>
  );
}

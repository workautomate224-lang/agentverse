'use client';

import { useState, useEffect, useRef } from 'react';
import { signIn } from 'next-auth/react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Loader2,
  Mail,
  Lock,
  Terminal,
  Eye,
  EyeOff,
  AlertTriangle,
  ArrowLeft,
  Zap,
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
  showPasswordToggle,
  onTogglePassword,
  showPassword,
}: {
  id: string;
  type: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder: string;
  icon: LucideIcon;
  disabled?: boolean;
  showPasswordToggle?: boolean;
  onTogglePassword?: () => void;
  showPassword?: boolean;
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
          type={showPasswordToggle ? (showPassword ? 'text' : 'password') : type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          className={`
            w-full pl-12 pr-${showPasswordToggle ? '12' : '4'} py-4
            bg-black/50 border text-sm font-mono text-white
            placeholder:text-white/20
            focus:outline-none transition-all duration-300
            ${isFocused ? 'border-cyan-400/60 shadow-[0_0_15px_rgba(0,255,255,0.15)]' : 'border-white/10'}
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        />
        {showPasswordToggle && (
          <button
            type="button"
            onClick={onTogglePassword}
            className="absolute right-4 text-white/30 hover:text-cyan-400 transition-colors"
          >
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
    </div>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get('callbackUrl') || '/dashboard';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loginSuccess, setLoginSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const result = await signIn('credentials', {
        email,
        password,
        redirect: false,
      });

      if (result?.error) {
        setError('ACCESS DENIED: Invalid credentials');
      } else {
        setLoginSuccess(true);
        setTimeout(() => {
          router.push(callbackUrl);
          router.refresh();
        }, 1000);
      }
    } catch (err) {
      setError('SYSTEM ERROR: Connection failed');
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
          {/* Login card */}
          <div className="relative bg-black/80 border border-cyan-500/30 p-8 backdrop-blur-sm">
            {/* Corner decorations */}
            <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-cyan-500" />
            <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-cyan-500" />
            <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-cyan-500" />
            <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-cyan-500" />

            {/* Success overlay */}
            {loginSuccess && (
              <div className="absolute inset-0 bg-black/90 flex items-center justify-center z-20 animate-fade-in">
                <div className="text-center">
                  <div className="w-16 h-16 border-2 border-green-500 flex items-center justify-center mx-auto mb-4">
                    <Zap className="w-8 h-8 text-green-500 animate-pulse" />
                  </div>
                  <p className="text-green-400 font-mono text-sm">ACCESS GRANTED</p>
                  <p className="text-white/40 font-mono text-xs mt-2">Redirecting to dashboard...</p>
                </div>
              </div>
            )}

            {/* Header */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-cyan-500/10 border border-cyan-500/30 mb-4">
                <div className="w-2 h-2 bg-cyan-500 rounded-full animate-pulse" />
                <span className="text-xs font-mono text-cyan-400 uppercase tracking-wider">
                  Secure Access
                </span>
              </div>
              <h1 className="text-2xl font-mono font-bold text-white mb-2">
                SYSTEM <span className="text-cyan-400">LOGIN</span>
              </h1>
              <p className="text-sm font-mono text-white/40">
                Enter credentials to access control panel
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
                  Email Address
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

              {/* Password input */}
              <div className="space-y-2">
                <label htmlFor="password" className="block text-[10px] font-mono text-white/40 uppercase tracking-wider">
                  Password
                </label>
                <CyberInput
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter secure password"
                  icon={Lock}
                  disabled={isLoading}
                  showPasswordToggle
                  showPassword={showPassword}
                  onTogglePassword={() => setShowPassword(!showPassword)}
                />
              </div>

              {/* Options row */}
              <div className="flex items-center justify-between text-xs font-mono">
                <label className="flex items-center gap-2 cursor-pointer group">
                  <div className="relative w-4 h-4 border border-white/20 group-hover:border-cyan-500/50 transition-colors">
                    <input type="checkbox" className="sr-only peer" />
                    <div className="absolute inset-0 bg-cyan-500 opacity-0 peer-checked:opacity-100 transition-opacity flex items-center justify-center">
                      <span className="text-black text-[10px]">&#10003;</span>
                    </div>
                  </div>
                  <span className="text-white/40 group-hover:text-white/60 transition-colors">
                    Remember device
                  </span>
                </label>
                <Link
                  href="/auth/forgot-password"
                  className="text-cyan-400/60 hover:text-cyan-400 transition-colors"
                >
                  Forgot password?
                </Link>
              </div>

              {/* Submit button */}
              <Button
                type="submit"
                disabled={isLoading || !email || !password}
                className={`
                  w-full py-6 font-mono text-sm
                  bg-gradient-to-r from-cyan-500 to-blue-500 text-black
                  hover:from-cyan-400 hover:to-blue-400
                  disabled:from-white/10 disabled:to-white/10 disabled:text-white/30
                  transition-all duration-300
                  ${!isLoading && email && password ? 'hover:shadow-[0_0_30px_rgba(0,255,255,0.3)]' : ''}
                `}
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    AUTHENTICATING...
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    <Terminal className="w-4 h-4" />
                    INITIALIZE SESSION
                  </span>
                )}
              </Button>
            </form>

            {/* Divider */}
            <div className="flex items-center gap-4 my-6">
              <div className="flex-1 h-px bg-gradient-to-r from-transparent to-white/10" />
              <span className="text-[10px] font-mono text-white/20 uppercase">or</span>
              <div className="flex-1 h-px bg-gradient-to-l from-transparent to-white/10" />
            </div>

            {/* Register link */}
            <div className="text-center">
              <p className="text-sm font-mono text-white/40">
                New to AgentVerse?{' '}
                <Link
                  href="/auth/register"
                  className="text-cyan-400 hover:text-cyan-300 transition-colors underline underline-offset-4"
                >
                  Create account
                </Link>
              </p>
            </div>

            {/* Status bar */}
            <div className="mt-8 pt-4 border-t border-white/5">
              <div className="flex items-center justify-between text-[10px] font-mono text-white/20">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                  <span>SECURE CONNECTION</span>
                </div>
                <span>TLS 1.3</span>
              </div>
            </div>
          </div>

          {/* Bottom text */}
          <p className="text-center text-[10px] font-mono text-white/20 mt-6">
            By signing in, you agree to our{' '}
            <a href="#" className="text-cyan-500/60 hover:text-cyan-400">Terms</a>
            {' '}and{' '}
            <a href="#" className="text-cyan-500/60 hover:text-cyan-400">Privacy Policy</a>
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
          from { opacity: 0; }
          to { opacity: 1; }
        }

        .animate-fade-in {
          animation: fade-in 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}

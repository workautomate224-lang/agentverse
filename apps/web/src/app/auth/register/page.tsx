'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { signIn } from 'next-auth/react';
import { Button } from '@/components/ui/button';
import {
  Loader2,
  Mail,
  Lock,
  User,
  Building,
  Terminal,
  Eye,
  EyeOff,
  AlertTriangle,
  ArrowLeft,
  Zap,
  Shield,
  Check,
  X,
  type LucideIcon,
} from 'lucide-react';
import api from '@/lib/api';

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
  name,
  type,
  value,
  onChange,
  placeholder,
  icon: Icon,
  disabled,
  required,
  showPasswordToggle,
  onTogglePassword,
  showPassword,
}: {
  id: string;
  name: string;
  type: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder: string;
  icon: LucideIcon;
  disabled?: boolean;
  required?: boolean;
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
          name={name}
          type={showPasswordToggle ? (showPassword ? 'text' : 'password') : type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          required={required}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          className={`
            w-full pl-12 pr-${showPasswordToggle ? '12' : '4'} py-3
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

// Password strength indicator
function PasswordStrength({ password }: { password: string }) {
  const strength = useMemo(() => {
    let score = 0;
    const checks = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /[0-9]/.test(password),
      special: /[^A-Za-z0-9]/.test(password),
    };

    if (checks.length) score++;
    if (checks.uppercase) score++;
    if (checks.lowercase) score++;
    if (checks.number) score++;
    if (checks.special) score++;

    return { score, checks };
  }, [password]);

  if (!password) return null;

  const getStrengthLabel = () => {
    if (strength.score <= 2) return { label: 'WEAK', color: 'text-red-400', barColor: 'bg-red-500' };
    if (strength.score <= 3) return { label: 'FAIR', color: 'text-yellow-400', barColor: 'bg-yellow-500' };
    if (strength.score <= 4) return { label: 'GOOD', color: 'text-blue-400', barColor: 'bg-blue-500' };
    return { label: 'STRONG', color: 'text-green-400', barColor: 'bg-green-500' };
  };

  const strengthInfo = getStrengthLabel();

  return (
    <div className="mt-2 space-y-2">
      {/* Strength bar */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1 bg-white/10 overflow-hidden">
          <div
            className={`h-full ${strengthInfo.barColor} transition-all duration-300`}
            style={{ width: `${(strength.score / 5) * 100}%` }}
          />
        </div>
        <span className={`text-[10px] font-mono ${strengthInfo.color}`}>
          {strengthInfo.label}
        </span>
      </div>

      {/* Requirements */}
      <div className="grid grid-cols-2 gap-1 text-[10px] font-mono">
        <div className={`flex items-center gap-1 ${strength.checks.length ? 'text-green-400' : 'text-white/30'}`}>
          {strength.checks.length ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
          8+ characters
        </div>
        <div className={`flex items-center gap-1 ${strength.checks.uppercase ? 'text-green-400' : 'text-white/30'}`}>
          {strength.checks.uppercase ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
          Uppercase
        </div>
        <div className={`flex items-center gap-1 ${strength.checks.lowercase ? 'text-green-400' : 'text-white/30'}`}>
          {strength.checks.lowercase ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
          Lowercase
        </div>
        <div className={`flex items-center gap-1 ${strength.checks.number ? 'text-green-400' : 'text-white/30'}`}>
          {strength.checks.number ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
          Number
        </div>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  const router = useRouter();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    fullName: '',
    company: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [registerSuccess, setRegisterSuccess] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError('MISMATCH ERROR: Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError('SECURITY REQUIREMENT: Password must be at least 8 characters');
      return;
    }

    if (!agreedToTerms) {
      setError('PROTOCOL REQUIRED: Accept terms to continue');
      return;
    }

    setIsLoading(true);

    try {
      // Register user
      await api.register({
        email: formData.email,
        password: formData.password,
        full_name: formData.fullName || undefined,
        company: formData.company || undefined,
      });

      // Auto sign in after registration
      const result = await signIn('credentials', {
        email: formData.email,
        password: formData.password,
        redirect: false,
      });

      if (result?.error) {
        setError('PARTIAL SUCCESS: Account created. Please sign in manually.');
        setTimeout(() => router.push('/auth/login'), 2000);
      } else {
        setRegisterSuccess(true);
        setTimeout(() => {
          router.push('/dashboard');
          router.refresh();
        }, 1500);
      }
    } catch (err: any) {
      if (err.detail) {
        setError(`REGISTRATION FAILED: ${err.detail}`);
      } else {
        setError('SYSTEM ERROR: Registration failed. Try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Step validation for visual feedback
  useEffect(() => {
    if (formData.email && formData.fullName) {
      setCurrentStep(2);
    }
    if (formData.password && formData.confirmPassword) {
      setCurrentStep(3);
    }
  }, [formData]);

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
      <main className="relative z-10 flex items-center justify-center min-h-[calc(100vh-80px)] p-4 py-8">
        <div className="w-full max-w-md">
          {/* Registration card */}
          <div className="relative bg-black/80 border border-cyan-500/30 p-8 backdrop-blur-sm">
            {/* Corner decorations */}
            <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-cyan-500" />
            <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-cyan-500" />
            <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-cyan-500" />
            <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-cyan-500" />

            {/* Success overlay */}
            {registerSuccess && (
              <div className="absolute inset-0 bg-black/90 flex items-center justify-center z-20 animate-fade-in">
                <div className="text-center">
                  <div className="w-16 h-16 border-2 border-green-500 flex items-center justify-center mx-auto mb-4">
                    <Shield className="w-8 h-8 text-green-500 animate-pulse" />
                  </div>
                  <p className="text-green-400 font-mono text-sm">ACCOUNT CREATED</p>
                  <p className="text-white/40 font-mono text-xs mt-2">Initializing session...</p>
                </div>
              </div>
            )}

            {/* Header */}
            <div className="text-center mb-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-cyan-500/10 border border-cyan-500/30 mb-4">
                <div className="w-2 h-2 bg-cyan-500 rounded-full animate-pulse" />
                <span className="text-xs font-mono text-cyan-400 uppercase tracking-wider">
                  New Agent Registration
                </span>
              </div>
              <h1 className="text-2xl font-mono font-bold text-white mb-2">
                CREATE <span className="text-cyan-400">ACCOUNT</span>
              </h1>
              <p className="text-sm font-mono text-white/40">
                Initialize your agent credentials
              </p>
            </div>

            {/* Progress indicator */}
            <div className="flex items-center justify-center gap-2 mb-6">
              {[1, 2, 3].map((step) => (
                <div
                  key={step}
                  className={`
                    w-8 h-1 transition-all duration-300
                    ${currentStep >= step ? 'bg-cyan-500' : 'bg-white/10'}
                  `}
                />
              ))}
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Error message */}
              {error && (
                <div className="flex items-center gap-3 px-4 py-3 bg-red-500/10 border border-red-500/30 animate-shake">
                  <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
                  <span className="text-sm font-mono text-red-400">{error}</span>
                </div>
              )}

              {/* Email input */}
              <div className="space-y-1.5">
                <label htmlFor="email" className="flex items-center gap-2 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                  Email Address
                  <span className="text-cyan-500">*</span>
                </label>
                <CyberInput
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="agent@agentverse.io"
                  icon={Mail}
                  disabled={isLoading}
                  required
                />
              </div>

              {/* Full Name input */}
              <div className="space-y-1.5">
                <label htmlFor="fullName" className="block text-[10px] font-mono text-white/40 uppercase tracking-wider">
                  Agent Designation
                </label>
                <CyberInput
                  id="fullName"
                  name="fullName"
                  type="text"
                  value={formData.fullName}
                  onChange={handleChange}
                  placeholder="Agent Smith"
                  icon={User}
                  disabled={isLoading}
                />
              </div>

              {/* Company input */}
              <div className="space-y-1.5">
                <label htmlFor="company" className="block text-[10px] font-mono text-white/40 uppercase tracking-wider">
                  Organization
                </label>
                <CyberInput
                  id="company"
                  name="company"
                  type="text"
                  value={formData.company}
                  onChange={handleChange}
                  placeholder="Cyberdyne Systems"
                  icon={Building}
                  disabled={isLoading}
                />
              </div>

              {/* Password input */}
              <div className="space-y-1.5">
                <label htmlFor="password" className="flex items-center gap-2 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                  Security Key
                  <span className="text-cyan-500">*</span>
                </label>
                <CyberInput
                  id="password"
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Enter secure password"
                  icon={Lock}
                  disabled={isLoading}
                  required
                  showPasswordToggle
                  showPassword={showPassword}
                  onTogglePassword={() => setShowPassword(!showPassword)}
                />
                <PasswordStrength password={formData.password} />
              </div>

              {/* Confirm Password input */}
              <div className="space-y-1.5">
                <label htmlFor="confirmPassword" className="flex items-center gap-2 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                  Confirm Security Key
                  <span className="text-cyan-500">*</span>
                </label>
                <CyberInput
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="Verify password"
                  icon={Lock}
                  disabled={isLoading}
                  required
                  showPasswordToggle
                  showPassword={showConfirmPassword}
                  onTogglePassword={() => setShowConfirmPassword(!showConfirmPassword)}
                />
                {formData.confirmPassword && formData.password !== formData.confirmPassword && (
                  <div className="flex items-center gap-1 text-[10px] font-mono text-red-400 mt-1">
                    <X className="w-3 h-3" />
                    Passwords do not match
                  </div>
                )}
                {formData.confirmPassword && formData.password === formData.confirmPassword && (
                  <div className="flex items-center gap-1 text-[10px] font-mono text-green-400 mt-1">
                    <Check className="w-3 h-3" />
                    Passwords match
                  </div>
                )}
              </div>

              {/* Terms checkbox */}
              <div className="pt-2">
                <label className="flex items-start gap-3 cursor-pointer group">
                  <div className="relative w-4 h-4 mt-0.5 border border-white/20 group-hover:border-cyan-500/50 transition-colors flex-shrink-0">
                    <input
                      type="checkbox"
                      checked={agreedToTerms}
                      onChange={(e) => setAgreedToTerms(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="absolute inset-0 bg-cyan-500 opacity-0 peer-checked:opacity-100 transition-opacity flex items-center justify-center">
                      <Check className="w-3 h-3 text-black" />
                    </div>
                  </div>
                  <span className="text-xs font-mono text-white/40 group-hover:text-white/60 transition-colors leading-relaxed">
                    I accept the{' '}
                    <a href="#" className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2">
                      Terms of Service
                    </a>{' '}
                    and{' '}
                    <a href="#" className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2">
                      Privacy Protocol
                    </a>
                  </span>
                </label>
              </div>

              {/* Submit button */}
              <Button
                type="submit"
                disabled={isLoading || !formData.email || !formData.password || !formData.confirmPassword || !agreedToTerms}
                className={`
                  w-full py-6 font-mono text-sm mt-4
                  bg-gradient-to-r from-cyan-500 to-blue-500 text-black
                  hover:from-cyan-400 hover:to-blue-400
                  disabled:from-white/10 disabled:to-white/10 disabled:text-white/30
                  transition-all duration-300
                  ${!isLoading && formData.email && formData.password && agreedToTerms ? 'hover:shadow-[0_0_30px_rgba(0,255,255,0.3)]' : ''}
                `}
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    INITIALIZING ACCOUNT...
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    <Zap className="w-4 h-4" />
                    CREATE AGENT PROFILE
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

            {/* Login link */}
            <div className="text-center">
              <p className="text-sm font-mono text-white/40">
                Already registered?{' '}
                <Link
                  href="/auth/login"
                  className="text-cyan-400 hover:text-cyan-300 transition-colors underline underline-offset-4"
                >
                  Access system
                </Link>
              </p>
            </div>

            {/* Status bar */}
            <div className="mt-6 pt-4 border-t border-white/5">
              <div className="flex items-center justify-between text-[10px] font-mono text-white/20">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                  <span>SECURE CHANNEL</span>
                </div>
                <span>AES-256</span>
              </div>
            </div>
          </div>

          {/* Bottom text */}
          <p className="text-center text-[10px] font-mono text-white/20 mt-6">
            Protected by AgentVerse Security Protocol v2.0
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

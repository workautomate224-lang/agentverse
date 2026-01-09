'use client';

import Link from 'next/link';
import { useEffect, useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import {
  ArrowRight,
  Zap,
  Users,
  BarChart3,
  Target,
  Terminal,
  Cpu,
  Activity,
  Shield,
  Brain,
  ChevronDown
} from 'lucide-react';

// Matrix rain effect component
function MatrixRain() {
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

    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*()アイウエオカキクケコサシスセソ';
    const fontSize = 14;
    const columns = Math.floor(canvas.width / fontSize);
    const drops: number[] = Array(columns).fill(1);

    const draw = () => {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.fillStyle = '#0ff';
      ctx.font = `${fontSize}px monospace`;

      for (let i = 0; i < drops.length; i++) {
        const text = chars[Math.floor(Math.random() * chars.length)];
        const x = i * fontSize;
        const y = drops[i] * fontSize;

        ctx.fillStyle = `rgba(0, 255, 255, ${Math.random() * 0.5 + 0.1})`;
        ctx.fillText(text, x, y);

        if (y > canvas.height && Math.random() > 0.975) {
          drops[i] = 0;
        }
        drops[i]++;
      }
    };

    const interval = setInterval(draw, 50);
    return () => {
      clearInterval(interval);
      window.removeEventListener('resize', resizeCanvas);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none opacity-30"
      style={{ zIndex: 0 }}
    />
  );
}

// Glitch text component
function GlitchText({ children, className = '' }: { children: string; className?: string }) {
  return (
    <span className={`glitch-text ${className}`} data-text={children}>
      {children}
    </span>
  );
}

// Typing animation component
function TypeWriter({ text, speed = 50, className = '' }: { text: string; speed?: number; className?: string }) {
  const [displayed, setDisplayed] = useState('');
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    let i = 0;
    const timer = setInterval(() => {
      if (i < text.length) {
        setDisplayed(text.slice(0, i + 1));
        i++;
      } else {
        clearInterval(timer);
      }
    }, speed);

    const cursorTimer = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500);

    return () => {
      clearInterval(timer);
      clearInterval(cursorTimer);
    };
  }, [text, speed]);

  return (
    <span className={className}>
      {displayed}
      <span className={`${showCursor ? 'opacity-100' : 'opacity-0'} transition-opacity`}>_</span>
    </span>
  );
}

// Cyber card component
function CyberCard({
  icon,
  title,
  description,
  delay = 0
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  delay?: number;
}) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  return (
    <div
      className={`
        group relative bg-black/50 border border-cyan-500/30 p-6
        hover:border-cyan-400/60 transition-all duration-500
        hover:shadow-[0_0_30px_rgba(0,255,255,0.15)]
        transform ${isVisible ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}
        transition-all duration-700
      `}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {/* Corner decorations */}
      <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-cyan-500" />
      <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-cyan-500" />
      <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-cyan-500" />
      <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-cyan-500" />

      {/* Scan line effect */}
      <div className="absolute inset-0 overflow-hidden opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-cyan-500/5 to-transparent animate-scan" />
      </div>

      <div className="relative">
        <div className="mb-4 text-cyan-400 group-hover:text-cyan-300 transition-colors">
          {icon}
        </div>
        <h3 className="text-lg font-mono font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">
          {title}
        </h3>
        <p className="text-sm font-mono text-white/60 leading-relaxed">
          {description}
        </p>
      </div>
    </div>
  );
}

// Stat counter - displays final value immediately (no animation to avoid SSR hydration issues)
function StatCounter({ value, suffix = '', label }: { value: number; suffix?: string; label: string }) {
  return (
    <div className="text-center">
      <div className="text-4xl md:text-5xl font-mono font-bold text-cyan-400 mb-2 animate-pulse">
        {value.toLocaleString()}{suffix}
      </div>
      <div className="text-xs font-mono text-white/40 uppercase tracking-wider">{label}</div>
    </div>
  );
}

export default function HomePage() {
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="relative min-h-screen bg-black text-white overflow-hidden">
      {/* Matrix background */}
      <MatrixRain />

      {/* Grid pattern overlay */}
      <div className="fixed inset-0 grid-pattern pointer-events-none opacity-50" style={{ zIndex: 1 }} />

      {/* Scan lines overlay */}
      <div className="fixed inset-0 scan-lines pointer-events-none" style={{ zIndex: 2 }} />

      {/* Header */}
      <header
        className={`
          fixed top-0 left-0 right-0 z-50 transition-all duration-300
          ${scrollY > 50 ? 'bg-black/90 backdrop-blur-md border-b border-cyan-500/20' : 'bg-transparent'}
        `}
      >
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="relative w-10 h-10 bg-black border-2 border-cyan-500 flex items-center justify-center group-hover:border-cyan-400 transition-colors">
              <Terminal className="w-5 h-5 text-cyan-500 group-hover:text-cyan-400" />
              <div className="absolute inset-0 bg-cyan-500/20 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <div>
              <span className="text-lg font-mono font-bold tracking-tight text-white group-hover:text-cyan-400 transition-colors">
                AGENTVERSE
              </span>
              <span className="text-[10px] font-mono text-cyan-500/60 ml-2">v1.0</span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-8">
            <a
              href="#features"
              className="text-sm font-mono text-white/60 hover:text-cyan-400 transition-colors relative group"
            >
              FEATURES
              <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-cyan-400 group-hover:w-full transition-all duration-300" />
            </a>
            <a
              href="#demo"
              className="text-sm font-mono text-white/60 hover:text-cyan-400 transition-colors relative group"
            >
              DEMO
              <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-cyan-400 group-hover:w-full transition-all duration-300" />
            </a>
            <Link
              href="/dashboard/guide"
              className="text-sm font-mono text-white/60 hover:text-cyan-400 transition-colors relative group"
            >
              DOCS
              <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-cyan-400 group-hover:w-full transition-all duration-300" />
            </Link>
          </nav>

          <div className="flex items-center gap-4">
            <Link href="/auth/login">
              <Button
                variant="ghost"
                className="font-mono text-sm text-white/70 hover:text-cyan-400 hover:bg-cyan-500/10 border border-transparent hover:border-cyan-500/30"
              >
                [LOGIN]
              </Button>
            </Link>
            <Link href="/auth/register">
              <Button className="font-mono text-sm bg-cyan-500 text-black hover:bg-cyan-400 hover:shadow-[0_0_20px_rgba(0,255,255,0.4)] transition-all duration-300">
                INITIALIZE
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center pt-20" style={{ zIndex: 10 }}>
        <div className="container mx-auto px-4 text-center">
          {/* Status indicator */}
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-500/10 border border-cyan-500/30 mb-8 animate-pulse-slow">
            <div className="w-2 h-2 bg-cyan-500 rounded-full animate-pulse" />
            <span className="text-xs font-mono text-cyan-400 uppercase tracking-wider">
              System Online • Neural Networks Active
            </span>
          </div>

          {/* Main heading with glitch effect */}
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-mono font-bold mb-6 leading-tight">
            <GlitchText className="block text-white">SIMULATE</GlitchText>
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500 animate-gradient">
              HUMAN DECISIONS
            </span>
          </h1>

          {/* Subtitle with typing effect */}
          <div className="text-lg md:text-xl font-mono text-white/60 mb-8 h-8">
            <TypeWriter
              text="&gt; Deploy AI agents. Predict outcomes. Shape the future."
              speed={30}
            />
          </div>

          {/* Description */}
          <p className="text-base md:text-lg font-mono text-white/40 mb-12 max-w-2xl mx-auto leading-relaxed">
            Replace expensive surveys with AI-powered simulations.
            Predict customer behavior, election outcomes, and market trends
            with <span className="text-cyan-400">10,000+</span> intelligent agents.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link href="/auth/register">
              <Button
                size="lg"
                className="
                  font-mono text-base bg-gradient-to-r from-cyan-500 to-blue-500
                  text-black hover:from-cyan-400 hover:to-blue-400
                  hover:shadow-[0_0_40px_rgba(0,255,255,0.4)]
                  transition-all duration-500 px-8 py-6
                  border-2 border-cyan-400/50
                "
              >
                <Zap className="mr-2 w-5 h-5" />
                START SIMULATION
              </Button>
            </Link>
            <a href="#demo">
              <Button
                size="lg"
                variant="outline"
                className="
                  font-mono text-base border-2 border-white/20 text-white
                  hover:border-cyan-500/50 hover:bg-cyan-500/10 hover:text-cyan-400
                  transition-all duration-300 px-8 py-6
                "
              >
                <Terminal className="mr-2 w-5 h-5" />
                WATCH DEMO
              </Button>
            </a>
          </div>

          {/* Scroll indicator */}
          <div className="animate-bounce">
            <ChevronDown className="w-8 h-8 text-cyan-500/50 mx-auto" />
          </div>
        </div>

        {/* Floating particles */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          {[...Array(20)].map((_, i) => (
            <div
              key={i}
              className="absolute w-1 h-1 bg-cyan-500 rounded-full animate-float"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                animationDelay: `${Math.random() * 5}s`,
                animationDuration: `${3 + Math.random() * 4}s`,
              }}
            />
          ))}
        </div>
      </section>

      {/* Stats Section */}
      <section className="relative py-20 border-y border-cyan-500/20" style={{ zIndex: 10 }}>
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <StatCounter value={10000} suffix="+" label="AI Agents" />
            <StatCounter value={90} suffix="%" label="Accuracy" />
            <StatCounter value={50} suffix="ms" label="Response Time" />
            <StatCounter value={24} suffix="/7" label="Uptime" />
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="relative py-24" style={{ zIndex: 10 }}>
        <div className="container mx-auto px-4">
          {/* Section header */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 text-xs font-mono text-cyan-400 uppercase tracking-wider mb-4">
              <Cpu className="w-4 h-4" />
              <span>System Capabilities</span>
            </div>
            <h2 className="text-3xl md:text-4xl font-mono font-bold text-white mb-4">
              WHY <span className="text-cyan-400">AGENTVERSE</span>?
            </h2>
            <p className="text-white/40 font-mono max-w-xl mx-auto">
              Advanced simulation engine powered by state-of-the-art neural networks
            </p>
          </div>

          {/* Features grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <CyberCard
              icon={<Users className="w-8 h-8" />}
              title="10,000+ AI AGENTS"
              description="Simulate diverse populations with customizable demographics, psychographics, and behavioral profiles. Each agent thinks independently."
              delay={0}
            />
            <CyberCard
              icon={<Activity className="w-8 h-8" />}
              title="REAL-TIME RESULTS"
              description="Watch agents think and decide live. Get instant insights with interactive dashboards and neural network visualization."
              delay={100}
            />
            <CyberCard
              icon={<Target className="w-8 h-8" />}
              title="90% ACCURACY"
              description="Validated against real-world surveys and elections. Our neural networks learn from millions of data points."
              delay={200}
            />
            <CyberCard
              icon={<Brain className="w-8 h-8" />}
              title="NEURAL REASONING"
              description="Each agent uses advanced LLMs to simulate human thought processes. Understand the 'why' behind every decision."
              delay={300}
            />
            <CyberCard
              icon={<Shield className="w-8 h-8" />}
              title="ENTERPRISE SECURITY"
              description="SOC 2 compliant infrastructure. Your data is encrypted at rest and in transit. Private cloud options available."
              delay={400}
            />
            <CyberCard
              icon={<BarChart3 className="w-8 h-8" />}
              title="PREDICTIVE ANALYTICS"
              description="Forecast trends before they happen. Run multiple scenarios and optimize outcomes with AI-powered insights."
              delay={500}
            />
          </div>
        </div>
      </section>

      {/* Terminal Demo Section */}
      <section id="demo" className="relative py-24 border-y border-cyan-500/20" style={{ zIndex: 10 }}>
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="bg-black/80 border border-cyan-500/30 rounded-none overflow-hidden">
              {/* Terminal header */}
              <div className="flex items-center gap-2 px-4 py-3 bg-cyan-500/10 border-b border-cyan-500/30">
                <div className="w-3 h-3 rounded-full bg-red-500/80" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <div className="w-3 h-3 rounded-full bg-green-500/80" />
                <span className="ml-4 text-xs font-mono text-cyan-400">agentverse@simulation:~</span>
              </div>

              {/* Terminal content */}
              <div className="p-6 font-mono text-sm">
                <div className="text-cyan-400 mb-2">$ agentverse init --agents 1000</div>
                <div className="text-white/60 mb-4">
                  [INFO] Initializing simulation environment...<br />
                  [INFO] Loading neural network models...<br />
                  [INFO] Generating 1000 unique agent personas...<br />
                  <span className="text-green-400">[SUCCESS]</span> Agents ready. Starting simulation...
                </div>
                <div className="text-cyan-400 mb-2">$ agentverse run --scenario &quot;product-launch&quot;</div>
                <div className="text-white/60">
                  [RUNNING] Simulating customer responses...<br />
                  [AGENT-001] &quot;I would definitely try this product...&quot;<br />
                  [AGENT-002] &quot;The price point seems reasonable...&quot;<br />
                  [AGENT-003] &quot;I prefer the competitor&apos;s option...&quot;<br />
                  <span className="text-cyan-400">[PROGRESS]</span> 847/1000 agents processed...
                </div>
                <div className="mt-4 flex items-center gap-2">
                  <span className="text-cyan-400">$</span>
                  <span className="w-2 h-4 bg-cyan-400 animate-pulse" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative py-24" style={{ zIndex: 10 }}>
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-5xl font-mono font-bold text-white mb-6">
            READY TO <span className="text-cyan-400">PREDICT</span> THE FUTURE?
          </h2>
          <p className="text-white/40 font-mono mb-8 max-w-xl mx-auto">
            Start your free trial today. No credit card required.
            Deploy your first simulation in under 5 minutes.
          </p>
          <Link href="/auth/register">
            <Button
              size="lg"
              className="
                font-mono text-base bg-gradient-to-r from-cyan-500 to-blue-500
                text-black hover:from-cyan-400 hover:to-blue-400
                hover:shadow-[0_0_40px_rgba(0,255,255,0.4)]
                transition-all duration-500 px-10 py-6
              "
            >
              <Terminal className="mr-2 w-5 h-5" />
              INITIALIZE SYSTEM
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative border-t border-cyan-500/20 py-12" style={{ zIndex: 10 }}>
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-black border border-cyan-500 flex items-center justify-center">
                <Terminal className="w-4 h-4 text-cyan-500" />
              </div>
              <div>
                <span className="font-mono font-bold text-white">AGENTVERSE</span>
                <p className="text-xs font-mono text-white/30">AI Simulation Engine</p>
              </div>
            </div>

            <div className="flex items-center gap-6 text-xs font-mono text-white/40">
              <a href="#" className="hover:text-cyan-400 transition-colors">Privacy</a>
              <a href="#" className="hover:text-cyan-400 transition-colors">Terms</a>
              <Link href="/dashboard/guide" className="hover:text-cyan-400 transition-colors">Documentation</Link>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono text-white/30">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span>ALL SYSTEMS OPERATIONAL</span>
            </div>
          </div>

          <div className="mt-8 pt-8 border-t border-white/5 text-center">
            <p className="text-xs font-mono text-white/20">
              &copy; {new Date().getFullYear()} AgentVerse. All rights reserved. Built for the future.
            </p>
          </div>
        </div>
      </footer>

      {/* Custom styles */}
      <style jsx>{`
        .glitch-text {
          position: relative;
          display: inline-block;
        }

        .glitch-text::before,
        .glitch-text::after {
          content: attr(data-text);
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
        }

        .glitch-text::before {
          animation: glitch-1 2s infinite linear alternate-reverse;
          clip-path: polygon(0 0, 100% 0, 100% 45%, 0 45%);
          color: #0ff;
        }

        .glitch-text::after {
          animation: glitch-2 2s infinite linear alternate-reverse;
          clip-path: polygon(0 55%, 100% 55%, 100% 100%, 0 100%);
          color: #f0f;
        }

        @keyframes glitch-1 {
          0%, 100% { transform: translate(0); }
          20% { transform: translate(-2px, 2px); }
          40% { transform: translate(-2px, -2px); }
          60% { transform: translate(2px, 2px); }
          80% { transform: translate(2px, -2px); }
        }

        @keyframes glitch-2 {
          0%, 100% { transform: translate(0); }
          20% { transform: translate(2px, -2px); }
          40% { transform: translate(2px, 2px); }
          60% { transform: translate(-2px, -2px); }
          80% { transform: translate(-2px, 2px); }
        }

        @keyframes scan {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100%); }
        }

        .animate-scan {
          animation: scan 2s ease-in-out infinite;
        }

        @keyframes float {
          0%, 100% {
            transform: translateY(0) translateX(0);
            opacity: 0.3;
          }
          50% {
            transform: translateY(-20px) translateX(10px);
            opacity: 0.8;
          }
        }

        .animate-float {
          animation: float 4s ease-in-out infinite;
        }

        .animate-pulse-slow {
          animation: pulse 3s ease-in-out infinite;
        }

        @keyframes gradient {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }

        .animate-gradient {
          background-size: 200% 200%;
          animation: gradient 4s ease infinite;
        }
      `}</style>
    </div>
  );
}

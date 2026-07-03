import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  ExternalLink,
  Database,
  CloudCog,
  BrainCircuit,
  Search,
  Sparkles,
  Droplets,
  Map,
  Wheat,
  Truck,
  MessagesSquare,
  BookOpenText,
  CloudRain,
  Gauge,
  Route,
  ScrollText,
  ShieldCheck,
  Radar,
  Satellite,
  ChevronRight,
} from "lucide-react";
import "../landing.css";
import HeroArt from "../components/landing/HeroArt";
import { Counter, Eyebrow, GlassCard, GradientBlob, Reveal, SectionHeading } from "../components/landing/primitives";

const TECH = [
  "Google Cloud",
  "Vertex AI",
  "BigQuery",
  "Cloud Run",
  "Firebase",
  "Gemini 2.5 Flash",
  "Agent Development Kit",
  "Google Earth Engine",
];

const PROBLEMS = [
  {
    icon: CloudRain,
    title: "Extreme rainfall uncertainty",
    body:
      "El Niño years scramble the monsoon signal — the same district can swing from a delayed onset to a flash-flood week within a single season, and averages hide the swing entirely.",
  },
  {
    icon: Droplets,
    title: "Water resource stress",
    body:
      "Reservoir levels and groundwater tables are tracked in separate systems on separate schedules, so the moment a block crosses into critical supply is often noticed weeks late.",
  },
  {
    icon: Wheat,
    title: "Agricultural losses",
    body:
      "Sowing windows are decided on habit, not on soil moisture trend lines — a wrong call on delay-sowing advisories compounds into yield loss that surfaces only at harvest.",
  },
];

const PIPELINE = [
  { icon: Database, title: "Data Sources", body: "IMD rainfall, Earth Engine soil moisture, reservoir telemetry, MGNREGA records" },
  { icon: CloudCog, title: "BigQuery", body: "District-day panel, harmonised and versioned for reproducible scoring" },
  { icon: Gauge, title: "Risk Model", body: "Composite drought-risk score with days-to-critical-reservoir projection" },
  { icon: Search, title: "Vertex AI Search", body: "Grounds every answer in advisories, SOPs and historical district reports" },
  { icon: BrainCircuit, title: "Gemini Agents", body: "Triage, allocation and farmer-advisory agents reason over the scored data" },
  { icon: Sparkles, title: "Decision Intelligence", body: "Ranked actions, delivered with confidence, reasoning and sources attached" },
];

const FEATURES = [
  { icon: ScrollText, title: "Explainable AI", body: "Every recommendation ships with its confidence, its reasoning chain and the exact records it drew from — nothing is a black box." },
  { icon: Map, title: "District Risk Maps", body: "Live choropleth of drought-risk scores across every district, updated as new signals land." },
  { icon: Droplets, title: "Reservoir Forecasting", body: "Days-to-critical projections per reservoir, so water releases can be timed before a crisis, not during one." },
  { icon: Wheat, title: "Crop Advisory", body: "Soil-moisture-aware sowing guidance, including when to promote millet and other short-duration crops." },
  { icon: Truck, title: "Resource Allocation", body: "Ranks blocks for tanker deployment and MGNREGA activation against real supply constraints." },
  { icon: MessagesSquare, title: "Conversational AI", body: "Administrators and farmers ask questions in plain language and get grounded, sourced answers back." },
  { icon: BookOpenText, title: "RAG Knowledge", body: "Vertex AI Search retrieves the exact advisory or SOP paragraph behind each recommendation." },
  { icon: Radar, title: "Real-time Weather", body: "IMD rainfall and heat signals stream in continuously, keeping every score current to the day." },
];

const AGENTS = [
  {
    name: "Triage Agent",
    role: "Watches every district",
    body: "Continuously re-scores drought risk as new signals arrive and flags the districts that just crossed a threshold, before a human would think to look.",
    tag: "Runs on Gemini 2.5 Flash",
  },
  {
    name: "Allocation Agent",
    role: "Ranks resource decisions",
    body: "Given a fixed budget of tankers or MGNREGA works, produces a ranked deployment plan that maximises coverage of the highest-risk blocks.",
    tag: "Grounded in BigQuery panel",
  },
  {
    name: "Farmer Advisory Agent",
    role: "Talks to the field",
    body: "Answers a farmer's question about sowing timing or water access in their own language, citing the district's current soil-moisture trend.",
    tag: "Served via Vertex AI Search",
  },
];

const ARCHITECTURE = [
  { icon: CloudRain, label: "Data Ingestion" },
  { icon: Database, label: "BigQuery" },
  { icon: Gauge, label: "Risk Model" },
  { icon: Search, label: "Vertex AI Search" },
  { icon: BrainCircuit, label: "Gemini" },
  { icon: Route, label: "Agent Development Kit" },
  { icon: CloudCog, label: "Cloud Run" },
  { icon: ShieldCheck, label: "Cloud Scheduler" },
];

const EXPLAIN = [
  { icon: Gauge, title: "Confidence", body: "A calibrated score, not a false sense of certainty — low-confidence calls are flagged, not hidden." },
  { icon: BrainCircuit, title: "Reasoning", body: "The chain of signals that led to the recommendation, laid out in the order the agent weighed them." },
  { icon: Database, title: "Data Sources", body: "The exact rainfall, reservoir and soil-moisture records behind the number, timestamped." },
  { icon: BookOpenText, title: "Supporting Documents", body: "The advisory or SOP passage retrieved by Vertex AI Search, quoted, not paraphrased." },
];

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing bg-grid min-h-screen w-full overflow-x-hidden bg-[#08111f]">
      <NavBar navigate={navigate} />
      <Hero navigate={navigate} />
      <TrustedTech />
      <Problem />
      <HowItWorks />
      <Features />
      <DashboardPreview navigate={navigate} />
      <Agents />
      <Architecture />
      <ExplainableAI />
      <CTA navigate={navigate} />
      <Footer />
    </div>
  );
}

function NavBar({ navigate }) {
  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-[#08111f]/75 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-[#00c8ff] to-[#00e5a8]">
            <Satellite className="h-4.5 w-4.5 text-[#08111f]" strokeWidth={2.4} />
          </div>
          <span className="font-display text-[15px] font-bold text-white">
            El Niño 2026 <span className="text-white/40">Copilot</span>
          </span>
        </div>
        <nav className="hidden items-center gap-8 text-[13.5px] font-medium text-white/60 md:flex">
          <a href="#how-it-works" className="transition hover:text-white">How it works</a>
          <a href="#features" className="transition hover:text-white">Platform</a>
          <a href="#agents" className="transition hover:text-white">Agents</a>
          <a href="#architecture" className="transition hover:text-white">Architecture</a>
        </nav>
        <button
          onClick={() => navigate("/overview")}
          className="rounded-full bg-white px-4 py-2 text-[13px] font-semibold text-[#08111f] transition hover:bg-white/90"
        >
          Launch Dashboard
        </button>
      </div>
    </header>
  );
}

function Hero({ navigate }) {
  return (
    <section className="relative overflow-hidden px-6 pb-24 pt-16 sm:pt-24">
      <GradientBlob tone="primary" className="-left-32 -top-32 h-[420px] w-[420px]" />
      <GradientBlob tone="secondary" className="-right-40 top-40 h-[380px] w-[380px]" />
      <div className="relative mx-auto grid max-w-7xl items-center gap-16 lg:grid-cols-[1.05fr_0.95fr]">
        <div>
          <Reveal>
            <Eyebrow>
              <Sparkles className="h-3.5 w-3.5" /> Built for the 2026 El Niño season
            </Eyebrow>
          </Reveal>
          <Reveal delay={0.08}>
            <h1 className="mt-6 text-[42px] font-extrabold leading-[1.08] text-white sm:text-[56px] lg:text-[60px]">
              AI decision intelligence for{" "}
              <span className="text-gradient">India's climate resilience</span>
            </h1>
          </Reveal>
          <Reveal delay={0.16}>
            <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-white/60 sm:text-[18px]">
              Prepare for the 2026 El Niño crisis with explainable, AI-powered
              recommendations for district administrators and farmers — every
              call backed by its data, its reasoning, and its confidence.
            </p>
          </Reveal>
          <Reveal delay={0.24}>
            <div className="mt-9 flex flex-wrap items-center gap-4">
              <button
                onClick={() => navigate("/overview")}
                className="group inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#00c8ff] to-[#00e5a8] px-6 py-3.5 text-[15px] font-semibold text-[#08111f] shadow-[0_0_30px_rgba(0,200,255,0.35)] transition-transform hover:scale-[1.03] active:scale-[0.98]"
              >
                Launch Dashboard
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </button>
              <a
                href="#architecture"
                className="inline-flex items-center gap-2 rounded-full border border-white/15 px-6 py-3.5 text-[15px] font-semibold text-white/85 transition hover:border-white/30 hover:bg-white/5"
              >
                View Architecture
              </a>
            </div>
          </Reveal>
          <Reveal delay={0.32}>
            <div className="mt-14 grid max-w-md grid-cols-3 gap-6 border-t border-white/[0.08] pt-8">
              <Stat value={29} suffix="" label="States &amp; UTs modelled" />
              <Stat value={70} suffix="+" label="Risk signals fused" />
              <Stat value={24} suffix="/7" label="Live scoring" />
            </div>
          </Reveal>
        </div>

        <Reveal delay={0.15} y={16}>
          <HeroArt />
        </Reveal>
      </div>
    </section>
  );
}

function Stat({ value, suffix, label }) {
  return (
    <div>
      <div className="font-display text-[26px] font-bold text-white">
        <Counter to={value} suffix={suffix} />
      </div>
      <div className="mt-1 text-[12.5px] leading-snug text-white/45">{label}</div>
    </div>
  );
}

function TrustedTech() {
  return (
    <section className="border-y border-white/[0.06] bg-white/[0.015] px-6 py-10">
      <div className="mx-auto max-w-7xl">
        <p className="text-center text-[11px] font-semibold uppercase tracking-[0.18em] text-white/35">
          Engineered on
        </p>
        <div className="mask-fade-x mt-6 flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
          {TECH.map((t) => (
            <span key={t} className="text-[14px] font-medium text-white/50 transition hover:text-white/90">
              {t}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function Problem() {
  return (
    <section className="px-6 py-28">
      <div className="mx-auto grid max-w-7xl items-center gap-16 lg:grid-cols-2">
        <Reveal>
          <div className="relative aspect-[4/3] w-full">
            <div className="absolute inset-0 rounded-3xl border border-white/[0.08] bg-[radial-gradient(circle_at_30%_20%,rgba(0,200,255,0.14),transparent_55%)]" />
            <svg viewBox="0 0 400 300" className="relative h-full w-full">
              <defs>
                <linearGradient id="problemLine" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#00c8ff" />
                  <stop offset="100%" stopColor="#ffc857" />
                </linearGradient>
              </defs>
              <polyline
                points="10,220 60,180 100,210 140,120 180,160 220,70 260,110 300,50 340,90 390,30"
                fill="none"
                stroke="url(#problemLine)"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              {[[10,220],[100,210],[180,160],[260,110],[340,90]].map(([x,y],i)=>(
                <circle key={i} cx={x} cy={y} r="5" fill="#08111f" stroke="#00c8ff" strokeWidth="2" />
              ))}
              <text x="10" y="250" fill="#ffffff55" fontSize="11">2020</text>
              <text x="340" y="250" fill="#ffffff55" fontSize="11">2026</text>
              <text x="150" y="270" fill="#ffffff88" fontSize="12">Rainfall volatility index, sample district</text>
            </svg>
          </div>
        </Reveal>
        <div>
          <Reveal>
            <Eyebrow>The problem</Eyebrow>
            <h2 className="mt-5 text-[32px] font-bold leading-[1.15] text-white sm:text-[38px]">
              Climate risk in India moves faster than the systems built to track it
            </h2>
          </Reveal>
          <div className="mt-10 space-y-5">
            {PROBLEMS.map((p, i) => (
              <Reveal key={p.title} delay={i * 0.08}>
                <GlassCard className="p-6">
                  <div className="flex gap-4">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[#00c8ff]/20 to-[#00e5a8]/20">
                      <p.icon className="h-5 w-5 text-[#00c8ff]" strokeWidth={1.8} />
                    </div>
                    <div>
                      <h3 className="text-[16px] font-semibold text-white">{p.title}</h3>
                      <p className="mt-1.5 text-[14.5px] leading-relaxed text-white/55">{p.body}</p>
                    </div>
                  </div>
                </GlassCard>
              </Reveal>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  return (
    <section id="how-it-works" className="relative px-6 py-28">
      <SectionHeading
        eyebrow="How it works"
        title="From raw signal to a decision, on one pipeline"
        description="Six stages turn scattered climate data into a ranked, sourced recommendation — automatically, every time new signal lands."
      />
      <div className="relative mx-auto mt-16 max-w-6xl">
        <div className="pointer-events-none absolute left-1/2 top-0 hidden h-full w-px -translate-x-1/2 bg-gradient-to-b from-transparent via-white/15 to-transparent lg:block" />
        <div className="grid gap-5 lg:grid-cols-3">
          {PIPELINE.map((step, i) => (
            <Reveal key={step.title} delay={i * 0.07}>
              <div className="relative">
                <GlassCard className="h-full p-6" glow>
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 bg-white/5">
                      <step.icon className="h-4.5 w-4.5 text-[#00e5a8]" strokeWidth={1.8} />
                    </div>
                    <span className="font-mono text-[11px] text-white/35">0{i + 1}</span>
                  </div>
                  <h3 className="mt-4 text-[16px] font-semibold text-white">{step.title}</h3>
                  <p className="mt-1.5 text-[14px] leading-relaxed text-white/55">{step.body}</p>
                </GlassCard>
                {i < PIPELINE.length - 1 && (
                  <ChevronRight className="absolute -right-3 top-1/2 hidden h-6 w-6 -translate-y-1/2 text-white/20 lg:block" />
                )}
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function Features() {
  return (
    <section id="features" className="border-y border-white/[0.06] bg-white/[0.015] px-6 py-28">
      <SectionHeading
        eyebrow="Platform"
        title="Everything a decision maker needs, nothing they don't"
        description="One console for the district administrator's morning briefing and the farmer's field question."
      />
      <div className="mx-auto mt-16 grid max-w-7xl grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((f, i) => (
          <Reveal key={f.title} delay={(i % 4) * 0.06}>
            <GlassCard className="h-full p-6" glow>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-[#00c8ff]/15 to-[#00e5a8]/15 transition group-hover:from-[#00c8ff]/25 group-hover:to-[#00e5a8]/25">
                <f.icon className="h-5 w-5 text-[#00c8ff]" strokeWidth={1.8} />
              </div>
              <h3 className="mt-4 text-[15.5px] font-semibold text-white">{f.title}</h3>
              <p className="mt-1.5 text-[13.5px] leading-relaxed text-white/55">{f.body}</p>
            </GlassCard>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function DashboardPreview({ navigate }) {
  return (
    <section className="relative overflow-hidden px-6 py-28">
      <GradientBlob tone="primary" className="left-1/2 top-0 h-[500px] w-[700px] -translate-x-1/2 opacity-[0.12]" />
      <SectionHeading
        eyebrow="Inside the console"
        title="A live risk picture, not a quarterly report"
        description="District scores, reservoir countdowns and the AI Copilot, all on one screen."
      />
      <Reveal delay={0.1}>
        <div className="relative mx-auto mt-16 max-w-5xl">
          <div className="glass relative overflow-hidden rounded-2xl p-3 shadow-[0_40px_100px_-30px_rgba(0,0,0,0.7)] sm:p-4">
            <div className="flex items-center gap-1.5 border-b border-white/[0.06] px-2 pb-3">
              <span className="h-2.5 w-2.5 rounded-full bg-[#ff6a6a]/60" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#ffc857]/60" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#00e5a8]/60" />
              <span className="ml-3 font-mono text-[11px] text-white/35">copilot.climate-resilience.in/overview</span>
            </div>
            <div className="grid gap-3 p-3 sm:grid-cols-[1.3fr_1fr] sm:p-4">
              <div className="rounded-xl border border-white/[0.06] bg-[#0c1626] p-4">
                <div className="flex items-center justify-between text-[12px] text-white/45">
                  <span>District risk map</span>
                  <span className="flex items-center gap-1 text-[#00e5a8]"><span className="h-1.5 w-1.5 rounded-full bg-[#00e5a8] animate-pulse-soft" /> live</span>
                </div>
                <div className="mt-3 grid grid-cols-8 gap-1.5">
                  {Array.from({ length: 48 }).map((_, i) => {
                    const seed = (i * 37) % 100;
                    const color = seed > 70 ? "#ff6a6a" : seed > 45 ? "#ffc857" : seed > 20 ? "#00c8ff" : "#00e5a8";
                    return <div key={i} className="aspect-square rounded-[3px]" style={{ background: color, opacity: 0.35 + (seed % 40) / 100 }} />;
                  })}
                </div>
              </div>
              <div className="flex flex-col gap-3">
                <div className="rounded-xl border border-white/[0.06] bg-[#0c1626] p-4">
                  <p className="text-[12px] text-white/45">Days to critical reservoir</p>
                  <p className="mt-1 font-display text-[26px] font-bold text-[#ffc857]">62</p>
                  <p className="mt-1 text-[11px] text-white/35">Marathwada cluster</p>
                </div>
                <div className="flex-1 rounded-xl border border-white/[0.06] bg-[#0c1626] p-4">
                  <div className="flex items-center gap-2 text-[12px] text-white/45">
                    <MessagesSquare className="h-3.5 w-3.5 text-[#00c8ff]" /> AI Copilot
                  </div>
                  <p className="mt-2 text-[12.5px] leading-relaxed text-white/70">
                    "Delay sowing by 8–10 days in Beed — soil moisture is 31%, trending down. Confidence: high."
                  </p>
                </div>
              </div>
            </div>
          </div>
          <button
            onClick={() => navigate("/overview")}
            className="mx-auto mt-8 flex items-center gap-2 text-[14px] font-semibold text-[#00c8ff] transition hover:text-[#7fe6ff]"
          >
            Open the live dashboard <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </Reveal>
    </section>
  );
}

function Agents() {
  return (
    <section id="agents" className="border-y border-white/[0.06] bg-white/[0.015] px-6 py-28">
      <SectionHeading
        eyebrow="AI agents"
        title="Three agents, one shared picture of risk"
        description="Each agent reasons over the same scored data, specialised for who needs the answer."
      />
      <div className="mx-auto mt-16 grid max-w-6xl gap-6 lg:grid-cols-3">
        {AGENTS.map((a, i) => (
          <Reveal key={a.name} delay={i * 0.1}>
            <div className="group relative rounded-2xl p-[1px]">
              <div className="animate-spin-slow absolute inset-0 rounded-2xl bg-[conic-gradient(from_0deg,#00c8ff,#00e5a8,#ffc857,#00c8ff)] opacity-40 transition-opacity group-hover:opacity-90" />
              <div className="relative rounded-2xl bg-[#0d1830] p-7">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7fe6ff]">{a.role}</p>
                <h3 className="mt-2 font-display text-[20px] font-bold text-white">{a.name}</h3>
                <p className="mt-3 text-[14px] leading-relaxed text-white/55">{a.body}</p>
                <p className="mt-5 font-mono text-[11px] text-white/35">{a.tag}</p>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function Architecture() {
  return (
    <section id="architecture" className="px-6 py-28">
      <SectionHeading
        eyebrow="Architecture"
        title="A production Google Cloud stack, end to end"
        description="Every stage is a managed service — no bespoke infrastructure to babysit during a crisis."
      />
      <Reveal delay={0.1}>
        <div className="mx-auto mt-16 max-w-5xl">
          <div className="glass relative rounded-2xl p-8 sm:p-10">
            <div className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-4">
              {ARCHITECTURE.map((n, i) => (
                <div key={n.label} className="relative flex flex-col items-center text-center">
                  {i < ARCHITECTURE.length - 1 && i % 4 !== 3 && (
                    <div className="absolute left-[calc(50%+28px)] top-6 hidden h-px w-[calc(100%-32px)] overflow-hidden sm:block">
                      <div className="h-full w-full bg-gradient-to-r from-[#00c8ff]/50 to-transparent" />
                    </div>
                  )}
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-[#0c1626] shadow-[0_0_20px_rgba(0,200,255,0.12)]">
                    <n.icon className="h-5 w-5 text-[#00c8ff]" strokeWidth={1.8} />
                  </div>
                  <p className="mt-3 text-[12.5px] font-medium text-white/70">{n.label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Reveal>
    </section>
  );
}

function ExplainableAI() {
  return (
    <section className="border-y border-white/[0.06] bg-white/[0.015] px-6 py-28">
      <SectionHeading
        eyebrow="Why explainable AI"
        title="A recommendation you can act on is one you can question"
        description="Every output carries the four things a district officer needs to defend a decision."
      />
      <div className="mx-auto mt-16 max-w-4xl">
        <div className="space-y-4">
          {EXPLAIN.map((e, i) => (
            <Reveal key={e.title} delay={i * 0.08}>
              <div className="flex gap-5 rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6 transition hover:bg-white/[0.04]">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[#00c8ff]/15 to-[#ffc857]/15">
                  <e.icon className="h-5 w-5 text-[#ffc857]" strokeWidth={1.8} />
                </div>
                <div>
                  <h3 className="text-[16px] font-semibold text-white">{e.title}</h3>
                  <p className="mt-1.5 text-[14.5px] leading-relaxed text-white/55">{e.body}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function CTA({ navigate }) {
  return (
    <section className="relative overflow-hidden px-6 py-28">
      <div className="absolute inset-0 bg-gradient-to-br from-[#00c8ff]/15 via-[#08111f] to-[#00e5a8]/10" />
      <GradientBlob tone="accent" className="left-1/2 top-1/2 h-[400px] w-[600px] -translate-x-1/2 -translate-y-1/2 opacity-20" />
      <Reveal className="relative mx-auto max-w-3xl text-center">
        <h2 className="text-[34px] font-bold leading-[1.15] text-white sm:text-[44px]">
          Ready to build climate resilience?
        </h2>
        <p className="mx-auto mt-5 max-w-xl text-[16px] leading-relaxed text-white/60">
          Put explainable AI in front of the people who make water and crop
          decisions this monsoon season.
        </p>
        <div className="mt-9 flex flex-wrap items-center justify-center gap-4">
          <button
            onClick={() => navigate("/overview")}
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#00c8ff] to-[#00e5a8] px-7 py-3.5 text-[15px] font-semibold text-[#08111f] shadow-[0_0_30px_rgba(0,200,255,0.35)] transition-transform hover:scale-[1.03]"
          >
            Launch Dashboard <ArrowRight className="h-4 w-4" />
          </button>
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-full border border-white/15 px-7 py-3.5 text-[15px] font-semibold text-white/85 transition hover:border-white/30 hover:bg-white/5"
          >
            <ExternalLink className="h-4 w-4" /> View GitHub
          </a>
        </div>
      </Reveal>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-white/[0.06] px-6 py-12">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-6 sm:flex-row">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-[#00c8ff] to-[#00e5a8]">
              <Satellite className="h-4 w-4 text-[#08111f]" strokeWidth={2.4} />
            </div>
            <span className="text-[14px] font-semibold text-white">El Niño 2026 Decision Copilot</span>
          </div>
          <p className="mt-2 text-[12.5px] text-white/40">
            Built for Google Gen AI Academy APAC · MIT License
          </p>
        </div>
        <div className="flex items-center gap-6 text-[13px] text-white/50">
          <span className="rounded-full border border-white/10 px-3 py-1.5 text-[11.5px] font-medium">
            Powered by Google Cloud
          </span>
          <a href="https://github.com" target="_blank" rel="noreferrer" className="flex items-center gap-1.5 transition hover:text-white">
            <ExternalLink className="h-3.5 w-3.5" /> GitHub
          </a>
          <a href="#how-it-works" className="transition hover:text-white">Documentation</a>
        </div>
      </div>
    </footer>
  );
}

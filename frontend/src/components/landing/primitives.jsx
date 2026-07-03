import { useEffect, useRef, useState } from "react";
import { motion, useInView, useMotionValue, useSpring } from "framer-motion";

export function GradientBlob({ className = "", tone = "primary" }) {
  const tones = {
    primary: "from-[#00c8ff] to-[#0066ff]",
    secondary: "from-[#00e5a8] to-[#00c8ff]",
    accent: "from-[#ffc857] to-[#ff8a3d]",
  };
  return (
    <div
      aria-hidden
      className={`animate-float-slow pointer-events-none absolute rounded-full bg-gradient-to-br ${tones[tone]} opacity-25 blur-[90px] ${className}`}
    />
  );
}

export function Reveal({ children, delay = 0, y = 24, className = "" }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function Eyebrow({ children }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1.5 text-[12px] font-semibold uppercase tracking-[0.14em] text-[#7fe6ff]">
      {children}
    </span>
  );
}

export function GlassCard({ children, className = "", glow = false }) {
  return (
    <div
      className={`glass group relative rounded-2xl transition-all duration-300 hover:border-white/20 hover:-translate-y-1 ${glow ? "hover:shadow-[0_0_40px_rgba(0,200,255,0.18)]" : "hover:shadow-[0_20px_50px_-20px_rgba(0,0,0,0.6)]"} ${className}`}
    >
      {children}
    </div>
  );
}

export function Counter({ to, suffix = "", prefix = "", decimals = 0, duration = 1.4 }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });
  const mv = useMotionValue(0);
  const spring = useSpring(mv, { duration: duration * 1000, bounce: 0 });
  const [display, setDisplay] = useState("0");

  useEffect(() => {
    if (inView) mv.set(to);
  }, [inView, to, mv]);

  useEffect(() => {
    const unsub = spring.on("change", (v) => {
      setDisplay(v.toFixed(decimals));
    });
    return unsub;
  }, [spring, decimals]);

  return (
    <span ref={ref}>
      {prefix}
      {display}
      {suffix}
    </span>
  );
}

export function SectionHeading({ eyebrow, title, description, align = "center" }) {
  return (
    <Reveal
      className={`mx-auto max-w-2xl ${align === "center" ? "text-center" : "text-left"}`}
    >
      {eyebrow && <div className={align === "center" ? "flex justify-center" : ""}><Eyebrow>{eyebrow}</Eyebrow></div>}
      <h2 className="mt-5 text-[32px] font-bold leading-[1.15] text-white sm:text-[40px]">
        {title}
      </h2>
      {description && (
        <p className="mt-4 text-[16px] leading-relaxed text-white/55">{description}</p>
      )}
    </Reveal>
  );
}

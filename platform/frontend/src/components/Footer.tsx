import Link from "next/link";
import {
  Leaf,
  Github,
  ExternalLink,
  BookOpen,
  Stethoscope,
  Video,
  HeartPulse,
} from "lucide-react";

const footerSections = [
  {
    title: "Platform",
    links: [
      { label: "Patient Intake", href: "/intake" },
      { label: "Shloka Search", href: "/search" },
      { label: "Knowledge Graph", href: "/dashboard" },
      { label: "Teleconsultation", href: "/consultation" },
    ],
  },
  {
    title: "For Practitioners",
    links: [
      { label: "Find Doctors", href: "/doctors" },
      { label: "Doctor Dashboard", href: "/dashboard" },
      { label: "Pharmacy", href: "/dashboard" },
      { label: "Claim Profile", href: "/doctors" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "API Docs", href: "#" },
      { label: "Data Dictionary", href: "#" },
      { label: "Security", href: "#" },
      { label: "GitHub", href: "#" },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="border-t border-[var(--border)] bg-[var(--background)]">
      <div className="container-app py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10">
          {/* Brand */}
          <div className="lg:col-span-2 space-y-4">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-[var(--ayur-emerald)] to-[var(--ayur-emerald-dark)] flex items-center justify-center">
                <Leaf className="w-5 h-5 text-white" />
              </div>
              <div>
                <span className="font-bold text-base tracking-tight">
                  Ayur<span className="gradient-text">LLM</span>
                </span>
                <span className="text-[var(--foreground-dim)] text-xs ml-1.5 font-medium">
                  Care
                </span>
              </div>
            </Link>
            <p className="text-sm text-[var(--foreground-muted)] max-w-sm leading-relaxed">
              Bridging classical Ayurvedic Shloka wisdom with modern clinical
              practice through AI-powered decision support and hospital management.
            </p>
            <div className="flex items-center gap-3 pt-2">
              <span className="badge badge-emerald">
                <HeartPulse className="w-3 h-3" />
                Open Source
              </span>
              <span className="badge badge-gold">v1.0.0</span>
            </div>
          </div>

          {/* Sections */}
          {footerSections.map((section) => (
            <div key={section.title} className="space-y-4">
              <h3 className="text-sm font-semibold text-[var(--foreground)] tracking-wide uppercase">
                {section.title}
              </h3>
              <ul className="space-y-2.5">
                {section.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-[var(--foreground-muted)] hover:text-[var(--foreground)] transition-colors"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="divider mt-12 mb-6" />
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[var(--foreground-dim)]">
          <p>
            © {new Date().getFullYear()} AyurLLM Care. Decision-support tool — not
            a substitute for professional medical advice.
          </p>
          <div className="flex items-center gap-4">
            <Link href="#" className="hover:text-[var(--foreground-muted)] transition-colors">
              Privacy
            </Link>
            <Link href="#" className="hover:text-[var(--foreground-muted)] transition-colors">
              Terms
            </Link>
            <Link href="#" className="hover:text-[var(--foreground-muted)] transition-colors">
              Disclaimer
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}

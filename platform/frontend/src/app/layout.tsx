import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AyurLLM Care — Ayurvedic Decision Support & Hospital Platform",
  description:
    "An AI-powered Ayurvedic hospital platform bridging classical Shloka wisdom with modern clinical practice. Patient intake, doctor network, teleconsultation & knowledge graph visualization.",
  keywords: [
    "Ayurveda",
    "Ayurvedic Hospital",
    "LLM",
    "Shloka Retrieval",
    "Decision Support",
    "Teleconsultation",
    "Neo4j Knowledge Graph",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      data-scroll-behavior="smooth"
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}

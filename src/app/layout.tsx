
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Gaurab Kushwaha | AI/ML Engineer",
  description:
    "Portfolio of Gaurab Kushwaha, an AI/ML engineering student interested in machine learning, generative AI, computer vision, and practical AI applications.",
  metadataBase: new URL("https://gaurabkus.dev"),
  openGraph: {
    title: "Gaurab Kushwaha | AI/ML Engineer",
    description:
      "Explore projects in machine learning, generative AI, computer vision, and software development.",
    url: "https://gaurabkus.dev",
    siteName: "Gaurab Kushwaha",
    type: "website",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#03050A",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${spaceGrotesk.variable} h-full antialiased`}
    >
      <body className="min-h-screen font-sans">{children}</body>
    </html>
  );
}

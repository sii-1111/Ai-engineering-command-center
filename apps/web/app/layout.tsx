import type { Metadata } from "next";
import "./globals.css";
import "./theme.css";
import "./eagle.css";

export const metadata: Metadata = {
  title: "AI Engineering Command Center",
  description: "Evidence-backed agentic engineering workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

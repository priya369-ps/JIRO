import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JIRO | Resume tailoring",
  description: "Evidence-led resume tailoring with visible validation."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

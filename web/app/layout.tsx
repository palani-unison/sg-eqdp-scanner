import type { Metadata } from "next";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { Footer } from "@/components/Footer";
import { Sidebar } from "@/components/Sidebar";
import { createClient } from "@/lib/supabase/server";
import { sans, serif } from "@/lib/fonts";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "EQDP Brief — Forensic SGX research",
    template: "%s · EQDP Brief",
  },
  description:
    "Inferring which Singapore-listed companies actually benefited from the MAS Equity Market Development Programme. Personal research by Palaniappan Chidambaram.",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  const adminEmail = process.env.ADMIN_EMAIL?.toLowerCase();
  const isAdmin =
    !!user && !!adminEmail && user.email?.toLowerCase() === adminEmail;

  return (
    <html lang="en" className={`${sans.variable} ${serif.variable}`}>
      <body className="font-sans min-h-screen antialiased bg-page text-ink">
        <DisclaimerBanner />
        <div className="flex min-h-[calc(100vh-1.875rem)]">
          <Sidebar userEmail={user?.email ?? null} isAdmin={isAdmin} />
          <div className="flex-1 flex flex-col min-w-0">
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
        </div>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Chaturya · College AI workspace",
  description:
    "Local college knowledge, study support, teaching material and administrative drafts.",
};
export default function Layout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

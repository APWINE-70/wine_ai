import "./globals.css";

export const metadata = {
  title: "Lanna Power Grid Reliability | Executive Outage Dashboard (2566–2567)",
  description:
    "Interactive SAIFI/SAIDI/CAIDI executive analytics dashboard for Lanna Power Distribution Co., Ltd.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="th" suppressHydrationWarning>
      <body className="min-h-screen antialiased" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}

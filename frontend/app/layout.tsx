import type { Metadata } from 'next';
import './styles/globals.css';

export const metadata: Metadata = {
  title: 'FinAlly - AI Trading Workstation',
  description: 'AI-powered trading workstation with live market data and portfolio management',
  viewport: 'width=device-width, initial-scale=1',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-terminal-dark text-terminal-text">
        {children}
      </body>
    </html>
  );
}

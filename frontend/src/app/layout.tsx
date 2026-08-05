import type { Metadata } from 'next';
import { IBM_Plex_Mono, Manrope, Sora } from 'next/font/google';
import { ThemeProvider } from 'next-themes';

import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'Diamond HPC',
    template: '%s | Diamond HPC'
  },
  description:
    'Diamond HPC unifies endpoint operations, images, datasets, and task execution in a single workspace.'
};

const displayFont = Sora({
  subsets: ['latin'],
  variable: '--font-display'
});

const bodyFont = Manrope({
  subsets: ['latin'],
  variable: '--font-body'
});

const monoFont = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-mono'
});

const desktopNavInitScript = `
  (() => {
    try {
      document.documentElement.dataset.desktopNavCollapsed = String(
        localStorage.getItem('diamond:desktop-nav-collapsed') === 'true'
      );
    } catch {}
  })();
`;

export default async function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="scroll-smooth" suppressHydrationWarning>
      <body
        className={`${displayFont.variable} ${bodyFont.variable} ${monoFont.variable} overflow-x-hidden antialiased`}
      >
        <script
          id="desktop-nav-init"
          dangerouslySetInnerHTML={{ __html: desktopNavInitScript }}
        />
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}

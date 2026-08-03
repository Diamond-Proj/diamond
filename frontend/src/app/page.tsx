import type { Metadata } from 'next';

import { LandingPage } from '@/components/landing/landing-page';
import { landingPageContent } from '@/content/landing-page-content';

export const metadata: Metadata = {
  description: landingPageContent.seo.description
};

export default function HomePage() {
  return <LandingPage />;
}

import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Dashboard',
  description:
    'Manage Diamond HPC endpoints, images, datasets, and tasks from the main workspace dashboard.'
};

export default function DashboardLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return children;
}

export const landingPageContent = {
  seo: {
    description:
      'Diamond HPC is a unified control plane for managed endpoints, container images, datasets, and task submission workflows.'
  },
  header: {
    eyebrow: 'Diamond HPC',
    label: 'Unified operations for research compute',
    docsHref: 'https://docs.diamondhpc.ai',
    docsLabel: 'Docs',
    primaryCta: {
      href: '/dashboard',
      label: 'Open workspace'
    }
  },
  hero: {
    headline: 'Fine-tune and serve models from one workspace.',
    screenshot: {
      src: '/screenshot/dashboard.png',
      alt: 'Diamond workspace dashboard showing endpoint and workload management views.',
      sideCardLabel: 'What you can do',
      sideCardItems: [
        'Leverage your HPC allocations (e.g. NSF ACCESS)',
        'Train and fine-tune models for specific applications',
        'Serve those models from your HPC systems'
      ]
    },
    primaryCta: {
      label: 'Open workspace',
      href: '/dashboard'
    }
  },
  hpcSystems: {
    title: 'Bring Diamond to the HPC environments your team already uses.',
    items: [
      {
        name: 'Delta',
        org: 'NCSA',
        image: {
          src: '/hpc-systems/delta.jpg',
          alt: 'NCSA Delta supercomputer'
        }
      },
      {
        name: 'Delta AI',
        org: 'NCSA',
        image: {
          src: '/hpc-systems/delta-ai.jpg',
          alt: 'DeltaAI system graphic'
        }
      },
      {
        name: 'Frontera',
        org: 'TACC',
        image: {
          src: '/hpc-systems/frontera.jpg',
          alt: 'Frontera supercomputer at TACC'
        }
      },
      {
        name: 'Stampede3',
        org: 'TACC',
        image: {
          src: '/hpc-systems/stampede3.jpg',
          alt: 'Stampede3 system graphic'
        }
      },
      {
        name: 'Lonestar6',
        org: 'TACC',
        image: {
          src: '/hpc-systems/lonestar6.jpg',
          alt: 'Lonestar6 supercomputer at TACC'
        }
      },
      {
        name: 'Anvil',
        org: 'RCAC'
      },
      {
        name: 'Bridges2',
        org: 'PSC',
        image: {
          src: '/hpc-systems/bridges2.jpg',
          alt: 'Bridges2 machine room at Pittsburgh Supercomputing Center'
        }
      }
    ]
  },
  highlights: {
    title: 'Core workflows in one place',
    description:
      'Diamond brings together your HPC allocations, runtime environments, datasets, and task launch in one workspace.',
    supportPanel: {
      points: [
        'Operators can track system status, container builds, and job submissions from a single screen.',
        'Researchers get a shorter path from infrastructure to first run.',
        'Shared teams can standardize workflows without losing operational context.'
      ]
    },
    items: [
      {
        icon: 'cpu',
        title: 'Prepare endpoints',
        description:
          'Manage available HPC systems to be used for task execution.'
      },
      {
        icon: 'layers',
        title: 'Build images',
        description:
          'Launch container builds so runtime environments stay tied to the systems and jobs that use them.'
      },
      {
        icon: 'database',
        title: 'Register datasets',
        description:
          'Store paths, machine context, and visibility settings so inputs are easy to find before submission.'
      },
      {
        icon: 'rocket',
        title: 'Launch tasks',
        description:
          'Submit work against active HPC systems with reusable task templates.'
      }
    ]
  },
  closing: {
    title: 'Run the workflow in Diamond.',
    description:
      'Connect your HPC systems, prepare runtime environments, register datasets, and launch reusable tasks from one interface.',
    primaryCta: {
      label: 'Open workspace',
      href: '/dashboard'
    },
    secondaryCta: {
      label: 'Read the docs',
      href: 'https://docs.diamondhpc.ai'
    }
  }
} as const;

export type LandingPageContent = typeof landingPageContent;

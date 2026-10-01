import type { Page, Route } from '@playwright/test';

const json = async (route: Route, body: unknown, status = 200) => {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body)
  });
};

export async function mockCommonApi(page: Page) {
  await page.route('**/api/auth/session', async (route) => {
    await json(route, {
      isAuthenticated: true,
      userInfo: {
        id: 'test-user-identity',
        name: 'Test Researcher',
        email: 'test.researcher@example.com',
        username: 'test-researcher',
        organization: 'Diamond UI Test Lab'
      },
      needsRefresh: false,
      nextRefreshAtSeconds: Math.floor(Date.now() / 1000) + 3000
    });
  });

  await page.route('**/api/profile**', async (route) => {
    if (route.request().method() === 'GET') {
      await json(route, {
        profile: {
          identity_id: 'test-user-identity',
          name: 'Test Researcher',
          email: 'test.researcher@example.com',
          institution: 'Diamond UI Test Lab',
          is_initialized: true
        }
      });
      return;
    }

    await json(route, { status: 'success' });
  });
}

export async function mockEndpointInventoryApi(page: Page) {
  const endpoints = [
    {
      endpoint_name: 'UI Test GPU Queue',
      endpoint_uuid: 'endpoint-ui-gpu',
      endpoint_host: 'gpu01.test',
      endpoint_status: 'online',
      diamond_dir: '/scratch/diamond',
      is_managed: true
    }
  ];

  await page.route('**/api/list_all_endpoints', async (route) => {
    await json(route, endpoints);
  });

  await page.route('**/api/list_active_managed_endpoints', async (route) => {
    await json(route, endpoints);
  });

  await page.route('**/api/get_diamond_dir**', async (route) => {
    await json(route, { diamond_dir: '/scratch/diamond' });
  });

  await page.route('**/api/list_partitions', async (route) => {
    await json(route, ['gpu', 'debug']);
  });

  await page.route('**/api/list_accounts', async (route) => {
    await json(route, ['research']);
  });
}

export async function mockDashboardApi(page: Page) {
  await mockCommonApi(page);

  await page.route('**/api/stats', async (route) => {
    await json(route, {
      tasks: {
        completed: 8,
        running: 2,
        failed: 1
      },
      endpoints: {
        online: 3,
        offline: 1
      },
      datasets: {
        public: 5,
        private: 4
      },
      images: {
        public: 7,
        private: 6
      },
      recent_tasks: [
        {
          task_id: 'task-ui-regression-001',
          name: 'UI Regression Training',
          status: 'RUNNING',
          create_time: '2026-05-27T18:00:00.000Z',
          last_update_time: '2026-05-27T18:15:00.000Z'
        }
      ]
    });
  });
}

export async function mockTasksApi(page: Page) {
  await mockCommonApi(page);
  await mockEndpointInventoryApi(page);

  await page.route('**/api/get_task_status', async (route) => {
    await json(route, {
      'task-ui-regression-001': {
        task_id: 'task-ui-regression-001',
        identity_id: 'test-user-identity',
        task_name: 'UI Regression Training',
        status: 'RUNNING',
        task_type: 'default',
        details: {
          endpoint_id: 'endpoint-ui-gpu',
          task_create_time: '2026-05-27T18:00:00.000Z'
        },
        result: null,
        error: null
      },
      'task-ui-regression-002': {
        task_id: 'task-ui-regression-002',
        identity_id: 'test-user-identity',
        task_name: 'Completed Dataset Prep',
        status: 'COMPLETED',
        task_type: 'default',
        details: {
          endpoint_id: 'endpoint-ui-gpu',
          task_create_time: '2026-05-27T17:00:00.000Z'
        },
        result: 'ok',
        error: null
      }
    });
  });

  await page.route('**/api/delete_task', async (route) => {
    await json(route, { status: 'success' });
  });

  await page.route('**/api/get_containers_on_endpoint', async (route) => {
    await json(route, {
      private: {
        'ui-regression-runtime': {
          status: 'completed',
          location: '/containers/ui-regression-runtime.sif',
          container_task_id: 'container-task-ui-001',
          base_image: 'nvidia/cuda:12.4.1-runtime-ubuntu22.04'
        }
      },
      public: {}
    });
  });

  await page.route('**/api/datasets', async (route) => {
    await json(route, {
      datasets: [
        {
          id: 1,
          collection_uuid: 'collection-ui-test',
          globus_path: '/globus/ui-regression',
          system_path: '/scratch/ui-regression',
          public: false,
          machine_name: 'UI Test GPU Queue',
          dataset_name: 'ui-regression-dataset',
          dataset_metadata: JSON.stringify({
            description: 'Dataset used by automated UI regression tests',
            size: '12 GB',
            format: 'jsonl'
          })
        }
      ]
    });
  });
}

export async function mockDatasetsApi(page: Page) {
  await mockCommonApi(page);

  await page.route('**/api/datasets', async (route) => {
    await json(route, {
      datasets: [
        {
          id: 1,
          collection_uuid: 'collection-ui-test',
          globus_path: '/globus/ui-regression',
          system_path: '/scratch/ui-regression',
          public: false,
          machine_name: 'UI Test GPU Queue',
          dataset_name: 'ui-regression-dataset',
          dataset_metadata: JSON.stringify({
            description: 'Dataset used by automated UI regression tests',
            size: '12 GB',
            format: 'jsonl'
          })
        },
        {
          id: 2,
          collection_uuid: 'collection-ui-public',
          globus_path: '/globus/public-benchmark',
          system_path: '/scratch/public-benchmark',
          public: true,
          machine_name: 'UI Test GPU Queue',
          dataset_name: 'public-benchmark-dataset',
          dataset_metadata: JSON.stringify({
            description: 'Public benchmark dataset for UI filter checks',
            size: '4 GB',
            format: 'parquet'
          })
        }
      ]
    });
  });
}

export async function mockImagesApi(page: Page) {
  await mockCommonApi(page);
  await mockEndpointInventoryApi(page);

  await page.route('**/api/get_all_containers', async (route) => {
    await json(route, {
      containers: {
        'ui-regression-runtime': {
          status: 'completed',
          location: '/containers/ui-regression-runtime.sif',
          container_task_id: 'container-task-ui-001',
          base_image: 'nvidia/cuda:12.4.1-runtime-ubuntu22.04',
          host_name: 'gpu01.test',
          is_public: false,
          is_owner: true,
          owner_identity_id: 'test-user-identity'
        }
      },
      public_by_host: {
        'gpu01.test': {
          'diamond-public-runtime': {
            status: 'active',
            location: '/containers/diamond-public-runtime.sif',
            container_task_id: 'container-task-public-001',
            base_image: 'ubuntu:22.04',
            host_name: 'gpu01.test',
            is_public: true,
            is_owner: false,
            owner_identity_id: 'another-user'
          }
        }
      }
    });
  });

  await page.route('**/api/delete_container', async (route) => {
    await json(route, { status: 'success' });
  });
}

export async function mockEndpointsPageApi(page: Page) {
  await mockCommonApi(page);

  const overview = {
    'endpoint-ui-gpu': {
      name: 'UI Test GPU Queue',
      is_managed: true
    },
    'endpoint-ui-available': {
      name: 'Available CPU Queue',
      is_managed: false
    }
  };

  const details = [
    {
      endpoint_name: 'UI Test GPU Queue',
      endpoint_uuid: 'endpoint-ui-gpu',
      endpoint_host: 'gpu01.test',
      endpoint_status: 'online',
      diamond_dir: '/scratch/diamond',
      is_managed: true
    },
    {
      endpoint_name: 'Available CPU Queue',
      endpoint_uuid: 'endpoint-ui-available',
      endpoint_host: 'cpu01.test',
      endpoint_status: 'online',
      diamond_dir: '',
      is_managed: false
    }
  ];

  await page.route('**/api/endpoint_overview', async (route) => {
    await json(route, overview);
  });

  await page.route('**/api/list_all_endpoints', async (route) => {
    await json(route, details);
  });

  await page.route('**/api/get_diamond_dir**', async (route) => {
    const url = new URL(route.request().url());
    const endpointUuid = url.searchParams.get('endpoint_uuid');

    await json(route, {
      diamond_dir:
        endpointUuid === 'endpoint-ui-gpu' ? '/scratch/diamond' : null
    });
  });

  await page.route('**/api/register_all_endpoints', async (route) => {
    await json(route, { status: 'success' });
  });

  await page.route('**/api/load_accounts_partitions', async (route) => {
    await json(route, { status: 'success' });
  });

  await page.route('**/api/manage_endpoint/**', async (route) => {
    await json(route, { status: 'success' });
  });

  await page.route('**/api/set_diamond_work_path', async (route) => {
    await json(route, { status: 'success' });
  });
}

function pdbAtomLine(
  serial: number,
  atomName: string,
  resName: string,
  chain: string,
  resSeq: number,
  x: number,
  y: number,
  z: number,
  bFactor: number,
  element: string
) {
  // Fixed-column PDB ATOM record (B-factor in columns 61-66 holds the pLDDT).
  const name = atomName.length < 4 ? ` ${atomName}`.padEnd(4) : atomName;
  return (
    'ATOM  ' +
    String(serial).padStart(5) +
    ' ' +
    name +
    ' ' +
    resName.padEnd(3) +
    ' ' +
    chain +
    String(resSeq).padStart(4) +
    '    ' +
    x.toFixed(3).padStart(8) +
    y.toFixed(3).padStart(8) +
    z.toFixed(3).padStart(8) +
    '  1.00' +
    bFactor.toFixed(2).padStart(6) +
    ' '.repeat(10) +
    element.padStart(2)
  );
}

const ALPHAFOLD_MOCK_PDB = [
  pdbAtomLine(1, 'N', 'MET', 'A', 1, 0, 0, 0, 96, 'N'),
  pdbAtomLine(2, 'CA', 'MET', 'A', 1, 1.5, 0, 0, 96, 'C'),
  pdbAtomLine(3, 'CA', 'ALA', 'A', 2, 3.8, 0, 0, 82, 'C'),
  pdbAtomLine(4, 'CA', 'GLY', 'A', 3, 6.1, 1, 0, 62, 'C'),
  pdbAtomLine(5, 'CA', 'LYS', 'B', 1, 9, 2, 0, 40, 'C'),
  'END',
  ''
].join('\n');

const ALPHAFOLD_MOCK_SCORES = {
  rank_001: {
    plddt: [96, 82, 62, 40],
    pae: [
      [0.5, 3, 10, 20],
      [3, 0.5, 8, 18],
      [10, 8, 0.4, 6],
      [20, 18, 6, 0.3]
    ],
    max_pae: 31.75,
    ptm: 0.71,
    iptm: 0.55
  },
  rank_002: {
    plddt: [90, 70, 50, 30],
    pae: [
      [0.6, 5, 12, 22],
      [5, 0.6, 9, 19],
      [12, 9, 0.5, 7],
      [22, 19, 7, 0.4]
    ],
    max_pae: 31.75,
    ptm: 0.6,
    iptm: 0.4
  }
};

// 1x1 transparent PNG used for the ColabFold plot thumbnails.
const TRANSPARENT_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
  'base64'
);

export async function mockAlphafoldApi(page: Page) {
  await mockCommonApi(page);
  await mockEndpointInventoryApi(page);

  await page.route('**/api/get_task_status', async (route) => {
    await json(route, {
      'task-alphafold-001': {
        task_id: 'task-alphafold-001',
        identity_id: 'test-user-identity',
        task_name: 'AlphaFold Demo',
        status: 'COMPLETED',
        task_type: 'alphafold',
        details: {
          endpoint_id: 'endpoint-ui-gpu',
          task_create_time: '2026-05-27T19:00:00.000Z'
        },
        result: '/scratch/diamond/logs/af-demo.stdout',
        error: '/scratch/diamond/logs/af-demo.stderr',
        artifact_path: '/scratch/diamond/outputs/af-demo',
        chat: null,
        alphafold: { pipeline: 'colabfold' }
      }
    });
  });

  await page.route(/\/api\/task_output_files(\?|$)/, async (route) => {
    await json(route, {
      artifact_path: '/scratch/diamond/outputs/af-demo',
      truncated: false,
      entries: [
        { name: 'af_demo.a3m', is_dir: false, size: 2048 },
        { name: 'af_demo.done.txt', is_dir: false, size: 0 },
        { name: 'af_demo_coverage.png', is_dir: false, size: 4096 },
        { name: 'af_demo_pae.png', is_dir: false, size: 4096 },
        { name: 'af_demo_plddt.png', is_dir: false, size: 4096 },
        {
          name: 'af_demo_scores_rank_001_alphafold2_ptm_model_3_seed_000.json',
          is_dir: false,
          size: 256
        },
        {
          name: 'af_demo_scores_rank_002_alphafold2_ptm_model_1_seed_000.json',
          is_dir: false,
          size: 256
        },
        {
          name: 'af_demo_unrelaxed_rank_001_alphafold2_ptm_model_3_seed_000.pdb',
          is_dir: false,
          size: 512
        },
        {
          name: 'af_demo_unrelaxed_rank_002_alphafold2_ptm_model_1_seed_000.pdb',
          is_dir: false,
          size: 512
        },
        { name: 'config.json', is_dir: false, size: 128 },
        { name: 'log.txt', is_dir: false, size: 1024 }
      ]
    });
  });

  // Regex so the singular route never swallows /api/task_output_files.
  await page.route(/\/api\/task_output_file\?/, async (route) => {
    const url = new URL(route.request().url());
    const filename = url.searchParams.get('filename') ?? '';
    if (filename.endsWith('.pdb')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/octet-stream',
        body: ALPHAFOLD_MOCK_PDB
      });
      return;
    }
    if (filename.endsWith('.json')) {
      const scores = filename.includes('rank_002')
        ? ALPHAFOLD_MOCK_SCORES.rank_002
        : ALPHAFOLD_MOCK_SCORES.rank_001;
      await route.fulfill({
        status: 200,
        contentType: 'application/octet-stream',
        body: JSON.stringify(scores)
      });
      return;
    }
    if (filename.endsWith('.png')) {
      await route.fulfill({
        status: 200,
        contentType: 'image/png',
        body: TRANSPARENT_PNG
      });
      return;
    }
    await json(route, { error: `${filename}: No such file or directory` }, 404);
  });

  await page.route('**/api/delete_task', async (route) => {
    await json(route, { status: 'success' });
  });
}

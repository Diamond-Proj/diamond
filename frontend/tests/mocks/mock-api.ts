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

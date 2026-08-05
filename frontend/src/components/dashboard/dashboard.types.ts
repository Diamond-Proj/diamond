export interface StatsResponse extends DashboardStats {
  recent_tasks: RecentTask[];
}

export interface DashboardStats {
  tasks: {
    completed: number;
    running: number;
    failed: number;
  };
  endpoints: {
    online: number;
    offline: number;
  };
  datasets: {
    public: number;
    private: number;
  };
  images: {
    public: number;
    private: number;
  };
}

export interface RecentTask {
  task_id: string;
  name: string;
  status: 'PENDING' | 'COMPLETED' | 'FAILED' | 'RUNNING';
  create_time: string;
  last_update_time: string;
}

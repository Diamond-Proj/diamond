import { TasksPageContent } from './components/tasks-page-content';

export default async function TasksPage() {
  const isAuthenticated = true;

  return <TasksPageContent isAuthenticated={isAuthenticated} />;
}

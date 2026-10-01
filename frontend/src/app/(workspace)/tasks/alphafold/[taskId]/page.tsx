import { AlphafoldPageContent } from './alphafold-page-content';

export default async function AlphafoldPage({
  params
}: {
  params: Promise<{ taskId: string }>;
}) {
  const { taskId } = await params;

  return <AlphafoldPageContent taskId={taskId} />;
}

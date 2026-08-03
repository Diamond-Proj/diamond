import { VllmChatPageContent } from './vllm-chat-page-content';

export default async function VllmChatPage({
  params
}: {
  params: Promise<{ taskId: string }>;
}) {
  const { taskId } = await params;

  return <VllmChatPageContent taskId={taskId} />;
}

'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, Loader2, RefreshCw, Send } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

import { Task, TasksApiResponse } from '../../tasks.types';

interface VllmChatPageContentProps {
  taskId: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface ChatServiceInfo {
  node?: string;
  port?: number;
  model?: string;
  base_url?: string;
}

function extractAssistantText(completion: unknown): string {
  if (!completion || typeof completion !== 'object') {
    return '';
  }

  const choices = (completion as { choices?: unknown }).choices;
  if (!Array.isArray(choices) || choices.length === 0) {
    return '';
  }

  const message = (choices[0] as { message?: { content?: unknown } }).message;
  const content = message?.content;

  if (typeof content === 'string') {
    return content;
  }

  if (Array.isArray(content)) {
    return content
      .map((item) => {
        if (typeof item === 'string') {
          return item;
        }
        if (
          item &&
          typeof item === 'object' &&
          typeof (item as { text?: unknown }).text === 'string'
        ) {
          return String((item as { text?: unknown }).text);
        }
        return '';
      })
      .filter(Boolean)
      .join('\n')
      .trim();
  }

  return '';
}

export function VllmChatPageContent({ taskId }: VllmChatPageContentProps) {
  const [task, setTask] = useState<Task | null>(null);
  const [loadingTask, setLoadingTask] = useState(true);
  const [taskError, setTaskError] = useState<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [prompt, setPrompt] = useState('');
  const [chatError, setChatError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [serviceInfo, setServiceInfo] = useState<ChatServiceInfo | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const isVllmTask = useMemo(() => task?.task_type === 'vllm_chat', [task?.task_type]);
  const servicePort = task?.chat?.port;
  const serviceModel = task?.chat?.model || 'diamond-assistant';

  const fetchTask = useCallback(async () => {
    try {
      const response = await fetch('/api/get_task_status', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch task status');
      }

      const data: TasksApiResponse = await response.json();
      const currentTask = data[taskId] ?? null;

      if (!currentTask) {
        setTask(null);
        setTaskError(`Task ${taskId} was not found.`);
        return;
      }

      setTask(currentTask);
      setTaskError(null);
    } catch (error) {
      console.error('Error loading vLLM task:', error);
      setTaskError('Failed to load task status.');
    } finally {
      setLoadingTask(false);
    }
  }, [taskId]);

  useEffect(() => {
    fetchTask();
    const interval = setInterval(fetchTask, 10000);
    return () => clearInterval(interval);
  }, [fetchTask]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const taskReadyForChat = Boolean(task && task.status === 'RUNNING' && isVllmTask);

  const handleClearConversation = () => {
    setMessages([]);
    setChatError(null);
  };

  const handleSendMessage = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt || sending) {
      return;
    }

    if (!task || !isVllmTask) {
      setChatError('This task is not a vLLM chat service task.');
      return;
    }

    if (task.status !== 'RUNNING') {
      setChatError(`Task status is ${task.status}. Chat is available only in RUNNING state.`);
      return;
    }

    setChatError(null);

    const userMessage: ChatMessage = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: trimmedPrompt
    };
    const nextMessages = [...messages, userMessage];

    setMessages(nextMessages);
    setPrompt('');
    setSending(true);

    const chatMessages = nextMessages.map((message) => ({
      role: message.role,
      content: message.content
    }));
    const outboundMessages = chatMessages;

    try {
      const response = await fetch('/api/vllm_chat', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          task_id: task.task_id,
          model: serviceModel,
          messages: outboundMessages
        })
      });

      const data = await response
        .json()
        .catch(() => ({ error: 'Invalid response from vLLM chat API' }));

      if (!response.ok) {
        throw new Error(data.error || 'Failed to get response from vLLM');
      }

      const assistantText = extractAssistantText(data.completion);
      const assistantMessage: ChatMessage = {
        id: `${Date.now()}-assistant`,
        role: 'assistant',
        content: assistantText || '[Empty response from model]'
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setServiceInfo(data.service || null);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to send message.';
      setChatError(errorMessage);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="dashboard-card relative overflow-hidden p-5 md:p-6">
        <div className="pointer-events-none absolute -right-10 -top-14 h-36 w-36 rounded-full bg-sky-400/8 blur-2xl" />
        <div className="pointer-events-none absolute -left-8 -bottom-10 h-32 w-32 rounded-full bg-primary/5 blur-2xl" />

        <div className="relative z-10 flex flex-wrap items-start justify-between gap-3">
          <div>
            <Link
              href="/tasks"
              className="mb-2 inline-flex items-center gap-1 text-sm text-slate-600 underline-offset-4 hover:underline dark:text-slate-300"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Tasks
            </Link>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              vLLM Chat
            </h1>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Task ID: <span className="font-mono">{taskId}</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={fetchTask}
              className="cursor-pointer"
            >
              <RefreshCw className="mr-1 h-3.5 w-3.5" />
              Refresh Status
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleClearConversation}
              disabled={messages.length === 0}
              className="cursor-pointer"
            >
              Clear Chat
            </Button>
          </div>
        </div>
      </section>

      <section className="dashboard-card p-5 md:p-6">
        {loadingTask ? (
          <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading task status...
          </div>
        ) : taskError ? (
          <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200">
            {taskError}
          </p>
        ) : !task ? (
          <p className="text-sm text-slate-600 dark:text-slate-300">Task not found.</p>
        ) : !isVllmTask ? (
          <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
            This task is not a vLLM chat task. Please launch one using the
            &quot;Launch vLLM Chat Service&quot; template.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/55">
              <span className="text-xs font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
                Task Status
              </span>
              <p className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
                {task.status}
              </p>
            </div>
            <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/55">
              <span className="text-xs font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
                Service Port
              </span>
              <p className="mt-1 font-mono font-semibold text-slate-900 dark:text-slate-100">
                {servicePort || 'Unknown'}
              </p>
            </div>
            <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/55">
              <span className="text-xs font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
                Model
              </span>
              <p className="mt-1 break-all font-mono font-semibold text-slate-900 dark:text-slate-100">
                {serviceModel}
              </p>
            </div>
            <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/55">
              <span className="text-xs font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
                Compute Node
              </span>
              <p className="mt-1 font-mono font-semibold text-slate-900 dark:text-slate-100">
                {serviceInfo?.node || 'Unknown'}
              </p>
            </div>
          </div>
        )}
      </section>

      <section className="dashboard-card p-5 md:p-6">
        <div className="h-[46vh] overflow-y-auto rounded-xl border border-slate-200/70 bg-slate-50/70 p-4 dark:border-slate-700/70 dark:bg-slate-900/45">
          {messages.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Send a message to start chatting with your vLLM service.
            </p>
          ) : (
            <div className="space-y-3">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`rounded-xl px-4 py-3 text-sm ${
                    message.role === 'user'
                      ? 'ml-auto max-w-[85%] bg-primary text-primary-foreground'
                      : 'max-w-[90%] border border-slate-200/70 bg-[hsl(var(--dashboard-surface))] text-slate-900 dark:border-slate-700/70 dark:text-slate-100'
                  }`}
                >
                  <p className="mb-1 text-xs font-semibold tracking-wide uppercase opacity-75">
                    {message.role}
                  </p>
                  <p className="whitespace-pre-wrap break-words">{message.content}</p>
                </div>
              ))}
            </div>
          )}
          {sending && (
            <div className="mt-3 inline-flex items-center gap-2 rounded-lg border border-slate-200/70 bg-[hsl(var(--dashboard-surface))] px-3 py-2 text-sm text-slate-700 dark:border-slate-700/70 dark:text-slate-200">
              <Loader2 className="h-4 w-4 animate-spin" />
              Waiting for model response...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {chatError && (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200">
            {chatError}
          </p>
        )}

        {!taskReadyForChat && !loadingTask && !taskError && (
          <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
            Chat requires task status RUNNING. Current status: {task?.status || 'Unknown'}.
          </p>
        )}

        <form onSubmit={handleSendMessage} className="mt-5 flex gap-3">
          <Textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={3}
            placeholder="Type your message..."
            className="min-h-24"
            disabled={!taskReadyForChat || sending}
          />
          <Button
            type="submit"
            disabled={!taskReadyForChat || sending || !prompt.trim()}
            className="h-fit cursor-pointer"
          >
            {sending ? (
              <>
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                Sending
              </>
            ) : (
              <>
                <Send className="mr-1 h-4 w-4" />
                Send
              </>
            )}
          </Button>
        </form>
      </section>
    </div>
  );
}

'use client';

import { useState } from 'react';
import { Button } from './ui/button';
import { Loader2, LogIn } from 'lucide-react';
import { toast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';
import { fetchDynamicGlobusScopes } from '@/lib/auth/client';
import { DEFAULT_GLOBUS_SCOPES } from '@/lib/auth/constants';

interface LoginButtonProps {
  className?: string;
}

export function LoginButton({ className }: LoginButtonProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    try {
      setIsLoading(true);

      const baseUrl = window.location.origin;
      const clientId = process.env.NEXT_PUBLIC_GLOBUS_CLIENT_ID;

      if (!clientId) {
        throw new Error('Globus client ID not configured');
      }
      const dynamicScopes = await fetchDynamicGlobusScopes();
      const staticScopes = process.env.NEXT_PUBLIC_GLOBUS_SCOPES
        ? process.env.NEXT_PUBLIC_GLOBUS_SCOPES.split(' ')
        : [];

      const allScopes = Array.from(
        new Set([...DEFAULT_GLOBUS_SCOPES.split(' '), ...staticScopes, ...dynamicScopes])
      ).join(' ');

      const redirectUri = `${baseUrl}/auth/callback`;
      const params = new URLSearchParams({
        client_id: clientId,
        redirect_uri: redirectUri,
        response_type: 'code',
        scope: allScopes,
        access_type: 'offline'
      });

      const loginUrl = `https://auth.globus.org/v2/oauth2/authorize?${params.toString()}`;

      // Redirect to Globus Auth
      window.location.href = loginUrl;
    } catch (error) {
      console.error('Login error:', error);
      setIsLoading(false);

      toast({
        title: 'Authentication Error',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to initiate login. Please try again.',
        variant: 'destructive'
      });
    }
  };

  return (
    <Button
      variant="outline"
      size="default"
      onClick={handleLogin}
      disabled={isLoading}
      className={cn(
        'h-10 cursor-pointer rounded-lg border border-slate-300/70 bg-transparent px-4 text-slate-700 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800 dark:hover:text-slate-100',
        className
      )}
    >
      {isLoading ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Connecting...</span>
        </>
      ) : (
        <>
          <LogIn className="h-4 w-4" />
          <span>Sign In</span>
        </>
      )}
    </Button>
  );
}


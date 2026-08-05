'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import {
  AUTH_REFRESH_MIN_DELAY_MS,
  AUTH_REFRESH_ENDPOINT,
  AUTH_REFRESH_RETRY_INTERVAL_MS,
  CLIENT_AUTH_REDIRECT_EXEMPT_ROUTES,
  SIGN_IN_ROUTE,
  pathnameMatches
} from './constants';
import { createDefaultAuthSession, fetchAuthSession } from './client';
import type { AuthSession } from './types';

export function useAuthSession(initialSession?: AuthSession) {
  const pathname = usePathname();
  const router = useRouter();
  const isFirstSessionEffectRef = useRef(true);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isRefreshingRef = useRef(false);
  const [session, setSession] = useState<AuthSession>(
    initialSession ?? createDefaultAuthSession()
  );
  const [isLoading, setIsLoading] = useState(!initialSession);

  const loadSession = useCallback(async (resetOnError = true) => {
    try {
      const nextSession = await fetchAuthSession();
      setSession(nextSession);
      return nextSession;
    } catch (error) {
      console.error('Failed to refresh auth session:', error);

      if (!resetOnError) {
        return null;
      }

      const fallbackSession = createDefaultAuthSession();
      setSession(fallbackSession);
      return fallbackSession;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const redirectToSignIn = useCallback(() => {
    if (!pathnameMatches(pathname, CLIENT_AUTH_REDIRECT_EXEMPT_ROUTES)) {
      router.push(SIGN_IN_ROUTE);
    }
  }, [pathname, router]);

  const refreshTokens = useCallback(async () => {
    if (isRefreshingRef.current) {
      console.log('Token refresh already in progress, skipping...');
      return null;
    }

    try {
      isRefreshingRef.current = true;
      console.log('Starting token refresh...');

      const response = await fetch(AUTH_REFRESH_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include'
      });

      if (!response.ok) {
        console.error('Token refresh failed:', response.status);

        if (response.status === 401) {
          const fallbackSession = createDefaultAuthSession();
          setSession(fallbackSession);
          setIsLoading(false);
          redirectToSignIn();
          return fallbackSession;
        }

        return null;
      }

      const payload = (await response.json()) as { session?: AuthSession };
      const nextSession = payload.session ?? createDefaultAuthSession();

      console.log('Tokens refreshed successfully');
      setSession(nextSession);
      setIsLoading(false);
      router.refresh();
      return nextSession;
    } catch (error) {
      console.error('Error refreshing tokens:', error);
      return null;
    } finally {
      isRefreshingRef.current = false;
    }
  }, [redirectToSignIn, router]);

  const syncSession = useCallback(
    async (resetOnError = true) => {
      const nextSession = await loadSession(resetOnError);

      if (!nextSession) {
        return null;
      }

      if (!nextSession.isAuthenticated) {
        console.log('No tokens found, stopping auto-refresh');
        redirectToSignIn();
        return nextSession;
      }

      if (nextSession.needsRefresh) {
        console.log('Tokens need refresh, refreshing...');
        return refreshTokens();
      }

      return nextSession;
    },
    [loadSession, redirectToSignIn, refreshTokens]
  );

  const getNextSyncDelayMs = useCallback((currentSession: AuthSession) => {
    if (!currentSession.isAuthenticated) {
      return null;
    }

    if (currentSession.needsRefresh) {
      return AUTH_REFRESH_RETRY_INTERVAL_MS;
    }

    if (!currentSession.nextRefreshAtSeconds) {
      return AUTH_REFRESH_RETRY_INTERVAL_MS;
    }

    return Math.max(
      currentSession.nextRefreshAtSeconds * 1000 - Date.now(),
      AUTH_REFRESH_MIN_DELAY_MS
    );
  }, []);

  useEffect(() => {
    if (isFirstSessionEffectRef.current) {
      isFirstSessionEffectRef.current = false;

      if (initialSession) {
        if (initialSession.isAuthenticated && initialSession.needsRefresh) {
          void refreshTokens();
        }
        return;
      }
    }

    void syncSession(true);
  }, [initialSession, refreshTokens, syncSession]);

  useEffect(() => {
    const handleFocus = () => {
      console.log('Window focused, syncing auth session...');
      void syncSession(true);
    };

    window.addEventListener('focus', handleFocus);

    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
      window.removeEventListener('focus', handleFocus);
    };
  }, [syncSession]);

  useEffect(() => {
    const nextSyncDelayMs = getNextSyncDelayMs(session);

    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }

    if (nextSyncDelayMs === null) {
      return;
    }

    refreshTimerRef.current = setTimeout(() => {
      void syncSession(false);
    }, nextSyncDelayMs);

    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
    };
  }, [getNextSyncDelayMs, session, syncSession]);

  return {
    session,
    isLoading
  };
}

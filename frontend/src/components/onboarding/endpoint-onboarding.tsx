'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { X } from 'lucide-react';

const ONBOARDING_STEP_KEY = 'diamond:endpoint-onboarding-step';

type OnboardingStep = 1 | 2;

interface TargetRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

interface EndpointOnboardingProps {
  isAuthenticated: boolean;
  primaryIdentity?: string;
  onOpenNavigation: () => void;
}

export function EndpointOnboarding({
  isAuthenticated,
  primaryIdentity,
  onOpenNavigation
}: EndpointOnboardingProps) {
  const [step, setStep] = useState<OnboardingStep | null>(null);
  const [targetRect, setTargetRect] = useState<TargetRect | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    let showTimer: ReturnType<typeof setTimeout> | undefined;

    async function checkInitialization() {
      if (!isAuthenticated || !primaryIdentity) {
        return;
      }

      try {
        const response = await fetch(
          `/api/profile?identity_id=${primaryIdentity}`
        );
        const data = await response.json();

        if (!response.ok || !data.profile || data.profile.is_initialized) {
          sessionStorage.removeItem(ONBOARDING_STEP_KEY);
          return;
        }

        const savedStep = sessionStorage.getItem(ONBOARDING_STEP_KEY);
        if (pathname === '/endpoints') {
          if (savedStep === '2') {
            showTimer = setTimeout(() => setStep(2), 350);
          }
          return;
        }

        showTimer = setTimeout(() => {
          onOpenNavigation();
          setStep(1);
        }, 1000);
      } catch (error) {
        console.error('Error checking profile initialization:', error);
      }
    }

    checkInitialization();
    return () => clearTimeout(showTimer);
  }, [isAuthenticated, onOpenNavigation, pathname, primaryIdentity]);

  useEffect(() => {
    if (!step) {
      return;
    }

    function dismissOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        sessionStorage.removeItem(ONBOARDING_STEP_KEY);
        setStep(null);
      }
    }

    window.addEventListener('keydown', dismissOnEscape);
    return () => window.removeEventListener('keydown', dismissOnEscape);
  }, [step]);

  useEffect(() => {
    if (!step) {
      return;
    }

    const targetName = step === 1 ? 'endpoints' : 'available-endpoints';

    function updateTargetRect() {
      const targets = Array.from(
        document.querySelectorAll<HTMLElement>(
          `[data-onboarding-target="${targetName}"]`
        )
      );
      const target = targets.find((element) => {
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      });

      if (!target) {
        return;
      }

      const rect = target.getBoundingClientRect();
      setTargetRect({
        top: rect.top,
        left: rect.left,
        width: rect.width,
        height: rect.height
      });
    }

    const frame = window.requestAnimationFrame(updateTargetRect);
    const observer = new MutationObserver(updateTargetRect);
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener('resize', updateTargetRect);

    return () => {
      window.cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener('resize', updateTargetRect);
    };
  }, [step]);

  function dismiss() {
    sessionStorage.removeItem(ONBOARDING_STEP_KEY);
    setTargetRect(null);
    setStep(null);
  }

  function continueToStepTwo() {
    sessionStorage.setItem(ONBOARDING_STEP_KEY, '2');
    setTargetRect(null);
    setStep(null);
  }

  function selectAvailableEndpoints() {
    document
      .querySelector<HTMLElement>(
        '[data-onboarding-target="available-endpoints"]'
      )
      ?.click();
    dismiss();
  }

  if (!step || !targetRect) {
    return null;
  }

  const isDesktopFirstStep = step === 1 && window.innerWidth >= 1024;
  const coachmarkStyle = isDesktopFirstStep
    ? {
        top: targetRect.top + targetRect.height / 2,
        left: targetRect.left + targetRect.width + 16,
        transform: 'translateY(-50%)'
      }
    : {
        top: targetRect.top + targetRect.height + 14,
        left:
          step === 2
            ? Math.min(
                Math.max(16, targetRect.left + targetRect.width - 304),
                window.innerWidth - 320
              )
            : 16
      };

  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        className="absolute inset-0 cursor-default bg-slate-950/25"
        onClick={dismiss}
        aria-label="Dismiss endpoint guide"
      />

      {step === 1 ? (
        <Link
          href="/endpoints"
          onClick={continueToStepTwo}
          className="focus-visible:ring-primary absolute rounded-xl shadow-[0_0_0_5px_rgba(255,255,255,0.28),0_10px_30px_rgba(15,23,42,0.2)] ring-2 ring-white focus-visible:ring-4 focus-visible:outline-none"
          style={targetRect}
          aria-label="Open Endpoints"
        />
      ) : (
        <button
          type="button"
          onClick={selectAvailableEndpoints}
          className="focus-visible:ring-primary absolute cursor-pointer rounded-xl shadow-[0_0_0_5px_rgba(255,255,255,0.28),0_10px_30px_rgba(15,23,42,0.2)] ring-2 ring-white focus-visible:ring-4 focus-visible:outline-none"
          style={targetRect}
          aria-label="Show available endpoints"
        />
      )}

      <section
        role="dialog"
        aria-labelledby="endpoint-onboarding-title"
        className="absolute w-[min(19rem,calc(100vw-2rem))] rounded-xl border border-slate-200 bg-white p-4 shadow-[0_18px_50px_rgba(15,23,42,0.22)] dark:border-slate-700 dark:bg-slate-900"
        style={coachmarkStyle}
      >
        <span
          className={`absolute h-3 w-3 rotate-45 border bg-white dark:bg-slate-900 ${
            isDesktopFirstStep
              ? 'top-1/2 -left-1.5 -translate-y-1/2 border-t-0 border-r-0 border-slate-200 dark:border-slate-700'
              : '-top-1.5 left-7 border-r-0 border-b-0 border-slate-200 dark:border-slate-700'
          }`}
          aria-hidden="true"
        />

        <button
          type="button"
          onClick={dismiss}
          className="focus-visible:ring-primary absolute top-2.5 right-2.5 cursor-pointer rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-800 focus-visible:ring-2 focus-visible:outline-none dark:hover:bg-slate-800 dark:hover:text-white"
          aria-label="Dismiss endpoint guide"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="pr-7">
          <p className="text-primary text-xs font-semibold">{step} of 2</p>
          <h2
            id="endpoint-onboarding-title"
            className="mt-1 text-sm leading-5 font-semibold text-slate-950 dark:text-white"
          >
            {step === 1 ? 'Open Endpoints' : 'Choose an available endpoint'}
          </h2>
        </div>
      </section>
    </div>
  );
}

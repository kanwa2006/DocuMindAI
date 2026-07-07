"use client";
import { useState, useCallback, useEffect } from "react";

export interface OnboardingState {
  currentStep: number;   // 1 | 2 | 3 | 0 (complete)
  isComplete: boolean;
  advance: () => void;
  dismiss: () => void;
}

export function useOnboarding(): OnboardingState {
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [isComplete, setIsComplete] = useState<boolean>(true);

  useEffect(() => {
    if (typeof window === "undefined") return;
    // Honour both legacy and BF5 dismissal keys.
    const complete =
      localStorage.getItem("onboarding_complete") === "true" ||
      localStorage.getItem("dm.onboarding.dismissed") === "true";
    if (complete) {
      setIsComplete(true);
      setCurrentStep(0);
      return;
    }
    const saved = parseInt(localStorage.getItem("onboarding_step") || "1", 10);
    setCurrentStep(saved);
    setIsComplete(false);
  }, []);

  const advance = useCallback(() => {
    setCurrentStep((prev) => {
      const next = prev + 1;
      if (next > 3) {
        localStorage.setItem("onboarding_complete", "true");
        localStorage.removeItem("onboarding_step");
        setIsComplete(true);
        return 0;
      }
      localStorage.setItem("onboarding_step", String(next));
      return next;
    });
  }, []);

  const dismiss = useCallback(() => {
    localStorage.setItem("onboarding_complete", "true");
    localStorage.removeItem("onboarding_step");
    setIsComplete(true);
    setCurrentStep(0);
  }, []);

  return { currentStep, isComplete, advance, dismiss };
}

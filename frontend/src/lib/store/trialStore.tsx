"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

export type PlanType = "trial" | "professional" | "business" | "enterprise";

export type UpgradeTrigger = "limit_reached" | "user_click" | "locked_workspace";

export interface TrialState {
  plan: PlanType;
  queriesUsed: number;
  queriesRemaining: number;
  showUpgradeModal: boolean;
  upgradeTrigger: UpgradeTrigger;
}

interface TrialActions {
  setTrialStatus: (queriesUsed: number, queriesRemaining: number) => void;
  setPlan: (plan: PlanType) => void;
  openUpgradeModal: (trigger: UpgradeTrigger) => void;
  closeUpgradeModal: () => void;
}

const TrialContext = createContext<(TrialState & TrialActions) | null>(null);

export function TrialProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<TrialState>({
    plan: "trial",
    queriesUsed: 0,
    queriesRemaining: 5,
    showUpgradeModal: false,
    upgradeTrigger: "user_click",
  });

  const setTrialStatus = useCallback((queriesUsed: number, queriesRemaining: number) => {
    setState((s) => ({ ...s, queriesUsed, queriesRemaining }));
  }, []);

  const setPlan = useCallback((plan: PlanType) => {
    setState((s) => ({ ...s, plan }));
  }, []);

  const openUpgradeModal = useCallback((trigger: UpgradeTrigger) => {
    setState((s) => ({ ...s, showUpgradeModal: true, upgradeTrigger: trigger }));
  }, []);

  const closeUpgradeModal = useCallback(() => {
    setState((s) => ({ ...s, showUpgradeModal: false }));
  }, []);

  return (
    <TrialContext.Provider
      value={{ ...state, setTrialStatus, setPlan, openUpgradeModal, closeUpgradeModal }}
    >
      {children}
    </TrialContext.Provider>
  );
}

export function useTrialStore(): TrialState & TrialActions {
  const ctx = useContext(TrialContext);
  if (!ctx) throw new Error("useTrialStore must be used inside <TrialProvider>");
  return ctx;
}

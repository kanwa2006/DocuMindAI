"use client";

import { useState } from "react";
import CorrectionModal from "./CorrectionModal";

export interface Citation {
  id: string;
  label: string;
  page_number?: number;
}

export interface FeedbackBarProps {
  messageId: string;
  sessionId: string;
  workspaceId: string;
  workspaceType?: string;
  hasCitations: boolean;
  citations?: Citation[];
  onVerifySource?: (messageId: string, citation: Citation) => void;
}

type ModalMode = "verify_source" | "suggest_correction" | "escalate" | "needs_review" | null;

const LEGAL_FINANCE = new Set(["legal", "finance"]);

export default function FeedbackBar({
  messageId,
  sessionId,
  workspaceId,
  workspaceType = "general",
  hasCitations,
  citations = [],
  onVerifySource,
}: FeedbackBarProps) {
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [visible, setVisible] = useState(false);

  const showEscalate = LEGAL_FINANCE.has(workspaceType);

  function open(mode: ModalMode) {
    setModalMode(mode);
  }

  function close() {
    setModalMode(null);
  }

  // Map action → CorrectionModal prefill issue_type
  const actionToIssueType: Record<string, string> = {
    suggest_correction: "",
    escalate: "other",
    needs_review: "other",
    verify_source: "citation_wrong",
  };

  return (
    <div
      className="feedback-bar"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {/* Second action row — visible on hover */}
      <div
        className="feedback-bar__actions"
        style={{ opacity: visible ? 1 : 0, transition: "opacity 0.15s ease" }}
        aria-hidden={!visible}
      >
        {hasCitations && (
          <button
            className="btn btn-ghost btn-sm"
            title="Verify Source — Open cited document page and confirm accuracy"
            onClick={() => {
              if (citations.length > 0 && onVerifySource) {
                onVerifySource(messageId, citations[0]);
              } else {
                open("verify_source");
              }
            }}
            tabIndex={visible ? 0 : -1}
          >
            🔍 Verify Source
          </button>
        )}

        <button
          className="btn btn-ghost btn-sm"
          title="Suggest Correction — Flag an inaccuracy or incorrect answer"
          onClick={() => open("suggest_correction")}
          tabIndex={visible ? 0 : -1}
        >
          ✏ Suggest Correction
        </button>

        {showEscalate && (
          <button
            className="btn btn-ghost btn-sm"
            title="Escalate Issue — Route this issue to senior review (Legal/Finance)"
            onClick={() => open("escalate")}
            tabIndex={visible ? 0 : -1}
          >
            ⚑ Escalate Issue
          </button>
        )}

        <button
          className="btn btn-ghost btn-sm"
          title="Needs Review — Flag this response for admin review queue"
          onClick={() => open("needs_review")}
          tabIndex={visible ? 0 : -1}
        >
          📋 Needs Review
        </button>
      </div>

      {modalMode && (
        <CorrectionModal
          sessionId={sessionId}
          messageId={messageId}
          workspaceId={workspaceId}
          citations={citations}
          prefillIssueType={
            modalMode === "suggest_correction" ? "" : actionToIssueType[modalMode] ?? ""
          }
          onClose={close}
        />
      )}
    </div>
  );
}

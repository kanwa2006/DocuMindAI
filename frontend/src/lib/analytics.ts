import posthog from 'posthog-js'

export const initAnalytics = () => {
  if (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_POSTHOG_KEY) {
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
      api_host: 'https://app.posthog.com',
      capture_pageview: false,
      capture_pageleave: true,
      autocapture: false,
    })
  }
}

export const track = (event: string, properties?: Record<string, unknown>) => {
  posthog.capture(event, properties)
}

// Typed event helpers — NEVER include query text, document names, answer content, email, or user_id
export const Analytics = {
  pageViewed: (path: string) =>
    track('page_viewed', { path }),

  workspaceSwitched: (from_workspace: string, to_workspace: string) =>
    track('workspace_switched', { from_workspace, to_workspace }),

  querySubmitted: (workspace: string, query_length_chars: number, has_documents: boolean) =>
    track('query_submitted', { workspace, query_length_chars, has_documents }),

  documentUploaded: (workspace: string, file_type: string, file_size_mb_bucket: '0-1' | '1-5' | '5+') =>
    track('document_uploaded', { workspace, file_type, file_size_mb_bucket }),

  trialQueryUsed: (queries_used: number, queries_remaining: number) =>
    track('trial_query_used', { queries_used, queries_remaining }),

  upgradeModalShown: (trigger: 'limit_reached' | 'feature_locked' | 'user_click') =>
    track('upgrade_modal_shown', { trigger }),

  upgradeClicked: (plan: string, billing_cycle: string, source_page: string) =>
    track('upgrade_clicked', { plan, billing_cycle, source_page }),

  subscriptionStarted: (plan: string, cycle: string) =>
    track('subscription_started', { plan, cycle }),

  exportDownloaded: (format: 'pdf' | 'docx' | 'md' | 'csv', workspace: string) =>
    track('export_downloaded', { format, workspace }),

  bookmarkSaved: (workspace: string) =>
    track('bookmark_saved', { workspace }),

  trustScoreExpanded: (trust_level: 'high' | 'medium' | 'low') =>
    track('trust_score_expanded', { trust_level }),

  contradictionAlertViewed: (workspace: string) =>
    track('contradiction_alert_viewed', { workspace }),

  secondOpinionRequested: (trust_score_before: number) =>
    track('second_opinion_requested', { trust_score_before }),

  feedbackSubmitted: (type: 'bug' | 'feature' | 'payment' | 'other') =>
    track('feedback_submitted', { type }),

  sessionCreated: (workspace: string) =>
    track('session_created', { workspace }),

  sessionShared: (workspace: string) =>
    track('session_shared', { workspace }),

  voiceQueryUsed: (workspace: string) =>
    track('voice_query_used', { workspace }),

  cameraScanUsed: (workspace: string) =>
    track('camera_scan_used', { workspace }),

  morningBriefingOpened: (num_cards: number) =>
    track('morning_briefing_opened', { num_cards }),

  clipTextUsed: (text_length_chars_bucket: '0-100' | '100-500' | '500+') =>
    track('clip_text_used', { text_length_chars_bucket }),

  pwaInstalled: () =>
    track('pwa_installed'),
}

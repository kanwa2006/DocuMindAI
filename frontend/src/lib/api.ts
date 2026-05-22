export interface Document {
  id: string;
  filename: string;
  status: 'PENDING_UPLOAD' | 'UPLOADED' | 'PROCESSING' | 'EXTRACTED' | 'READY' | 'FAILED' | 'DEDUPLICATED';
  duplicate_of?: string;
  workspace_id?: string;
  created_at: string;
  source?: string; // "upload" | "clip" | "scan"
}

export interface EvidenceChunk {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number;
  text_content: string;
  similarity_score?: number;
  rerank_score?: number;
}

export interface TracingDiagnostics {
  embedding_time_sec: number;
  database_time_sec: number;
  reranking_time_sec: number;
  generation_time_sec: number;
  total_time_sec: number;
  candidates_retrieved: number;
  evidence_accepted: number;
  estimated_tokens: number;
}

export interface QueryResponse {
  query: string;
  answer: string;
  confidence_score: number;
  evidence: EvidenceChunk[];
  diagnostics: TracingDiagnostics;
  /** C10 — false when the backend answered from general knowledge (no documents indexed for this workspace). */
  grounded?: boolean;
  /** C10 — "grounded" | "general". Frontend shows an Ungrounded badge for "general". */
  mode?: "grounded" | "general";
}

export const API_BASE = process.env.NEXT_PUBLIC_API_URL;

if (!API_BASE) {
  console.warn("NEXT_PUBLIC_API_URL is not set. API calls will fail.");
}

let csrfToken = '';
let deviceFingerprint = '';
let _csrfPromise: Promise<void> | null = null;

function _fetchCsrf(): Promise<void> {
  if (_csrfPromise) return _csrfPromise;
  _csrfPromise = fetch(`${API_BASE}/csrf-token`, { credentials: 'include' })
    .then(res => res.json())
    .then(data => { csrfToken = data.csrf_token; })
    .catch(() => { /* will retry on next mutation */ })
    .finally(() => { _csrfPromise = null; });
  return _csrfPromise;
}

// Fetch CSRF on boot (best-effort; apiFetch also awaits before first mutation)
if (typeof window !== 'undefined') {
  _fetchCsrf();
}

async function initDeviceFingerprint(): Promise<void> {
  try {
    const FP = await import('@fingerprintjs/fingerprintjs');
    const fp = await FP.load();
    const result = await fp.get();
    deviceFingerprint = result.visitorId;
  } catch {
    // non-blocking — fingerprint is best-effort
  }
}

export async function getDeviceFingerprint(): Promise<string> {
  if (!deviceFingerprint) await initDeviceFingerprint();
  return deviceFingerprint;
}

// Initialize fingerprint once at app load (browser only)
if (typeof window !== 'undefined') {
  initDeviceFingerprint();
}

// TASK 1.1: Silent JWT refresh state
let _isRefreshing = false;
let _refreshPromise: Promise<boolean> | null = null;

export function getCsrfToken(): string { return csrfToken; }

function redirectToLogin() {
  if (typeof window !== 'undefined') {
    sessionStorage.setItem('returnTo', window.location.pathname);
    window.location.href = '/login?expired=true';
  }
}

async function doRefreshToken(): Promise<boolean> {
  try {
    const r = await fetch(`${API_BASE}/auth/refresh`, { method: 'POST', credentials: 'include' });
    return r.ok;
  } catch { return false; }
}

export const apiFetch = async (endpoint: string, options: RequestInit = {}, _retried = false): Promise<Response> => {
  const isMutation = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method?.toUpperCase() || 'GET');
  // E2 fix: if the boot-time CSRF fetch hasn't resolved yet, wait for it
  // (or refetch) before sending the mutation. Otherwise CSRFMiddleware 403s.
  // /auth/* are CSRF-exempt server-side, so we skip the wait for them.
  if (isMutation && !csrfToken && !endpoint.startsWith('/auth/')) {
    await _fetchCsrf();
  }
  const headers = new Headers(options.headers || {});
  if (isMutation && csrfToken) headers.set('X-CSRF-Token', csrfToken);
  if (deviceFingerprint) headers.set('X-Device-ID', deviceFingerprint);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers, credentials: 'include' });
  } catch (error: any) {
    if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
      throw new Error('Network error: The server is unreachable. Please check your connection.');
    }
    throw error;
  }

  // TASK 1.1: 401 → silent refresh → retry once
  if (response.status === 401 && !_retried) {
    if (!_isRefreshing) {
      _isRefreshing = true;
      _refreshPromise = doRefreshToken().finally(() => { _isRefreshing = false; _refreshPromise = null; });
    }
    const refreshed = await _refreshPromise!;
    if (refreshed) return apiFetch(endpoint, options, true);
    // Dispatch event — SessionExpiredOverlay catches this; no hard redirect
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('session:expired'));
    }
    throw new Error('Session expired');
  }

  return response;
};

export const login = async (form: FormData) => {
  const res = await apiFetch('/auth/login', {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Login failed");
  }
  return res.json();
};

export const logout = async () => {
  const res = await apiFetch('/auth/logout', { method: 'POST' });
  if (!res.ok) throw new Error("Logout failed");
  return res.json();
};

export const uploadDocument = async (file: File, workspaceId?: string): Promise<Document> => {
  // 1. Get Presigned URL (or local upload info)
  const wsParam = workspaceId ? `&workspace_id=${encodeURIComponent(workspaceId)}` : '';
  const preRes = await apiFetch(`/documents/upload/presigned?filename=${encodeURIComponent(file.name)}&content_type=${encodeURIComponent(file.type || 'application/pdf')}&file_size=${file.size}${wsParam}`);
  if (!preRes.ok) throw new Error("Failed to get presigned upload URL");
  const presigned = await preRes.json();

  let uploadMeta: { storage_path?: string; filename?: string; size_bytes?: number; mime_type?: string; file_hash?: string };

  if (presigned.provider === "local") {
    // FIX 0.8: Local upload via multipart POST
    const formData = new FormData();
    formData.append("file", file);
    formData.append("workspace_id", presigned.workspace_id || workspaceId || "general");
    const localRes = await apiFetch("/documents/upload/local", {
      method: "POST",
      body: formData,
      // No Content-Type header — browser sets multipart boundary
    });
    if (!localRes.ok) throw new Error("Failed to upload file locally");
    uploadMeta = await localRes.json();
  } else {
    // S3 PUT flow — upload directly to S3 (no auth headers)
    const putRes = await fetch(presigned.upload_url, {
      method: 'PUT',
      headers: { 'Content-Type': file.type || 'application/pdf' },
      body: file
    });
    if (!putRes.ok) throw new Error("Failed to upload file payload");
    uploadMeta = {};
  }

  // 3. Verify and Trigger Pipeline
  const verRes = await apiFetch(`/documents/upload/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      document_id: presigned.document_id,
      filename: file.name,
      object_key: uploadMeta.storage_path || presigned.object_key,
      file_hash: uploadMeta.file_hash,
      mime_type: uploadMeta.mime_type,
      size_bytes: uploadMeta.size_bytes,
    })
  });
  if (!verRes.ok) throw new Error("Failed to verify upload");

  return verRes.json();
};


export const listDocuments = async (workspaceId?: string): Promise<Document[]> => {
  const qs = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : '';
  const res = await apiFetch(`/documents${qs}`, {});
  if (!res.ok) throw new Error('Failed to sync workspace');
  return res.json();
};

export const getDocument = async (docId: string): Promise<Document> => {
  const res = await apiFetch(`/documents/${docId}`, {});
  if (!res.ok) throw new Error("Document fetch failed");
  return res.json();
};

// Phase 28 — Instant Text Clip
export interface ClipTextRequest {
  title?: string;
  content: string;
  source_hint?: 'email' | 'message' | 'web' | 'note' | 'other';
}

export interface ClipTextResponse {
  document_id: string;
  filename?: string;
  status: string;
  estimated_seconds: number;
  message?: string;
}

export const clipText = async (request: ClipTextRequest): Promise<ClipTextResponse> => {
  const res = await apiFetch('/documents/clip', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as any).detail || `Clip failed: ${res.status}`);
  }
  return res.json();
};

export const askQuestion = async (query: string, topK: number = 5): Promise<QueryResponse> => {
  const res = await apiFetch(`/query/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK, similarity_threshold: 0.1 })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Query failed");
  }
  return res.json();
};

export const askQuestionStream = async (
  query: string,
  topK: number,
  onStatus: (msg: string) => void,
  onMetadata: (metadata: any) => void,
  onToken: (token: string) => void,
  onError: (err: string) => void,
  onDone: () => void,
  signal?: AbortSignal,
  sessionId?: string,
  workspaceType?: string,
  onTrialStatus?: (status: { queriesUsed: number; queriesRemaining: number }) => void,
  onThinkingStage?: (stage: { stage: string; detail: string }) => void,
  comparisonMode?: boolean,
  onTrustReport?: (trust: any) => void,
) => {
  try {
    const res = await apiFetch(`/query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal,
      body: JSON.stringify({
        query,
        top_k: topK,
        similarity_threshold: 0.1,
        session_id: sessionId || null,
        workspace_type: workspaceType || "general",
        comparison_mode: comparisonMode || false,
      })
    });

    if (!res.ok) {
      // Phase 10 — trial exhausted: dispatch event so UpgradeModal appears
      if (res.status === 402) {
        const detail = await res.json().catch(() => ({}));
        if (detail?.detail?.error === "trial_exhausted") {
          if (typeof window !== "undefined") {
            window.dispatchEvent(new CustomEvent("trial:exhausted"));
          }
          return;
        }
      }
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Stream failed");
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No readable stream");

    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let lastTrialStatus: { queriesUsed: number; queriesRemaining: number } | null = null;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || "";

      for (const block of blocks) {
        if (!block.trim()) continue;
        const lines = block.split('\n');
        let event = "message";
        let data = "";

        for (const line of lines) {
          if (line.startsWith('event: ')) event = line.slice(7).trim();
          else if (line.startsWith('data: ')) data = line.slice(6).trim();
        }

        if (event === "status") {
          onStatus(JSON.parse(data).message);
        } else if (event === "metadata") {
          onMetadata(JSON.parse(data));
        } else if (event === "token") {
          onToken(JSON.parse(data).token);
        } else if (event === "thinking_stage") {
          onThinkingStage?.(JSON.parse(data) as { stage: string; detail: string });
        } else if (event === "trial_status") {
          const ts = JSON.parse(data) as { queries_used: number; queries_remaining: number };
          lastTrialStatus = { queriesUsed: ts.queries_used, queriesRemaining: ts.queries_remaining };
          onTrialStatus?.(lastTrialStatus);
        } else if (event === "trust_report") {
          onTrustReport?.(JSON.parse(data));
        } else if (event === "error") {
          const parsed = JSON.parse(data);
          onError(parsed.detail || parsed.message || "Error");
        } else if (event === "done") {
          onDone();
          // Phase 10 — show upgrade modal 500ms AFTER the last (5th) query response renders
          if (lastTrialStatus && lastTrialStatus.queriesRemaining === 0 && typeof window !== "undefined") {
            setTimeout(() => {
              window.dispatchEvent(new CustomEvent("trial:exhausted"));
            }, 500);
          }
        }
      }
    }
  } catch (err: any) {
    if (err.name === 'AbortError') {
      onError("Request cancelled.");
    } else {
      onError(err.message || "Stream interrupted");
    }
  }
};

export interface SubQuestion {
  id: string;
  label: string;
  text: string;
  marks: number;
  answer_key?: string;
  rubric?: string;
}

export interface Question {
  id: string;
  text: string;
  marks: number;
  difficulty?: string;
  bloom_taxonomy?: string;
  co_po_mapping?: string;
  topic?: string;
  sub_questions: SubQuestion[];
  answer_key?: string;
  rubric?: string;
}

export interface Section {
  id: string;
  title: string;
  instructions?: string;
  questions: Question[];
}

export interface ExamPaperContent {
  sections: Section[];
}

export interface ExamPaper {
  id: string;
  title: string;
  description?: string;
  content: ExamPaperContent;
  status: string;
  share_token?: string;
  created_at: string;
}

export const createExam = async (title: string, description?: string): Promise<ExamPaper> => {
  const res = await apiFetch(`/exams`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, description, content: { sections: [] } })
  });
  if (!res.ok) throw new Error("Failed to create exam");
  return res.json();
};

export const listExams = async (): Promise<ExamPaper[]> => {
  const res = await apiFetch(`/exams`, {});
  if (!res.ok) throw new Error("Failed to list exams");
  return res.json();
};

export const getExam = async (id: string): Promise<ExamPaper> => {
  const res = await apiFetch(`/exams/${id}`, {});
  if (!res.ok) throw new Error("Failed to get exam");
  return res.json();
};

export const updateExam = async (id: string, updates: any): Promise<ExamPaper> => {
  const res = await apiFetch(`/exams/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates)
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail?.[0]?.msg || error.detail || "Failed to update exam");
  }
  return res.json();
};

export const generateQuestion = async (topic: string, marks: number, difficulty: string = "medium"): Promise<{ question: Question, retrieval_diagnostics: any }> => {
  const res = await apiFetch(`/exams/generate/question`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, marks, difficulty })
  });
  if (!res.ok) throw new Error("Failed to generate question");
  return res.json();
};

export const generateDiagram = async (topic: string): Promise<{ type: string, content: string }> => {
  const res = await apiFetch(`/exams/generate/diagram?topic=${encodeURIComponent(topic)}`, {
    method: "POST"
  });
  if (!res.ok) throw new Error("Failed to generate diagram");
  return res.json();
};

export const exportToDocx = async (jobPayload: any): Promise<any> => {
  const res = await apiFetch(`/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ format: "docx", export_type: "exam", payload: jobPayload })
  });
  if (!res.ok) throw new Error("Failed to trigger export");
  return res.json();
};

export interface JobRole {
  id: string;
  title: string;
  department?: string;
  description?: string;
  status: string;
  created_at: string;
}

export const createJobRole = async (title: string, description?: string): Promise<JobRole> => {
  const res = await apiFetch(`/hr/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, description, requirements: {} })
  });
  if (!res.ok) throw new Error("Failed to create job role");
  return res.json();
};

export const listJobRoles = async (): Promise<JobRole[]> => {
  const res = await apiFetch(`/hr/jobs`, {});
  if (!res.ok) throw new Error("Failed to list jobs");
  return res.json();
};

export const getJobCandidates = async (jobId: string, searchParams?: { search?: string, min_score?: number, status?: string }): Promise<any[]> => {
  const query = new URLSearchParams();
  if (searchParams?.search) query.append('search', searchParams.search);
  if (searchParams?.min_score) query.append('min_score', searchParams.min_score.toString());
  if (searchParams?.status) query.append('status', searchParams.status);

  const res = await apiFetch(`/hr/jobs/${jobId}/candidates?${query.toString()}`, {});
  if (!res.ok) throw new Error("Failed to load candidates");
  return res.json();
};

export const processCandidate = async (jobId: string, documentId: string): Promise<any> => {
  const res = await apiFetch(`/hr/jobs/${jobId}/candidates/process?document_id=${documentId}`, {
    method: "POST"
  });
  if (!res.ok) throw new Error("Failed to process candidate");
  return res.json();
};

export const getJobAnalytics = async (jobId: string): Promise<any> => {
  const res = await apiFetch(`/hr/jobs/${jobId}/analytics`, {});
  if (!res.ok) throw new Error("Failed to load analytics");
  return res.json();
};

export const exportCandidatesCSV = async (jobId: string) => {
  const res = await apiFetch(`/hr/jobs/${jobId}/candidates/export/csv`, {});
  if (!res.ok) throw new Error("Failed to export candidates");

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `candidates_job_${jobId}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
};

export const getCandidateNotes = async (candidateId: string): Promise<any[]> => {
  const res = await apiFetch(`/hr/candidates/${candidateId}/notes`, {});
  if (!res.ok) throw new Error("Failed to load notes");
  return res.json();
};

export const addCandidateNote = async (candidateId: string, content: string): Promise<any> => {
  const res = await apiFetch(`/hr/candidates/${candidateId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content })
  });
  if (!res.ok) throw new Error("Failed to add note");
  return res.json();
};

export const listContracts = async (): Promise<any[]> => {
  const res = await apiFetch(`/legal/contracts`, {});
  if (!res.ok) throw new Error("Failed to list contracts");
  return res.json();
};

export const getContractClauses = async (contractId: string): Promise<any[]> => {
  const res = await apiFetch(`/legal/contracts/${contractId}/clauses`, {});
  if (!res.ok) throw new Error("Failed to load clauses");
  return res.json();
};

export const processContract = async (documentId: string): Promise<any> => {
  const res = await apiFetch(`/legal/contracts/process?document_id=${documentId}`, {
    method: "POST"
  });
  if (!res.ok) throw new Error("Failed to process contract");
  return res.json();
};

export const searchClauses = async (query: string): Promise<any[]> => {
  const params = new URLSearchParams();
  params.append('query', query);

  const res = await apiFetch(`/legal/clauses/search?${params.toString()}`, {});
  if (!res.ok) throw new Error("Search failed");
  return res.json();
};

export const listFinancialDocuments = async (): Promise<any[]> => {
  const res = await apiFetch(`/finance/documents`, {});
  if (!res.ok) throw new Error("Failed to list financial documents");
  return res.json();
};

export const listAuditFindings = async (): Promise<any[]> => {
  const res = await apiFetch(`/finance/findings`, {});
  if (!res.ok) throw new Error("Failed to load audit findings");
  return res.json();
};

export const processFinanceDocument = async (documentId: string): Promise<any> => {
  const res = await apiFetch(`/finance/process?document_id=${documentId}`, {
    method: "POST"
  });
  if (!res.ok) throw new Error("Failed to process document");
  return res.json();
};

export const searchTransactions = async (query: string): Promise<any[]> => {
  const params = new URLSearchParams();
  params.append('query', query);

  const res = await apiFetch(`/finance/transactions/search?${params.toString()}`, {});
  if (!res.ok) throw new Error("Search failed");
  return res.json();
};

export const listDecks = async (): Promise<any[]> => {
  const res = await apiFetch(`/study/decks`, {});
  if (!res.ok) throw new Error("Failed to load decks");
  return res.json();
};

export const listFlashcards = async (deckId: string): Promise<any[]> => {
  const res = await apiFetch(`/study/decks/${deckId}/flashcards`, {});
  if (!res.ok) throw new Error("Failed to load flashcards");
  return res.json();
};

export const processStudyDocument = async (documentId: string): Promise<any> => {
  const res = await apiFetch(`/study/process?document_id=${documentId}`, {
    method: "POST"
  });
  if (!res.ok) throw new Error("Failed to process document");
  return res.json();
};

export const searchStudyMaterial = async (query: string): Promise<any[]> => {
  const params = new URLSearchParams();
  params.append('query', query);

  const res = await apiFetch(`/study/search?${params.toString()}`, {});
  if (!res.ok) throw new Error("Search failed");
  return res.json();
};

export const listResearchProjects = async (): Promise<any[]> => {
  const res = await apiFetch(`/research/projects`, {});
  if (!res.ok) throw new Error("Failed to load projects");
  return res.json();
};

export const createResearchProject = async (title: string, description: string): Promise<any> => {
  const res = await apiFetch(`/research/projects?title=${encodeURIComponent(title)}&description=${encodeURIComponent(description)}`, {
    method: "POST"
  });
  if (!res.ok) throw new Error("Failed to create project");
  return res.json();
};

export const listResearchPapers = async (projectId: string): Promise<any[]> => {
  const res = await apiFetch(`/research/projects/${projectId}/papers`, {});
  if (!res.ok) throw new Error("Failed to load papers");
  return res.json();
};

export const listResearchFindings = async (paperId: string): Promise<any[]> => {
  const res = await apiFetch(`/research/papers/${paperId}/findings`, {});
  if (!res.ok) throw new Error("Failed to load findings");
  return res.json();
};

export const processResearchDocument = async (documentId: string, projectId: string): Promise<any> => {
  const res = await apiFetch(`/research/process?document_id=${documentId}&project_id=${projectId}`, {
    method: "POST"
  });
  if (!res.ok) throw new Error("Failed to process paper");
  return res.json();
};

export const runSynthesis = async (projectId: string): Promise<any> => {
  const res = await apiFetch(`/research/synthesis/${projectId}`, {});
  if (!res.ok) throw new Error("Synthesis failed");
  return res.json();
};

export const searchResearch = async (query: string): Promise<any[]> => {
  const params = new URLSearchParams();
  params.append('query', query);

  const res = await apiFetch(`/research/search?${params.toString()}`, {});
  if (!res.ok) throw new Error("Search failed");
  return res.json();
};

export interface ChatSession {
  id: string;
  title: string;
  workspace_type: string;
  is_pinned: boolean;
  is_archived: boolean;
  created_at?: string;
  workspace_id?: string;
  tags?: string[];
}

export const updateChatTags = async (id: string, tags: string[]): Promise<void> => {
  const res = await apiFetch(`/chats/${id}/tags`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tags }),
  });
  if (!res.ok) throw new Error("Failed to update tags");
};

export interface ChatMessage {
  id: string;
  role: string;
  content: string;
}

export const getChats = async (workspaceType: string = "general", limit: number = 50, offset: number = 0, search: string = ""): Promise<ChatSession[]> => {
  const params = new URLSearchParams({ workspace_type: workspaceType, limit: limit.toString(), offset: offset.toString() });
  if (search) params.append("search", search);
  const res = await apiFetch(`/chats?${params.toString()}`, {});
  if (!res.ok) throw new Error("Failed to load chats");
  return res.json();
};

export const createChat = async (title: string, workspaceType: string = "general"): Promise<ChatSession> => {
  const res = await apiFetch(`/chats`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, workspace_type: workspaceType })
  });
  if (!res.ok) throw new Error("Failed to create chat");
  return res.json();
};

export const updateChat = async (id: string, updates: Partial<ChatSession>): Promise<ChatSession> => {
  const res = await apiFetch(`/chats/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates)
  });
  if (!res.ok) throw new Error("Failed to update chat");
  return res.json();
};

export const deleteChat = async (id: string): Promise<void> => {
  const res = await apiFetch(`/chats/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete chat");
};

export const getChatMessages = async (sessionId: string, limit: number = 50, offset: number = 0): Promise<ChatMessage[]> => {
  const res = await apiFetch(`/chats/${sessionId}/messages?limit=${limit}&offset=${offset}`, {});
  if (!res.ok) throw new Error("Failed to load messages");
  return res.json();
};

export const createChatMessage = async (sessionId: string, role: string, content: string): Promise<ChatMessage> => {
  const res = await apiFetch(`/chats/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role, content })
  });
  if (!res.ok) throw new Error('Failed to send message');
  return res.json();
};

// ── Phase 10 — Registration & Email Verification ─────────────────────────────

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
}

export const register = async (payload: RegisterPayload): Promise<{ success: boolean; user_id: string; message: string }> => {
  const res = await apiFetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    if (typeof detail === "object" && detail?.error === "email_exists") {
      throw new Error("An account with this email already exists.");
    }
    throw new Error(typeof detail === "string" ? detail : "Registration failed.");
  }
  return res.json();
};

export const verifyEmail = async (otp: string): Promise<{ success: boolean; message: string }> => {
  const res = await apiFetch("/auth/verify-email", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ otp }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Verification failed.");
  }
  return res.json();
};

export const forgotPassword = async (email: string): Promise<{ message: string }> => {
  const res = await apiFetch("/auth/forgot-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  // Always treated as success — backend returns 202 regardless to prevent enumeration.
  return res.json().catch(() => ({ message: "If an account exists, a reset link has been sent." }));
};

export const resetPassword = async (token: string, newPassword: string): Promise<{ success: boolean; message: string }> => {
  const res = await apiFetch("/auth/reset-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Password reset failed.");
  }
  return res.json();
};

export const resendVerificationEmail = async (): Promise<{ success: boolean; message: string }> => {
  const res = await apiFetch("/auth/verify-email/resend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to resend verification.");
  }
  return res.json();
};

// ── Phase 10 — Billing ────────────────────────────────────────────────────────

export interface BillingStatus {
  plan: string;
  trial_queries_used: number;
  trial_limit: number;
  queries_remaining: number | null;
  email_verified: boolean;
  subscribed_at: string | null;
  subscription_ends_at: string | null;
}

export const getBillingStatus = async (): Promise<BillingStatus> => {
  const res = await apiFetch("/billing/status", {});
  if (!res.ok) throw new Error("Failed to load billing status");
  return res.json();
};

export const upgradePlan = async (
  plan: "go" | "plus" | "pro" | "professional" | "business" | "enterprise" = "plus",
  billing_cycle: "monthly" | "annual" = "monthly"
): Promise<{ success: boolean; plan: string; message: string }> => {
  const res = await apiFetch("/billing/upgrade", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan, billing_cycle }),
  });
  if (!res.ok) throw new Error("Upgrade failed");
  return res.json();
};

// ── TASK 3.2 — XHR Upload with Real Progress ──────────────────────────────────

export interface UploadResult {
  document_id: string;
  filename: string;
  storage_path?: string;
  object_key?: string;
  mime_type?: string;
  size_bytes?: number;
  file_hash?: string;
}

export const uploadDocumentWithProgress = (
  file: File,
  workspaceId: string,
  onProgress: (pct: number) => void
): Promise<UploadResult> => {
  return new Promise(async (resolve, reject) => {
    try {
      // 1. Get presigned URL / local upload info
      const preRes = await apiFetch(
        `/documents/upload/presigned?filename=${encodeURIComponent(file.name)}&content_type=${encodeURIComponent(file.type || 'application/pdf')}&file_size=${file.size}&workspace_id=${encodeURIComponent(workspaceId)}`
      );
      if (!preRes.ok) { reject(new Error('Failed to get upload URL')); return; }
      const presigned = await preRes.json();

      if (presigned.provider === 'local') {
        // Local multipart POST via XHR for real progress
        const formData = new FormData();
        formData.append('file', file);
        formData.append('workspace_id', presigned.workspace_id || workspaceId);

        const xhr = new XMLHttpRequest();
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const meta = JSON.parse(xhr.responseText);
              resolve({ document_id: presigned.document_id, filename: file.name, ...meta });
            } catch { reject(new Error('Invalid upload response')); }
          } else {
            try {
              const err = JSON.parse(xhr.responseText);
              reject(new Error(err.detail || `Upload failed: ${xhr.status}`));
            } catch { reject(new Error(`Upload failed: ${xhr.status}`)); }
          }
        };
        xhr.onerror = () => reject(new Error('Network error during upload'));
        xhr.open('POST', `${API_BASE}/documents/upload/local`);
        xhr.setRequestHeader('X-CSRF-Token', getCsrfToken());
        xhr.withCredentials = true;
        xhr.send(formData);
      } else {
        // S3 PUT via XHR
        const xhr = new XMLHttpRequest();
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve({ document_id: presigned.document_id, filename: file.name, object_key: presigned.object_key });
          } else {
            reject(new Error(`S3 upload failed: ${xhr.status}`));
          }
        };
        xhr.onerror = () => reject(new Error('Network error during S3 upload'));
        xhr.open('PUT', presigned.upload_url);
        xhr.setRequestHeader('Content-Type', file.type || 'application/pdf');
        xhr.send(file);
      }
    } catch (err: any) {
      reject(err);
    }
  });
};

// ── TASK 3.3 — Document Status Polling ───────────────────────────────────────

// ── Phase 16 — Phone OTP ─────────────────────────────────────────────────────

export const sendPhoneOTP = async (phone: string): Promise<{ message: string; expires_in: number }> => {
  const res = await apiFetch('/auth/send-phone-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to send OTP');
  }
  return res.json();
};

export const verifyPhone = async (otp: string): Promise<{ verified: boolean }> => {
  const res = await apiFetch('/auth/verify-phone', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ otp }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Phone verification failed');
  }
  return res.json();
};

export const pollDocumentStatus = (
  docId: string,
  onStatusChange: (status: string) => void,
  timeoutMs: number = 300000
): (() => void) => {
  let stopped = false;
  let intervalId: ReturnType<typeof setInterval> | null = null;

  const timeoutId = setTimeout(() => {
    stopped = true;
    if (intervalId) clearInterval(intervalId);
    onStatusChange('timeout');
  }, timeoutMs);

  intervalId = setInterval(async () => {
    if (stopped) return;
    try {
      const res = await apiFetch(`/documents/${docId}`, {});
      if (!res.ok) return;
      const doc = await res.json();
      const status: string = typeof doc.status === 'string' ? doc.status : String(doc.status);
      onStatusChange(status);
      if (status === 'READY' || status === 'FAILED') {
        stopped = true;
        clearTimeout(timeoutId);
        if (intervalId) clearInterval(intervalId);
      }
    } catch {
      // transient network error — keep polling
    }
  }, 2000);

  // Cleanup function
  return () => {
    stopped = true;
    clearTimeout(timeoutId);
    if (intervalId) clearInterval(intervalId);
  };
};

// ── Phase 22 — Collaboration / Session Sharing ────────────────────────────────

export interface ShareSessionResult {
  share_url: string;
  share_token: string;
  share_permissions: string;
  max_collaborators: number;
}

export interface SharedSessionMessage {
  id: string;
  role: string;
  content: string;
  created_at?: string;
}

export interface SharedSession {
  id: string;
  title: string;
  workspace_type: string;
  share_permissions: string;
  owner_id: string;
  messages: SharedSessionMessage[];
}

export const shareSession = async (
  sessionId: string,
  share_permissions: "view_only" | "view_and_ask" = "view_and_ask"
): Promise<ShareSessionResult> => {
  const res = await apiFetch(`/chats/${sessionId}/share`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ share_permissions }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as any).detail ?? "Failed to generate share link");
  }
  return res.json();
};

export const unshareSession = async (sessionId: string): Promise<void> => {
  const res = await apiFetch(`/chats/${sessionId}/share`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to stop sharing");
};

export const getSharedSession = async (token: string): Promise<SharedSession> => {
  const res = await fetch(`${API_BASE}/shared/${token}`);
  if (!res.ok) throw new Error("Shared session not found");
  return res.json();
};

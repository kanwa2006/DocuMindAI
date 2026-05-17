export interface Document {
  id: string;
  filename: string;
  status: 'PENDING_UPLOAD' | 'UPLOADED' | 'PROCESSING' | 'EXTRACTED' | 'READY' | 'FAILED';
  workspace_id?: string;
  created_at: string;
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
}

export const API_BASE = process.env.NEXT_PUBLIC_API_URL;

if (!API_BASE) {
  console.warn("NEXT_PUBLIC_API_URL is not set. API calls will fail.");
}

let csrfToken = '';

// Fetch CSRF on boot
if (typeof window !== 'undefined') {
  fetch(`${API_BASE}/csrf-token`, { credentials: 'include' })
    .then(res => res.json())
    .then(data => { csrfToken = data.csrf_token; })
    .catch(() => { });
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

const apiFetch = async (endpoint: string, options: RequestInit = {}, _retried = false): Promise<Response> => {
  const isMutation = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method?.toUpperCase() || 'GET');
  const headers = new Headers(options.headers || {});
  if (isMutation && csrfToken) headers.set('X-CSRF-Token', csrfToken);

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
  signal?: AbortSignal
) => {
  try {
    const res = await apiFetch(`/query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal,
      body: JSON.stringify({ query, top_k: topK, similarity_threshold: 0.1 })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Stream failed");
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No readable stream");

    const decoder = new TextDecoder("utf-8");
    let buffer = "";

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
        } else if (event === "error") {
          onError(JSON.parse(data).detail);
        } else if (event === "done") {
          onDone();
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
}

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
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role, content })
  });
  if (!res.ok) throw new Error("Failed to send message");
  return res.json();
};

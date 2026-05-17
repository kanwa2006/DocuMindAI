"use client";

import { useState, useEffect, useRef } from "react";
import { Toaster, toast } from "react-hot-toast";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import React, { memo } from "react";
import { uploadDocument, askQuestionStream, listDocuments, getDocument, Document, QueryResponse, getChats, createChat, getChatMessages, createChatMessage, ChatMessage, updateChat } from "../lib/api";

const MemoizedMessage = memo(({ msg, chatId }: { msg: ChatMessage, chatId: string | null }) => {
  let parsedRes: any = null;
  let textContent = msg.content;
  if (msg.role === 'assistant') {
    try {
      parsedRes = JSON.parse(msg.content);
      textContent = parsedRes.answer || "";
    } catch (e) {
      // legacy plain text fallback
    }
  }

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const handleShare = (id: string) => {
    const url = `${window.location.origin}${window.location.pathname}?chat=${id}`;
    navigator.clipboard.writeText(url);
    toast.success("Link copied to clipboard");
  };

  return (
    <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      {msg.role === 'user' ? (
        <div className="bg-black/5 dark:bg-white/10 px-5 py-3 rounded-2xl rounded-tr-sm max-w-[80%] text-[15px] shadow-sm">
          {msg.content}
        </div>
      ) : (
        <div className="bg-white dark:bg-black border border-black/10 dark:border-white/10 shadow-sm px-5 py-4 rounded-2xl rounded-tl-sm w-full max-w-[90%] relative group">
          <div className="flex justify-between items-center mb-4 pb-3 border-b border-black/5 dark:border-white/5">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded bg-black dark:bg-white flex items-center justify-center text-white dark:text-black text-[10px] font-bold tracking-tighter">D</div>
              <span className="text-xs font-semibold uppercase tracking-widest text-black/70 dark:text-white/70">DocuMindAI</span>
            </div>
            {(parsedRes && parsedRes.confidence_score > 0) && (
               <div className="flex items-center gap-1.5 px-2 py-1 rounded-md border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 transition-colors hover:bg-black/10 dark:hover:bg-white/10 cursor-default" title="AI Retrieval Confidence Score">
                 <div className="w-1.5 h-1.5 rounded-full bg-black dark:bg-white" style={{ opacity: Math.max(0.2, parsedRes.confidence_score) }}></div>
                 <span className="text-[10px] font-mono font-medium tracking-wide">
                   {(parsedRes.confidence_score * 100).toFixed(1)}%
                 </span>
               </div>
            )}
          </div>
          <div className="text-[15px] leading-relaxed whitespace-pre-wrap markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{textContent}</ReactMarkdown>
          </div>

          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
            <button onClick={() => handleCopy(textContent)} className="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded text-black/50 dark:text-white/50 transition-colors" title="Copy">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
            </button>
            <button onClick={() => chatId && handleShare(chatId)} className="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded text-black/50 dark:text-white/50 transition-colors" title="Share">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" /></svg>
            </button>
          </div>

          {(parsedRes && parsedRes.evidence && parsedRes.evidence.length > 0) && (
            <div className="mt-5 pt-4 border-t border-black/5 dark:border-white/5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-black/40 dark:text-white/40 mb-3 block">Retrieved Evidence</span>
              <div className="flex gap-2 flex-wrap">
                {parsedRes.evidence.slice(0,4).map((chunk: any, i: number) => (
                  <div key={i} className="group/citation relative flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 hover:border-black/30 dark:hover:border-white/30 transition-all cursor-default">
                    <svg className="w-3 h-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                    <span className="truncate max-w-[150px] font-medium">{chunk.filename}</span>
                    <span className="opacity-50 text-[10px]">p.{chunk.page_number}</span>
                    
                    {/* Hover Preview Tooltip */}
                    <div className="absolute bottom-full left-0 mb-2 w-64 p-3 bg-black dark:bg-white text-white dark:text-black text-xs rounded-lg shadow-xl opacity-0 invisible group-hover/citation:opacity-100 group-hover/citation:visible transition-all z-50 pointer-events-none">
                      <div className="font-semibold mb-1 border-b border-white/20 dark:border-black/20 pb-1">{chunk.filename} (Page {chunk.page_number})</div>
                      <div className="line-clamp-4 leading-relaxed opacity-90">{chunk.text_content || "Content preview not available."}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

export default function WorkspaceUI({ workspaceType = "general" }: { workspaceType?: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [docs, setDocs] = useState<Document[]>([]);
  const [activeDoc, setActiveDoc] = useState<Document | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const pollingIntervalsRef = useRef<NodeJS.Timeout[]>([]);
  
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const chatId = searchParams.get('chat');

  // Load chat history or create new session
  useEffect(() => {
    const initChat = async () => {
      try {
        if (chatId) {
          const msgs = await getChatMessages(chatId);
          setHistory(msgs);
        } else {
          // fetch chats for this workspace
          const chats = await getChats(workspaceType);
          if (chats.length > 0) {
            router.replace(`${pathname}?chat=${chats[0].id}`);
          } else {
            const newChat = await createChat(`New ${workspaceType} chat`, workspaceType);
            router.replace(`${pathname}?chat=${newChat.id}`);
          }
        }
      } catch (err) {
        console.error("Failed to init chat", err);
      }
    };
    initChat();
    
    return () => {
      // Cleanup all active polling intervals on unmount
      pollingIntervalsRef.current.forEach(clearInterval);
      
      // Cleanup active streaming connections
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [chatId, workspaceType, pathname, router]);

  // Restore draft when switching chats
  useEffect(() => {
    if (chatId) {
      const savedDraft = sessionStorage.getItem(`draft_${chatId}`);
      if (savedDraft) setQuery(savedDraft);
      else setQuery("");
    }
  }, [chatId]);

  const handleQueryChange = (val: string) => {
    setQuery(val);
    if (chatId) {
      sessionStorage.setItem(`draft_${chatId}`, val);
    }
  };

  // Persist current active workspace
  useEffect(() => {
    localStorage.setItem("lastActiveWorkspace", pathname || "/");
  }, [pathname]);

  // 1. Workspace-wide Document Synchronization
  useEffect(() => {
    const syncWorkspace = async () => {
      try {
        const fetchedDocs = await listDocuments();
        
        // Filter by workspace using local storage memory
        const wsDocs = JSON.parse(localStorage.getItem(`docs_${workspaceType}`) || '[]');
        const filteredDocs = fetchedDocs.filter(d => wsDocs.includes(d.id));
        
        setDocs(filteredDocs);
        if (filteredDocs.length > 0) {
          setActiveDoc(filteredDocs[0]);
        } else {
          setActiveDoc(null);
        }
      } catch (err: any) {
        toast.error("Failed to sync workspace connection");
      }
    };
    syncWorkspace();
  }, [workspaceType]);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;
    
    setLoading(true);
    const toastId = toast.loading("Uploading document securely...");
    
    try {
      const uploadedDoc = await uploadDocument(selectedFile);
      
      // Save workspace mapping in localStorage since backend schema cannot be modified
      const wsDocs = JSON.parse(localStorage.getItem(`docs_${workspaceType}`) || '[]');
      wsDocs.push(uploadedDoc.id);
      localStorage.setItem(`docs_${workspaceType}`, JSON.stringify(wsDocs));
      
      setDocs(prev => [uploadedDoc, ...prev]);
      setActiveDoc(uploadedDoc);
      toast.success("Document uploaded. Starting pipeline...", { id: toastId });

      const interval = setInterval(async () => {
        try {
          const statusDoc = await getDocument(uploadedDoc.id);
          setActiveDoc(statusDoc);
          setDocs(prev => prev.map(d => d.id === statusDoc.id ? statusDoc : d));
          if (statusDoc.status === 'READY') {
            toast.success("Extraction complete!", { id: toastId });
            clearInterval(interval);
            setLoading(false);
          } else if (statusDoc.status === 'FAILED') {
            toast.error("Extraction failed.", { id: toastId });
            clearInterval(interval);
            setLoading(false);
          }
        } catch(err) {
          console.warn("Polling interval warning:", err);
        }
      }, 2000);
      pollingIntervalsRef.current.push(interval);
    } catch (err: any) {
      toast.error(err.message || "Upload failed.", { id: toastId });
    } finally {
      setLoading(false);
      // reset file input
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const handleShare = (id: string) => {
    const url = `${window.location.origin}${pathname}?chat=${id}`;
    navigator.clipboard.writeText(url);
    toast.success("Link copied to clipboard");
  };

  const handleStopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setLoading(false);
      toast("Generation stopped.", { icon: "🛑" });
      
      setResponse(currentRes => {
        if (currentRes && chatId) {
          const payload = JSON.stringify(currentRes);
          createChatMessage(chatId, 'assistant', payload).then(savedMsg => {
            setHistory(prev => [...prev, savedMsg]);
          });
        }
        return null;
      });
      setQuery("");
    }
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;
    if (!activeDoc || activeDoc.status !== 'READY') {
      toast.error("Please wait for document to be ready.");
      return;
    }

    setLoading(true);
    abortControllerRef.current = new AbortController();
    
    // Save user message
    if (chatId) {
      await createChatMessage(chatId, 'user', query);
      setHistory(prev => [...prev, { id: Date.now().toString(), role: 'user', content: query }]);
      
      // Auto-title generation if this is the first real question
      if (history.length === 0) {
        let newTitle = query.length > 40 ? query.substring(0, 37) + "..." : query;
        try {
          // Attempt to use the existing LLM pipeline to generate a clean, short title
          const { apiFetch } = require('../lib/api');
          const titleRes = await apiFetch('/query/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              query: `Generate a concise, 3-word title summarizing this request: "${query}". Respond ONLY with the title, no quotes.`, 
              top_k: 1, 
              similarity_threshold: 0.0 
            })
          });
          if (titleRes.ok) {
            const titleData = await titleRes.json();
            if (titleData && titleData.answer) {
              const cleaned = titleData.answer.replace(/["']/g, '').trim();
              if (cleaned.length > 0 && cleaned.length < 50) {
                newTitle = cleaned;
              }
            }
          }
        } catch (err) {
          console.warn("LLM title generation failed, using fallback heuristic.", err);
        }
        
        updateChat(chatId, { title: newTitle }).then(() => {
          window.dispatchEvent(new CustomEvent("chat-title-updated", { detail: { id: chatId, title: newTitle } }));
        }).catch(console.error);
      }
    }

    if (chatId) sessionStorage.removeItem(`draft_${chatId}`);

    setResponse({
      query,
      answer: "",
      confidence_score: 0,
      evidence: [],
      diagnostics: {
        embedding_time_sec: 0, database_time_sec: 0, reranking_time_sec: 0, 
        generation_time_sec: 0, total_time_sec: 0, candidates_retrieved: 0, 
        evidence_accepted: 0, estimated_tokens: 0
      }
    });

    const toastId = toast.loading("Initializing secure stream...");
    
    try {
      await askQuestionStream(
        query,
        5,
        (msg) => toast.loading(msg, { id: toastId }),
        (metadata) => {
          setResponse((prev) => prev ? {
            ...prev,
            confidence_score: metadata.confidence_score,
            evidence: metadata.evidence,
            diagnostics: {
              ...prev.diagnostics,
              ...metadata.tracing.retrieval_tracing,
              reranking_time_sec: metadata.tracing.reranking_time_sec,
              total_time_sec: metadata.tracing.total_grounding_time_sec,
              candidates_retrieved: metadata.tracing.candidates_retrieved,
              evidence_accepted: metadata.tracing.evidence_accepted,
              estimated_tokens: metadata.tracing.estimated_tokens
            }
          } : null);
        },
        (token) => {
          setResponse((prev) => prev ? { ...prev, answer: prev.answer + token } : null);
        },
        (err) => {
          if (err !== "Request cancelled.") {
            toast.error(err, { id: toastId });
          }
          setLoading(false);
          abortControllerRef.current = null;
        },
        async () => {
          if (!abortControllerRef.current) return; // aborted
          toast.success("Streaming complete.", { id: toastId });
          setLoading(false);
          abortControllerRef.current = null;
          
          // Save assistant message when done
          setResponse(currentRes => {
            if (currentRes && chatId) {
              const payload = JSON.stringify(currentRes);
              createChatMessage(chatId, 'assistant', payload).then(savedMsg => {
                setHistory(prev => [...prev, savedMsg]);
              });
            }
            return currentRes;
          });
          
          // Clear current response to flow into history
          setTimeout(() => {
            setResponse(null);
            setQuery("");
          }, 100);
        },
        abortControllerRef.current?.signal
      );
    } catch (err: any) {
      toast.error(err.message || "Query failed to execute.", { id: toastId });
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col px-4 md:px-8 py-6 pb-0 w-full max-w-6xl mx-auto">
      <Toaster position="top-center" toastOptions={{ className: "dark:bg-black dark:text-white border dark:border-white/10 shadow-lg rounded-md text-sm" }} />
      
      {/* Response Area */}
      <div className="flex-1 overflow-y-auto mb-6 pr-2">
        {(!response && !loading && history.length === 0) && (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-6 opacity-60 px-4">
            <div className="w-16 h-16 rounded-2xl bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 flex items-center justify-center">
              <svg className="w-8 h-8 text-black/40 dark:text-white/40" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
            </div>
            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-black dark:text-white mb-2">How can I help you today?</h2>
              <p className="text-[15px] font-medium text-black/50 dark:text-white/50 max-w-md mx-auto leading-relaxed">Upload a document below to securely extract insights, summarize research, and ask questions across your enterprise data.</p>
            </div>
          </div>
        )}

        <div className="space-y-6 pb-10">
          {/* History Mapping */}
          {history.map((msg, idx) => (
            <MemoizedMessage key={msg.id || idx} msg={msg} chatId={chatId} />
          ))}

          {/* Active Streaming Response */}
          {response && (
            <>
              {/* User Query */}
              <div className="flex justify-end">
                <div className="bg-black/5 dark:bg-white/10 px-5 py-3 rounded-2xl rounded-tr-sm max-w-[80%] text-[15px] shadow-sm">
                  {response.query}
                </div>
              </div>

            {/* AI Response */}
            <div className="flex justify-start">
              <div className="bg-white dark:bg-black border border-black/10 dark:border-white/10 shadow-sm px-5 py-4 rounded-2xl rounded-tl-sm w-full max-w-[90%] relative group">
                {/* Header with confidence */}
                <div className="flex justify-between items-center mb-4 pb-3 border-b border-black/5 dark:border-white/5">
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded bg-black dark:bg-white flex items-center justify-center text-white dark:text-black text-[10px] font-bold tracking-tighter">D</div>
                    <span className="text-xs font-semibold uppercase tracking-widest text-black/70 dark:text-white/70 animate-pulse">DocuMindAI</span>
                  </div>
                  {response.confidence_score > 0 && (
                     <div className="flex items-center gap-1.5 px-2 py-1 rounded-md border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 transition-colors hover:bg-black/10 dark:hover:bg-white/10 cursor-default" title="AI Retrieval Confidence Score">
                       <div className="w-1.5 h-1.5 rounded-full bg-black dark:bg-white" style={{ opacity: Math.max(0.2, response.confidence_score) }}></div>
                       <span className="text-[10px] font-mono font-medium tracking-wide">
                         {(response.confidence_score * 100).toFixed(1)}%
                       </span>
                     </div>
                  )}
                </div>
                
                <div className="text-[15px] leading-relaxed whitespace-pre-wrap markdown-body">
                   <ReactMarkdown remarkPlugins={[remarkGfm]}>{response.answer || "Thinking..."}</ReactMarkdown>
                   {loading && <span className="inline-block w-2 h-4 ml-1 bg-black dark:bg-white animate-pulse align-middle" />}
                </div>

                {loading && (
                  <div className="mt-4 pt-4 border-t border-black/5 dark:border-white/5 flex justify-end">
                    <button onClick={handleStopGenerating} className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium border border-black/20 dark:border-white/20 rounded-md hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" /></svg>
                      Stop Generating
                    </button>
                  </div>
                )}

                {/* Actions */}
                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                  <button onClick={() => handleCopy(response.answer)} className="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded text-black/50 dark:text-white/50 transition-colors" title="Copy">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                  </button>
                  <button onClick={() => chatId && handleShare(chatId)} className="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded text-black/50 dark:text-white/50 transition-colors" title="Share">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" /></svg>
                  </button>
                </div>

                {/* Citations if any */}
                {response.evidence && response.evidence.length > 0 && (
                  <div className="mt-5 pt-4 border-t border-black/5 dark:border-white/5 animate-in fade-in slide-in-from-bottom-2 duration-500">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-black/40 dark:text-white/40 mb-3 block">Retrieved Evidence</span>
                    <div className="flex gap-2 flex-wrap">
                      {response.evidence.slice(0,4).map((chunk, idx) => (
                        <div key={idx} className="group/citation relative flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 hover:border-black/30 dark:hover:border-white/30 transition-all cursor-default">
                          <svg className="w-3 h-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                          <span className="truncate max-w-[150px] font-medium">{chunk.filename}</span>
                          <span className="opacity-50 text-[10px]">p.{chunk.page_number}</span>
                          
                          {/* Hover Preview Tooltip */}
                          <div className="absolute bottom-full left-0 mb-2 w-64 p-3 bg-black dark:bg-white text-white dark:text-black text-xs rounded-lg shadow-xl opacity-0 invisible group-hover/citation:opacity-100 group-hover/citation:visible transition-all z-50 pointer-events-none">
                            <div className="font-semibold mb-1 border-b border-white/20 dark:border-black/20 pb-1">{chunk.filename} (Page {chunk.page_number})</div>
                            <div className="line-clamp-4 leading-relaxed opacity-90">{chunk.text_content || "Content preview not available."}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
            </>
          )}
          <div ref={chatEndRef} />
        </div>
      </div>

      {/* Bottom Area */}
      <div className="w-full pb-6 pt-2 bg-white/90 dark:bg-black/90 backdrop-blur-sm z-10 sticky bottom-0">
        {/* Document Tray */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2 px-1">
             <span className="text-xs font-semibold text-black/50 dark:text-white/50 tracking-wider">DOCUMENTS</span>
             <button className="text-xs font-medium text-black/50 hover:text-black dark:text-white/50 dark:hover:text-white">View All</button>
          </div>
          <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin">
            <div 
              onClick={handleUploadClick}
              className="flex-shrink-0 w-32 h-24 border-2 border-dashed border-black/20 dark:border-white/20 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 transition-colors group"
            >
              <svg className="w-6 h-6 text-black/30 dark:text-white/30 group-hover:text-black dark:group-hover:text-white mb-1 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
              <span className="text-xs font-medium text-black/50 dark:text-white/50 group-hover:text-black dark:group-hover:text-white transition-colors">Upload</span>
            </div>
            
            <input type="file" className="hidden" accept=".pdf" ref={fileInputRef} onChange={handleFileChange} />

            {docs.map(d => (
              <div 
                key={d.id} 
                onClick={() => setActiveDoc(d)}
                className={`flex-shrink-0 w-32 h-24 border rounded-xl p-3 flex flex-col justify-between cursor-pointer transition-all ${activeDoc?.id === d.id ? 'border-black dark:border-white shadow-md bg-black/5 dark:bg-white/5' : 'border-black/10 dark:border-white/10 hover:border-black/30 dark:hover:border-white/30'}`}
              >
                <div className="text-xs font-medium truncate" title={d.filename}>{d.filename}</div>
                <div className="flex justify-between items-end">
                  <div className={`w-2 h-2 rounded-full ${d.status === 'READY' ? 'bg-black dark:bg-white' : d.status === 'FAILED' ? 'bg-black/5 dark:bg-white/5' : 'bg-black/30 dark:bg-white/30 animate-pulse'}`}></div>
                  <div className="text-[10px] text-black/50 dark:text-white/50">{d.status}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Input Area */}
        <form onSubmit={handleAsk} className="relative">
          <button 
            type="button" 
            onClick={handleUploadClick}
            className="absolute left-3 top-1/2 -translate-y-1/2 p-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-full text-black/50 dark:text-white/50"
            title="Upload Document"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
          </button>
          
          <input 
            type="text" 
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            disabled={!activeDoc || activeDoc.status !== 'READY' || loading}
            placeholder={!activeDoc ? "Upload a document to ask anything..." : activeDoc.status !== 'READY' ? "Processing document..." : "Ask Anything..."}
            className="w-full pl-14 pr-12 py-4 bg-white dark:bg-black border border-black/10 dark:border-white/10 hover:border-black/20 dark:hover:border-white/20 focus:border-black dark:focus:border-white rounded-2xl shadow-sm focus:outline-none focus:ring-0 transition-all text-sm disabled:opacity-50"
          />
          
          <button 
            type="submit" 
            disabled={!query || loading}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-black dark:bg-white text-white dark:text-black rounded-xl hover:opacity-80 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {loading ? (
               <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
            ) : (
               <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

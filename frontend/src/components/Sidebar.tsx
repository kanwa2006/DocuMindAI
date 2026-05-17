"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useVirtualizer } from "@tanstack/react-virtual";
import LogoutButton from "./LogoutButton";
import { getChats, createChat, updateChat, deleteChat, ChatSession } from "@/lib/api";

export default function Sidebar({ isOpen, setIsOpen }: { isOpen: boolean, setIsOpen: (val: boolean) => void }) {
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const parentRef = useRef<HTMLDivElement>(null);
  
  const pathname = usePathname();
  const router = useRouter();
  
  const workspaceType = pathname === "/" || pathname === "/dashboard" ? "general" 
    : pathname.replace("/", "");

  const loadChats = async (reset: boolean = false, overrideSearch: string | null = null) => {
    try {
      const currentOffset = reset ? 0 : offset;
      const currentSearch = overrideSearch !== null ? overrideSearch : searchQuery;
      const fetchedChats = await getChats(workspaceType, 50, currentOffset, currentSearch);
      
      if (reset) {
        setChats(fetchedChats.sort((a, b) => Number(b.is_pinned) - Number(a.is_pinned)));
        setOffset(50);
      } else {
        setChats(prev => [...prev, ...fetchedChats].sort((a, b) => Number(b.is_pinned) - Number(a.is_pinned)));
        setOffset(currentOffset + 50);
      }
      
      setHasMore(fetchedChats.length === 50);
    } catch (err) {
      console.error("Failed to load chats", err);
    } finally {
      setIsLoadingMore(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      loadChats(true, searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, workspaceType]);

  useEffect(() => {
    const handleChatsUpdated = () => loadChats(true);
    const handleChatTitleUpdated = (e: any) => {
      setChats(prev => prev.map(c => c.id === e.detail.id ? { ...c, title: e.detail.title } : c));
    };
    window.addEventListener("chats-updated", handleChatsUpdated);
    window.addEventListener("chat-title-updated", handleChatTitleUpdated);
    return () => {
      window.removeEventListener("chats-updated", handleChatsUpdated);
      window.removeEventListener("chat-title-updated", handleChatTitleUpdated);
    };
  }, [workspaceType]);

  const rowVirtualizer = useVirtualizer({
    count: chats.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 36, // 36px height per chat item
    overscan: 5,
  });

  const handleNewChat = async () => {
    try {
      const chat = await createChat("New " + workspaceType + " Chat", workspaceType);
      setChats([chat, ...chats].sort((a, b) => Number(b.is_pinned) - Number(a.is_pinned)));
      router.push(`${pathname}?chat=${chat.id}`);
    } catch (err) {
      console.error("Failed to create chat", err);
    }
  };

  const handleRename = async (e: React.MouseEvent, chat: ChatSession) => {
    e.stopPropagation();
    const newTitle = prompt("Enter new chat name:", chat.title);
    if (!newTitle || newTitle === chat.title) return;
    try {
      const updated = await updateChat(chat.id, { title: newTitle });
      setChats(chats.map(c => c.id === chat.id ? updated : c));
    } catch (err) {
      console.error("Failed to rename", err);
    }
  };

  const handleTogglePin = async (e: React.MouseEvent, chat: ChatSession) => {
    e.stopPropagation();
    try {
      const updated = await updateChat(chat.id, { is_pinned: !chat.is_pinned });
      setChats(chats.map(c => c.id === chat.id ? updated : c).sort((a, b) => Number(b.is_pinned) - Number(a.is_pinned)));
    } catch (err) {
      console.error("Failed to pin/unpin", err);
    }
  };

  const handleToggleArchive = async (e: React.MouseEvent, chat: ChatSession) => {
    e.stopPropagation();
    try {
      const updated = await updateChat(chat.id, { is_archived: !chat.is_archived });
      // Remove from sidebar if archived, or keep with visual indicator depending on logic.
      // Usually archived chats don't show in Recents.
      if (updated.is_archived) {
        setChats(chats.filter(c => c.id !== chat.id));
      } else {
        setChats(chats.map(c => c.id === chat.id ? updated : c));
      }
    } catch (err) {
      console.error("Failed to archive", err);
    }
  };

  const handleDelete = async (e: React.MouseEvent, chatId: string) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this chat?")) return;
    try {
      await deleteChat(chatId);
      setChats(chats.filter(c => c.id !== chatId));
      // if active chat deleted, push to root
      if (typeof window !== 'undefined' && window.location.search.includes(`chat=${chatId}`)) {
        router.push(pathname);
      }
    } catch (err) {
      console.error("Failed to delete", err);
    }
  };

  return (
    <nav className={`flex-shrink-0 border-r border-black/10 dark:border-white/10 flex flex-col h-screen bg-white dark:bg-black text-black dark:text-white transition-all duration-300 ease-in-out shadow-[4px_0_24px_rgba(0,0,0,0.02)] dark:shadow-[4px_0_24px_rgba(255,255,255,0.02)] z-50 overflow-hidden ${isOpen ? 'w-64 absolute md:relative translate-x-0' : 'w-0 md:w-16 -translate-x-full md:translate-x-0'}`}>
      
      {/* Collapsed State (Desktop Only) */}
      {!isOpen && (
        <div className="w-16 hidden md:flex flex-col items-center py-4 h-full">
          <button onClick={() => setIsOpen(true)} className="p-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-md transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
          </button>
        </div>
      )}

      {/* Expanded State */}
      <div className={`flex flex-col h-full w-64 ${!isOpen ? 'opacity-0 pointer-events-none hidden' : 'opacity-100'}`}>
        <div className="p-4 flex items-center justify-between border-b border-black/5 dark:border-white/5 flex-shrink-0">
          <Link href="/" className="font-bold text-lg tracking-tight flex items-center gap-2">
            <div className="w-6 h-6 rounded-sm bg-black dark:bg-white flex items-center justify-center text-white dark:text-black text-xs font-serif font-bold">D</div>
            DocuMindAI
          </Link>
          <button onClick={() => setIsOpen(false)} className="p-1 hover:bg-black/5 dark:hover:bg-white/5 rounded-md transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          </button>
        </div>

      <div className="p-4 flex-1 overflow-hidden flex flex-col gap-4">
        <button onClick={handleNewChat} className="w-full flex-shrink-0 flex items-center gap-2 px-3 py-2 border border-black/10 dark:border-white/10 rounded-md hover:bg-black/5 dark:hover:bg-white/5 transition-colors font-medium text-sm">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
          NEW CHAT
        </button>

        <div className="relative flex-shrink-0">
          <svg className="w-4 h-4 absolute left-3 top-2.5 text-black/40 dark:text-white/40" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
          <input 
            type="text" 
            placeholder="Search CHATS" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-transparent border border-black/10 dark:border-white/10 rounded-md text-sm focus:outline-none focus:border-black/30 dark:focus:border-white/30 transition-colors" 
          />
        </div>

        <div className="flex-1 min-h-0 flex flex-col">
          <div className="text-xs font-semibold text-black/50 dark:text-white/50 tracking-wider mb-2 px-1 flex-shrink-0">Recents</div>
          <div className="flex-1 overflow-y-auto pr-1" ref={parentRef}>
            {chats.length === 0 && (
              <div className="px-3 py-6 flex flex-col items-center justify-center text-center opacity-50 space-y-2 mt-4">
                <svg className="w-8 h-8 text-black/20 dark:text-white/20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                <div className="text-xs font-medium">{searchQuery ? "No results found." : "No chats yet."}</div>
                {searchQuery && <div className="text-[10px]">Try a different search term.</div>}
              </div>
            )}
            
            <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, width: '100%', position: 'relative' }}>
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const chat = chats[virtualRow.index];
                return (
                  <div 
                    key={chat.id} 
                    style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: `${virtualRow.size}px`, transform: `translateY(${virtualRow.start}px)` }}
                    className="px-0 py-0.5"
                  >
                    <div onClick={() => router.push(`${pathname}?chat=${chat.id}`)} className="group h-full flex items-center justify-between px-3 rounded-md hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer text-sm">
                      <div className="flex items-center gap-2 truncate">
                        <svg className="w-3.5 h-3.5 text-black/40 dark:text-white/40 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
                        <span className="truncate">{chat.title}</span>
                      </div>
                      <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-opacity bg-white dark:bg-black pl-2">
                        <button onClick={(e) => handleRename(e, chat)} className="p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded" title="Rename"><svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg></button>
                        <button onClick={(e) => handleTogglePin(e, chat)} className="p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded" title={chat.is_pinned ? "Unpin" : "Pin"}><svg className={`w-3 h-3 ${chat.is_pinned ? 'fill-current' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" /></svg></button>
                        <button onClick={(e) => handleToggleArchive(e, chat)} className="p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded" title="Archive"><svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" /></svg></button>
                        <button onClick={(e) => handleDelete(e, chat.id)} className="p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded" title="Delete"><svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg></button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {hasMore && (
              <button 
                onClick={() => { setIsLoadingMore(true); loadChats(false); }}
                disabled={isLoadingMore}
                className="mt-2 w-full text-xs py-1.5 rounded bg-black/5 dark:bg-white/5 text-black/60 dark:text-white/60 hover:text-black dark:hover:text-white transition-colors flex-shrink-0"
              >
                {isLoadingMore ? "Loading..." : "Load More"}
              </button>
            )}
          </div>
        </div>

        <div className="flex-shrink-0 pt-4 border-t border-black/5 dark:border-white/5">
          <div className="text-xs font-semibold text-black/50 dark:text-white/50 tracking-wider mb-2 mt-4 px-1">Workspaces</div>
          <div className="space-y-1">
            <Link href="/" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer text-sm">General Workspace</Link>
            <Link href="/exam" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer text-sm">Teacher Workspace</Link>
            <Link href="/hr" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer text-sm">HR Workspace</Link>
            <Link href="/study" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer text-sm">Student Workspace</Link>
            <Link href="/research" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer text-sm">Research Workspace</Link>
            <Link href="/legal" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer text-sm">Legal Workspace</Link>
            <Link href="/finance" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer text-sm">CA Workspace</Link>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-black/5 dark:border-white/5">
        <button className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer text-sm mb-2 font-medium">
          ALL CHATS
        </button>
        <LogoutButton />
        </div>
      </div>
    </nav>
  );
}

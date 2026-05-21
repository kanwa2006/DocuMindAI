"use client";

import { useState } from "react";
import { API_BASE, getCsrfToken } from "@/lib/api";
import { toast } from "react-hot-toast";

interface BookmarkButtonProps {
  messageId: string;
  sessionId: string;
  content: string;
  citations?: any[];
  workspace?: string;
  initialBookmarked?: boolean;
  bookmarkId?: string;
}

export default function BookmarkButton({
  messageId,
  sessionId,
  content,
  citations,
  workspace = "general",
  initialBookmarked = false,
  bookmarkId: initialBookmarkId,
}: BookmarkButtonProps) {
  const [bookmarked, setBookmarked] = useState(initialBookmarked);
  const [bookmarkId, setBookmarkId] = useState<string | undefined>(initialBookmarkId);
  const [loading, setLoading] = useState(false);

  const toggle = async () => {
    if (loading) return;
    setLoading(true);
    try {
      if (bookmarked && bookmarkId) {
        await fetch(`${API_BASE}/bookmarks/${bookmarkId}`, {
          method: "DELETE",
          credentials: "include",
          headers: { "X-CSRF-Token": getCsrfToken() },
        });
        setBookmarked(false);
        setBookmarkId(undefined);
        toast("Bookmark removed");
      } else {
        const res = await fetch(`${API_BASE}/bookmarks`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json", "X-CSRF-Token": getCsrfToken() },
          body: JSON.stringify({
            session_id: sessionId,
            message_id: messageId,
            content,
            citations,
            tags: [],
            workspace,
          }),
        });
        if (res.ok) {
          const data = await res.json();
          setBookmarked(true);
          setBookmarkId(data.id);
          toast.success("Bookmarked!");
        }
      }
    } catch {
      toast.error("Failed to update bookmark");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={toggle}
      disabled={loading}
      className="btn btn-ghost btn-sm"
      aria-label={bookmarked ? "Remove bookmark" : "Bookmark this response"}
      title={bookmarked ? "Remove bookmark" : "Save to bookmarks"}
      style={{
        height: "28px",
        color: bookmarked ? "var(--brand)" : undefined,
        opacity: loading ? 0.5 : 1,
      }}
    >
      <span aria-hidden="true">{bookmarked ? "🔖" : "🔖"}</span>
      <span style={{ color: bookmarked ? "var(--brand)" : undefined }}>
        {bookmarked ? "Saved" : "Save"}
      </span>
    </button>
  );
}

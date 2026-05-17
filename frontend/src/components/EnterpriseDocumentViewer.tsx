'use client';
import { useState, useRef, useEffect, memo } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Configure WebWorker for parsing performance (Phase 8: Performance Hardening)
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface BoundingBox {
  id: string;
  type: 'text' | 'table' | 'formula';
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
  content: string;
}

interface DocumentViewerProps {
  pdfUrl: string;
  targetPage?: number;
  activeAnnotationId?: string;
  annotations: BoundingBox[];
  onAnnotationClick?: (annotation: BoundingBox) => void;
}

// Phase 8: Performance Hardening - Memoized Annotations Overlay
const AnnotationsOverlay = memo(({ 
  annotations, 
  scale, 
  activeAnnotationId, 
  onAnnotationClick 
}: { 
  annotations: BoundingBox[];
  scale: number;
  activeAnnotationId?: string;
  onAnnotationClick?: (box: BoundingBox) => void;
}) => {
  const getOverlayStyle = (box: BoundingBox) => {
    const isActive = activeAnnotationId === box.id;
    let borderColor = 'rgba(59, 130, 246, 0.5)';
    let bgColor = 'rgba(59, 130, 246, 0.1)';

    if (box.type === 'table') {
      borderColor = 'rgba(16, 185, 129, 0.5)';
      bgColor = 'rgba(16, 185, 129, 0.1)';
    } else if (box.type === 'formula') {
      borderColor = 'rgba(139, 92, 246, 0.5)';
      bgColor = 'rgba(139, 92, 246, 0.1)';
    }

    if (isActive) {
      borderColor = 'rgba(239, 68, 68, 0.8)';
      bgColor = 'rgba(239, 68, 68, 0.3)';
    }

    return {
      position: 'absolute' as const,
      left: `${box.x * scale}px`,
      top: `${box.y * scale}px`,
      width: `${box.width * scale}px`,
      height: `${box.height * scale}px`,
      border: `2px solid ${borderColor}`,
      backgroundColor: bgColor,
      cursor: 'pointer',
      transition: 'all 0.2s ease-in-out',
      zIndex: isActive ? 10 : 5
    };
  };

  return (
    <>
      {annotations.map((box) => (
        <div
          key={box.id}
          style={getOverlayStyle(box)}
          onClick={() => onAnnotationClick && onAnnotationClick(box)}
          title={`Confidence: ${(box.confidence * 100).toFixed(1)}%`}
          className="group"
        >
          <div className="absolute hidden group-hover:block bottom-full left-1/2 -translate-x-1/2 mb-2 w-max bg-black dark:bg-white text-white dark:text-black text-xs px-2 py-1 rounded shadow-lg z-50">
            {box.type.toUpperCase()}: {(box.confidence * 100).toFixed(1)}%
          </div>
        </div>
      ))}
    </>
  );
});
AnnotationsOverlay.displayName = 'AnnotationsOverlay';

export default function EnterpriseDocumentViewer({
  pdfUrl,
  targetPage = 1,
  activeAnnotationId,
  annotations,
  onAnnotationClick
}: DocumentViewerProps) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(targetPage);
  const [scale, setScale] = useState(1.0);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const pageRef = useRef<HTMLDivElement>(null);

  // Sync external page navigation
  useEffect(() => {
    if (targetPage && targetPage !== pageNumber) {
      setPageNumber(targetPage);
    }
  }, [targetPage]);

  // Phase 9: Security Hardening - Authenticated PDF Fetch
  useEffect(() => {
    let objectUrl: string | null = null;
    let isMounted = true;
    
    if (pdfUrl && (pdfUrl.startsWith('http') || pdfUrl.startsWith('/api'))) {
      fetch(pdfUrl, { credentials: 'include' })
        .then(res => res.blob())
        .then(blob => {
          if (!isMounted) return;
          objectUrl = URL.createObjectURL(blob);
          setPdfBlobUrl(objectUrl);
        })
        .catch(err => console.error("Failed to securely fetch PDF:", err));
    } else {
      setPdfBlobUrl(pdfUrl);
    }

    return () => {
      isMounted = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [pdfUrl]);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
  }

  return (
    <div className="flex flex-col h-full bg-black/5 dark:bg-white/5 rounded-xl overflow-hidden border border-black/10 dark:border-white/10 shadow-inner">
      {/* Top Navigation Bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-black border-b border-black/10 dark:border-white/10">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setPageNumber(p => Math.max(1, p - 1))}
            disabled={pageNumber <= 1}
            className="px-3 py-1.5 bg-black/5 dark:bg-white/5 text-black/70 dark:text-white/70 rounded-lg hover:bg-black/10 dark:hover:bg-white/10 disabled:opacity-50 font-medium text-sm transition-colors"
          >
            Prev
          </button>
          <span className="text-sm font-medium text-black/60 dark:text-white/60">
            Page {pageNumber} of {numPages || '--'}
          </span>
          <button 
            onClick={() => setPageNumber(p => Math.min(numPages || p, p + 1))}
            disabled={pageNumber >= (numPages || 1)}
            className="px-3 py-1.5 bg-black/5 dark:bg-white/5 text-black/70 dark:text-white/70 rounded-lg hover:bg-black/10 dark:hover:bg-white/10 disabled:opacity-50 font-medium text-sm transition-colors"
          >
            Next
          </button>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-2 bg-black/5 dark:bg-white/5 rounded-lg p-1">
          <button onClick={() => setScale(s => Math.max(0.5, s - 0.25))} className="px-3 py-1 text-black/60 dark:text-white/60 hover:bg-white dark:hover:bg-black hover:shadow-sm rounded-md transition-all">-</button>
          <span className="text-sm font-medium w-12 text-center text-black/60 dark:text-white/60">{Math.round(scale * 100)}%</span>
          <button onClick={() => setScale(s => Math.min(3.0, s + 0.25))} className="px-3 py-1 text-black/60 dark:text-white/60 hover:bg-white dark:hover:bg-black hover:shadow-sm rounded-md transition-all">+</button>
        </div>
      </div>

      {/* Main Document Area */}
      <div className="flex-1 overflow-auto relative flex justify-center p-6" ref={pageRef}>
        {pdfBlobUrl && (
          <Document
            file={pdfBlobUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={
            <div className="flex flex-col items-center justify-center h-64">
              <div className="w-8 h-8 border-4 border-black dark:border-white border-t-transparent rounded-full animate-spin mb-4"></div>
              <p className="text-black/50 dark:text-white/50 font-medium animate-pulse">Parsing Document Engine...</p>
            </div>
          }
          className="shadow-2xl bg-white transition-transform"
        >
          <div className="relative">
            <Page 
              pageNumber={pageNumber} 
              scale={scale} 
              renderTextLayer={true}
              renderAnnotationLayer={true}
              className="max-w-full"
            />
            {/* PHASE 2: OCR OVERLAY ENGINE */}
            <AnnotationsOverlay 
              annotations={annotations}
              scale={scale}
              activeAnnotationId={activeAnnotationId}
              onAnnotationClick={onAnnotationClick}
            />
          </div>
        </Document>
        )}
      </div>
    </div>
  );
}

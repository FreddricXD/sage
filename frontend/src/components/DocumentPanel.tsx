import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Upload, FileText, Trash2, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { api, type Document } from "@/api/client";
import { cn, formatBytes } from "@/lib/utils";

const STATUS_META: Record<Document["status"], { label: string; className: string; icon: typeof CheckCircle2 }> = {
  pending: { label: "Queued", className: "text-amber-600", icon: Loader2 },
  processing: { label: "Processing", className: "text-blue-600", icon: Loader2 },
  ready: { label: "Ready", className: "text-emerald-600", icon: CheckCircle2 },
  failed: { label: "Failed", className: "text-destructive", icon: AlertCircle },
};

export function DocumentPanel({ collectionId }: { collectionId: string }) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadError, setUploadError] = useState("");

  // Poll so processing status updates live.
  const { data: documents } = useQuery({
    queryKey: ["documents", collectionId],
    queryFn: () => api.listDocuments(collectionId),
    refetchInterval: (query) => {
      const docs = query.state.data;
      const active = docs?.some((d) => d.status === "pending" || d.status === "processing");
      return active ? 2000 : false;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadDocument(collectionId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", collectionId] });
      queryClient.invalidateQueries({ queryKey: ["collection", collectionId] });
    },
    onError: (e) => setUploadError(e instanceof Error ? e.message : "Upload failed"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteDocument(collectionId, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", collectionId] });
      queryClient.invalidateQueries({ queryKey: ["collection", collectionId] });
    },
  });

  const handleFiles = (files: FileList | null) => {
    setUploadError("");
    if (!files) return;
    for (const file of Array.from(files)) uploadMutation.mutate(file);
  };

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 text-center transition-colors",
          dragOver ? "border-primary bg-primary/5" : "border-border hover:border-primary/40",
        )}
      >
        <Upload className="mb-2 h-6 w-6 text-muted-foreground" />
        <p className="text-sm font-medium">Drop files or click to upload</p>
        <p className="mt-0.5 text-xs text-muted-foreground">PDF, DOCX, MD, TXT · up to 20 MB</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.md,.markdown,.txt"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {uploadError && (
        <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{uploadError}</div>
      )}

      <div className="space-y-2">
        {documents?.length === 0 && (
          <p className="py-4 text-center text-sm text-muted-foreground">No documents yet.</p>
        )}
        {documents?.map((doc) => {
          const meta = STATUS_META[doc.status];
          const Icon = meta.icon;
          const spin = doc.status === "pending" || doc.status === "processing";
          return (
            <div key={doc.id} className="group flex items-center gap-3 rounded-lg border bg-background p-3">
              <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{doc.filename}</p>
                <p className="text-xs text-muted-foreground">
                  {formatBytes(doc.size_bytes)}
                  {doc.status === "ready" && ` · ${doc.chunk_count} chunks`}
                  {doc.status === "failed" && doc.error && ` · ${doc.error}`}
                </p>
              </div>
              <span className={cn("flex items-center gap-1 text-xs font-medium", meta.className)}>
                <Icon className={cn("h-3.5 w-3.5", spin && "animate-spin")} />
                {meta.label}
              </span>
              <button
                onClick={() => deleteMutation.mutate(doc.id)}
                className="rounded-md p-1.5 text-muted-foreground opacity-0 transition hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                aria-label="Delete document"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

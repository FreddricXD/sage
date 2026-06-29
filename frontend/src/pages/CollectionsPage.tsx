import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, FolderOpen, FileText, Trash2 } from "lucide-react";
import { api } from "@/api/client";
import { createCollectionSchema } from "@/lib/schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingState } from "@/components/ui/spinner";
import type { z } from "zod";

type FormData = z.infer<typeof createCollectionSchema>;

export function CollectionsPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const { data: collections, isLoading } = useQuery({
    queryKey: ["collections"],
    queryFn: api.listCollections,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(createCollectionSchema) });

  const createMutation = useMutation({
    mutationFn: (data: FormData) => api.createCollection(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      reset();
      setShowForm(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteCollection(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["collections"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Knowledge bases</h1>
          <p className="mt-1 text-muted-foreground">Group your documents and chat with them</p>
        </div>
        <Button onClick={() => setShowForm((v) => !v)} className="gap-2">
          <Plus className="h-4 w-4" />
          New collection
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Create a collection</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              onSubmit={handleSubmit((d) => createMutation.mutate(d))}
              className="flex flex-col gap-3 sm:flex-row sm:items-start"
            >
              <div className="flex-1 space-y-1">
                <Input {...register("name")} placeholder="e.g. Research papers" className="h-11" />
                {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
              </div>
              <Input
                {...register("description")}
                placeholder="Description (optional)"
                className="h-11 flex-1"
              />
              <Button type="submit" disabled={isSubmitting} className="h-11">
                {isSubmitting ? "Creating..." : "Create"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {isLoading && <LoadingState message="Loading collections..." />}

      {collections && collections.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center py-16 text-center">
            <div className="mb-4 rounded-full bg-muted p-4">
              <FolderOpen className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold">No collections yet</h3>
            <p className="mb-6 mt-1 max-w-sm text-muted-foreground">
              Create a collection, upload some documents, and start asking questions.
            </p>
            <Button onClick={() => setShowForm(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Create your first collection
            </Button>
          </CardContent>
        </Card>
      )}

      {collections && collections.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {collections.map((c) => (
            <Card key={c.id} className="group relative transition-all hover:border-primary/30 hover:shadow-md">
              <Link to={`/collections/${c.id}`}>
                <CardHeader>
                  <CardTitle className="group-hover:text-primary">{c.name}</CardTitle>
                  {c.description && (
                    <p className="line-clamp-2 text-sm text-muted-foreground">{c.description}</p>
                  )}
                </CardHeader>
                <CardContent>
                  <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                    <FileText className="h-4 w-4" />
                    {c.document_count} document{c.document_count === 1 ? "" : "s"}
                  </span>
                </CardContent>
              </Link>
              <button
                onClick={() => {
                  if (confirm(`Delete "${c.name}"? This removes all its documents.`)) {
                    deleteMutation.mutate(c.id);
                  }
                }}
                className="absolute right-3 top-3 rounded-md p-2 text-muted-foreground opacity-0 transition hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                aria-label="Delete collection"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

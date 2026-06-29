import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { api } from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingState } from "@/components/ui/spinner";
import { ChatPanel } from "@/components/ChatPanel";
import { DocumentPanel } from "@/components/DocumentPanel";

export function CollectionDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: collection, isLoading } = useQuery({
    queryKey: ["collection", id],
    queryFn: () => api.getCollection(id!),
    enabled: !!id,
  });

  const { data: documents } = useQuery({
    queryKey: ["documents", id],
    queryFn: () => api.listDocuments(id!),
    enabled: !!id,
  });

  if (isLoading) return <LoadingState message="Loading collection..." />;
  if (!collection) return <p className="text-destructive">Collection not found</p>;

  const hasReadyDocs = (documents ?? []).some((d) => d.status === "ready");

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/"
          className="mb-2 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          All collections
        </Link>
        <h1 className="text-3xl font-bold tracking-tight">{collection.name}</h1>
        {collection.description && (
          <p className="mt-1 text-muted-foreground">{collection.description}</p>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-lg">Documents</CardTitle>
          </CardHeader>
          <CardContent>
            <DocumentPanel collectionId={collection.id} />
          </CardContent>
        </Card>

        <ChatPanel collectionId={collection.id} hasDocuments={hasReadyDocs} />
      </div>
    </div>
  );
}

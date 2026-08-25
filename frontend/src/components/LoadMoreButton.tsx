interface Props {
  hasMore: boolean;
  isFetchingNextPage: boolean;
  onLoadMore: () => void;
  loadedCount: number;
  total?: number | null;
  itemLabel?: string;
}

export function LoadMoreButton({ hasMore, isFetchingNextPage, onLoadMore, loadedCount, total, itemLabel = "kayıt" }: Props) {
  return (
    <div className="mt-3 flex items-center justify-between text-xs" style={{ color: "var(--text-muted)" }}>
      <span>
        {total != null ? `${loadedCount} / ${total} ${itemLabel} gösteriliyor` : `${loadedCount} ${itemLabel} gösteriliyor`}
      </span>
      {hasMore && (
        <button
          disabled={isFetchingNextPage}
          onClick={onLoadMore}
          className="rounded-md px-3 py-1.5 disabled:opacity-40"
          style={{ border: "1px solid var(--border-strong)" }}
        >
          {isFetchingNextPage ? "Yükleniyor..." : "Daha Fazla Yükle"}
        </button>
      )}
    </div>
  );
}

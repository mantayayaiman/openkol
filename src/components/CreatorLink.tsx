import Link from 'next/link';

export function CreatorLink({
  id,
  name,
}: {
  id: number;
  name: string;
}) {
  return (
    <Link
      href={`/creator/${id}`}
      className="inline-flex items-center gap-1 rounded-md bg-accent/10 px-1.5 py-0.5 text-sm font-medium text-accent transition-colors hover:bg-accent/20"
    >
      @{name}
    </Link>
  );
}

import Link from "next/link";

export function DisclaimerBanner() {
  return (
    <div className="bg-ink text-page text-[11px]">
      <div className="mx-auto max-w-7xl px-4 py-1.5 flex items-center justify-between gap-4">
        <span className="opacity-80">
          Personal research of Palaniappan Chidambaram. Not investment advice.
          Not affiliated with Unison Group.
        </span>
        <Link
          href="/disclaimer"
          className="opacity-80 hover:opacity-100 underline-offset-2 hover:underline whitespace-nowrap"
        >
          Full disclaimer →
        </Link>
      </div>
    </div>
  );
}

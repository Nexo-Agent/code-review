import type { ReactNode } from "react"

import { InlineError } from "@/components/patterns/inline-error"
import { Skeleton } from "@/components/ui/skeleton"

export function DataPanel({
  loading,
  error,
  errorMessage,
  errorHint,
  children,
}: {
  loading?: boolean
  error?: boolean
  errorMessage?: string
  errorHint?: ReactNode
  children: ReactNode
}) {
  if (loading) {
    return (
      <div className="flex flex-col gap-1.5 p-4">
        <Skeleton className="h-7 w-full" />
        <Skeleton className="h-7 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4">
        <InlineError
          message={errorMessage ?? "Something went wrong."}
          hint={errorHint}
        />
      </div>
    )
  }

  return <div className="overflow-hidden rounded-lg">{children}</div>
}

import type { ReactNode } from "react"

import { InlineError } from "@/components/patterns/inline-error"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

export function DataPanel({
  loading,
  error,
  errorMessage,
  errorHint,
  className,
  children,
}: {
  loading?: boolean
  error?: boolean
  errorMessage?: string
  errorHint?: ReactNode
  className?: string
  children: ReactNode
}) {
  if (loading) {
    return (
      <div className={cn("flex flex-col gap-1.5 p-4", className)}>
        <Skeleton className="h-7 w-full" />
        <Skeleton className="h-7 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className={cn("p-4", className)}>
        <InlineError
          message={errorMessage ?? "Something went wrong."}
          hint={errorHint}
        />
      </div>
    )
  }

  return <div className={cn("overflow-hidden rounded-lg", className)}>{children}</div>
}

import type { ReactNode } from "react"

export function InlineError({
  message,
  hint,
}: {
  message: string
  hint?: ReactNode
}) {
  return (
    <p className="text-destructive text-sm">
      {message}
      {hint ? <> {hint}</> : null}
    </p>
  )
}

export function CodeHint({ children }: { children: string }) {
  return <code className="text-xs">{children}</code>
}

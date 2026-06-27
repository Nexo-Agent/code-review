import type { ReactNode } from "react"

export function EmptyState({
  children,
  colSpan,
}: {
  children: ReactNode
  colSpan?: number
}) {
  if (colSpan !== undefined) {
    return (
      <tr>
        <td
          colSpan={colSpan}
          className="text-muted-foreground h-12 px-3 py-2 text-center text-sm"
        >
          {children}
        </td>
      </tr>
    )
  }

  return (
    <p className="text-muted-foreground p-4 text-center text-sm">{children}</p>
  )
}

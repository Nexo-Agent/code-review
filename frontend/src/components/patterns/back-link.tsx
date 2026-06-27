import { Link } from "@tanstack/react-router"
import { ChevronLeft } from "lucide-react"

export function BackLink({
  to,
  label = "Back",
}: {
  to: string
  label?: string
}) {
  return (
    <Link
      to={to}
      className="text-muted-foreground hover:text-foreground mb-4 inline-flex items-center gap-0.5 text-xs transition-colors"
    >
      <ChevronLeft className="size-3.5" />
      {label}
    </Link>
  )
}

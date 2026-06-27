import type { VariantProps } from "class-variance-authority"

import { Badge, badgeVariants } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>["variant"]>

const reviewStatusVariant: Record<string, BadgeVariant> = {
  completed: "success",
  failed: "destructive",
  running: "info",
  pending: "muted",
}

const severityVariant: Record<string, BadgeVariant> = {
  critical: "destructive",
  warning: "warning",
  info: "info",
}

const healthStatusVariant: Record<string, BadgeVariant> = {
  ok: "success",
  healthy: "success",
  up: "success",
  connected: "success",
  error: "destructive",
  down: "destructive",
  disconnected: "destructive",
}

function formatLabel(value: string): string {
  return value.replace(/_/g, " ")
}

export function StatusBadge({
  status,
  className,
}: {
  status: string
  className?: string
}) {
  const variant = reviewStatusVariant[status] ?? "muted"
  return (
    <Badge variant={variant} className={className}>
      {formatLabel(status)}
    </Badge>
  )
}

export function SeverityBadge({
  severity,
  className,
}: {
  severity: string
  className?: string
}) {
  const variant = severityVariant[severity] ?? "muted"
  return (
    <Badge variant={variant} className={cn("h-5 px-1.5 text-[10px]", className)}>
      {formatLabel(severity)}
    </Badge>
  )
}

export function HealthBadge({
  value,
  className,
}: {
  value: string
  className?: string
}) {
  const variant = healthStatusVariant[value.toLowerCase()] ?? "muted"
  return (
    <Badge variant={variant} className={className}>
      {value}
    </Badge>
  )
}

export function EnabledBadge({
  enabled,
  className,
}: {
  enabled: boolean
  className?: string
}) {
  return (
    <Badge variant={enabled ? "success" : "muted"} className={className}>
      {enabled ? "Enabled" : "Disabled"}
    </Badge>
  )
}

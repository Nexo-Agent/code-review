import { RepoIntegrationDialog } from "@/components/settings/RepoIntegrationDialog"

type TeamRepositoryAddDialogProps = {
  teamId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionKey: number
}

export function TeamRepositoryAddDialog({
  teamId,
  open,
  onOpenChange,
  sessionKey,
}: TeamRepositoryAddDialogProps) {
  return (
    <RepoIntegrationDialog
      teamId={teamId}
      open={open}
      onOpenChange={onOpenChange}
      repo={null}
      sessionKey={sessionKey}
    />
  )
}

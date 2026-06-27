import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"

import type { Team } from "@/api/team-types"
import { Field } from "@/components/forms/Field"
import { ConfirmDialog } from "@/components/patterns/confirm-dialog"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useDeleteTeam, useUpdateTeam } from "@/hooks/use-teams"

type TeamSettingsDialogProps = {
  team: Team
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionKey: number
}

export function TeamSettingsDialog({
  team,
  open,
  onOpenChange,
  sessionKey,
}: TeamSettingsDialogProps) {
  const navigate = useNavigate()
  const updateTeam = useUpdateTeam(team.id)
  const deleteTeam = useDeleteTeam(team.id)
  const [name, setName] = useState(team.name)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)

  const isPending = updateTeam.isPending || deleteTeam.isPending

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmedName = name.trim()
    if (!trimmedName) return
    try {
      await updateTeam.mutateAsync({ name: trimmedName })
      toast.success("Team updated")
      onOpenChange(false)
    } catch {
      toast.error("Failed to update team")
    }
  }

  async function confirmDelete() {
    try {
      await deleteTeam.mutateAsync()
      toast.success("Team deleted")
      setDeleteConfirmOpen(false)
      onOpenChange(false)
      void navigate({ to: "/teams" })
    } catch {
      toast.error("Failed to delete team")
    }
  }

  return (
    <>
      <ConfirmDialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
        title="Delete team?"
        description={`Delete team "${team.name}"? Projects and repositories under this team will be removed.`}
        confirmLabel="Delete"
        variant="destructive"
        loading={deleteTeam.isPending}
        onConfirm={confirmDelete}
      />
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-md">
          <form key={sessionKey} onSubmit={handleSubmit}>
            <DialogHeader>
              <DialogTitle>Team settings</DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <Field label="Team name">
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoFocus
                />
              </Field>
            </div>
            <DialogFooter className="sm:justify-between">
              <Button
                type="button"
                variant="destructive"
                disabled={isPending}
                onClick={() => setDeleteConfirmOpen(true)}
              >
                Delete team
              </Button>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  disabled={isPending}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={!name.trim() || isPending}
                >
                  Save changes
                </Button>
              </div>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}

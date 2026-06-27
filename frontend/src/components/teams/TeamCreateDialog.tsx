import { useState } from "react"
import { toast } from "sonner"

import { Field } from "@/components/forms/Field"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useCreateTeam } from "@/hooks/use-teams"

type TeamCreateDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionKey: number
}

export function TeamCreateDialog({
  open,
  onOpenChange,
  sessionKey,
}: TeamCreateDialogProps) {
  const createTeam = useCreateTeam()
  const [name, setName] = useState("")

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    try {
      await createTeam.mutateAsync({ name: trimmed })
      toast.success("Team created")
      setName("")
      onOpenChange(false)
    } catch {
      toast.error("Failed to create team")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form key={sessionKey} onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create team</DialogTitle>
            <DialogDescription>
              Teams isolate reviews and group projects for your organization.
            </DialogDescription>
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
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createTeam.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!name.trim() || createTeam.isPending}>
              Create team
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

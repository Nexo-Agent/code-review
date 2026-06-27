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
import { useCreateProject } from "@/hooks/use-teams"

type ProjectCreateDialogProps = {
  teamId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionKey: number
}

export function ProjectCreateDialog({
  teamId,
  open,
  onOpenChange,
  sessionKey,
}: ProjectCreateDialogProps) {
  const createProject = useCreateProject(teamId)
  const [name, setName] = useState("")

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    try {
      await createProject.mutateAsync({ name: trimmed })
      toast.success("Project created")
      setName("")
      onOpenChange(false)
    } catch {
      toast.error("Failed to create project")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form key={sessionKey} onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add project</DialogTitle>
            <DialogDescription>
              Projects group repositories under this team.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Field label="Project name">
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
              disabled={createProject.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!name.trim() || createProject.isPending}>
              Create project
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

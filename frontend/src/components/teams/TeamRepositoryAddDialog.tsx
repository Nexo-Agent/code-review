import { useState } from "react"

import { Field } from "@/components/forms/Field"
import { RepoIntegrationDialog } from "@/components/settings/RepoIntegrationDialog"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useProjects } from "@/hooks/use-teams"

type TeamRepositoryAddDialogProps = {
  teamId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionKey: number
  onCreateProject: () => void
}

export function TeamRepositoryAddDialog({
  teamId,
  open,
  onOpenChange,
  sessionKey,
  onCreateProject,
}: TeamRepositoryAddDialogProps) {
  const projects = useProjects(teamId)
  const [projectId, setProjectId] = useState("")
  const [repoDialogOpen, setRepoDialogOpen] = useState(false)
  const [repoDialogSession, setRepoDialogSession] = useState(0)
  const projectList = projects.data ?? []

  function handleClose(nextOpen: boolean) {
    if (!nextOpen) {
      setProjectId("")
      setRepoDialogOpen(false)
    }
    onOpenChange(nextOpen)
  }

  function handleContinue() {
    if (!projectId) return
    setRepoDialogSession((session) => session + 1)
    setRepoDialogOpen(true)
  }

  function handleRepoDialogChange(nextOpen: boolean) {
    setRepoDialogOpen(nextOpen)
    if (!nextOpen) {
      handleClose(false)
    }
  }

  return (
    <>
      <Dialog open={open && !repoDialogOpen} onOpenChange={handleClose}>
        <DialogContent className="sm:max-w-md">
          <form
            key={sessionKey}
            onSubmit={(event) => {
              event.preventDefault()
              handleContinue()
            }}
          >
            <DialogHeader>
              <DialogTitle>Add repository</DialogTitle>
              <DialogDescription>
                Choose a project, then configure the repository integration.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3 py-4">
              <Field label="Project">
                <Select value={projectId} onValueChange={setProjectId}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select project" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {projectList.map((project) => (
                        <SelectItem key={project.id} value={project.id}>
                          {project.name}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>
              {projectList.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  No projects yet. Create a project first.
                </p>
              ) : null}
            </div>
            <DialogFooter className="sm:justify-between">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  handleClose(false)
                  onCreateProject()
                }}
              >
                Create project
              </Button>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => handleClose(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={!projectId}>
                  Continue
                </Button>
              </div>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {projectId ? (
        <RepoIntegrationDialog
          teamId={teamId}
          projectId={projectId}
          open={repoDialogOpen}
          onOpenChange={handleRepoDialogChange}
          repo={null}
          sessionKey={repoDialogSession}
        />
      ) : null}
    </>
  )
}

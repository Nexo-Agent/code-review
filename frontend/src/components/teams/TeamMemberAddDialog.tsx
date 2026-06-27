import { useState } from "react"
import { toast } from "sonner"

import { Field } from "@/components/forms/Field"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
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
import { useAddTeamMember, useUsers } from "@/hooks/use-teams"

type TeamMemberAddDialogProps = {
  teamId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionKey: number
}

export function TeamMemberAddDialog({
  teamId,
  open,
  onOpenChange,
  sessionKey,
}: TeamMemberAddDialogProps) {
  const users = useUsers()
  const addMember = useAddTeamMember(teamId)
  const [userId, setUserId] = useState("")

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!userId) return
    try {
      await addMember.mutateAsync({ user_id: userId })
      toast.success("Member added")
      setUserId("")
      onOpenChange(false)
    } catch {
      toast.error("Failed to add member")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form key={sessionKey} onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add member</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <Field label="User">
              <Select value={userId} onValueChange={setUserId}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select user" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {(users.data ?? []).map((user) => (
                      <SelectItem key={user.id} value={user.id}>
                        {user.email}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </Field>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={addMember.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!userId || addMember.isPending}>
              Add member
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

import { createFileRoute } from "@tanstack/react-router"
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table"
import { useMemo, useState } from "react"
import { toast } from "sonner"

import type { Example } from "@/api/types"
import { AppShell } from "@/components/layout/AppShell"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useCreateExample, useExamples } from "@/hooks/use-examples"

export const Route = createFileRoute("/examples/")({
  component: ExamplesPage,
})

function ExamplesPage() {
  const examples = useExamples()
  const createExample = useCreateExample()
  const [name, setName] = useState("")

  const columns = useMemo<ColumnDef<Example>[]>(
    () => [
      { accessorKey: "name", header: "Name" },
      {
        accessorKey: "created_at",
        header: "Created",
        cell: ({ row }) =>
          new Date(row.original.created_at).toLocaleString(),
      },
    ],
    [],
  )

  const table = useReactTable({
    data: examples.data ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return

    try {
      await createExample.mutateAsync({ name: trimmed })
      setName("")
      toast.success("Example created")
    } catch {
      toast.error("Failed to create example")
    }
  }

  return (
    <AppShell title="Examples">
      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>New example</CardTitle>
            <CardDescription>
              Vertical slice: form → API → Postgres → table refresh
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="flex gap-2" onSubmit={handleSubmit}>
              <Input
                placeholder="Name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                disabled={createExample.isPending}
              />
              <Button type="submit" disabled={createExample.isPending}>
                Add
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>All examples</CardTitle>
          </CardHeader>
          <CardContent>
            {examples.isPending ? (
              <div className="space-y-2">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : examples.isError ? (
              <p className="text-destructive text-sm">
                Could not load examples. Run migrations with{" "}
                <code className="text-xs">make migrate</code>.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  {table.getHeaderGroups().map((headerGroup) => (
                    <TableRow key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <TableHead key={header.id}>
                          {header.isPlaceholder
                            ? null
                            : flexRender(
                                header.column.columnDef.header,
                                header.getContext(),
                              )}
                        </TableHead>
                      ))}
                    </TableRow>
                  ))}
                </TableHeader>
                <TableBody>
                  {table.getRowModel().rows.length ? (
                    table.getRowModel().rows.map((row) => (
                      <TableRow key={row.id}>
                        {row.getVisibleCells().map((cell) => (
                          <TableCell key={cell.id}>
                            {flexRender(
                              cell.column.columnDef.cell,
                              cell.getContext(),
                            )}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell
                        colSpan={columns.length}
                        className="text-muted-foreground h-16 text-center"
                      >
                        No examples yet
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}

import { ChevronDownIcon } from "lucide-react"
import { useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

export type MultiSelectOption = {
  value: string
  label: string
}

function triggerLabel(
  selected: string[],
  options: MultiSelectOption[],
  emptyLabel: string,
): string {
  if (selected.length === 0) {
    return emptyLabel
  }
  const labelByValue = new Map(options.map((option) => [option.value, option.label]))
  if (selected.length === 1) {
    return labelByValue.get(selected[0]) ?? selected[0]
  }
  return `${selected.length} selected`
}

export function MultiSelectFilter({
  options,
  selected,
  onSelectedChange,
  emptyLabel,
  searchPlaceholder = "Search…",
  className,
}: {
  options: MultiSelectOption[]
  selected: string[]
  onSelectedChange: (selected: string[]) => void
  emptyLabel: string
  searchPlaceholder?: string
  className?: string
}) {
  const [search, setSearch] = useState("")
  const selectedSet = useMemo(() => new Set(selected), [selected])

  const filteredOptions = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) {
      return options
    }
    return options.filter(
      (option) =>
        option.label.toLowerCase().includes(query) ||
        option.value.toLowerCase().includes(query),
    )
  }, [options, search])

  function toggleOption(value: string) {
    const next = new Set(selectedSet)
    if (next.has(value)) {
      next.delete(value)
    } else {
      next.add(value)
    }
    onSelectedChange([...next])
  }

  function selectFiltered() {
    const next = new Set(selectedSet)
    for (const option of filteredOptions) {
      next.add(option.value)
    }
    onSelectedChange([...next])
  }

  return (
    <DropdownMenu
      onOpenChange={(open) => {
        if (!open) {
          setSearch("")
        }
      }}
    >
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            "h-9 justify-between px-3 font-normal shadow-xs",
            className,
          )}
        >
          <span className="truncate">
            {triggerLabel(selected, options, emptyLabel)}
          </span>
          <ChevronDownIcon className="size-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72 p-0">
        <div
          className="p-2"
          onKeyDown={(event) => event.stopPropagation()}
        >
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={searchPlaceholder}
            className="h-8"
          />
        </div>
        <DropdownMenuSeparator />
        <div className="max-h-60 overflow-y-auto p-1">
          {filteredOptions.length ? (
            filteredOptions.map((option) => (
              <DropdownMenuCheckboxItem
                key={option.value}
                checked={selectedSet.has(option.value)}
                onCheckedChange={() => toggleOption(option.value)}
                onSelect={(event) => event.preventDefault()}
                className="truncate"
              >
                {option.label}
              </DropdownMenuCheckboxItem>
            ))
          ) : (
            <p className="px-2 py-4 text-center text-sm text-muted-foreground">
              No matches.
            </p>
          )}
        </div>
        {(selected.length > 0 || filteredOptions.length > 0) && (
          <>
            <DropdownMenuSeparator />
            <div className="flex p-1">
              {filteredOptions.length > 0 && (
                <DropdownMenuItem
                  className="flex-1 justify-center"
                  onSelect={(event) => {
                    event.preventDefault()
                    selectFiltered()
                  }}
                >
                  Select visible
                </DropdownMenuItem>
              )}
              {selected.length > 0 && (
                <DropdownMenuItem
                  className="flex-1 justify-center"
                  onSelect={(event) => {
                    event.preventDefault()
                    onSelectedChange([])
                  }}
                >
                  Clear
                </DropdownMenuItem>
              )}
            </div>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

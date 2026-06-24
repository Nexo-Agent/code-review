import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/api/client"
import type { Example, ExampleCreate } from "@/api/types"

const QUERY_KEY = ["examples"] as const

export function useExamples() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => api<Example[]>("/examples"),
  })
}

export function useCreateExample() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: ExampleCreate) =>
      api<Example>("/examples", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })
}

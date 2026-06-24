import { createFileRoute } from "@tanstack/react-router"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import type { IntegrationSettingsUpdate } from "@/api/types"
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
  useIntegrationSettings,
  useUpdateIntegrationSettings,
} from "@/hooks/use-integration-settings"

export const Route = createFileRoute("/settings/")({
  component: SettingsPage,
})

function SettingsPage() {
  const settings = useIntegrationSettings()
  const updateSettings = useUpdateIntegrationSettings()

  const [gitProvider, setGitProvider] = useState("github")
  const [githubRepo, setGithubRepo] = useState("")
  const [webhookSecret, setWebhookSecret] = useState("")
  const [githubToken, setGithubToken] = useState("")
  const [llmProviderId, setLlmProviderId] = useState("openai-compat")
  const [llmBaseUrl, setLlmBaseUrl] = useState("https://api.openai.com/v1")
  const [llmModel, setLlmModel] = useState("gpt-4o")
  const [llmApiToken, setLlmApiToken] = useState("")
  const [opencodeModel, setOpencodeModel] = useState("")

  useEffect(() => {
    if (!settings.data) return
    setGitProvider(settings.data.git_provider)
    setGithubRepo(settings.data.github_repo_full_name)
    setLlmProviderId(settings.data.llm_provider_id)
    setLlmBaseUrl(settings.data.llm_base_url)
    setLlmModel(settings.data.llm_model)
    setOpencodeModel(settings.data.opencode_model)
    setWebhookSecret("")
    setGithubToken("")
    setLlmApiToken("")
  }, [settings.data])

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const payload: IntegrationSettingsUpdate = {
      git_provider: gitProvider,
      github_repo_full_name: githubRepo,
      llm_provider_id: llmProviderId,
      llm_base_url: llmBaseUrl,
      llm_model: llmModel,
      opencode_model: opencodeModel,
    }
    if (webhookSecret) payload.github_webhook_secret = webhookSecret
    if (githubToken) payload.github_token = githubToken
    if (llmApiToken) payload.llm_api_token = llmApiToken

    try {
      await updateSettings.mutateAsync(payload)
      toast.success("Settings saved — restart opencode-serve to apply LLM changes")
    } catch {
      toast.error("Failed to save settings")
    }
  }

  const data = settings.data

  return (
    <AppShell title="Integration settings">
      <p className="text-muted-foreground mb-6 text-sm">
        Git repository, webhook secret, and LLM provider are stored in the
        database and managed here. Infrastructure settings (Redis, OpenCode
        server URL) remain in environment variables.
      </p>

      {settings.isPending ? (
        <Skeleton className="h-96 w-full" />
      ) : settings.isError ? (
        <p className="text-destructive text-sm">
          Could not load settings. Run{" "}
          <code className="text-xs">make dev-migrate</code> first.
        </p>
      ) : (
        <form className="grid gap-6" onSubmit={handleSubmit}>
          <Card>
            <CardHeader>
              <CardTitle>GitHub</CardTitle>
              <CardDescription>
                Webhook URL:{" "}
                <code className="text-xs">POST /api/v1/webhooks/github</code>
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <label className="grid gap-2 text-sm">
                <span>Git provider</span>
                <Input
                  value={gitProvider}
                  onChange={(e) => setGitProvider(e.target.value)}
                />
              </label>
              <label className="grid gap-2 text-sm">
                <span>Repository (owner/repo)</span>
                <Input
                  placeholder="acme/my-app — empty accepts all repos"
                  value={githubRepo}
                  onChange={(e) => setGithubRepo(e.target.value)}
                />
              </label>
              <label className="grid gap-2 text-sm">
                <span>
                  Webhook secret
                  {data?.github_webhook_secret_configured ? (
                    <span className="text-muted-foreground ml-2 text-xs">
                      (configured — leave blank to keep)
                    </span>
                  ) : null}
                </span>
                <Input
                  type="password"
                  placeholder="GitHub webhook secret"
                  value={webhookSecret}
                  onChange={(e) => setWebhookSecret(e.target.value)}
                />
              </label>
              <label className="grid gap-2 text-sm">
                <span>
                  GitHub token (PAT)
                  {data?.github_token_configured ? (
                    <span className="text-muted-foreground ml-2 text-xs">
                      (configured — leave blank to keep)
                    </span>
                  ) : null}
                </span>
                <Input
                  type="password"
                  placeholder="ghp_..."
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                />
              </label>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>LLM (OpenAI-compatible)</CardTitle>
              <CardDescription>
                Resolved OpenCode model:{" "}
                <code className="text-xs">
                  {data?.resolved_opencode_model ?? "—"}
                </code>
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <label className="grid gap-2 text-sm">
                <span>Provider ID</span>
                <Input
                  value={llmProviderId}
                  onChange={(e) => setLlmProviderId(e.target.value)}
                />
              </label>
              <label className="grid gap-2 text-sm">
                <span>Base URL</span>
                <Input
                  value={llmBaseUrl}
                  onChange={(e) => setLlmBaseUrl(e.target.value)}
                />
              </label>
              <label className="grid gap-2 text-sm">
                <span>Model</span>
                <Input
                  value={llmModel}
                  onChange={(e) => setLlmModel(e.target.value)}
                />
              </label>
              <label className="grid gap-2 text-sm">
                <span>
                  API token
                  {data?.llm_api_token_configured ? (
                    <span className="text-muted-foreground ml-2 text-xs">
                      (configured — leave blank to keep)
                    </span>
                  ) : null}
                </span>
                <Input
                  type="password"
                  placeholder="sk-..."
                  value={llmApiToken}
                  onChange={(e) => setLlmApiToken(e.target.value)}
                />
              </label>
              <label className="grid gap-2 text-sm">
                <span>OpenCode model override (optional)</span>
                <Input
                  placeholder="openai-compat/gpt-4o"
                  value={opencodeModel}
                  onChange={(e) => setOpencodeModel(e.target.value)}
                />
              </label>
            </CardContent>
          </Card>

          <div className="flex items-center gap-4">
            <Button type="submit" disabled={updateSettings.isPending}>
              Save settings
            </Button>
            {data?.updated_at ? (
              <span className="text-muted-foreground text-xs">
                Last updated {new Date(data.updated_at).toLocaleString()}
              </span>
            ) : null}
          </div>
        </form>
      )}
    </AppShell>
  )
}

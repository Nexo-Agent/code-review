import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import type { Components } from "react-markdown"

import { cn } from "@/lib/utils"

const markdownComponents: Components = {
  p: ({ children }) => (
    <p className="mb-2 leading-relaxed last:mb-0">{children}</p>
  ),
  ul: ({ children }) => (
    <ul className="mb-2 list-disc pl-5 last:mb-0">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-2 list-decimal pl-5 last:mb-0">{children}</ol>
  ),
  li: ({ children }) => <li className="mb-1">{children}</li>,
  h1: ({ children }) => (
    <h3 className="text-foreground mb-2 text-base font-semibold">{children}</h3>
  ),
  h2: ({ children }) => (
    <h4 className="text-foreground mb-2 text-sm font-semibold">{children}</h4>
  ),
  h3: ({ children }) => (
    <h5 className="text-foreground mb-1 text-sm font-medium">{children}</h5>
  ),
  code: ({ className, children, ...props }) => {
    const isBlock = Boolean(className?.includes("language-"))
    return (
      <code
        className={cn(
          isBlock
            ? "block text-xs"
            : "bg-muted rounded px-1 py-0.5 text-xs",
          className,
        )}
        {...props}
      >
        {children}
      </code>
    )
  },
  pre: ({ children }) => (
    <pre className="bg-muted mb-2 overflow-x-auto rounded-md p-3 text-xs last:mb-0">
      {children}
    </pre>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-primary hover:underline"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-border text-muted-foreground mb-2 border-l-2 pl-3 italic last:mb-0">
      {children}
    </blockquote>
  ),
  strong: ({ children }) => (
    <strong className="text-foreground font-semibold">{children}</strong>
  ),
  table: ({ children }) => (
    <div className="mb-2 overflow-x-auto last:mb-0">
      <table className="w-full border-collapse text-xs">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border-border border px-2 py-1 text-left font-medium">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-border border px-2 py-1">{children}</td>
  ),
}

export function MarkdownContent({
  content,
  className,
}: {
  content: string
  className?: string
}) {
  if (!content.trim()) {
    return null
  }

  return (
    <div className={cn("text-muted-foreground text-sm", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  )
}

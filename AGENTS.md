# AGENTS.md

Instructions for AI coding agents working on this repository.

## Communication

- All source code, code comments, commit messages, and technical artifacts must use English.
- All chat messages to the user must use Vietnamese.
- Keep communication concise, direct, and action-oriented.
- When presenting plans, assumptions, risks, or implementation status, make them explicit so the user can review quickly.
- Do not use emoji in source code. Avoid overusing emoji in chat.

## Development flow

Follow the principles below during feature development.

- Do not skip the steps below when a task affects business logic, architecture, schema, API, authentication, authorization, background jobs, integrations, or production data.
- For small, simple tasks or narrowly scoped bug fixes, the level of formality may be reduced, but the spirit of the process must still be preserved.
- Always prioritize understanding the problem correctly and the current state of the system before proposing or implementing changes.

### 1. Brainstorm:
  - Clarify unclear points, open questions, and functional limitations in the proposal.
  - During this phase, use tools such as web_search or context7 to gather additional information when needed in order to improve the accuracy of facts and decisions.
  - For uncertain points, ask the user to clarify expectations and business requirements.
  - Clearly identify the scope of the request: goals, expected behavior, limits of the change, and what is out of scope.
  - State the assumptions being used. If an assumption could affect design, business logic, schema, contract, or user experience, ask the user before implementation.
  - Only use web_search or context7 when the repository does not provide enough information, when the issue involves external frameworks/libraries/APIs/tooling, or when a technical detail may have changed over time.
  - Do not overuse external search for issues that can be verified directly from source code, @docs, tests, or the current repository configuration.
  - If multiple implementation approaches are reasonable and involve trade-offs, explicitly list the options and recommend the most suitable one.
  - Clarify possible risks: regression, side effects, data inconsistency, security issues, performance issues, or operational complexity.

### 2. Planning
  - Read @docs and the source code to understand the current functional and technical state of the system.
  - Refer to external technical sources through context7 or web_search when needed.
  - Break the work into sufficiently small (atomic) tasks so execution is straightforward.
  - Before coding, provide a brief summary of the current system state relevant to the task: current flow, affected components, and the points that need to change.
  - The plan should be divided into small steps that can be independently verified and executed in a clear order.
  - Each subtask should identify its goal, the files or system areas affected, the main risks, and the validation approach.
  - If a conflict is found between @docs and the source code, do not arbitrarily choose one side and continue as if it were certain; report it to the user or clearly state the handling assumption.
  - When evaluating solutions, prioritize the option that best fits the existing architecture, is easy to review, easy to test, and has the smallest necessary scope to achieve the goal.
  - Do not expand the scope beyond the main request without user approval, even if you notice a refactoring opportunity. If you have improvement ideas, separate them as recommendations.

### 3. Implementation
  - If you are on the `main` branch, create a new branch before implementation. If there is any issue during checkout, ask the user.
  - Write prototypes for functions / classes / modules together with descriptions through docstrings or comments for user review.
  - Implement each prototype step by step.
  - Write unit tests with a focus on edge cases.
  - If bugs appear, fix them and test again.
  - Before modifying code, clearly identify which files will be affected and why each change is necessary.
  - For large features, new modules, architectural changes, public interface changes, or important data changes, prepare a prototype or implementation outline for user review first.
  - For small tasks or local bug fixes, direct implementation is allowed without a full prototype, but the approach must still be stated clearly before editing.
  - All changes must follow the existing patterns, conventions, layering, naming, dependency direction, and style already present in the codebase.
  - Do not introduce new abstractions, internal frameworks, or generalizations unless there is a proven practical need within the task scope.
  - Do not modify unrelated parts just because it is convenient. If unrelated changes are required to complete the task, explain the reason clearly.
  - When adding or changing logic, update or add corresponding tests at an appropriate level. Prioritize tests for the main flow, edge cases, and scenarios likely to regress.
  - When possible, run the smallest reliable test scope first, then expand validation if the change has broader impact.
  - If tests cannot be run or an important part cannot be verified, state that clearly in the final report.
  - When encountering a bug or unexpected behavior during implementation, identify the root cause when possible, fix it thoroughly within task scope, and re-check related flows.
  - After implementation is complete, review the diff to remove dead code, temporary debug code, temporary logs, unnecessary comments, or out-of-scope changes.

### 4. Post-implementation report
  - Summarize each implemented part from a functional perspective.
  - Explain how I can run those features.
  - List the cases I should test in the product.
  - Note any important implementation considerations, if any.
  - Clearly state what has been verified in practice: which tests were run, what the results were, and the current confidence level.
  - Clearly state what has not yet been verified or completed, if any.
  - Point out notable side effects: migration, config, env, permission, dependency, queue, cron, cache, or backward compatibility.
  - If assumptions were used during the work, restate them in the final report so the user can validate them.
  - The report should be short enough to scan quickly but specific enough for the user to continue reviewing, testing, or handing off the work.

### 5. Documentation updates
  - Always ask the user before creating a PR.
  - Before updating documentation, report the proposed changes to the user for review.
  - If the user agrees, update @docs.
  - Do not update @docs on your own just because you notice information that could be clarified; propose the changes first and wait for user approval.
  - When proposing an @docs update, clearly state the reason, the affected scope, and the main content to be added or changed.
  - If code changes affect development, operations, integrations, or system understanding, proactively inform the user that @docs may need to be updated.
  - If the user has not approved updating @docs, you must still complete the code work and clearly report the documentation gaps or mismatches that remain.

## Notice

- During the work, always follow the system's established overall architecture.
- Do not create your own general architectural design. If such a change becomes necessary, discuss and brainstorm it with the user first.
- If the current architecture is unclear, read @docs and the source code before drawing conclusions or proposing a direction.
- If the current architecture appears problematic, do not redesign it within the same task unless the user explicitly asks for that. Instead, describe the observation, its impact, and propose handling it as a separate track.
- When there is a conflict between delivery speed and architectural consistency, prioritize architectural consistency unless the user explicitly requests a different trade-off.
- Do not impose personal preferences about code style, folder structure, abstractions, or patterns if the repository already has its own standards.
- Prefer changes that are small, clear, easy to review, and aligned with the overall direction of the system.

## Definition of done

- A request is only considered complete when the following conditions are satisfied, where applicable to the task scope:
- The user request has been correctly understood and reflected, or the applied assumptions have been clearly stated.
- Sufficient context has been read from the source code and @docs.
- The minimum necessary change to achieve the goal has been implemented.
- Tests have been added or updated at a reasonable level, or a clear reason has been given if that was not possible.
- Validation appropriate to the impact of the change has been performed.
- The results, run instructions, test guidance, remaining risks, and important notes have been reported back.

## Decision rules

- Ask the user again when a change may affect business rules, schema, data migration, API contracts, the security model, the permission model, billing, or user experience in a way that is difficult to reverse.
- Ask the user again when more than one reasonable solution exists and the right choice depends on product or operational priorities.
- You may decide on your own for local issues such as a clearly understood bug fix, test improvement, typing fix, lint fix, or a small refactor that does not change behavior.
- If you decide on your own, clearly state the assumptions and validation approach you used.

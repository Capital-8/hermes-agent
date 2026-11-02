# Projects and folders (`hermes project`)

A **Project** is a named workspace that can span several folders — a repo, a monorepo, a
scratch directory, a sibling repo you always open together. Projects are the named
workspaces the desktop sidebar groups chats by, and a kanban task linked to a project gets a
worktree and branch under the project's primary repo.

Projects are **not** git concepts and not config keys: they live in their own SQLite store,
one per profile (`$HERMES_HOME/projects.db`), so two profiles keep separate project lists.
The store is created on first use; nothing to enable.

## Command surface

`hermes project <sub> --help` is authoritative for flags.

| Subcommand | What it does |
|---|---|
| `create <name> [folders...]` | New project. First folder becomes the primary; `--slug`, `--primary PATH`, `--description`, `--icon`, `--color`, `--board SLUG`, `--use` (make it active). |
| `list` (alias `ls`) | Projects, oldest first; `*` marks the active one; `--all` includes archived. |
| `show <project>` | Slug, id, name, about/board/primary, folder list (`*` = primary). |
| `add-folder <project> <path>` | Add a folder; `--label`, `--primary` (make it primary). |
| `remove-folder <project> <path>` | Drop a folder (repoints primary if it was primary). |
| `rename <project> <name>` | Change the display name. The slug does **not** change. |
| `set-primary <project> <path>` | Primary folder; the path must already be in the project. |
| `use [<project>]` | Set the active project; with no argument, clear it. |
| `archive <project>` / `restore <project>` | Hide / unhide a project (reversible; nothing on disk moves). |
| `bind-board <project> [<board>]` | Record a kanban board on the project; omit the board to unbind. It does not link the board's tasks to the project (see Kanban below). |

`<project>` is an id (`p_1a2b3c4d`) or a slug, matched case-insensitively. The CLI does
**not** accept the display name: `hermes project show "Hermes Agent"` fails with
`no such project`; use the slug (`hermes-agent`) from `hermes project list`.

## Semantics worth knowing

- **Slug** — derived from the name (lowercased, runs of non-alphanumerics collapse to `-`,
  capped at 64 chars) unless `--slug` is given. An invalid `--slug` exits **2**. A slug that
  is already taken gets a suffix (`team-docs-2`, …), an explicit `--slug` included, so read
  the slug back from the `Created project <slug>` line.
- **Folders** — stored as absolute paths; `~`, relative paths and trailing slashes are
  normalized on every command, and paths are not checked for existence. The primary is the
  first folder given, or `--primary`; it anchors kanban worktrees and the folder a desktop
  chat moves to.
- **One project per primary folder** — `create` refuses a primary path that is already the
  primary of another (non-archived) project: `folder already belongs to project '<slug>'
  …; switch to it instead of creating a duplicate`. Reuse that project; two projects owning
  one path produce duplicate sidebar subtrees.
- **Active project** — one per-profile pointer that `use` sets and clears. Unscoped callers
  (CLI, scripts, messaging platforms) treat it as "the current project". A live desktop / TUI
  chat is scoped to its own workspace instead (see `desktop_project` below).
- **Archived projects** are hidden from `list` (use `--all`) and stop claiming their folders
  for path → project resolution; they still resolve by id or slug. `restore` brings them back.
- **Path → project resolution** — a folder owns itself and everything under it, and the
  longest matching folder wins, so a nested project resolves to the innermost one.
- **Deleting** — the CLI has no delete; `archive` is the reversible way to retire a project.
  The desktop app's project menu deletes permanently.
- **Exit codes** — `0` ok; `1` no such project, or the path is not a folder of that project
  (`remove-folder`, `set-primary`); `2` invalid input (bad slug or board slug, empty name,
  duplicate primary folder, bad arguments).

## What projects actually drive

- **Desktop sidebar grouping.** A chat's workspace (its cwd) resolves to the owning project
  by the path rule above, and the TUI status line and desktop status bar name it. The
  sidebar also shows automatic groups for git repos that are not projects; those do not
  appear in `hermes project list`.
- **The `desktop_project` tool** (toolset `project`, folded in by the desktop/TUI gateway;
  not in the default CLI or messaging toolsets). `action: create|switch|list` with `name` /
  `path`; unlike the CLI it also matches display names. In a live desktop/TUI chat, `create`
  and `switch` move *that chat's* workspace to the project's primary folder and the sidebar
  follows — the intended way to move a chat between projects, not `cd`. That move leaves the
  active-project pointer alone so other open chats are not redirected; a project with no
  folders cannot move the chat, so it sets the pointer instead. `create` with a `path` that
  is already another project's primary reuses that project instead of failing.
- **Kanban.** A task is linked to a project when it is created with
  `hermes kanban create … --project <slug>`, or when its board is bound to the project in the
  kanban dashboard (the board's Project selector); tasks on such a board inherit the project
  unless created with `--workspace scratch`. A project-linked worktree task gets a worktree
  at `<primary>/.worktrees/<task-id>` on branch `<project-slug>/<task-id>[-<title-slug>]`
  instead of the generic `wt/<task-id>`.
  `hermes project bind-board` is not that binding: it records the board on the project and,
  when the board already exists, sets the board's default workdir to the project's primary
  folder. Tasks on that board are not project-linked unless created with `--project`.

## Common tasks

```bash
# Make a project for a repo and start using it
hermes project create "Hermes Agent" ~/Work/hermes-agent --use

# A workspace spanning two repos (first given = primary)
hermes project create "Payments" ~/Work/payments-api ~/Work/payments-web

# Add a folder later / move the primary
hermes project add-folder payments ~/Work/payments-infra --label infra
hermes project set-primary payments ~/Work/payments-web

# What is active (archived included), and what a project contains
hermes project list --all
hermes project show payments

# Retire one without losing it
hermes project archive payments        # hidden from list / path resolution
hermes project restore payments

# A project-linked kanban worktree task (deterministic branch)
hermes kanban create "Wire the webhook" --workspace worktree --project payments
```

`$HERMES_HOME` defaults to `~/.hermes`; each profile keeps its own `projects.db`
(`hermes -p <profile> project list` lists that profile's projects).

## Troubleshooting

- **`no such project: <Name>`** — the CLI takes an id or slug, not the display name; get the
  slug from `hermes project list`.
- **"switched project but this chat didn't move"** — `hermes project use` only moves the
  profile pointer. A desktop/TUI chat follows its own workspace: switch from inside the chat
  (the `desktop_project` tool), or start the chat in the project's folder.
- **`create` refused: folder already belongs to project X** — the folder is already X's
  primary. Use X (`hermes project show X`, `rename` it if the name is wrong) rather than
  adding the folder to a second project.
- **Tasks on a bound board get no project branch** — `bind-board` does not link tasks; pass
  `--project <slug>` to `hermes kanban create`, or bind the board to the project in the
  kanban dashboard.
- **A project's folders look "unprojected"** — the project is archived;
  `hermes project restore <project>`.
- **Two profiles show different projects** — expected: `projects.db` is per profile.

## See also

- `references/cli-reference.md` — `hermes project` in the CLI command map.
- `references/background-systems.md` — kanban overview.
- `references/project-context-files.md` — a different feature: `AGENTS.md` / `.hermes.md` /
  `CLAUDE.md` instruction files that load into a session.
- Docs: `/user-guide/features/kanban#managing-boards-from-the-dashboard` (board ↔ project
  binding) and `/reference/cli-commands#hermes-project`.

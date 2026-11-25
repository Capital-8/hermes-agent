import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { ErrorBanner } from '@/components/ui/error-state'
import { installMessagingCatalogPlatform, type MessagingCatalogPlatform } from '@/hermes'
import { useI18n } from '@/i18n'
import { Download } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'

import { PlatformAvatar } from './platform-icon'

/** Selection id of a catalog row; installed platforms keep their bare id. */
export const catalogRowId = (row: MessagingCatalogPlatform) => `catalog:${row.name}`

const CAPTION =
  'text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-(--ui-text-tertiary)'

function BadgePill({ badge }: { badge: MessagingCatalogPlatform['badge'] }) {
  const { t } = useI18n()

  return (
    <span
      className={cn(
        'inline-flex h-5 shrink-0 items-center rounded-full px-2 text-[0.68rem] font-medium',
        badge === 'labs' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-300' : 'bg-primary/10 text-primary'
      )}
    >
      {t.messaging.catalog.badges[badge]}
    </span>
  )
}

export function CatalogPlatformRow({
  active,
  onSelect,
  row
}: {
  active: boolean
  onSelect: () => void
  row: MessagingCatalogPlatform
}) {
  return (
    <button
      className={cn(
        'row-hover flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:text-foreground',
        active ? 'bg-(--ui-row-active-background) text-foreground' : 'text-(--ui-text-secondary)'
      )}
      onClick={onSelect}
      type="button"
    >
      <PlatformAvatar platformId={row.name} platformName={row.title} />
      <span className="flex min-w-0 flex-1 items-center justify-between gap-2">
        <span className="truncate text-[length:var(--conversation-text-font-size)] font-normal">{row.title}</span>
        <BadgePill badge={row.badge} />
      </span>
    </button>
  )
}

/** A catalog platform's pane: what it is, then Install (a Hermes Labs one asks first), or why it cannot
 *  install here and the command that does. `onInstalled` gets the platform ids the plugin registered. */
export function CatalogPlatformDetail({
  onInstalled,
  row,
  scopeProfile
}: {
  onInstalled: (platformIds: string[]) => Promise<void>
  row: MessagingCatalogPlatform
  scopeProfile: string | undefined
}) {
  const { t } = useI18n()
  const c = t.messaging.catalog
  const [installing, setInstalling] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [failure, setFailure] = useState<null | { command: string; error: string }>(null)
  const [prevName, setPrevName] = useState(row.name)

  if (prevName !== row.name) {
    setPrevName(row.name)
    setFailure(null)
  }

  async function install(confirmed: boolean) {
    setInstalling(true)
    setFailure(null)

    try {
      const result = await installMessagingCatalogPlatform(row.name, confirmed, scopeProfile)

      if (!result.ok) {
        setFailure({ command: result.install_command || row.install_command, error: result.error || c.installFailed(row.title) })

        return
      }

      notify({ kind: 'success', title: c.installed(row.title), message: c.installedDetail })
      await onInstalled(result.platforms ?? [])
    } catch (err) {
      setFailure({ command: row.install_command, error: err instanceof Error ? err.message : String(err) })
    } finally {
      setInstalling(false)
    }
  }

  const blockedReason = row.blocked === 'lazy_installs_off' ? c.lazyOff : row.blocked_reason

  return (
    <>
      <header className="flex items-start gap-3">
        <PlatformAvatar platformId={row.name} platformName={row.title} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="min-w-0 truncate text-[0.9375rem] font-semibold tracking-tight">{row.title}</h3>
            <BadgePill badge={row.badge} />
            <span className={CAPTION}>{c.notInstalled}</span>
          </div>
          <p className={cn('mt-1', CAPTION)}>{row.summary}</p>
          {row.disclosure && (
            <p className={cn('mt-1', CAPTION)}>
              <span className="font-medium">{c.disclosure}</span> {row.disclosure}
            </p>
          )}
          {row.needs_confirm && <p className={cn('mt-1', CAPTION)}>{c.labsBody(row.title)}</p>}
        </div>
      </header>

      {row.blocked ? (
        <section className={cn('grid gap-1', CAPTION)} data-testid="catalog-blocked">
          <p>{blockedReason}</p>
          <p>
            {c.runCommand} <code className="rounded bg-muted px-1 py-0.5 text-foreground">{row.install_command}</code>
          </p>
        </section>
      ) : (
        <div>
          <Button disabled={installing} onClick={() => (row.needs_confirm ? setConfirming(true) : void install(false))} size="sm">
            <Download />
            {installing ? c.installing : c.install}
          </Button>
          <p className={cn('mt-2', CAPTION)}>{c.intro(row.title)}</p>
        </div>
      )}

      {failure && (
        <ErrorBanner>
          {failure.error}
          {failure.command && (
            <span className="block">
              {c.runCommand} <code>{failure.command}</code>
            </span>
          )}
        </ErrorBanner>
      )}

      <ConfirmDialog
        busyLabel={c.installing}
        cancelLabel={t.common.cancel}
        confirmLabel={c.labsConfirm}
        description={c.labsBody(row.title)}
        onClose={() => setConfirming(false)}
        onConfirm={() => install(true)}
        open={confirming}
        title={c.labsTitle}
      />
    </>
  )
}

import { useEffect, useMemo, useState } from "react"
import { Loader2, Lock } from "lucide-react"
import { toast } from "sonner"
import { MatchHero } from "@/components/match-hero"
import { SiteHeader } from "@/components/site-header"
import { SkinsDialog } from "@/components/skins-dialog"
import { TeamCard } from "@/components/team-card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { useAssets } from "@/hooks/use-assets"
import { LangProvider, useLang } from "@/hooks/use-lang"
import { useMatch } from "@/hooks/use-match"
import type { Player } from "@/lib/types"
import { teamLabel, teamOrder } from "@/lib/valorant"

type Side = "blue" | "red" | "none"
const sideOf = (team: string): Side => (team === "Blue" ? "blue" : team === "Red" ? "red" : "none")

function useLanUrl() {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => {
    fetch("/info", { cache: "no-store" })
      .then((r) => r.json())
      .then((i) => i?.lan_ip && i?.port && setUrl(`http://${i.lan_ip}:${i.port}`))
      .catch(() => {})
  }, [])
  return url
}

function Placeholder({ text }: { text: string }) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-20 text-muted-foreground">
      <Loader2 className="size-8 animate-spin text-primary" />
      <p>{text}</p>
    </div>
  )
}

function LicenseError({ message, hwid }: { message?: string; hwid?: string }) {
  const { t } = useLang()
  const copy = () => {
    if (hwid) navigator.clipboard?.writeText(hwid).then(() => toast.success(t.copied + hwid))
  }
  return (
    <div className="mx-auto flex max-w-lg flex-col items-center gap-3 py-16 text-center">
      <Lock className="size-10 text-primary" />
      <h2 className="text-xl font-bold text-primary">{t.licenseFailedTitle}</h2>
      <p>{message || t.machineNotAuthorized}</p>
      <p className="text-sm text-muted-foreground">{t.sendHwid}</p>
      <button
        type="button"
        onClick={copy}
        title={t.clickToCopy}
        className="w-full break-all rounded-lg border bg-card p-3 font-mono text-sm"
      >
        {hwid}
      </button>
      <Button variant="outline" onClick={copy}>
        {t.copyHwid}
      </Button>
    </div>
  )
}

function Panel() {
  const { t } = useLang()
  const { data, hasData, failed } = useMatch()
  const { agents, tiers } = useAssets()
  const lan = useLanUrl()
  const [skinsFor, setSkinsFor] = useState<string | null>(null)
  const [quit, setQuit] = useState(false)

  const state = data.state ?? undefined
  const licenseErr = state === "LICENSE_ERROR"
  const live = !!state && state !== "DISCONNECTED" && !licenseErr
  const stateLabel = licenseErr
    ? t.licenseError
    : (state && (t.state as Record<string, string>)[state]) || t.waiting
  const modeText = data.mode ? (t.mode as Record<string, string>)[data.mode] || data.mode : ""

  let statusText = !hasData ? t.connecting : stateLabel + (modeText ? " · " + modeText : "")
  if (failed >= 3) statusText = t.connectionError

  const groups = useMemo(() => {
    const entries = Object.entries(data.players ?? {})
    const distinct = [...new Set(entries.map(([, p]) => p.team).filter(Boolean))] as string[]
    if (distinct.length === 2) {
      return distinct
        .sort((a, b) => teamOrder(a) - teamOrder(b))
        .map((team, idx) => ({
          key: team,
          title: teamLabel(team, data.state, idx, t),
          side: sideOf(team),
          list: entries.filter(([, p]) => p.team === team),
        }))
    }
    if (distinct.length === 1) {
      const team = distinct[0]
      return [{ key: team, title: teamLabel(team, data.state, 0, t), side: sideOf(team), list: entries }]
    }
    return [{ key: "all", title: t.playersTitle, side: "none" as Side, list: entries }]
  }, [data, t])

  const quitApp = () => {
    fetch("/quit").catch(() => {})
    setQuit(true)
  }

  if (quit) return <p className="mt-32 text-center text-muted-foreground">{t.quitMsg}</p>

  const hasPlayers = Object.keys(data.players ?? {}).length > 0
  const skinPlayer: Player | null = skinsFor ? (data.players?.[skinsFor] ?? null) : null

  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader statusText={statusText} live={live} onQuit={quitApp} />

      <main className="mx-auto w-full max-w-7xl flex-1 space-y-6 px-4 py-6 sm:px-6">
        <MatchHero
          stateLabel={hasData ? stateLabel : t.loading}
          mapName={licenseErr ? t.accessDenied : data.map_name || "Valorant Decloak"}
          modeLine={
            licenseErr
              ? data.message || t.licenseNotVerified
              : modeText + (data.server ? (modeText ? " • " : "") + data.server : "")
          }
          image={licenseErr ? undefined : data.map_image}
        />

        {licenseErr ? (
          <LicenseError message={data.message} hwid={data.hwid} />
        ) : !hasData ? (
          <div className="grid gap-5 lg:grid-cols-2">
            <Skeleton className="h-80 rounded-xl" />
            <Skeleton className="hidden h-80 rounded-xl lg:block" />
          </div>
        ) : !hasPlayers ? (
          <Placeholder text={state === "DISCONNECTED" ? t.disconnected : t.noPlayers} />
        ) : (
          <div className={groups.length === 2 ? "grid items-start gap-5 lg:grid-cols-2" : "mx-auto max-w-3xl"}>
            {groups.map((g) => (
              <TeamCard
                key={g.key}
                title={g.title}
                side={g.side}
                players={g.list}
                selfPuuid={data.puuid}
                agents={agents}
                tiers={tiers}
                onSkins={setSkinsFor}
              />
            ))}
          </div>
        )}
      </main>

      <footer className="border-t py-5 text-center text-xs text-muted-foreground">
        {lan && (
          <>
            {t.web}
            <a className="font-semibold text-primary hover:underline" href={lan}>
              {lan}
            </a>
            {" • "}
          </>
        )}
        Valorant Decloak by{" "}
        <a
          href="https://x.com/tcoyapps"
          target="_blank"
          rel="noopener"
          className="font-semibold text-primary hover:underline"
        >
          tcoy
        </a>
      </footer>

      <SkinsDialog player={skinPlayer} onClose={() => setSkinsFor(null)} />
      <Toaster position="bottom-center" theme="dark" />
    </div>
  )
}

export default function App() {
  return (
    <LangProvider>
      <TooltipProvider delayDuration={200}>
        <Panel />
      </TooltipProvider>
    </LangProvider>
  )
}

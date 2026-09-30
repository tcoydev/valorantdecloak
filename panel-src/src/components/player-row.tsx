import type { CSSProperties } from "react"
import { Shirt } from "lucide-react"
import { toast } from "sonner"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { TableCell, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { GameImg } from "@/components/game-img"
import { useLang } from "@/hooks/use-lang"
import { HIDDEN_NAME } from "@/lib/i18n"
import type { Player, TierInfo } from "@/lib/types"
import { VLOGO, partyColor, predictedColor, rankInfo, splitName } from "@/lib/valorant"
import { cn } from "@/lib/utils"

interface Props {
  puuid: string
  player: Player
  isSelf: boolean
  agents: Record<string, string>
  tiers: Record<number, TierInfo>
  onSkins: (puuid: string) => void
}

function copyText(text: string, label: string) {
  if (!navigator.clipboard) return
  navigator.clipboard
    .writeText(text)
    .then(() => toast.success(label + text, { duration: 1300 }))
    .catch(() => {})
}

function Stat({ value, className }: { value: string | null; className?: string }) {
  return (
    <span className={cn("font-semibold tabular-nums", className)}>
      {value ?? <span className="text-muted-foreground/40">–</span>}
    </span>
  )
}

// Kendi satırın: altın; gerçek premade: dolu renkli kenar; tahmini: kesik kenar.
function rowStyle(isSelf: boolean, real: string | null, predicted: string | null): CSSProperties | undefined {
  if (isSelf) {
    return {
      background: "linear-gradient(90deg, color-mix(in oklab, var(--gold) 12%, transparent), transparent 70%)",
      boxShadow: "inset 3px 0 0 var(--gold)",
    }
  }
  if (real) {
    return {
      background: `linear-gradient(90deg, color-mix(in srgb, ${real} 16%, transparent), transparent 72%)`,
      boxShadow: `inset 3px 0 0 ${real}`,
    }
  }
  if (predicted) {
    return {
      backgroundImage: `repeating-linear-gradient(to bottom, ${predicted} 0 4px, transparent 4px 9px), linear-gradient(90deg, color-mix(in srgb, ${predicted} 8%, transparent), transparent 72%)`,
      backgroundSize: "3px 100%, 100% 100%",
      backgroundRepeat: "no-repeat",
      backgroundPosition: "left, 0 0",
    }
  }
  return undefined
}

export function PlayerRow({ puuid, player: p, isSelf, agents, tiers, onSkins }: Props) {
  const { t } = useLang()
  const real = partyColor(p)
  const predicted = real ? null : predictedColor(p) // gerçek parti önceliklidir

  const ri = rankInfo(parseInt(String(p.rank), 10) || 0, tiers, t)
  const { name, tag } = splitName(p.name)
  const full = p.name || ""
  const card = p.playerCard ? `https://media.valorant-api.com/playercards/${p.playerCard}/smallart.png` : null
  const avatarSrc = (p.agent && agents[p.agent]) || card || VLOGO

  const rrNum = p.rr === 0 || p.rr ? parseInt(String(p.rr), 10) : null

  // Sadece gerçek sayılar: "-" (competitive maçı yok) ve "N/A" (hata) gizlenir.
  // Stat verisi arka planda çekilir; gelene kadar boş kalır.
  const statsReady = p.kd != null
  const kdNum = parseFloat(String(p.kd))
  const kd = statsReady && !isNaN(kdNum) ? String(p.kd) : null
  const hsNum = parseFloat(String(p.headshotPercentage))
  const hs = statsReady && !isNaN(hsNum) ? hsNum + "%" : null
  const lvlNum = parseInt(String(p.level), 10)
  const lvl = statsReady && lvlNum > 0 ? String(p.level) : null

  const peakIdx = parseInt(String(p.peakRank), 10)
  const peak = !isNaN(peakIdx) && peakIdx > 2 ? rankInfo(peakIdx, tiers, t) : null
  const peakSub =
    p.peakRR === 0 || p.peakRR
      ? `${parseInt(String(p.peakRR), 10)} RR`
      : String(p.peakRankAct || "").replace(/[()\s]/g, "")

  const trackerUrl = "https://tracker.gg/valorant/profile/riot/" + encodeURIComponent(full) + "/overview"
  const vtlUrl = "https://vtl.lol/id/" + encodeURIComponent(puuid)

  const onName = () => {
    // Telefonda nicke basınca skinleri aç; masaüstünde kopyala.
    if (window.matchMedia("(max-width: 640px)").matches) onSkins(puuid)
    else copyText(full === HIDDEN_NAME ? puuid : full, t.copied)
  }

  return (
    <TableRow className="group/row" style={rowStyle(isSelf, real, predicted)}>
      <TableCell className="w-full max-w-0 py-2.5 pl-4">
        <div className="flex items-center gap-3">
          <Avatar className="size-10 rounded-lg after:rounded-lg">
            <AvatarImage src={avatarSrc} className="rounded-lg bg-black object-cover" />
            <AvatarFallback className="rounded-lg">
              <img src={VLOGO} alt="" className="size-5" />
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={onName}
                  className="flex max-w-full items-baseline gap-0.5 rounded text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="truncate text-sm font-semibold transition-colors group-hover/row:text-primary">
                    {name}
                  </span>
                  <span className="text-xs text-muted-foreground">{tag}</span>
                </button>
              </TooltipTrigger>
              <TooltipContent>{full === HIDDEN_NAME ? "PUUID" : full}</TooltipContent>
            </Tooltip>
            <div className="mt-1 flex items-center gap-2">
              <span
                className="inline-flex items-center gap-1.5 rounded-md border bg-muted/40 py-0.5 pl-1 pr-2 text-xs font-semibold"
                style={{ color: ri.color }}
              >
                {ri.icon && <GameImg src={ri.icon} className="size-4" />}
                {ri.name}
              </span>
              {rrNum !== null && (
                <span className="text-xs font-medium tabular-nums text-muted-foreground">{rrNum} RR</span>
              )}
            </div>
          </div>
        </div>
      </TableCell>

      <TableCell className="px-2 text-center">
        <Stat value={kd} className={kdNum >= 1 ? "text-positive" : "text-negative"} />
      </TableCell>
      <TableCell className="hidden px-2 text-center sm:table-cell">
        <Stat value={hs} />
      </TableCell>
      <TableCell className="hidden px-2 text-center md:table-cell">
        <Stat value={lvl} className="text-muted-foreground" />
      </TableCell>
      <TableCell className="px-2 text-center">
        {statsReady && peak?.icon ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="mx-auto flex w-14 flex-col items-center gap-0.5">
                <GameImg src={peak.icon} className="size-5" />
                <span className="text-[11px] font-bold tabular-nums text-gold">{peakSub}</span>
              </div>
            </TooltipTrigger>
            <TooltipContent>Peak: {peak.name}</TooltipContent>
          </Tooltip>
        ) : null}
      </TableCell>

      <TableCell className="pr-3 max-sm:hidden">
        <div className="ml-auto grid w-[4.5rem] grid-cols-2 gap-0.5 opacity-60 transition-opacity group-hover/row:opacity-100">
          <Button asChild variant="outline" size="xs" className="h-5 rounded-md px-1 text-[10px] font-bold">
            <a href={trackerUrl} target="_blank" rel="noopener">TRK</a>
          </Button>
          <Button asChild variant="outline" size="xs" className="h-5 rounded-md px-1 text-[10px] font-bold">
            <a href={vtlUrl} target="_blank" rel="noopener">VTL</a>
          </Button>
          <Button
            variant="outline"
            size="xs"
            className="col-span-2 h-5 gap-1 rounded-md px-1 text-[10px] [&_svg]:size-3"
            onClick={() => onSkins(puuid)}
            title={t.skinsTitleAttr}
          >
            <Shirt /> {t.skins}
          </Button>
        </div>
      </TableCell>
    </TableRow>
  )
}

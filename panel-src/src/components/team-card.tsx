import { Card, CardAction, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { PlayerRow } from "@/components/player-row"
import { useLang } from "@/hooks/use-lang"
import type { Player, TierInfo } from "@/lib/types"
import { cn } from "@/lib/utils"

interface Props {
  title: string
  side: "blue" | "red" | "none"
  players: [string, Player][]
  selfPuuid?: string
  agents: Record<string, string>
  tiers: Record<number, TierInfo>
  onSkins: (puuid: string) => void
}

export function TeamCard({ title, side, players, selfPuuid, agents, tiers, onSkins }: Props) {
  const { t } = useLang()
  return (
    <Card className="gap-0 overflow-hidden py-0">
      <CardHeader
        className={cn(
          "border-b bg-muted/30 py-3.5",
          side === "blue" && "border-l-[3px] border-l-team-a",
          side === "red" && "border-l-[3px] border-l-team-b",
        )}
      >
        <CardTitle
          className={cn(
            "text-sm font-bold uppercase tracking-wider",
            side === "blue" && "text-team-a",
            side === "red" && "text-team-b",
          )}
        >
          {title}
        </CardTitle>
        <CardAction className="text-xs font-medium uppercase tabular-nums text-muted-foreground">
          {players.length} {t.players}
        </CardAction>
      </CardHeader>

      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="pl-4">{t.playersTitle}</TableHead>
            <TableHead className="px-2 text-center" title={t.statsNote}>K/D</TableHead>
            <TableHead className="hidden px-2 text-center sm:table-cell" title={t.statsNote}>HS</TableHead>
            <TableHead className="hidden px-2 text-center md:table-cell">LVL</TableHead>
            <TableHead className="px-2 text-center">PEAK</TableHead>
            <TableHead className="max-sm:hidden" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {players.map(([puuid, p]) => (
            <PlayerRow
              key={puuid}
              puuid={puuid}
              player={p}
              isSelf={puuid === selfPuuid}
              agents={agents}
              tiers={tiers}
              onSkins={onSkins}
            />
          ))}
        </TableBody>
      </Table>
      <p className="border-t px-4 py-2 text-[11px] text-muted-foreground">{t.statsNote}</p>
    </Card>
  )
}

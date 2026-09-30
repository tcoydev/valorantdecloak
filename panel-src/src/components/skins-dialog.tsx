import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { GameImg } from "@/components/game-img"
import { useLang } from "@/hooks/use-lang"
import type { Player, Weapon } from "@/lib/types"
import { WEAPON_GROUPS, splitName } from "@/lib/valorant"

interface Props {
  player: Player | null
  onClose: () => void
}

function WeaponCard({ label, w }: { label: string; w?: Weapon }) {
  const { t } = useLang()
  return (
    <div
      className="relative overflow-hidden rounded-lg border bg-muted/30 px-3 pb-2 pt-3 transition-colors hover:bg-muted/60"
      title={w?.skinDisplayName}
    >
      <div className="flex h-14 items-center justify-center">
        {w?.skinDisplayIcon && (
          <GameImg
            src={w.skinDisplayIcon}
            loading="lazy"
            className="max-h-14 max-w-full object-contain drop-shadow-md"
          />
        )}
      </div>
      {w?.buddy_displayIcon && (
        <GameImg
          src={w.buddy_displayIcon}
          loading="lazy"
          title={t.buddy}
          className="absolute bottom-6 right-2 size-6 object-contain"
        />
      )}
      <div className="mt-1.5 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">{label}</div>
    </div>
  )
}

export function SkinsDialog({ player: p, onClose }: Props) {
  const { t } = useLang()
  const { name, tag } = splitName(p?.name)

  const byName: Record<string, Weapon> = {}
  Object.values(p?.weapons ?? {}).forEach((w) => {
    if (w?.weapon) byName[String(w.weapon).toLowerCase()] = w
  })
  const hasWeapons = Object.keys(byName).length > 0
  const lvl = parseInt(String(p?.level), 10)
  const cardArt = p?.playerCard
    ? `https://media.valorant-api.com/playercards/${p.playerCard}/largeart.png`
    : null

  return (
    <Dialog open={!!p} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="flex max-h-[90vh] w-[96vw] flex-col gap-0 p-0 sm:max-w-6xl">
        <DialogHeader className="border-b px-5 py-4">
          <DialogTitle className="flex items-baseline gap-2 text-xl">
            {name}
            <span className="text-sm font-normal text-muted-foreground">{tag}</span>
          </DialogTitle>
          <DialogDescription className="text-xs font-bold uppercase tracking-widest text-primary">
            {t.weaponSkins}
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="min-h-0 flex-1">
          <div className="columns-1 gap-x-5 p-5 sm:columns-2 lg:columns-4 xl:columns-5">
            {hasWeapons ? (
              WEAPON_GROUPS.map((names, i) => (
                <section key={i} className="mb-6 break-inside-avoid space-y-2">
                  <h3 className="text-center text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    {t.weaponCats[i]}
                  </h3>
                  {names.map((nm) => (
                    <WeaponCard key={nm} label={nm} w={byName[nm.toLowerCase()]} />
                  ))}
                </section>
              ))
            ) : (
              <p className="mb-6 break-inside-avoid rounded-lg border bg-muted/30 p-6 text-center text-sm text-muted-foreground">
                {t.skinsEmpty}
              </p>
            )}

            <section className="mb-6 break-inside-avoid space-y-2">
              <h3 className="text-center text-xs font-bold uppercase tracking-wider text-muted-foreground">
                {t.playerCard}
              </h3>
              <div className="relative overflow-hidden rounded-lg border bg-background">
                {lvl > 0 && (
                  <span className="absolute left-1/2 top-2 z-10 -translate-x-1/2 rounded-full border border-gold bg-background/85 px-3 py-0.5 text-xs font-bold text-gold">
                    {p?.level}
                  </span>
                )}
                {cardArt ? <GameImg src={cardArt} className="block h-auto w-full" /> : <div className="h-64 bg-muted" />}
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-background/95 to-transparent p-2 text-center text-sm font-bold">
                  {name}
                </div>
              </div>
            </section>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}

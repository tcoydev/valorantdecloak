import { Crosshair, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useLang } from "@/hooks/use-lang"
import type { Lang } from "@/lib/i18n"
import { cn } from "@/lib/utils"

interface Props {
  statusText: string
  live: boolean
  onQuit: () => void
}

export function SiteHeader({ statusText, live, onQuit }: Props) {
  const { t, lang, setLang } = useLang()

  return (
    <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 w-full max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
        <div className="flex items-center gap-2.5">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <Crosshair className="size-4" />
          </div>
          <span className="text-sm font-bold tracking-[0.18em]">
            VALORANT <span className="text-primary">DECLOAK</span>
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="h-7 gap-2 px-3 font-medium text-muted-foreground" aria-live="polite">
            <span
              className={cn(
                "size-2 rounded-full bg-muted-foreground/50",
                live && "animate-pulse bg-positive shadow-[0_0_8px] shadow-positive",
              )}
            />
            <span className="max-w-[38vw] truncate sm:max-w-none">{statusText}</span>
          </Badge>

          <ToggleGroup
            type="single"
            variant="outline"
            size="sm"
            value={lang}
            onValueChange={(v) => v && setLang(v as Lang)}
            aria-label="Language / Dil"
          >
            <ToggleGroupItem value="tr" className="px-2.5 text-xs font-semibold">TR</ToggleGroupItem>
            <ToggleGroupItem value="en" className="px-2.5 text-xs font-semibold">EN</ToggleGroupItem>
          </ToggleGroup>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                onClick={onQuit}
                aria-label={t.quitTitle}
                className="hover:border-primary hover:bg-primary hover:text-primary-foreground"
              >
                <X />
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t.quitTitle}</TooltipContent>
          </Tooltip>
        </div>
      </div>
    </header>
  )
}

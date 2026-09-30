import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"

interface Props {
  stateLabel: string
  mapName: string
  modeLine: string
  image?: string
}

export function MatchHero({ stateLabel, mapName, modeLine, image }: Props) {
  return (
    <Card className="relative h-44 justify-end overflow-hidden py-0 sm:h-52">
      {image && <img src={image} alt="" className="absolute inset-0 size-full object-cover" />}
      <div className="absolute inset-0 bg-gradient-to-r from-background via-background/70 to-background/10" />
      <div className="absolute inset-0 bg-gradient-to-t from-background/90 to-transparent" />
      <div className="relative z-10 flex flex-col items-start gap-2 p-5 sm:p-7">
        <Badge className="border border-primary/40 bg-primary/15 uppercase tracking-widest text-primary hover:bg-primary/15">
          {stateLabel}
        </Badge>
        <h1 className="text-3xl font-bold leading-none tracking-tight drop-shadow sm:text-5xl">{mapName}</h1>
        <p className="text-sm font-medium text-muted-foreground">{modeLine}</p>
      </div>
    </Card>
  )
}

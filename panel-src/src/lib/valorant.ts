import type { Dict } from "@/lib/i18n"
import type { Player, TierInfo } from "@/lib/types"

export const VLOGO =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 300'%3E%3Cpolygon points='150,30 270,270 210,270 150,115 90,270 30,270' fill='%23FF4655'/%3E%3C/svg%3E"

// Aynı numara = aynı grup = aynı renk. 1. renk (sarı) kendi grubunla aynı tonda.
const PARTY_COLORS = ["#f5c451", "#4c97ed", "#43d17a", "#e0658a", "#b07cf0", "#5ad1cd"]

function partyIdx(n: unknown) {
  const v = parseInt(String(n), 10)
  return !v || v <= 0 ? null : PARTY_COLORS[(v - 1) % PARTY_COLORS.length]
}
export const partyColor = (p: Player) => partyIdx(p.partyNumber)
// Tahmini grup: presence ile gerçek tespit yapılamayanlar için geçmiş maç birlikteliğinden.
export const predictedColor = (p: Player) => partyIdx(p.predictedParty)

export function splitName(full?: string) {
  if (!full) return { name: "?", tag: "" }
  const i = full.lastIndexOf("#")
  return i < 0 ? { name: full, tag: "" } : { name: full.slice(0, i), tag: full.slice(i) }
}

export function rankInfo(idx: number, tiers: Record<number, TierInfo>, t: Dict) {
  const tier = tiers[idx]
  return {
    name: t.ranks[idx] ?? "?",
    color: tier ? tier.color : "#8a909c",
    icon: tier ? tier.icon : null,
  }
}

export function teamOrder(team: string) {
  return team === "Blue" ? 0 : team === "Red" ? 1 : 2
}

export function teamLabel(team: string, state: string | null | undefined, idx: number, t: Dict) {
  let label: string
  if (team === "Blue") label = t.teamA
  else if (team === "Red") label = t.teamB
  else label = t.teamFallback + String.fromCharCode(65 + idx)
  if (state === "PREGAME" && (team === "Blue" || team === "Red")) {
    label += " - " + (team === "Blue" ? t.defense : t.attack)
  }
  return label
}

// Silahlar dilden bağımsız; kategori başlığı çevrilir.
export const WEAPON_GROUPS = [
  ["Classic", "Shorty", "Frenzy", "Ghost", "Sheriff"],
  ["Stinger", "Spectre"],
  ["Bucky", "Judge"],
  ["Bulldog", "Guardian", "Phantom", "Vandal"],
  ["Melee"],
  ["Marshal", "Outlaw", "Operator"],
  ["Ares", "Odin"],
]

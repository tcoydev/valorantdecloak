export interface Weapon {
  weapon?: string
  skinDisplayIcon?: string
  skinDisplayName?: string
  buddy_displayIcon?: string
}

export interface Player {
  name?: string
  team?: string
  agent?: string
  rank?: number | string
  rr?: number | string | null
  peakRank?: number | string
  peakRR?: number | string | null
  peakRankAct?: string
  kd?: number | string | null
  headshotPercentage?: number | string | null
  level?: number | string | null
  playerCard?: string
  partyNumber?: number | string
  predictedParty?: number | string
  weapons?: Record<string, Weapon>
}

export interface MatchData {
  state?: string | null
  mode?: string
  map_name?: string
  map_image?: string
  server?: string
  puuid?: string
  players: Record<string, Player>
  // LICENSE_ERROR durumu
  message?: string
  hwid?: string
}

export interface TierInfo {
  color: string
  icon: string | null
}

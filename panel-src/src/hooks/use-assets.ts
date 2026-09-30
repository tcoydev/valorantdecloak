import { useEffect, useState } from "react"
import type { TierInfo } from "@/lib/types"

// Ajan/rank ikon adresleri valorant-api.com'dan gelir. Başarısız olursa artan
// aralıkla tekrar denenir; sonuç localStorage'a yazılır, sonraki açılışta anında görünür.
const CACHE_KEY = "vd_assets_v1"

interface Assets {
  agents: Record<string, string>
  tiers: Record<number, TierInfo>
}

function readCache(): Assets {
  try {
    const c = JSON.parse(localStorage.getItem(CACHE_KEY) || "{}")
    return { agents: c.agents ?? {}, tiers: c.tiers ?? {} }
  } catch {
    return { agents: {}, tiers: {} }
  }
}

async function retryUntilOk(fn: () => Promise<void>, cancelled: () => boolean) {
  for (let delay = 2000; !cancelled(); delay = Math.min(delay * 2, 30000)) {
    try {
      await fn()
      return
    } catch {
      /* tekrar dene */
    }
    await new Promise((r) => setTimeout(r, delay))
  }
}

export function useAssets() {
  const [assets, setAssets] = useState<Assets>(readCache)

  useEffect(() => {
    let stop = false
    const save = (next: Assets) => {
      try {
        localStorage.setItem(CACHE_KEY, JSON.stringify(next))
      } catch {
        /* yoksay */
      }
    }

    // Dış siteye giden istekler /data poll'unu asla bloklamaz; ayrı ve bağımsız çalışır.
    retryUntilOk(async () => {
      const res = await fetch("https://valorant-api.com/v1/agents?isPlayableCharacter=true", {
        signal: AbortSignal.timeout(8000),
      })
      const j = await res.json()
      const agents: Record<string, string> = {}
      j.data.forEach((a: { displayName: string; displayIcon: string }) => {
        agents[a.displayName] = a.displayIcon
      })
      if (!Object.keys(agents).length) throw new Error("boş ajan listesi")
      if (stop) return
      setAssets((prev) => {
        const next = { ...prev, agents }
        save(next)
        return next
      })
    }, () => stop)

    retryUntilOk(async () => {
      const res = await fetch("https://valorant-api.com/v1/competitivetiers", {
        signal: AbortSignal.timeout(8000),
      })
      const j = await res.json()
      const tiers: Record<number, TierInfo> = {}
      j.data[j.data.length - 1].tiers.forEach(
        (t: { tier: number; color?: string; smallIcon: string }) => {
          tiers[t.tier] = { color: "#" + (t.color ? t.color.slice(0, 6) : "8a909c"), icon: t.smallIcon }
        },
      )
      if (!Object.keys(tiers).length) throw new Error("boş rank listesi")
      if (stop) return
      setAssets((prev) => {
        const next = { ...prev, tiers }
        save(next)
        return next
      })
    }, () => stop)

    return () => {
      stop = true
    }
  }, [])

  return assets
}

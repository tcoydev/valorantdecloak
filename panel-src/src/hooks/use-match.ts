import { useEffect, useRef, useState } from "react"
import type { MatchData } from "@/lib/types"

const EMPTY: MatchData = { state: null, players: {} }

// /data'yı 1.5 sn'de bir çeker. Veri değişmediyse state güncellenmez (gereksiz render yok).
export function useMatch() {
  const [data, setData] = useState<MatchData>(EMPTY)
  const [hasData, setHasData] = useState(false)
  const [failed, setFailed] = useState(0)
  const last = useRef("")

  useEffect(() => {
    let stop = false
    async function poll() {
      try {
        const res = await fetch("/data", { cache: "no-store", signal: AbortSignal.timeout(5000) })
        const text = await res.text()
        if (stop) return
        setFailed(0)
        if (text !== last.current) {
          last.current = text
          setData(JSON.parse(text) as MatchData)
          setHasData(true)
        }
      } catch {
        if (!stop) setFailed((n) => n + 1)
      }
    }
    poll()
    const id = setInterval(poll, 1500)
    return () => {
      stop = true
      clearInterval(id)
    }
  }, [])

  return { data, hasData, failed }
}

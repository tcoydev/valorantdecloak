import { useEffect, useRef, useState } from "react"
import type { ImgHTMLAttributes } from "react"

// valorant-api.com görselleri geçici ağ hatasında 3 kereye kadar artan gecikmeyle
// yeniden denenir; ikon kalıcı olarak kaybolmaz. Hâlâ yüklenemezse fallback gösterilir.
export function GameImg({
  src,
  fallback,
  ...rest
}: ImgHTMLAttributes<HTMLImageElement> & { src: string; fallback?: string }) {
  const [attempt, setAttempt] = useState(0)
  const [dead, setDead] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => {
    setAttempt(0)
    setDead(false)
  }, [src])
  useEffect(() => () => clearTimeout(timer.current), [])

  if (dead) return fallback ? <img {...rest} src={fallback} alt="" /> : null

  const url = attempt === 0 ? src : src + (src.includes("?") ? "&" : "?") + "r=" + attempt
  return (
    <img
      {...rest}
      src={url}
      alt={rest.alt ?? ""}
      onError={() => {
        if (attempt >= 3) return setDead(true)
        timer.current = setTimeout(() => setAttempt((a) => a + 1), 1500 * (attempt + 1))
      }}
    />
  )
}

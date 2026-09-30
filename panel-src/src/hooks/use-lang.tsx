import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"
import type { ReactNode } from "react"
import { I18N } from "@/lib/i18n"
import type { Dict, Lang } from "@/lib/i18n"

interface LangCtx {
  lang: Lang
  t: Dict
  setLang: (l: Lang) => void
}

const Ctx = createContext<LangCtx | null>(null)

function initialLang(): Lang {
  try {
    const v = localStorage.getItem("vd_lang")
    if (v === "tr" || v === "en") return v
  } catch {
    /* localStorage kapalı olabilir */
  }
  return "tr"
}

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang)

  const setLang = useCallback((l: Lang) => {
    setLangState(l)
    try {
      localStorage.setItem("vd_lang", l)
    } catch {
      /* yoksay */
    }
  }, [])

  // Discord RPC'nin de aynı dili kullanması için backend'e bildir.
  useEffect(() => {
    document.documentElement.lang = lang
    fetch("/lang?l=" + encodeURIComponent(lang)).catch(() => {})
  }, [lang])

  const value = useMemo(() => ({ lang, t: I18N[lang] as Dict, setLang }), [lang, setLang])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useLang() {
  const c = useContext(Ctx)
  if (!c) throw new Error("useLang, LangProvider içinde kullanılmalı")
  return c
}

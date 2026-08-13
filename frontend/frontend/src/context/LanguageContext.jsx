import { createContext, useContext, useState, useCallback } from 'react'
import { TRANSLATIONS, getSavedLanguage, saveLanguage, resolve } from '../i18n/index'

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(getSavedLanguage)

  const setLanguage = useCallback((code) => {
    if (TRANSLATIONS[code]) {
      setLang(code)
      saveLanguage(code)
    }
  }, [])

  /** t('nav.home') → translated string */
  const t = useCallback(
    (key) => resolve(TRANSLATIONS[lang], key),
    [lang]
  )

  return (
    <LanguageContext.Provider value={{ lang, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used inside <LanguageProvider>')
  return ctx
}

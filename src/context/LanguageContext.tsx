import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import { translations } from '../translations';
import type { Language, TranslationKey } from '../translations';

// ============================================================================
// TYPES
// ============================================================================

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: TranslationKey, variables?: Record<string, string | number>) => string;
  toggleLanguage: () => void;
  availableLanguages: Language[];
  isRTL: boolean;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const STORAGE_KEY = 'threshold-ai-language';
const AVAILABLE_LANGUAGES: Language[] = ['tr', 'en'];
const RTL_LANGUAGES: Language[] = []; // Add RTL languages if needed

// ============================================================================
// CONTEXT
// ============================================================================

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

// ============================================================================
// PROVIDER
// ============================================================================

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>('tr');

  // Load saved language on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && AVAILABLE_LANGUAGES.includes(stored as Language)) {
      setLanguageState(stored as Language);
    } else {
      const browserLang = navigator.language.split('-')[0];
      if (AVAILABLE_LANGUAGES.includes(browserLang as Language)) {
        setLanguageState(browserLang as Language);
      }
    }
  }, []);

  // Persist language selection
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, language);
    document.documentElement.lang = language;
    document.documentElement.dir = RTL_LANGUAGES.includes(language) ? 'rtl' : 'ltr';
  }, [language]);

  const setLanguage = useCallback((lang: Language) => {
    if (AVAILABLE_LANGUAGES.includes(lang)) {
      setLanguageState(lang);
    }
  }, []);

  const toggleLanguage = useCallback(() => {
    setLanguageState((prev) => (prev === 'tr' ? 'en' : 'tr'));
  }, []);

  /**
   * Translation function with variable interpolation support
   * Usage: t('greeting', { name: 'John' }) -> "Hello, John!"
   * Variables in translation strings: "Hello, {{name}}!"
   */
  const t = useCallback((key: TranslationKey, variables?: Record<string, string | number>): string => {
    let text = translations[language][key];
    
    if (!text) {
      // Fallback to English if key not found
      text = translations.en[key];
      if (!text) {
        console.warn(`Translation key "${key}" not found`);
        return key;
      }
    }

    // Interpolate variables if provided
    if (variables) {
      Object.entries(variables).forEach(([varKey, value]) => {
        text = text.replace(new RegExp(`{{${varKey}}}`, 'g'), String(value));
      });
    }

    return text;
  }, [language]);

  const isRTL = RTL_LANGUAGES.includes(language);

  const value: LanguageContextType = {
    language,
    setLanguage,
    t,
    toggleLanguage,
    availableLanguages: AVAILABLE_LANGUAGES,
    isRTL,
  };

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

// ============================================================================
// HOOKS
// ============================================================================

/**
 * Primary hook for accessing language context
 */
export function useLanguage(): LanguageContextType {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}

/**
 * Convenience hook that returns just the translation function
 * Useful when you only need to translate strings
 */
export function useTranslation(): {
  t: (key: TranslationKey, variables?: Record<string, string | number>) => string;
  language: Language;
} {
  const { t, language } = useLanguage();
  return { t, language };
}

/**
 * Hook for components that need to react to language changes
 * Returns a key that changes when language changes (useful for re-rendering)
 */
export function useLanguageKey(): string {
  const { language } = useLanguage();
  return `lang-${language}`;
}

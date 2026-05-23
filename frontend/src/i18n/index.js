import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import enCommon from '../locales/en/common.json';
import knCommon from '../locales/kn/common.json';
import hiCommon from '../locales/hi/common.json';

const STORAGE_KEY = 'app_lang';
const FALLBACK_LANGUAGE = 'en';
const supportedLanguages = ['en', 'kn', 'hi'];

const readPreferredLanguage = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && supportedLanguages.includes(stored)) {
      return stored;
    }
  } catch (_err) {
    // Ignore storage access failures.
  }
  return FALLBACK_LANGUAGE;
};

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: enCommon },
      kn: { translation: knCommon },
      hi: { translation: hiCommon },
    },
    lng: readPreferredLanguage(),
    fallbackLng: FALLBACK_LANGUAGE,
    interpolation: {
      escapeValue: false,
    },
  });

i18n.on('languageChanged', (language) => {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = language;
  }
  try {
    localStorage.setItem(STORAGE_KEY, language);
  } catch (_err) {
    // Ignore storage access failures.
  }
});

export const I18N_SUPPORTED_LANGUAGES = supportedLanguages;
export default i18n;

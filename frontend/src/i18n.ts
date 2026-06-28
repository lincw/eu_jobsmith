import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import enTranslation from './locales/en/translation.json';
import zhTranslation from './locales/zh/translation.json';

const resources = {
  en: { translation: enTranslation },
  zh: { translation: zhTranslation }
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: localStorage.getItem('i18nextLng') || 'zh', // default to Traditional Chinese
    fallbackLng: 'en',
    keySeparator: false, // use flat keys containing dots
    interpolation: {
      escapeValue: false // react already safes from xss
    }
  });

export default i18n;

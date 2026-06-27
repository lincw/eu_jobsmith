import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import i18n from './i18n'
import App from './App.tsx'
import { ErrorBoundary } from './ui/ErrorBoundary'
import { I18nextProvider } from 'react-i18next'


const originalFetch = window.fetch;
window.fetch = async (...args) => {
  let [resource, config] = args;
  config = config || {};
  config.headers = config.headers || {};
  
  // get current language from i18n
  const lang = i18n.language.startsWith('zh') ? 'zh' : 'en';
  
  if (config.headers instanceof Headers) {
    config.headers.set('X-Lang', lang);
  } else {
    (config.headers as Record<string, string>)['X-Lang'] = lang;
  }
  
  return originalFetch(resource, config);
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <I18nextProvider i18n={i18n}>
        <App />
      </I18nextProvider>
    </ErrorBoundary>
  </StrictMode>,
)

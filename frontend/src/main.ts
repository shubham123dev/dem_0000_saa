import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { createAppConfig } from './app/app.config';
import { loadAppRuntimeConfig } from './app/core/config/app-config.loader';

async function start(): Promise<void> {
  const runtimeConfig = await loadAppRuntimeConfig('/config/app-config.json');
  await bootstrapApplication(AppComponent, createAppConfig(runtimeConfig));
}

void start().catch((error: unknown) => {
  console.error('Angular bootstrap failed', error);
  const root = document.querySelector('app-root');
  if (root) {
    const message = document.createElement('main');
    message.setAttribute('role', 'alert');
    message.style.cssText = 'padding:24px;font-family:system-ui';
    message.textContent = 'The application could not start because its runtime configuration is invalid.';
    root.replaceChildren(message);
  }
});

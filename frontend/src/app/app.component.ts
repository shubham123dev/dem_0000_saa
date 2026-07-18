import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { APP_RUNTIME_CONFIG } from './core/config/app-config.token';
import { CurrentUserStore } from './core/auth/current-user.store';

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  private readonly runtimeConfig = inject(APP_RUNTIME_CONFIG);
  readonly currentUser = inject(CurrentUserStore);
  readonly apiBaseUrl = this.runtimeConfig.apiBaseUrl;
  readonly organizationId = this.runtimeConfig.defaultOrganizationId;
}

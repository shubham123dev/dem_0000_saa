import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { CurrentUserStore } from './core/auth/current-user.store';
import { APP_RUNTIME_CONFIG } from './core/config/app-config.token';
import { UiThemeService } from './shared/theme/ui-theme.service';
import { UiThemeToggleComponent } from './shared/theme/ui-theme-toggle.component';
import {
  UiBadgeComponent,
  UiButtonComponent,
  UiCalloutComponent,
  UiIconButtonComponent,
  UiInputComponent,
  UiSkeletonComponent,
  UiStatusIndicatorComponent,
  UiSurfaceComponent,
  UiTextareaComponent
} from './shared/ui';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    UiBadgeComponent,
    UiButtonComponent,
    UiCalloutComponent,
    UiIconButtonComponent,
    UiInputComponent,
    UiSkeletonComponent,
    UiStatusIndicatorComponent,
    UiSurfaceComponent,
    UiTextareaComponent,
    UiThemeToggleComponent
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  private readonly runtimeConfig = inject(APP_RUNTIME_CONFIG);
  readonly currentUser = inject(CurrentUserStore);
  readonly theme = inject(UiThemeService);
  readonly organizationId = this.runtimeConfig.defaultOrganizationId;
  searchValue = '';
  messageValue = '';
}

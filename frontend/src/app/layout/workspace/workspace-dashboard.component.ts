import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { UiActionSurfaceComponent, UiBadgeComponent, UiButtonComponent, UiCalloutComponent, UiInputComponent } from '../../shared/ui';
import { navigationItem, SHELL_NAVIGATION, type ShellNavigationItem, type ShellSectionId } from '../shell/shell-navigation.model';

@Component({
  selector: 'app-workspace-dashboard',
  standalone: true,
  imports: [UiActionSurfaceComponent, UiBadgeComponent, UiButtonComponent, UiCalloutComponent, UiInputComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './workspace-dashboard.component.html',
  styleUrl: './workspace-dashboard.component.scss'
})
export class WorkspaceDashboardComponent {
  @Input({ required: true }) section: ShellSectionId = 'home';
  @Output() readonly navigate = new EventEmitter<ShellSectionId>();
  @Output() readonly askAi = new EventEmitter<void>();
  searchValue = '';

  get current(): ShellNavigationItem { return navigationItem(this.section); }
  get visibleResources(): readonly ShellNavigationItem[] {
    const term = this.searchValue.trim().toLowerCase();
    return SHELL_NAVIGATION.filter((item) => item.id !== 'home' && (!term || [item.label,item.description,...item.keywords].some((value) => value.toLowerCase().includes(term))));
  }
  get relatedResources(): readonly ShellNavigationItem[] {
    return SHELL_NAVIGATION.filter((item) => item.id !== 'home' && item.id !== this.section).slice(0, 4);
  }
}

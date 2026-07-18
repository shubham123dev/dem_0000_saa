import { ChangeDetectionStrategy, Component, EventEmitter, HostListener, Input, Output, signal } from '@angular/core';
import { UiThemeToggleComponent } from '../../shared/theme/ui-theme-toggle.component';

@Component({
  selector: 'app-global-header',
  standalone: true,
  imports: [UiThemeToggleComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './global-header.component.html',
  styleUrl: './global-header.component.scss'
})
export class GlobalHeaderComponent {
  @Input({ required: true }) sectionTitle = '';
  @Input() compact = false;
  @Input() assistantOpen = true;
  @Output() readonly navigationPressed = new EventEmitter<void>();
  @Output() readonly assistantPressed = new EventEmitter<void>();
  readonly supportOpen = signal(false);
  readonly accountOpen = signal(false);

  toggleSupport(): void { this.supportOpen.update((open) => !open); this.accountOpen.set(false); }
  toggleAccount(): void { this.accountOpen.update((open) => !open); this.supportOpen.set(false); }
  @HostListener('document:keydown.escape')
  closeMenus(): void { this.supportOpen.set(false); this.accountOpen.set(false); }
}

import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

export type UiStatusTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

@Component({
  selector: 'app-ui-status-indicator',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<span class="status status--{{ tone }}" role="status"><span class="status__dot" aria-hidden="true"></span>{{ label }}</span>',
  styleUrl: './ui-status-indicator.component.scss'
})
export class UiStatusIndicatorComponent {
  @Input() tone: UiStatusTone = 'neutral';
  @Input({ required: true }) label = '';
}

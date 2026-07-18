import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

export type UiBadgeTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

@Component({
  selector: 'app-ui-badge',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<span class="badge badge--{{ tone }}"><ng-content /></span>',
  styleUrl: './ui-badge.component.scss'
})
export class UiBadgeComponent {
  @Input() tone: UiBadgeTone = 'neutral';
}

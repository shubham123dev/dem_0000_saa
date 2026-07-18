import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

export type UiCalloutTone = 'info' | 'success' | 'warning' | 'danger';

@Component({
  selector: 'app-ui-callout',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './ui-callout.component.html',
  styleUrl: './ui-callout.component.scss'
})
export class UiCalloutComponent {
  @Input() tone: UiCalloutTone = 'info';
  @Input({ required: true }) title = '';
}

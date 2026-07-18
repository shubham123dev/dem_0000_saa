import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

export type UiSurfaceVariant = 'base' | 'subtle' | 'muted' | 'raised' | 'interactive';

@Component({
  selector: 'app-ui-surface',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<div class="surface surface--{{ variant }}" [class.surface--padded]="padded"><ng-content /></div>',
  styleUrl: './ui-surface.component.scss'
})
export class UiSurfaceComponent {
  @Input() variant: UiSurfaceVariant = 'base';
  @Input() padded = true;
}

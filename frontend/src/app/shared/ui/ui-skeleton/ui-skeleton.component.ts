import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

@Component({
  selector: 'app-ui-skeleton',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<span class="skeleton" aria-hidden="true" [style.width]="width" [style.height]="height" [style.border-radius]="radius"></span>',
  styleUrl: './ui-skeleton.component.scss'
})
export class UiSkeletonComponent {
  @Input() width = '100%';
  @Input() height = '1rem';
  @Input() radius = 'var(--ui-radius-sm)';
}

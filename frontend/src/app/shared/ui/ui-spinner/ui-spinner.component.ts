import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

@Component({
  selector: 'app-ui-spinner',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<span class="spinner" role="status" [attr.aria-label]="label"><span class="sr-only">{{ label }}</span></span>',
  styleUrl: './ui-spinner.component.scss'
})
export class UiSpinnerComponent {
  @Input() label = 'Loading';
}

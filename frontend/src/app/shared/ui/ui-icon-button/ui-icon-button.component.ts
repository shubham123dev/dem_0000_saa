import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-ui-icon-button',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './ui-icon-button.component.html',
  styleUrl: './ui-icon-button.component.scss'
})
export class UiIconButtonComponent {
  @Input({ required: true }) label = '';
  @Input() disabled = false;
  @Input() pressed: boolean | null = null;
  @Input() tone: 'neutral' | 'danger' = 'neutral';
  @Output() readonly activated = new EventEmitter<MouseEvent>();
}

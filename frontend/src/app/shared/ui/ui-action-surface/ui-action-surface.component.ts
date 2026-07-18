import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-ui-action-surface',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './ui-action-surface.component.html',
  styleUrl: './ui-action-surface.component.scss'
})
export class UiActionSurfaceComponent {
  @Input({ required: true }) heading = '';
  @Input() description = '';
  @Input() meta = '';
  @Input() icon = '◇';
  @Input() selected = false;
  @Input() disabled = false;
  @Output() readonly activated = new EventEmitter<void>();
}

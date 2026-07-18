import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';

let nextInputId = 0;

@Component({
  selector: 'app-ui-input',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './ui-input.component.html',
  styleUrl: './ui-input.component.scss'
})
export class UiInputComponent {
  @Input({ required: true }) label = '';
  @Input() inputId = `ui-input-${++nextInputId}`;
  @Input() value = '';
  @Input() type: 'text' | 'email' | 'search' | 'url' | 'tel' = 'text';
  @Input() placeholder = '';
  @Input() description = '';
  @Input() error = '';
  @Input() disabled = false;
  @Input() required = false;
  @Input() autocomplete = 'off';
  @Output() readonly valueChange = new EventEmitter<string>();

  update(event: Event): void {
    this.valueChange.emit((event.target as HTMLInputElement).value);
  }
}

import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';

let nextTextareaId = 0;

@Component({
  selector: 'app-ui-textarea',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './ui-textarea.component.html',
  styleUrl: './ui-textarea.component.scss'
})
export class UiTextareaComponent {
  @Input({ required: true }) label = '';
  @Input() textareaId = `ui-textarea-${++nextTextareaId}`;
  @Input() value = '';
  @Input() placeholder = '';
  @Input() description = '';
  @Input() error = '';
  @Input() disabled = false;
  @Input() required = false;
  @Input() rows = 4;
  @Input() maxLength: number | null = null;
  @Output() readonly valueChange = new EventEmitter<string>();

  update(event: Event): void {
    this.valueChange.emit((event.target as HTMLTextAreaElement).value);
  }
}

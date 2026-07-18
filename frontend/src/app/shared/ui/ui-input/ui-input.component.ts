import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, forwardRef, inject, Input, Output } from '@angular/core';
import { type ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

let nextInputId = 0;

@Component({
  selector: 'app-ui-input',
  standalone: true,
  providers: [{ provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => UiInputComponent), multi: true }],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './ui-input.component.html',
  styleUrl: './ui-input.component.scss'
})
export class UiInputComponent implements ControlValueAccessor {
  private modelValue = '';
  private formDisabled = false;
  private onChange: (value: string) => void = () => undefined;
  private onTouched: () => void = () => undefined;
  private readonly changeDetector = inject(ChangeDetectorRef);

  @Input({ required: true }) label = '';
  @Input() inputId = `ui-input-${++nextInputId}`;
  @Input() type: 'text' | 'email' | 'search' | 'url' | 'tel' = 'text';
  @Input() placeholder = '';
  @Input() description = '';
  @Input() error = '';
  @Input() disabled = false;
  @Input() required = false;
  @Input() autocomplete = 'off';
  @Output() readonly valueChange = new EventEmitter<string>();

  @Input()
  set value(value: string | null | undefined) {
    this.modelValue = value ?? '';
  }
  get value(): string { return this.modelValue; }
  get isDisabled(): boolean { return this.disabled || this.formDisabled; }

  update(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.modelValue = value;
    this.valueChange.emit(value);
    this.onChange(value);
  }

  markTouched(): void { this.onTouched(); }
  writeValue(value: string | null): void { this.modelValue = value ?? ''; this.changeDetector.markForCheck(); }
  registerOnChange(fn: (value: string) => void): void { this.onChange = fn; }
  registerOnTouched(fn: () => void): void { this.onTouched = fn; }
  setDisabledState(disabled: boolean): void { this.formDisabled = disabled; this.changeDetector.markForCheck(); }
}

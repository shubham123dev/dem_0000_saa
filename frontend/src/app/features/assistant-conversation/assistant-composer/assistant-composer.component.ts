import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output, ViewChild, signal, type ElementRef } from '@angular/core';
import { UiButtonComponent } from '../../../shared/ui';

@Component({
  selector: 'app-assistant-composer',
  standalone: true,
  imports: [UiButtonComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './assistant-composer.component.html',
  styleUrl: './assistant-composer.component.scss'
})
export class AssistantComposerComponent {
  @ViewChild('editor') private editor?: ElementRef<HTMLTextAreaElement>;
  @Input() disabled = false;
  @Input() pending = false;
  @Input() maxLength = 4000;
  @Input() clarificationActive = false;
  @Input() cancelAvailable = false;
  @Output() readonly submitted = new EventEmitter<string>();
  @Output() readonly stopRequested = new EventEmitter<void>();
  @Output() readonly cancelRequested = new EventEmitter<void>();
  @Output() readonly clarificationCancelled = new EventEmitter<void>();
  readonly draft = signal('');

  get remaining(): number { return this.maxLength - this.draft().length; }
  get canSend(): boolean { return !this.disabled && !this.pending && this.draft().trim().length > 0 && this.remaining >= 0; }
  update(event: Event): void { this.draft.set((event.target as HTMLTextAreaElement).value); }
  keydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); this.submit(); }
  }
  submit(): void { if (this.canSend) { this.submitted.emit(this.draft().trim()); this.draft.set(''); } }
  focus(): void { this.editor?.nativeElement.focus(); }
}

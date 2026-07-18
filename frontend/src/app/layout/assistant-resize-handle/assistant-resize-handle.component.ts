import { DOCUMENT } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, HostListener, inject, Input, Output } from '@angular/core';

@Component({
  selector: 'app-assistant-resize-handle',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '',
  styleUrl: './assistant-resize-handle.component.scss',
  host: {
    role: 'separator',
    tabindex: '0',
    'aria-label': 'Resize Ask AI panel',
    'aria-orientation': 'vertical',
    '[attr.aria-valuemin]': '352',
    '[attr.aria-valuemax]': '608',
    '[attr.aria-valuenow]': 'width'
  }
})
export class AssistantResizeHandleComponent {
  private readonly document = inject(DOCUMENT);
  private cleanup: (() => void) | null = null;
  @Input({ required: true }) width = 448;
  @Output() readonly widthChange = new EventEmitter<number>();

  @HostListener('pointerdown', ['$event'])
  start(event: PointerEvent): void {
    event.preventDefault();
    this.stop();
    const startX = event.clientX;
    const startWidth = this.width;
    const view = this.document.defaultView;
    if (!view) return;
    const move = (moveEvent: PointerEvent): void => this.widthChange.emit(startWidth + startX - moveEvent.clientX);
    const up = (): void => this.stop();
    view.addEventListener('pointermove', move);
    view.addEventListener('pointerup', up, { once: true });
    this.cleanup = () => { view.removeEventListener('pointermove', move); view.removeEventListener('pointerup', up); this.cleanup = null; };
  }

  @HostListener('keydown', ['$event'])
  keyboard(event: KeyboardEvent): void {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    event.preventDefault();
    this.widthChange.emit(this.width + (event.key === 'ArrowLeft' ? 16 : -16));
  }
  private stop(): void { this.cleanup?.(); }
}

import { DOCUMENT } from '@angular/common';
import { computed, DestroyRef, effect, inject, Injectable, signal } from '@angular/core';
import type { ShellSectionId } from './shell-navigation.model';

const ASSISTANT_WIDTH_KEY = 'dbmr-workplace-assistant-width';
const ASSISTANT_OPEN_KEY = 'dbmr-workplace-assistant-open';
const MIN_ASSISTANT_WIDTH = 352;
const MAX_ASSISTANT_WIDTH = 608;
const DEFAULT_ASSISTANT_WIDTH = 448;

@Injectable({ providedIn: 'root' })
export class ShellStateService {
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);
  private readonly compactQuery = this.document.defaultView?.matchMedia?.('(max-width: 47.99rem)') ?? null;
  private readonly narrowQuery = this.document.defaultView?.matchMedia?.('(max-width: 73.99rem)') ?? null;
  private readonly activeSectionState = signal<ShellSectionId>('home');
  private readonly sidebarOpenState = signal(false);
  private readonly assistantOpenState = signal(this.readBoolean(ASSISTANT_OPEN_KEY, !(this.compactQuery?.matches ?? false)));
  private readonly assistantWidthState = signal(this.readWidth());
  private readonly compactState = signal(this.compactQuery?.matches ?? false);
  private readonly narrowState = signal(this.narrowQuery?.matches ?? false);

  readonly activeSection = this.activeSectionState.asReadonly();
  readonly sidebarOpen = this.sidebarOpenState.asReadonly();
  readonly assistantOpen = this.assistantOpenState.asReadonly();
  readonly assistantWidth = this.assistantWidthState.asReadonly();
  readonly isCompact = this.compactState.asReadonly();
  readonly isNarrow = this.narrowState.asReadonly();
  readonly assistantOverlay = computed(() => this.isNarrow());

  constructor() {
    const onCompact = (event: MediaQueryListEvent): void => {
      this.compactState.set(event.matches);
      if (!event.matches) this.sidebarOpenState.set(false);
    };
    const onNarrow = (event: MediaQueryListEvent): void => this.narrowState.set(event.matches);
    this.compactQuery?.addEventListener('change', onCompact);
    this.narrowQuery?.addEventListener('change', onNarrow);
    this.destroyRef.onDestroy(() => {
      this.compactQuery?.removeEventListener('change', onCompact);
      this.narrowQuery?.removeEventListener('change', onNarrow);
    });
    effect(() => this.writeStorage(ASSISTANT_WIDTH_KEY, String(this.assistantWidth())));
    effect(() => this.writeStorage(ASSISTANT_OPEN_KEY, String(this.assistantOpen())));
  }

  selectSection(section: ShellSectionId): void {
    this.activeSectionState.set(section);
    if (this.isCompact()) this.sidebarOpenState.set(false);
  }
  openSidebar(): void { this.sidebarOpenState.set(true); }
  closeSidebar(): void { this.sidebarOpenState.set(false); }
  toggleSidebar(): void { this.sidebarOpenState.update((open) => !open); }
  openAssistant(): void { this.assistantOpenState.set(true); }
  closeAssistant(): void { this.assistantOpenState.set(false); }
  toggleAssistant(): void { this.assistantOpenState.update((open) => !open); }
  setAssistantWidth(width: number): void {
    this.assistantWidthState.set(Math.min(MAX_ASSISTANT_WIDTH, Math.max(MIN_ASSISTANT_WIDTH, Math.round(width))));
  }
  closeOverlays(): void {
    if (this.isCompact()) this.closeSidebar();
    if (this.assistantOverlay()) this.closeAssistant();
  }

  /**
   * Sync active section from Angular Router route data.
   * Unlike selectSection(), this does NOT close the sidebar —
   * the section change comes from URL navigation, not a sidebar click.
   */
  syncFromRoute(section: ShellSectionId): void {
    this.activeSectionState.set(section);
  }

  private readWidth(): number {
    const parsed = Number(this.readStorage(ASSISTANT_WIDTH_KEY));
    return Number.isFinite(parsed) ? Math.min(MAX_ASSISTANT_WIDTH, Math.max(MIN_ASSISTANT_WIDTH, parsed)) : DEFAULT_ASSISTANT_WIDTH;
  }
  private readBoolean(key: string, fallback: boolean): boolean {
    const value = this.readStorage(key);
    return value === 'true' ? true : value === 'false' ? false : fallback;
  }
  private readStorage(key: string): string | null {
    try { return this.document.defaultView?.localStorage.getItem(key) ?? null; } catch { return null; }
  }
  private writeStorage(key: string, value: string): void {
    try { this.document.defaultView?.localStorage.setItem(key, value); } catch { /* unavailable storage is non-fatal */ }
  }
}

import { A11yModule } from '@angular/cdk/a11y';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { UiBadgeComponent, UiButtonComponent, UiCalloutComponent } from '../../shared/ui';
import type { ShellSectionId } from '../shell/shell-navigation.model';

interface AssistantSuggestion { readonly label: string; readonly detail: string; readonly section: ShellSectionId; readonly icon: string; }

@Component({
  selector: 'app-assistant-panel',
  standalone: true,
  imports: [A11yModule, UiBadgeComponent, UiButtonComponent, UiCalloutComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './assistant-panel.component.html',
  styleUrl: './assistant-panel.component.scss'
})
export class AssistantPanelComponent {
  @Input() overlay = false;
  @Output() readonly closePressed = new EventEmitter<void>();
  @Output() readonly sectionSelected = new EventEmitter<ShellSectionId>();
  readonly announcement = signal('');
  readonly suggestions: readonly AssistantSuggestion[] = [
    { label: 'Review pending approvals', detail: 'Open proposals awaiting a decision', section: 'approvals', icon: '✓' },
    { label: 'Explore users and roles', detail: 'Open organization memberships', section: 'users', icon: '○' },
    { label: 'Inspect report access', detail: 'Open report entitlements', section: 'reports', icon: '▤' }
  ];
  readonly greeting = this.createGreeting();

  choose(suggestion: AssistantSuggestion): void {
    this.sectionSelected.emit(suggestion.section);
    this.announcement.set(`${suggestion.label} opened in the workspace.`);
  }
  resetPreview(): void { this.announcement.set('Preview reset. Conversation tools arrive in Phase 4.'); }
  private createGreeting(): string {
    const hour = new Date().getHours();
    return hour < 12 ? 'Good morning.' : hour < 18 ? 'Good afternoon.' : 'Good evening.';
  }
}

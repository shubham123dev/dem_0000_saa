import { ChangeDetectionStrategy, Component, type ElementRef, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import { SHELL_NAVIGATION, type ShellNavigationItem, type ShellSectionId } from '../shell/shell-navigation.model';

@Component({
  selector: 'app-primary-sidebar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './primary-sidebar.component.html',
  styleUrl: './primary-sidebar.component.scss'
})
export class PrimarySidebarComponent {
  @Input({ required: true }) activeSection: ShellSectionId = 'home';
  @Input() compact = false;
  @Input() open = false;
  @Output() readonly sectionSelected = new EventEmitter<ShellSectionId>();
  @Output() readonly closePressed = new EventEmitter<void>();
  @ViewChild('searchInput') private searchInput?: ElementRef<HTMLInputElement>;
  query = '';

  get groups(): readonly ('Workspace' | 'Governance')[] { return ['Workspace', 'Governance']; }
  items(group: 'Workspace' | 'Governance'): readonly ShellNavigationItem[] {
    const term = this.query.trim().toLowerCase();
    return SHELL_NAVIGATION.filter((item) => item.group === group && (!term || [item.label,item.description,...item.keywords].some((value) => value.toLowerCase().includes(term))));
  }
  updateQuery(event: Event): void { this.query = (event.target as HTMLInputElement).value; }
  focusSearch(): void { this.searchInput?.nativeElement.focus(); }
}

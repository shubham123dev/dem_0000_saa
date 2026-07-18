import { ChangeDetectionStrategy, Component, HostListener, ViewChild, inject } from '@angular/core';
import { AssistantPanelComponent } from '../assistant-panel/assistant-panel.component';
import { AssistantResizeHandleComponent } from '../assistant-resize-handle/assistant-resize-handle.component';
import { GlobalHeaderComponent } from '../global-header/global-header.component';
import { PrimarySidebarComponent } from '../primary-sidebar/primary-sidebar.component';
import { navigationItem, type ShellSectionId } from '../shell/shell-navigation.model';
import { ShellStateService } from '../shell/shell-state.service';
import { WorkspaceDashboardComponent } from '../workspace/workspace-dashboard.component';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [AssistantPanelComponent, AssistantResizeHandleComponent, GlobalHeaderComponent, PrimarySidebarComponent, WorkspaceDashboardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './app-shell.component.html',
  styleUrl: './app-shell.component.scss'
})
export class AppShellComponent {
  @ViewChild(PrimarySidebarComponent) private sidebar?: PrimarySidebarComponent;
  readonly state = inject(ShellStateService);
  get sectionTitle(): string { return navigationItem(this.state.activeSection()).label; }

  navigate(section: ShellSectionId): void {
    this.state.selectSection(section);
    if (this.state.assistantOverlay()) this.state.closeAssistant();
  }
  askAboutCurrentSection(): void { this.state.openAssistant(); }

  @HostListener('document:keydown', ['$event'])
  shortcuts(event: KeyboardEvent): void {
    if (event.key === 'Escape') { this.state.closeOverlays(); return; }
    if ((event.ctrlKey || event.metaKey) && !event.shiftKey && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      if (this.state.isCompact()) this.state.openSidebar();
      queueMicrotask(() => this.sidebar?.focusSearch());
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'a') {
      event.preventDefault();
      this.state.toggleAssistant();
    }
  }
}

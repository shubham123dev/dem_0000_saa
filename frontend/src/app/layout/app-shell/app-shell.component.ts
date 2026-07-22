import { ChangeDetectionStrategy, Component, HostListener, OnInit, ViewChild, inject } from '@angular/core';
import { AssistantPanelComponent } from '../assistant-panel/assistant-panel.component';
import { AssistantResizeHandleComponent } from '../assistant-resize-handle/assistant-resize-handle.component';
import { GlobalHeaderComponent } from '../global-header/global-header.component';
import { PrimarySidebarComponent } from '../primary-sidebar/primary-sidebar.component';
import { navigationItem, type ShellSectionId } from '../shell/shell-navigation.model';
import { ShellStateService } from '../shell/shell-state.service';
import { WorkspaceDashboardComponent } from '../workspace/workspace-dashboard.component';

import { ApprovalCenterComponent } from '../../features/approval-center/approval-center.component';
import { AuthService } from '../../core/auth/auth.service';
import { CurrentUserStore } from '../../core/auth/current-user.store';
import { AuthLoginModalComponent } from '../../core/auth/auth-login-modal.component';
import { signal } from '@angular/core';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    ApprovalCenterComponent, AssistantPanelComponent, AssistantResizeHandleComponent, GlobalHeaderComponent, PrimarySidebarComponent, WorkspaceDashboardComponent, AuthLoginModalComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './app-shell.component.html',
  styleUrl: './app-shell.component.scss'
})
export class AppShellComponent implements OnInit {
  @ViewChild(PrimarySidebarComponent) private sidebar?: PrimarySidebarComponent;
  readonly state = inject(ShellStateService);
  private readonly auth = inject(AuthService);
  private readonly userStore = inject(CurrentUserStore);
  readonly loginModalOpen = signal(false);

  openLoginModal(): void { this.loginModalOpen.set(true); }
  closeLoginModal(): void { this.loginModalOpen.set(false); }

  ngOnInit(): void {
    // Check if an active session cookie exists for returning user
    this.auth.getMe().subscribe();
  }
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

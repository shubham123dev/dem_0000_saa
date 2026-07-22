/**
 * OrganizationWorkspaceComponent — routed shell for `/organizations/:orgId`.
 *
 * This component is the routed container that:
 * 1. Reads `:orgId` from the route
 * 2. Hosts the sidebar, header, assistant panel, and a <router-outlet>
 *    for child section views (users, reports, approvals, etc.)
 * 3. Syncs ShellStateService.activeSection from route data
 *
 * It replaces the old conditional rendering in app-shell for section content.
 */
import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  OnInit,
  ViewChild,
  inject,
  signal,
} from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DestroyRef } from '@angular/core';
import { filter, map } from 'rxjs';
import { AssistantPanelComponent } from '../assistant-panel/assistant-panel.component';
import { AssistantResizeHandleComponent } from '../assistant-resize-handle/assistant-resize-handle.component';
import { GlobalHeaderComponent } from '../global-header/global-header.component';
import { PrimarySidebarComponent } from '../primary-sidebar/primary-sidebar.component';
import { navigationItem, type ShellSectionId } from '../shell/shell-navigation.model';
import { ShellStateService } from '../shell/shell-state.service';
import { AuthLoginModalComponent } from '../../core/auth/auth-login-modal.component';
import { OrganizationRouteService } from '../../core/routing/organization-route.service';

@Component({
  selector: 'app-organization-workspace',
  standalone: true,
  imports: [
    AssistantPanelComponent,
    AssistantResizeHandleComponent,
    GlobalHeaderComponent,
    PrimarySidebarComponent,
    RouterOutlet,
    AuthLoginModalComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <a class="skip-link" href="#main-content">Skip to content</a>
    <div
      class="app-shell"
      [class.app-shell--assistant-open]="state.assistantOpen()"
      [class.app-shell--assistant-overlay]="state.assistantOverlay()"
      [style.--shell-assistant-current.px]="state.assistantOpen() && !state.assistantOverlay() ? state.assistantWidth() : 0"
    >
      <div class="brand-strip" aria-hidden="true"></div>
      <app-global-header
        class="shell-header"
        [sectionTitle]="sectionTitle"
        [compact]="state.isCompact()"
        [assistantOpen]="state.assistantOpen()"
        (navigationPressed)="state.openSidebar()"
        (assistantPressed)="state.toggleAssistant()"
        (loginRequested)="openLoginModal()"
      />

      @if (state.isCompact() && state.sidebarOpen()) {
        <button type="button" class="shell-backdrop shell-backdrop--sidebar" aria-label="Close navigation" (click)="state.closeSidebar()"></button>
      }
      <app-primary-sidebar
        class="shell-sidebar"
        [activeSection]="state.activeSection()"
        [compact]="state.isCompact()"
        [open]="state.sidebarOpen()"
        (sectionSelected)="navigate($event)"
        (closePressed)="state.closeSidebar()"
      />

      <main id="main-content" class="shell-workspace" tabindex="-1">
        <router-outlet />
      </main>

      @if (state.assistantOpen()) {
        @if (state.assistantOverlay()) {
          <button type="button" class="shell-backdrop shell-backdrop--assistant" aria-label="Close Ask SARA" (click)="state.closeAssistant()"></button>
        }
        <section class="shell-assistant" aria-label="Ask SARA panel">
          @if (!state.assistantOverlay()) {
            <app-assistant-resize-handle [width]="state.assistantWidth()" (widthChange)="state.setAssistantWidth($event)" />
          }
          <app-assistant-panel
            [overlay]="state.assistantOverlay()"
            [currentSection]="state.activeSection()"
            (closePressed)="state.closeAssistant()"
            (sectionSelected)="navigate($event)"
            (loginRequested)="openLoginModal()"
          />
        </section>
      }

      @if (loginModalOpen()) {
        <app-auth-login-modal (loggedIn)="closeLoginModal()" (closed)="closeLoginModal()" />
      }
    </div>
  `,
  styleUrl: '../app-shell/app-shell.component.scss',
})
export class OrganizationWorkspaceComponent implements OnInit {
  @ViewChild(PrimarySidebarComponent) private sidebar?: PrimarySidebarComponent;

  readonly state = inject(ShellStateService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly orgRoute = inject(OrganizationRouteService);
  readonly loginModalOpen = signal(false);

  openLoginModal(): void { this.loginModalOpen.set(true); }
  closeLoginModal(): void { this.loginModalOpen.set(false); }

  get sectionTitle(): string {
    return navigationItem(this.state.activeSection()).label;
  }

  ngOnInit(): void {
    // Sync active section from the child route's data on every navigation
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe(() => this.syncSectionFromRoute());

    // Initial sync
    this.syncSectionFromRoute();
  }

  navigate(section: ShellSectionId): void {
    const orgId = this.orgRoute.organizationId();
    if (!orgId) return;

    const path = section === 'home' ? [] : [section];
    this.router.navigate(['/organizations', orgId, ...path]);

    if (this.state.assistantOverlay()) {
      this.state.closeAssistant();
    }
  }

  askAboutCurrentSection(): void {
    this.state.openAssistant();
  }

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

  private syncSectionFromRoute(): void {
    let child = this.route;
    while (child.firstChild) {
      child = child.firstChild;
    }
    const section = child.snapshot.data['section'] as ShellSectionId | undefined;
    if (section) {
      this.state.syncFromRoute(section);
    }
  }
}

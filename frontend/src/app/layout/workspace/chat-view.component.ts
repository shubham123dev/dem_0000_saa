/**
 * ChatRedirectComponent — routed at `/organizations/:orgId/chat`.
 *
 * This component opens the SARA assistant panel automatically and
 * renders the home dashboard behind it. Provides a dedicated deep-link
 * URL for the chat workspace module.
 */
import { ChangeDetectionStrategy, Component, OnInit, inject } from '@angular/core';
import { WorkspaceDashboardComponent } from './workspace-dashboard.component';
import { ShellStateService } from '../shell/shell-state.service';
import { OrganizationRouteService } from '../../core/routing/organization-route.service';
import { Router } from '@angular/router';
import type { ShellSectionId } from '../shell/shell-navigation.model';

@Component({
  selector: 'app-chat-view',
  standalone: true,
  imports: [WorkspaceDashboardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-workspace-dashboard
      [section]="'home'"
      (navigate)="onNavigate($event)"
      (askAi)="state.openAssistant()"
    />
  `,
})
export class ChatViewComponent implements OnInit {
  readonly state = inject(ShellStateService);
  private readonly router = inject(Router);
  private readonly orgRoute = inject(OrganizationRouteService);

  ngOnInit(): void {
    // Automatically open the assistant panel when /chat is visited
    this.state.openAssistant();
  }

  onNavigate(section: ShellSectionId): void {
    const orgId = this.orgRoute.organizationId();
    if (!orgId) return;
    const path = section === 'home' ? [] : [section];
    this.router.navigate(['/organizations', orgId, ...path]);
  }
}

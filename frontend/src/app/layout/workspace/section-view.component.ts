/**
 * SectionViewComponent — routed wrapper for non-approval workspace sections.
 *
 * Each child route under `/organizations/:orgId/{section}` renders this
 * component, which delegates to the existing WorkspaceDashboardComponent.
 * The `section` route data drives which section content is shown.
 */
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { WorkspaceDashboardComponent } from './workspace-dashboard.component';
import type { ShellSectionId } from '../shell/shell-navigation.model';
import { ShellStateService } from '../shell/shell-state.service';
import { OrganizationRouteService } from '../../core/routing/organization-route.service';

@Component({
  selector: 'app-section-view',
  standalone: true,
  imports: [WorkspaceDashboardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-workspace-dashboard
      [section]="section"
      (navigate)="onNavigate($event)"
      (askAi)="onAskAi()"
    />
  `,
})
export class SectionViewComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly state = inject(ShellStateService);
  private readonly orgRoute = inject(OrganizationRouteService);

  get section(): ShellSectionId {
    return (this.route.snapshot.data['section'] as ShellSectionId) ?? 'home';
  }

  onNavigate(section: ShellSectionId): void {
    const orgId = this.orgRoute.organizationId();
    if (!orgId) return;
    const path = section === 'home' ? [] : [section];
    this.router.navigate(['/organizations', orgId, ...path]);
  }

  onAskAi(): void {
    this.state.openAssistant();
  }
}

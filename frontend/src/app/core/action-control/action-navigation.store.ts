import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ActionNavigationStore {
  private readonly selectedState = signal<string | null>(null);
  readonly selectedProposalId = this.selectedState.asReadonly();
  open(proposalId: string | null): void { this.selectedState.set(proposalId); }
  clear(): void { this.selectedState.set(null); }
}

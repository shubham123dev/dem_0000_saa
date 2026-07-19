import type { z } from 'zod';
import type {
  actionCapabilityCatalogueSchema,
  actionExecutionEventSchema,
  actionProposalControlListSchema,
  actionProposalControlSchema
} from './action-control.schemas';

export type ActionProposalControl = z.infer<typeof actionProposalControlSchema>;
export type ActionProposalControlList = z.infer<typeof actionProposalControlListSchema>;
export type ActionCapabilityCatalogue = z.infer<typeof actionCapabilityCatalogueSchema>;
export type ActionExecutionEvent = z.infer<typeof actionExecutionEventSchema>;
export type ActionConnectionState = 'connecting' | 'open' | 'reconnecting' | 'closed';
export type ActionExecutionStreamUpdate =
  | { readonly kind: 'state'; readonly state: ActionConnectionState }
  | { readonly kind: 'event'; readonly event: ActionExecutionEvent };

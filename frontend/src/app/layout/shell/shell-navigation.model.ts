export type ShellSectionId =
  | 'home'
  | 'organizations'
  | 'users'
  | 'seats'
  | 'reports'
  | 'access-packages'
  | 'settings'
  | 'approvals'
  | 'audit';

export interface ShellNavigationItem {
  id: ShellSectionId;
  label: string;
  description: string;
  icon: string;
  group: 'Workspace' | 'Governance';
  keywords: readonly string[];
}

export const SHELL_NAVIGATION: readonly ShellNavigationItem[] = [
  { id: 'home', label: 'Workspace home', description: 'Overview and common tasks', icon: '⌂', group: 'Workspace', keywords: ['home','overview'] },
  { id: 'organizations', label: 'Organizations', description: 'Profiles and workspace status', icon: '◇', group: 'Workspace', keywords: ['company','account'] },
  { id: 'users', label: 'Users', description: 'Memberships and roles', icon: '○', group: 'Workspace', keywords: ['people','members','roles'] },
  { id: 'seats', label: 'Seat management', description: 'Assignments and availability', icon: '▦', group: 'Workspace', keywords: ['licenses','assignments'] },
  { id: 'reports', label: 'Reports', description: 'Report access and entitlements', icon: '▤', group: 'Workspace', keywords: ['documents','access'] },
  { id: 'access-packages', label: 'Access packages', description: 'Reusable permission bundles', icon: '◫', group: 'Workspace', keywords: ['permissions','entitlements'] },
  { id: 'settings', label: 'Settings', description: 'Workspace configuration', icon: '⚙', group: 'Governance', keywords: ['configuration','rules'] },
  { id: 'approvals', label: 'Pending approvals', description: 'Review governed proposals', icon: '✓', group: 'Governance', keywords: ['proposals','review'] },
  { id: 'audit', label: 'Audit history', description: 'Trace decisions and outcomes', icon: '◷', group: 'Governance', keywords: ['history','events','receipts'] }
];

export function navigationItem(id: ShellSectionId): ShellNavigationItem {
  const item = SHELL_NAVIGATION.find((candidate) => candidate.id === id);
  if (!item) throw new Error(`Unknown shell section: ${id}`);
  return item;
}

import type { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./layout/app-shell/app-shell.component').then(
        (m) => m.AppShellComponent
      ),
    data: { section: 'home' },
  },
  {
    path: 'organizations/:orgId',
    loadComponent: () =>
      import('./layout/app-shell/app-shell.component').then(
        (m) => m.AppShellComponent
      ),
    data: { section: 'home' },
    children: [
      {
        path: 'users',
        loadComponent: () =>
          import('./layout/app-shell/app-shell.component').then(
            (m) => m.AppShellComponent
          ),
        data: { section: 'users' },
      },
      {
        path: 'seats',
        loadComponent: () =>
          import('./layout/app-shell/app-shell.component').then(
            (m) => m.AppShellComponent
          ),
        data: { section: 'seats' },
      },
      {
        path: 'reports',
        loadComponent: () =>
          import('./layout/app-shell/app-shell.component').then(
            (m) => m.AppShellComponent
          ),
        data: { section: 'reports' },
      },
      {
        path: 'access-packages',
        loadComponent: () =>
          import('./layout/app-shell/app-shell.component').then(
            (m) => m.AppShellComponent
          ),
        data: { section: 'access-packages' },
      },
      {
        path: 'settings',
        loadComponent: () =>
          import('./layout/app-shell/app-shell.component').then(
            (m) => m.AppShellComponent
          ),
        data: { section: 'settings' },
      },
      {
        path: 'approvals',
        loadComponent: () =>
          import('./layout/app-shell/app-shell.component').then(
            (m) => m.AppShellComponent
          ),
        data: { section: 'approvals' },
      },
      {
        path: 'audit',
        loadComponent: () =>
          import('./layout/app-shell/app-shell.component').then(
            (m) => m.AppShellComponent
          ),
        data: { section: 'audit' },
      },
      {
        path: 'chat',
        loadComponent: () =>
          import('./layout/app-shell/app-shell.component').then(
            (m) => m.AppShellComponent
          ),
        data: { section: 'home' },
      },
    ],
  },
  {
    path: '**',
    redirectTo: '',
  },
];

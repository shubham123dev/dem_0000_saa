import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { catchError, Observable, of, tap } from 'rxjs';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';
import { CurrentUserStore, UserProfile } from './current-user.store';

export interface LoginPayload {
  email?: string;
  user_id?: string;
  password?: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(APP_RUNTIME_CONFIG);
  private readonly userStore = inject(CurrentUserStore);

  login(payload: LoginPayload): Observable<UserProfile> {
    const url = `${this.config.apiBaseUrl}/auth/login`;
    return this.http.post<UserProfile>(url, payload, { withCredentials: true }).pipe(
      tap((profile) => {
        this.userStore.setUserProfile(profile);
      })
    );
  }

  logout(): Observable<{ message: string }> {
    const url = `${this.config.apiBaseUrl}/auth/logout`;
    return this.http.post<{ message: string }>(url, {}, { withCredentials: true }).pipe(
      tap(() => {
        this.userStore.clearUser();
      })
    );
  }

  getMe(): Observable<UserProfile | null> {
    const url = `${this.config.apiBaseUrl}/auth/me`;
    return this.http.get<UserProfile>(url, { withCredentials: true }).pipe(
      tap((profile) => {
        this.userStore.setUserProfile(profile);
      }),
      catchError(() => {
        this.userStore.setUserProfile(null);
        return of(null);
      })
    );
  }
}

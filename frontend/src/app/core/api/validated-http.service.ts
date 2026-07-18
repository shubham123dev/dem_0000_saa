import { HttpClient, type HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { catchError, map, throwError, timeout, TimeoutError, type Observable } from 'rxjs';
import type { ZodType } from 'zod';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';
import { WorkplaceApiError } from '../errors/workplace-api.error';

@Injectable({ providedIn: 'root' })
export class ValidatedHttpService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(APP_RUNTIME_CONFIG);

  request<T>(
    method: 'GET' | 'POST',
    path: string,
    schema: ZodType<T>,
    options: { body?: unknown; params?: HttpParams } = {}
  ): Observable<T> {
    return this.http
      .request<unknown>(method, `${this.config.apiBaseUrl}${path}`, {
        body: options.body,
        params: options.params
      })
      .pipe(
        timeout(this.config.requestTimeoutMs),
        map((payload) => {
          const parsed = schema.safeParse(payload);
          if (!parsed.success) {
            throw new WorkplaceApiError(
              502,
              'invalid_success_payload',
              'The server returned an unexpected success payload.',
              undefined,
              parsed.error
            );
          }
          return parsed.data;
        }),
        catchError((error: unknown) => {
          if (error instanceof WorkplaceApiError) {
            return throwError(() => error);
          }
          if (error instanceof TimeoutError) {
            return throwError(
              () =>
                new WorkplaceApiError(
                  408,
                  'request_timeout',
                  'The request did not complete before the configured timeout.',
                  undefined,
                  error
                )
            );
          }
          return throwError(() => error);
        })
      );
  }
}

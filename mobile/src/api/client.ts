import { USE_MOCK } from '@/config';
import { HttpApi } from './http';
import { MockApi } from './mock';
import type { Api } from './types';

// Single API instance for the app. Mock mode keeps everything in memory and works offline.
export const api: Api = USE_MOCK ? new MockApi() : new HttpApi();

export { ApiError } from './types';
export type * from './types';

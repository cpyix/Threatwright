import { untrack } from 'svelte'

// Requests in flight, for the global loading bar. Background polling passes `quiet`.
export const loading = $state({ count: 0 })

export async function track<T>(work: Promise<T>, quiet = false): Promise<T> {
  if (quiet) return work
  // untracked: `count++` reads the count, and an effect calling api() would rerun on every change
  untrack(() => loading.count++)
  try {
    return await work
  } finally {
    untrack(() => loading.count--)
  }
}

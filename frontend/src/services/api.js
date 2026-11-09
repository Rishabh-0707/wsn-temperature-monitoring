export async function get(path, signal) {
  const response = await fetch(`/api${path}`, { signal });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      detail = (await response.json()).detail || detail;
    } catch {
      /* Non-JSON server response. */
    }
    throw new Error(
      typeof detail === "string" ? detail : "Invalid API response",
    );
  }
  return response.json();
}
export const query = (run) => `run_id=${encodeURIComponent(run)}`;

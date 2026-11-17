/**
 * Consulta móvil privada mediante Cloudflare Worker + Access.
 *
 * Seguridad por defecto: sin Access autenticado o sin correo permitido
 * se DENIEGA toda petición, incluso HTML, JSON, CSS y fichas de carrera.
 *
 * IMPORTANTE: Wrangler debe usar assets.run_worker_first=true.
 * NO reutilizar este código detrás de una URL de Pages sin protección.
 */
export default {
  async fetch(request, env, ctx) {
    const allowed = String(env.CORRERADAR_PRIVATE_EMAIL || '').trim().toLowerCase();
    if (!allowed) {
      return new Response('Falta configurar el acceso privado.', {
        status: 503, headers: { 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex' }
      });
    }
    if (!ctx.access) {
      return new Response('Se requiere acceso autenticado.', {
        status: 403, headers: { 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex' }
      });
    }
    let identity = null;
    try {
      identity = await ctx.access.getIdentity();
    } catch {
      // Nunca se sirve contenido por fallo del proveedor de identidad.
    }
    const email = String(identity?.email || '').trim().toLowerCase();
    if (email !== allowed) {
      return new Response('No autorizado.', {
        status: 403, headers: { 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex' }
      });
    }
    const response = await env.ASSETS.fetch(request);
    const headers = new Headers(response.headers);
    headers.set('Cache-Control', 'private, no-store');
    headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive');
    headers.set('Referrer-Policy', 'no-referrer');
    headers.set('X-Content-Type-Options', 'nosniff');
    return new Response(response.body, {
      status: response.status, statusText: response.statusText, headers
    });
  }
};

/**
 * Cloudflare Worker privado. No usa Assets Binding: la ruta pasa por este
 * Worker ANTES de servir un solo byte de HTML, CSS, JS o JSON.
 *
 * Con Static Assets el router interno no propaga ctx.access al Worker; por
 * ello el generador empaqueta el sitio como un módulo privado.
 */
import { FILES } from './generated.mjs';

const DENIED_HEADERS = {
  'Cache-Control': 'no-store',
  'X-Robots-Tag': 'noindex, nofollow',
  'Referrer-Policy': 'no-referrer',
  'X-Content-Type-Options': 'nosniff'
};

function respond(status, message) {
  return new Response(message, { status, headers: DENIED_HEADERS });
}

export default {
  async fetch(request, env, ctx) {
    const allowed = String(env.CORRERADAR_PRIVATE_EMAIL || '').trim().toLowerCase();
    if (!allowed) return respond(503, 'Falta configurar el acceso privado.');
    if (!ctx.access) return respond(403, 'Se requiere autenticación.');

    let identity = null;
    try { identity = await ctx.access.getIdentity(); }
    catch { return respond(403, 'No se ha podido verificar la identidad.'); }
    if (String(identity?.email || '').trim().toLowerCase() !== allowed) {
      return respond(403, 'Este calendario es privado.');
    }

    if (!['GET', 'HEAD'].includes(request.method)) {
      return respond(405, 'Método no permitido.');
    }
    let pathname;
    try { pathname = decodeURIComponent(new URL(request.url).pathname); }
    catch { return respond(400, 'URL inválida.'); }
    if (!pathname.startsWith('/') || pathname.includes('\\') || pathname.includes('..')) {
      return respond(400, 'URL inválida.');
    }
    const direct = pathname.endsWith('/') ? pathname + 'index.html' : pathname;
    const file = Object.prototype.hasOwnProperty.call(FILES, direct)
      ? FILES[direct]
      : Object.prototype.hasOwnProperty.call(FILES, direct + '/index.html')
        ? FILES[direct + '/index.html'] : null;
    if (!file) return respond(404, 'No encontrado.');
    const [base64, mime] = file;
    const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
    const headers = {
      'Content-Type': mime,
      'Cache-Control': 'private, no-store',
      'X-Robots-Tag': 'noindex, nofollow, noarchive',
      'Referrer-Policy': 'no-referrer',
      'X-Content-Type-Options': 'nosniff'
    };
    return new Response(request.method === 'HEAD' ? null : bytes, {
      status: 200, headers
    });
  }
};

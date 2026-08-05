/**
 * FJSTI ID JavaScript SDK
 * Usage:
 *   import { FjstiClient } from './fjsti-id.js'
 *   const client = new FjstiClient('http://localhost:8000', 'fjsti_...')
 *   const res = await client.verifyFace(file)
 */

export class FjstiClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.apiKey = apiKey;
  }

  headers(extra = {}) {
    return { "X-API-Key": this.apiKey, ...extra };
  }

  async verifyFace(file, deviceInfo) {
    const fd = new FormData();
    fd.append("file", file);
    if (deviceInfo) fd.append("device_info", deviceInfo);
    const r = await fetch(`${this.baseUrl}/api/v1/face/verify`, {
      method: "POST",
      headers: this.headers(),
      body: fd,
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async getUser(userId) {
    const r = await fetch(`${this.baseUrl}/api/v1/users/${userId}`, {
      headers: this.headers(),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async verifyQr(qrToken) {
    const fd = new FormData();
    fd.append("qr_token", qrToken);
    const r = await fetch(`${this.baseUrl}/api/v1/face/verify-qr`, {
      method: "POST",
      headers: this.headers(),
      body: fd,
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }
}

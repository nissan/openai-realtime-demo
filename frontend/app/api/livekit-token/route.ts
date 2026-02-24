import { createHmac } from "crypto";
import { NextResponse } from "next/server";

function base64url(data: string | Buffer): string {
  const b64 = Buffer.from(data).toString("base64");
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export async function GET() {
  const apiKey = process.env.LIVEKIT_API_KEY ?? "devkey";
  const apiSecret = process.env.LIVEKIT_API_SECRET ?? "secret";
  const roomName = process.env.NEXT_PUBLIC_LIVEKIT_ROOM ?? "tutor-room";
  const identity = `student-${Date.now()}`;

  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "HS256", typ: "JWT" };
  const payload = {
    iss: apiKey,
    sub: identity,
    name: "Student",
    video: { roomJoin: true, room: roomName },
    iat: now,
    exp: now + 3600,
    jti: crypto.randomUUID(),
  };

  const headerB64 = base64url(JSON.stringify(header));
  const payloadB64 = base64url(JSON.stringify(payload));
  const signingInput = `${headerB64}.${payloadB64}`;

  const hmac = createHmac("sha256", apiSecret);
  hmac.update(signingInput);
  const signature = base64url(hmac.digest());

  return NextResponse.json({ token: `${signingInput}.${signature}` });
}

import { NextResponse } from 'next/server';

const ORCHESTRATOR_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8001';

export async function POST(request, context) {
  const params = await context?.params;
  const requestId = params?.requestId;

  if (!requestId) {
    return NextResponse.json({ error: 'Missing requestId' }, { status: 400 });
  }

  const normalizedRequestId = decodeURIComponent(requestId);
  const encodedRequestId = encodeURIComponent(normalizedRequestId);

  try {
    const body = await request.json();
    const res = await fetch(`${ORCHESTRATOR_URL}/leave/requests/${encodedRequestId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10000),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error('[leave.decision] POST error:', err);
    return NextResponse.json({ error: 'Could not decide leave request' }, { status: 500 });
  }
}

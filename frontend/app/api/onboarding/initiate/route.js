import { NextResponse } from 'next/server';

const ORCHESTRATOR_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8001';

export async function POST(request) {
  try {
    const body = await request.json();
    const res = await fetch(`${ORCHESTRATOR_URL}/onboarding/initiate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(15000),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error('[onboarding.initiate] POST error:', err);
    return NextResponse.json({ error: 'Could not initiate onboarding workflow' }, { status: 500 });
  }
}

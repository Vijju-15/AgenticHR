import { NextResponse } from 'next/server';

const ORCHESTRATOR_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8001';

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const tenant_id = searchParams.get('tenant_id') || 'acme_corp';

    const qs = new URLSearchParams({ tenant_id });
    const res = await fetch(`${ORCHESTRATOR_URL}/onboarding/journeys?${qs}`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(10000),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error('[onboarding.journeys] GET error:', err);
    return NextResponse.json({ error: 'Could not fetch onboarding journeys' }, { status: 500 });
  }
}

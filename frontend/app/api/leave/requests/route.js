import { NextResponse } from 'next/server';

const ORCHESTRATOR_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8001';

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const tenant_id = searchParams.get('tenant_id') || 'acme_corp';
  const status = searchParams.get('status') || '';
  const employee_id = searchParams.get('employee_id') || '';
  const employee_email = searchParams.get('employee_email') || '';

  try {
    const qs = new URLSearchParams({ tenant_id });
    if (status) qs.set('status', status);
    if (employee_id) qs.set('employee_id', employee_id);
    if (employee_email) qs.set('employee_email', employee_email);

    const res = await fetch(`${ORCHESTRATOR_URL}/leave/requests?${qs}`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(10000),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error('[leave.requests] GET error:', err);
    return NextResponse.json({ error: 'Could not fetch leave requests' }, { status: 500 });
  }
}
